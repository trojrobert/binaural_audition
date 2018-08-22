import os
import sys
from sys import exit
import shutil

import numpy as np
from keras.callbacks import ModelCheckpoint
from keras.layers import Dense, Input, CuDNNLSTM, Dropout
from keras.models import Model
from keras.optimizers import Adam

from heiner import hyperparameters as hp
from heiner import train_utils as tr_utils
from heiner import utils
from heiner import plotting as plot

from timeit import default_timer as timer

from heiner import use_tmux as use_tmux

from heiner.my_tmuxprocess import TmuxProcess
import datetime

def run_hcomb(h, ID, hcm, model_dir, INTERMEDIATE_PLOTS, GLOBAL_GRADIENT_NORM_PLOT):
    # LOGGING
    sys.stdout = utils.UnbufferedLogAndPrint(os.path.join(model_dir, 'logfile'), sys.stdout)
    sys.stderr = utils.UnbufferedLogAndPrint(os.path.join(model_dir, 'errorfile'), sys.stderr)

    ################################################# HCOMB

    print(5 * '\n' + 'Hyperparameter combination...\n')
    print(h.__dict__)

    ################################################# CROSS VALIDATION
    start = timer()

    # METRICS
    NUMBER_OF_CLASSES = 13
    val_class_accuracies_over_folds = [[0] * NUMBER_OF_CLASSES] * len(h.ALL_FOLDS)
    val_acc_over_folds = [0] * len(h.ALL_FOLDS)

    print(5 * '\n' + 'Starting Cross Validation...\n')

    for i_val_fold, val_fold in enumerate(h.VAL_FOLDS):
        model_save_dir = os.path.join(model_dir, 'val_fold{}'.format(val_fold))
        os.makedirs(model_save_dir, exist_ok=True)

        TRAIN_FOLDS = list(set(h.ALL_FOLDS).difference({val_fold}))

        val_fold_str = 'val_fold: {} ({} / {})'.format(val_fold, i_val_fold + 1, len(h.VAL_FOLDS))

        ################################################# MODEL DEFINITION

        print('\nBuild model...\n')

        x = Input(batch_shape=(h.BATCH_SIZE, h.TIME_STEPS, h.N_FEATURES), name='Input', dtype='float32')
        y = x

        # Input dropout
        y = Dropout(h.INPUT_DROPOUT, noise_shape=(h.BATCH_SIZE, 1, h.N_FEATURES))(y)
        for units in h.UNITS_PER_LAYER_LSTM:
            y = CuDNNLSTM(units, return_sequences=True, stateful=True)(y)

            # LSTM Output dropout
            y = Dropout(h.LSTM_OUTPUT_DROPOUT, noise_shape=(h.BATCH_SIZE, 1, units))(y)
        for units in h.UNITS_PER_LAYER_MLP:
            if units != h.N_CLASSES:
                y = Dense(units, activation='relu')(y)
            else:
                y = Dense(units, activation='sigmoid')(y)

            # MLP Output dropout but not last layer
            if units != h.N_CLASSES:
                y = Dropout(h.MLP_OUTPUT_DROPOUT, noise_shape=(h.BATCH_SIZE, 1, units))(y)
        model = Model(x, y)

        model.summary()
        print(5 * '\n')

        my_loss = utils.my_loss_builder(h.MASK_VAL, utils.get_loss_weights(TRAIN_FOLDS, h.TRAIN_SCENES, h.LABEL_MODE))

        ################################################# LOAD CHECKPOINTED MODEL

        latest_weights_path, epochs_finished, val_acc = utils.latest_training_state(model_save_dir)
        if latest_weights_path is not None:
            model.load_weights(latest_weights_path)

            if h.epochs_finished[i_val_fold] != epochs_finished:
                print('MISMATCH: Latest state in hyperparameter combination list is different to checkpointed state.')
                h.epochs_finished[i_val_fold] = epochs_finished
                h.val_acc[i_val_fold] = val_acc
                hcm.replace_at_id(ID, h)

        ################################################# COMPILE MODEL

        adam = Adam(lr=h.LEARNING_RATE, clipnorm=1.)
        model.compile(optimizer=adam, loss=my_loss, metrics=None)

        print('\nModel compiled.\n')

        ################################################# DATA LOADER
        use_multiprocessing = False
        BUFFER = utils.get_buffer_size_wrt_time_steps(h.TIME_STEPS)
        BUFFER = int(BUFFER // 2) - 5 if use_multiprocessing else BUFFER
        train_loader, val_loader = tr_utils.create_dataloaders(h.LABEL_MODE, TRAIN_FOLDS, h.TRAIN_SCENES, h.BATCH_SIZE,
                                                               h.TIME_STEPS, h.MAX_EPOCHS, h.N_FEATURES, h.N_CLASSES,
                                                               [val_fold], h.VAL_STATEFUL,
                                                               BUFFER=BUFFER, use_multiprocessing=use_multiprocessing)

        ################################################# CALLBACKS
        model_ckp_last = ModelCheckpoint(os.path.join(model_save_dir,
                                                      'model_ckp_epoch_{epoch:02d}-val_acc_{val_final_acc:.3f}.hdf5'),
                                         verbose=1, monitor='val_final_acc')
        model_ckp_last.set_model(model)
        model_ckp_best = ModelCheckpoint(os.path.join(model_save_dir,
                                                      'best_model_ckp_epoch_{epoch:02d}-val_acc_{val_final_acc:.3f}.hdf5'),
                                         verbose=1, monitor='val_final_acc', save_best_only=True)
        model_ckp_best.set_model(model)

        args = [h.OUTPUT_THRESHOLD, h.MASK_VAL, h.MAX_EPOCHS, val_fold_str, GLOBAL_GRADIENT_NORM_PLOT, h.RECURRENT_DROPOUT, h.METRIC]

        # training phase
        train_phase = tr_utils.Phase('train', model, train_loader, BUFFER, *args)

        # validation phase
        val_phase = tr_utils.Phase('val', model, val_loader, BUFFER, *args)

        # needed for early stopping
        best_val_acc = -1
        best_epoch = 0
        epochs_without_improvement = 0

        for e in range(h.epochs_finished[i_val_fold], h.MAX_EPOCHS):

            train_phase.run()
            val_phase.run()

            tr_utils.update_latest_model_ckp(model_ckp_last, model_save_dir, e, val_phase.accs[-1])
            tr_utils.update_best_model_ckp(model_ckp_best, model_save_dir, e, val_phase.accs[-1])

            metrics = {'metric': h.METRIC,
                       'train_losses': np.array(train_phase.losses),
                       'train_accs': np.array(train_phase.accs),
                       'val_losses': np.array(val_phase.losses),
                       'val_accs': np.array(val_phase.accs),
                       'val_accs_bac2': np.array(val_phase.accs_bac2),
                       'val_class_accs': np.array(val_phase.class_accs),
                       'val_class_accs_bac2': np.array(val_phase.class_accs_bac2),
                       'val_class_scene_accs': np.array(val_phase.class_scene_accs),
                       'val_class_scene_accs_bac2': np.array(val_phase.class_scene_accs_bac2),
                       'val_scene_accs': np.array(val_phase.scene_accs),
                       'val_scene_accs_bac2': np.array(val_phase.scene_accs_bac2),
                       'train_class_sens_spec': np.array(train_phase.sens_spec_class_scene),
                       'val_sens_spec_class_scene': np.array(val_phase.sens_spec_class_scene),
                       'val_sens_spec_class': np.array(val_phase.sens_spec_class)}

            if GLOBAL_GRADIENT_NORM_PLOT:
                metrics['global_gradient_norm'] = np.array(train_phase.global_gradient_norms)

            utils.pickle_metrics(metrics, model_save_dir)

            if val_phase.accs[-1] > best_val_acc:
                best_val_acc = val_phase.accs[-1]
                epochs_without_improvement = 0
                best_epoch = e + 1
            else:
                epochs_without_improvement += 1

            hcm.finish_epoch(ID, h, val_phase.accs[-1], val_fold - 1, best_epoch, (timer() - start)/60)

            if INTERMEDIATE_PLOTS:
                plot.plot_metrics(metrics, model_save_dir)

            if GLOBAL_GRADIENT_NORM_PLOT:
                plot.plot_global_gradient_norm(np.array(train_phase.global_gradient_norms), model_save_dir)

            # early stopping
            if epochs_without_improvement > h.PATIENCE_IN_EPOCHS and h.PATIENCE_IN_EPOCHS > 0:
                break

        val_class_accuracies_over_folds[val_fold - 1] = val_phase.class_accs[-1]
        val_acc_over_folds[val_fold - 1] = val_phase.accs[-1]

        metrics = {'val_class_accs_over_folds': np.array(val_class_accuracies_over_folds),
                   'val_acc_over_folds': np.array(val_acc_over_folds)}
        utils.pickle_metrics(metrics, model_dir)

        if INTERMEDIATE_PLOTS:
            plot.plot_metrics(metrics, model_save_dir)

    ################################################# CROSS VALIDATION: MEAN AND VARIANCE

    val_class_accuracies_mean_over_folds = np.mean(np.array(val_class_accuracies_over_folds), axis=0)
    val_class_accuracies_var_over_folds = np.var(np.array(val_class_accuracies_over_folds), axis=0)
    val_acc_mean_over_folds = np.mean(val_acc_over_folds)
    val_acc_var_over_folds = np.var(val_acc_over_folds)

    metrics = {'val_class_accs_over_folds': np.array(val_class_accuracies_over_folds),
               'val_class_accs_mean_over_folds': np.array(val_class_accuracies_mean_over_folds),
               'val_class_accs_var_over_folds': np.array(val_class_accuracies_var_over_folds),
               'val_acc_over_folds': np.array(val_acc_over_folds),
               'val_acc_mean_over_folds': np.array(val_acc_mean_over_folds),
               'val_acc_var_over_folds': np.array(val_acc_var_over_folds)}
    utils.pickle_metrics(metrics, model_dir)

    hcm.finish_hcomb(ID, h, val_acc_mean_over_folds, np.sqrt(val_class_accuracies_var_over_folds), timer() - start)

    if INTERMEDIATE_PLOTS:
        plot.plot_metrics(metrics, model_dir)


def run_gpu(gpu, save_path, reset_hcombs, INTERMEDIATE_PLOTS=True, GLOBAL_GRADIENT_NORM_PLOT=True):

    hcm = hp.HCombManager(save_path)

    os.environ['CUDA_VISIBLE_DEVICES'] = gpu

    while True:
        h = hcm.poll_hcomb()
        if h is None:
            return gpu

        ID, h.__dict__, already_contained = hcm.get_hcomb_id(h)
        if h.finished:
            print('Hyperparameter Combination for this model version already evaluated. ABORT.')
            continue
        hcm.set_hostname_and_batch_size(ID, h, *utils.get_hostname_batch_size_wrt_time_steps(h.TIME_STEPS))

        model_dir = os.path.join(save_path, 'stage' + str(h.STAGE), 'hcomb_' + str(ID))

        if reset_hcombs and already_contained and os.path.exists(model_dir):
            shutil.rmtree(model_dir)

        os.makedirs(model_dir, exist_ok=True)
        h.save_to_dir(model_dir)

        if use_tmux.use_tmux:

            p_hcomb = TmuxProcess(session_name=use_tmux.session_name, target=run_hcomb,
                                  args=(h, ID, hcm, model_dir, INTERMEDIATE_PLOTS, GLOBAL_GRADIENT_NORM_PLOT),
                                  name='gpu{}_run_hcomb_{}'.format(gpu, ID))
            print('Running hcomb_{} on GPU {}.'.format(ID, gpu))
            print('Start: {}'.format(datetime.datetime.now().isoformat()))
            p_hcomb.start()
            p_hcomb.join()
            print('Exitcode {}.'.format(p_hcomb.exitcode))
            if p_hcomb.exitcode == 1:
                print('Aborted by CTRL + C.')
            print('End: {}\n'.format(datetime.datetime.now().isoformat()))

        else:
            run_hcomb(h, ID, hcm, model_dir, INTERMEDIATE_PLOTS, GLOBAL_GRADIENT_NORM_PLOT)