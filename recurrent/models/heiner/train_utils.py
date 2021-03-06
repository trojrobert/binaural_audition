import copy
import glob
import os
import time

import numpy as np
from keras import backend as K
from keras.layers import CuDNNLSTM
from keras.utils.data_utils import GeneratorEnqueuer
from skimage.util.shape import view_as_blocks
from scipy.special import expit as sigmoid

import accuracy_utils as acc_u
import model_extension as m_ext
from dataloader import DataLoader


def calculate_sample_weights_batch(y_scene_instance_ids, file_lengths_dict, scene_instance_ids_dict, mode,
                                   no_new_weighting=False):
    if no_new_weighting:
        return None

    weights_per_scene = acc_u.get_scene_weights(mode)
    weights_per_scene /= np.mean(weights_per_scene)

    # commented out masking because masked time steps already dealed with in my_loss_builder
    # here is no class-wise masking possible

    # masked_time_steps = (y_scene_instance_ids != mask_val).astype(np.float32)
    scene_instance_ids_in_batch = y_scene_instance_ids.astype(np.int)
    weights = weights_per_scene[:, 0][((scene_instance_ids_in_batch // 1e4) - 1).astype(np.int)]  # * masked_time_steps

    # remark: performance improvement possible by doing the following dict inversion
    #         only once and not per call of this function which is done in each batch
    inv_scene_instance_ids_dict = {v: k for k, v in scene_instance_ids_dict.items()}
    mean_inv_file_lengths = 0.00027947386527248043 # mean inv filelength (all folds), cf. file_lengths_dict

    for sid in np.unique(scene_instance_ids_in_batch):
        if sid == -1.0:
            continue

        w_length = (1. / file_lengths_dict[inv_scene_instance_ids_dict[sid]]) / mean_inv_file_lengths
        weights[scene_instance_ids_in_batch == sid] *= w_length

    return weights


def create_generator(dloader):
    while True:
        # ret is either b_x, b_y or b_x, b_y, keep_states
        ret = dloader.next_batch()
        if ret[0] is None or ret[1] is None:
            return
        yield ret


def create_generator_multithreading(dloader):
    standard_gen = create_generator(dloader)
    dloader_enqueuer = GeneratorEnqueuer(standard_gen, use_multiprocessing=False)
    dloader_enqueuer.start(workers=1, max_queue_size=1)
    return dloader_enqueuer.get()


def create_train_dataloader(LABEL_MODE, TRAIN_FOLDS, TRAIN_SCENES, BATCHSIZE, TIMESTEPS, EPOCHS, NFEATURES, NCLASSES,
                            BUFFER, use_multithreading=True, input_standardization=True):
    train_loader = DataLoader('train', LABEL_MODE, TRAIN_FOLDS, TRAIN_SCENES, batchsize=BATCHSIZE,
                              timesteps=TIMESTEPS, epochs=EPOCHS, features=NFEATURES, classes=NCLASSES,
                              buffer=BUFFER, use_multithreading=use_multithreading,
                              input_standardization=input_standardization)
    train_loader_len = train_loader.len()
    print('Number of batches per epoch (training): ' + str(train_loader_len))

    print('Data efficiency per epoch (training): ' + str(train_loader.data_efficiency()))

    return train_loader


def create_val_dataloader(LABEL_MODE, TRAIN_SCENES, BATCHSIZE, TIMESTEPS, EPOCHS, NFEATURES, NCLASSES, VAL_FOLDS,
                          VAL_STATEFUL, BUFFER, use_multithreading=True, input_standardization=True):
    val_loader = DataLoader('val', LABEL_MODE, VAL_FOLDS, TRAIN_SCENES, epochs=EPOCHS, batchsize=BATCHSIZE,
                            timesteps=TIMESTEPS, features=NFEATURES, classes=NCLASSES, val_stateful=VAL_STATEFUL,
                            buffer=BUFFER, use_multithreading=use_multithreading,
                            input_standardization=input_standardization)

    val_loader_len = val_loader.len()
    print('Number of batches per epoch (validation): ' + str(val_loader_len))

    print('Data efficiency per epoch (validation): ' + str(val_loader.data_efficiency()))

    return val_loader


def create_test_dataloader(LABEL_MODE, input_standardization=True, val_fold3_as_test=False):
    test_loader = DataLoader('test', LABEL_MODE, -1, -1, input_standardization=input_standardization,
                             val_fold3_as_test=val_fold3_as_test)

    test_loader_len = test_loader.len()
    print('Number of batches per epoch (test): ' + str(test_loader_len))

    print('Data efficiency per epoch (test): ' + str(test_loader.data_efficiency()))

    return test_loader


def create_dataloaders(LABEL_MODE, TRAIN_FOLDS, TRAIN_SCENES, BATCHSIZE, TIMESTEPS, EPOCHS, NFEATURES, NCLASSES,
                       VAL_FOLDS, VAL_STATEFUL, BUFFER, use_multithreading=True, subsample_time_steps=False):
    train_loader = create_train_dataloader(LABEL_MODE, TRAIN_FOLDS, TRAIN_SCENES, BATCHSIZE, TIMESTEPS, EPOCHS,
                                           NFEATURES, NCLASSES, BUFFER, use_multithreading=use_multithreading)

    time_steps = TIMESTEPS if not subsample_time_steps else TIMESTEPS // 2
    val_loader = create_val_dataloader(LABEL_MODE, TRAIN_SCENES, BATCHSIZE, time_steps, EPOCHS, NFEATURES, NCLASSES,
                                       VAL_FOLDS, VAL_STATEFUL, BUFFER, use_multithreading=use_multithreading)

    return train_loader, val_loader


def update_best_model_ckp(best_model_ckp_last, model_save_dir, e, acc):
    best_model_ckp_last.on_epoch_end(e, logs={'val_final_acc': acc})
    created_best_checkpoints = glob.glob(os.path.join(model_save_dir, 'best_model_ckp_epoch*.hdf5'))
    if len(created_best_checkpoints) > 1:  # new one is better than the old
        created_best_checkpoints = sorted(created_best_checkpoints)
        if os.path.exists(created_best_checkpoints[0]):
            os.remove(created_best_checkpoints[0])
        else:
            raise ValueError('Model checkpoint found by glob but is not a file.')


def update_latest_model_ckp(model_ckp_last, model_save_dir, e, acc):
    created_checkpoints = glob.glob(os.path.join(model_save_dir, 'model_ckp_epoch*.hdf5'))
    if len(created_checkpoints) > 1:
        raise ValueError('Just one latest Model checkpoint besides the best should exist. N:{} exist.'.format(
            len(created_checkpoints)))
    if len(created_checkpoints) == 1:
        if os.path.exists(created_checkpoints[0]):
            os.remove(created_checkpoints[0])
        else:
            raise ValueError('Model checkpoint found by glob but is not a file.')

    model_ckp_last.on_epoch_end(e, logs={'val_final_acc': acc})


class TestPhase:

    def __init__(self, model, dloader, OUTPUT_THRESHOLD, MASK_VAL, EPOCHS, val_fold_str, model_save_dir,
                 metric='BAC2',
                 ret=('final', 'per_class', 'per_class_scene', 'per_scene'),
                 code_test_mode=False):
        self.prefix = 'test'

        self.model_save_dir = model_save_dir

        self.model = model
        self.dloader = dloader

        self.OUTPUT_THRESHOLD = OUTPUT_THRESHOLD
        self.MASK_VAL = MASK_VAL
        self.EPOCHS = EPOCHS

        self.val_fold_str = val_fold_str

        self.e = 0

        self.metric = metric
        self.ret = ret

        if dloader.use_multithreading:
            self.gen = create_generator_multithreading(dloader)
        else:
            self.gen = create_generator(dloader)
        self.dloader_len = dloader.len()

        self.accs = []
        self.class_accs = []
        self.accs_bac2 = []
        self.class_accs_bac2 = []

        self.class_scene_accs = []
        self.class_scene_accs_bac2 = []

        self.scene_accs = []
        self.scene_accs_bac2 = []

        self.sens_spec_class_scene = []
        self.sens_spec_class = []

        self.code_test_mode = code_test_mode

    @property
    def epoch_str(self):
        return 'epoch: {:{prec}} / {:{prec}}'.format(self.e + 1, self.EPOCHS, prec=len(str(self.EPOCHS)))

    def run(self):
        scene_instance_id_metrics_dict = dict()

        for iteration in range(1, self.dloader_len[self.e] + 1):
            self.model.reset_states()

            iteration_start_time = time.time()
            it_str = '{}_iteration: {:{prec}} / {:{prec}}'.format(self.prefix, iteration, self.dloader_len[self.e],
                                                                  prec=len(str(self.dloader_len[self.e])))

            iteration_start_time_data_loading = time.time()

            b_x, b_y = next(self.gen)

            elapsed_time_data_loading = time.time() - iteration_start_time_data_loading

            iteration_start_time_tf_graph = time.time()
            tf_graph_verbose = False
            tf_graph_time_spent_str = ''

            out_logits = self.model.predict_on_batch(b_x)
            y_pred = sigmoid(out_logits, out=out_logits)
            y_pred = np.greater_equal(y_pred, self.OUTPUT_THRESHOLD, out=y_pred)

            elapsed_time_tf_graph = time.time() - iteration_start_time_tf_graph

            iteration_start_time_accuracy_metrics = time.time()
            acc_u.calculate_class_accuracies_metrics_per_scene_instance_in_batch(scene_instance_id_metrics_dict,
                                                                                 y_pred, b_y, self.MASK_VAL)
            elapsed_time_accuracy_metrics = time.time() - iteration_start_time_accuracy_metrics
            elapsed_time = time.time() - iteration_start_time
            time_spent_str = 'time spent: {} (data loading: {}, tf graph: {}{}, accuracy metrics: {})'.format(
                time.strftime("%H:%M:%S", time.gmtime(elapsed_time)),
                time.strftime("%H:%M:%S", time.gmtime(elapsed_time_data_loading)),
                time.strftime("%H:%M:%S", time.gmtime(elapsed_time_tf_graph)),
                tf_graph_time_spent_str if tf_graph_verbose else '',
                time.strftime("%H:%M:%S", time.gmtime(elapsed_time_accuracy_metrics))
            )
            loss_log_str = '{:<20}  {:<20}  {:<20}  {}'.format(self.val_fold_str, self.epoch_str, it_str,
                                                               time_spent_str)
            print(loss_log_str)

        scene_instance_id_metrics_dict_counts = copy.deepcopy(scene_instance_id_metrics_dict) \
            if self.code_test_mode else None

        with open(os.path.join(self.model_save_dir, 'scene_instance_id_metrics_dict_counts.pickle'), 'wb') as handle:
            import pickle
            pickle.dump(scene_instance_id_metrics_dict_counts, handle, protocol=pickle.HIGHEST_PROTOCOL)

        # TODO: can get a mismatch here, as number of returned values may change depending on parameter 'ret'
        final_acc, final_acc_bac2, class_accuracies, class_accuracies_bac2, \
        class_scene_accuracies, class_scene_accuracies_bac2, \
        scene_accuracies, scene_accuracies_bac2, \
        sens_spec_class_scene, sens_spec_class = \
            acc_u.val_accuracy(scene_instance_id_metrics_dict, metric=('BAC', 'BAC2'), ret=self.ret, mode='test')
        self.class_accs.append(class_accuracies)
        self.accs_bac2.append(final_acc_bac2)
        self.class_accs_bac2.append(class_accuracies_bac2)
        self.class_scene_accs.append(class_scene_accuracies)
        self.class_scene_accs_bac2.append(class_scene_accuracies_bac2)
        self.scene_accs.append(scene_accuracies)
        self.scene_accs_bac2.append(scene_accuracies_bac2)
        self.sens_spec_class.append(sens_spec_class)
        self.accs.append(final_acc)
        self.sens_spec_class_scene.append(sens_spec_class_scene)

        acc_str = '{}_accuracy: {}'.format(self.prefix, final_acc)
        acc_log_str = '{:<20}  {:<20}  {:<20}  {:<20}'.format(self.val_fold_str, self.epoch_str, '', acc_str)
        print(acc_log_str)

        self.e += 1

        return False, scene_instance_id_metrics_dict_counts


class Phase:

    def __init__(self, train_or_val, model, dloader, BUFFER, OUTPUT_THRESHOLD, MASK_VAL, EPOCHS, val_fold_str,
                 calc_global_gradient_norm, recurrent_dropout=0.,
                 metric='BAC',
                 ret=('final', 'per_class', 'per_class_scene', 'per_scene'),
                 code_test_mode=False,
                 no_new_weighting=False, changbin_recurrent_dropout=False,
                 subsample_time_steps=False):

        self.subsample_time_steps = False

        self.prefix = train_or_val
        if train_or_val == 'train':
            self.train = True
            self.subsample_time_steps = subsample_time_steps
        elif train_or_val == 'val':
            self.train = False
        else:
            raise ValueError('unknown train_or_val: {}'.format(train_or_val))

        self.recurrent_dropout = min(1., max(0., recurrent_dropout))

        if self.train and 0. < self.recurrent_dropout <= 1.:
            self.apply_recurrent_dropout = True
        else:
            self.apply_recurrent_dropout = False

        self.model = model
        self.dloader = dloader
        self.BUFFER = BUFFER
        self.e = 0
        self.OUTPUT_THRESHOLD = OUTPUT_THRESHOLD
        self.MASK_VAL = MASK_VAL
        self.EPOCHS = EPOCHS

        self.val_fold_str = val_fold_str

        self.calc_global_gradient_norm = calc_global_gradient_norm

        self.metric = metric
        self.ret = ret

        if dloader.use_multithreading:
            self.gen = create_generator_multithreading(dloader)
        else:
            self.gen = create_generator(dloader)
        self.dloader_len = dloader.len()

        self.losses = []
        self.accs = []
        self.class_accs = []
        self.accs_bac2 = []
        self.class_accs_bac2 = []

        self.class_scene_accs = []
        self.class_scene_accs_bac2 = []

        self.scene_accs = []
        self.scene_accs_bac2 = []

        self.sens_spec_class_scene = []
        self.sens_spec_class = []

        self.global_gradient_norms = []

        self.code_test_mode = code_test_mode

        self.no_new_weighting = no_new_weighting

        self.changbin_recurrent_dropout = changbin_recurrent_dropout
        self.dropout_applied_once = False

    def resume_from_epoch(self, resume_epoch):
        if hasattr(self.dloader, 'act_epoch'):
            for _ in range(self.e, resume_epoch - 1):
                _ = self.dloader.next_epoch()
                self.e += 1
            assert self.dloader.act_epoch == resume_epoch
        else:
            raise ValueError('Can resume for training or validation loader only.')

    @property
    def epoch_str(self):
        return 'epoch: {:{prec}} / {:{prec}}'.format(self.e + 1, self.EPOCHS, prec=len(str(self.EPOCHS)))

    def _changbin_recurrent_dropout(self):
        def _drop_in_recurrent_kernel(rk):
            # print('Zeros in weight matrix before dropout: {}'.format(np.sum(rk == 0)))

            # rk_s = rk.shape
            # mask = np.random.binomial(1., 1-self.recurrent_dropout, (rk_s[0], 1))
            # mask = np.tile(mask, rk_s[0]*4)
            # rk = rk * mask * (1./(1-self.recurrent_dropout))

            ########################## NEW (like in https://arxiv.org/pdf/1708.02182.pdf)

            rk_s = rk.shape
            mask = np.random.binomial(1., 1 - self.recurrent_dropout, rk_s)
            rk *= mask
            rk *= (1. / (1 - self.recurrent_dropout))

            # print('Zeros in weight matrix after dropout: {}'.format(np.sum(rk == 0)))
            # print('Weight matrix norm after dropout: {}'.format(np.linalg.norm(rk)))

            return rk

        for layer in self.model.layers:
            if type(layer) is CuDNNLSTM:
                rk0 = _drop_in_recurrent_kernel(K.get_value(layer.weights[0]))
                rk1 = _drop_in_recurrent_kernel(K.get_value(layer.weights[1]))
                rk2 = _drop_in_recurrent_kernel(K.get_value(layer.weights[2]))
                K.set_value(layer.weights[0], rk0)
                K.set_value(layer.weights[1], rk1)
                K.set_value(layer.weights[2], rk2)

    def _recurrent_dropout(self):
        def _drop_in_recurrent_kernel(rk):
            # print('Zeros in weight matrix before dropout: {}'.format(np.sum(rk == 0)))

            # rk_s = rk.shape
            # mask = np.random.binomial(1., 1-self.recurrent_dropout, (rk_s[0], 1))
            # mask = np.tile(mask, rk_s[0]*4)
            # rk = rk * mask * (1./(1-self.recurrent_dropout))

            ########################## NEW (like in https://arxiv.org/pdf/1708.02182.pdf)

            rk_s = rk.shape
            mask = np.random.binomial(1., 1 - self.recurrent_dropout, rk_s)
            rk *= mask
            rk *= (1. / (1 - self.recurrent_dropout))

            # print('Zeros in weight matrix after dropout: {}'.format(np.sum(rk == 0)))
            # print('Weight matrix norm after dropout: {}'.format(np.linalg.norm(rk)))

            return rk, mask

        original_weights_and_masks = []
        for layer in self.model.layers:
            if type(layer) is CuDNNLSTM:
                rk = K.get_value(layer.weights[1])
                rk_old = np.copy(rk)
                rk, mask = _drop_in_recurrent_kernel(rk)
                original_weights_and_masks.append((rk_old, mask))
                K.set_value(layer.weights[1], rk)

        return original_weights_and_masks

    def _load_original_weights_updated(self, original_weights_and_masks):
        i = 0
        for layer in self.model.layers:
            if type(layer) is CuDNNLSTM:
                rk = K.get_value(layer.weights[1])
                mask = original_weights_and_masks[i][1]
                original_weights_updated = original_weights_and_masks[i][0] + (
                            rk - (1 / (1 - self.recurrent_dropout)) * original_weights_and_masks[i][0]) \
                                           * mask
                K.set_value(layer.weights[1], original_weights_updated)
                i += 1

    def run(self):
        self.model.reset_states()

        scene_instance_id_metrics_dict = dict()

        for iteration in range(1, self.dloader_len[self.e] + 1):
            iteration_start_time = time.time()
            it_str = '{}_iteration: {:{prec}} / {:{prec}}'.format(self.prefix, iteration, self.dloader_len[self.e],
                                                                  prec=len(str(self.dloader_len[self.e])))

            is_val_loader_stateful = not self.train and self.dloader.val_stateful

            iteration_start_time_data_loading = time.time()
            keep_states = None
            if is_val_loader_stateful:
                b_x, b_y, keep_states = next(self.gen)
            else:
                b_x, b_y = next(self.gen)
            if self.subsample_time_steps:
                b_x_old_shape = b_x.shape

                b_x_block_shape = (b_x.shape[0],) + (2,) + b_x.shape[2:]
                # after squeezing: n_block x batch_size x size_block_time_steps (2) * feats
                # swapping: batch_size x n_block x size_block_time_steps (2) * feats
                # n_block should remain, because these are the subsampled time steps
                b_x_blocks = view_as_blocks(b_x, block_shape=b_x_block_shape).squeeze().swapaxes(0, 1)
                b_x = b_x_blocks.mean(axis=2)

                b_x_new_shape = (b_x_old_shape[0], b_x_old_shape[1]//2, b_x_old_shape[2])
                assert b_x_new_shape == b_x.shape, 'Shapes are not matching after subsampling.'

                b_y_labels = b_y[:, :, :, 0]
                b_y_scene_ind = b_y[:, :, :, 1]
                b_y_labels_old_shape = b_y_labels.shape

                assert b_y_scene_ind.shape == b_y_labels_old_shape, 'Shapes of labels and scene indices do not match.'

                b_y_labels_block_shape = (b_y_labels.shape[0],) + (2,) + b_y_labels.shape[2:]
                # after squeezing: n_block x batch_size x size_block_time_steps (2) * labels
                # swapping: batch_size x n_block x size_block_time_steps (2) * labels
                # n_block should remain, because these are the subsampled time steps
                b_y_labels_blocks = view_as_blocks(b_y_labels,
                                                  block_shape=b_y_labels_block_shape).squeeze().swapaxes(0,1)
                b_y_scene_ind_blocks = view_as_blocks(b_y_scene_ind,
                                                     block_shape=b_y_labels_block_shape).squeeze().swapaxes(0,1)

                b_y_labels = b_y_labels_blocks.max(axis=2)
                b_y_max_indices = b_y_labels_blocks.swapaxes(2, -1).argmax(axis=-1)

                def reshape_based(x, m):
                    shp = x.shape[:-1]
                    n_ele = np.prod(shp)
                    return x.reshape(n_ele, -1)[np.arange(n_ele), m.ravel()].reshape(shp)

                b_y_scene_ind = reshape_based(b_y_scene_ind_blocks.swapaxes(2, -1), b_y_max_indices).swapaxes(2, -1)

                b_y_labels_new_shape = (b_y_labels_old_shape[0], b_y_labels_old_shape[1] // 2, b_y_labels_old_shape[2])
                assert b_y_labels_new_shape == b_y_labels.shape, 'Shapes are not matching after subsampling (labels).'
                assert b_y_labels_new_shape == b_y_scene_ind.shape, \
                    'Shapes are not matching after subsampling (scene ind).'

                b_y = np.stack((b_y_labels, b_y_scene_ind), axis=-1)

            if not (b_x != 0).any() or not (b_y[:, :, :, 0] != -1).any():
                break

            elapsed_time_data_loading = time.time() - iteration_start_time_data_loading

            iteration_start_time_tf_graph = time.time()
            tf_graph_verbose = False
            tf_graph_time_spent_str = ''
            if self.train:
                original_weights_and_masks = None

                iteration_start_time_tf_graph_apply_dropout = time.time()
                if self.apply_recurrent_dropout:
                    if self.changbin_recurrent_dropout:
                        # changbin applies dropout just once in the beginning
                        if not self.dropout_applied_once:
                            self._changbin_recurrent_dropout()
                            self.dropout_applied_once = True
                    else:
                        original_weights_and_masks = self._recurrent_dropout()
                elapsed_time_tf_graph_apply_dropout = time.time() - iteration_start_time_tf_graph_apply_dropout

                iteration_start_time_tf_graph_call = time.time()
                loss, out_logits, gradient_norm = m_ext.train_and_predict_on_batch(
                    self.model, b_x, b_y[:, :, :, 0],
                    sample_weight=calculate_sample_weights_batch(
                        b_y[:, :, 0, 1],
                        self.dloader.length_dict_(),
                        self.dloader.scene_instance_ids_dict_(),
                        'train',
                        no_new_weighting=self.no_new_weighting
                    ),
                    calc_global_gradient_norm=self.calc_global_gradient_norm
                )

                if np.isnan(loss):
                    return True, None

                y_pred = sigmoid(out_logits, out=out_logits)
                y_pred = np.greater_equal(y_pred, self.OUTPUT_THRESHOLD, out=y_pred)

                elapsed_time_tf_graph_call = time.time() - iteration_start_time_tf_graph_call

                if self.calc_global_gradient_norm:
                    self.global_gradient_norms.append(gradient_norm)

                iteration_start_time_tf_graph_dropout_load_original = time.time()
                if self.apply_recurrent_dropout and not self.changbin_recurrent_dropout:
                    self._load_original_weights_updated(original_weights_and_masks)
                    del original_weights_and_masks
                elapsed_time_tf_graph_dropout_load_original = time.time() - \
                                                              iteration_start_time_tf_graph_dropout_load_original

                tf_graph_time_spent_str = ' (apply drop: {}, train_predict: {}, drop load original: {})' \
                    .format(
                    time.strftime("%H:%M:%S", time.gmtime(elapsed_time_tf_graph_apply_dropout)),
                    time.strftime("%H:%M:%S", time.gmtime(elapsed_time_tf_graph_call)),
                    time.strftime("%H:%M:%S", time.gmtime(elapsed_time_tf_graph_dropout_load_original))
                )
            else:
                loss, out_logits = m_ext.test_and_predict_on_batch(
                    self.model, b_x, b_y[:, :, :, 0],
                    sample_weight=calculate_sample_weights_batch(
                        b_y[:, :, 0, 1],
                        self.dloader.length_dict_(),
                        self.dloader.scene_instance_ids_dict_(),
                        'val',
                        no_new_weighting=self.no_new_weighting
                    )
                )

                if np.isnan(loss):
                    return True, None

                y_pred = sigmoid(out_logits, out=out_logits)
                y_pred = np.greater_equal(y_pred, self.OUTPUT_THRESHOLD, out=y_pred)

            self.losses.append(loss)
            elapsed_time_tf_graph = time.time() - iteration_start_time_tf_graph

            iteration_start_time_accuracy_metrics = time.time()
            acc_u.calculate_class_accuracies_metrics_per_scene_instance_in_batch(scene_instance_id_metrics_dict,
                                                                                 y_pred, b_y, self.MASK_VAL)
            elapsed_time_accuracy_metrics = time.time() - iteration_start_time_accuracy_metrics
            elapsed_time = time.time() - iteration_start_time
            time_spent_str = 'time spent: {} (data loading: {}, tf graph: {}{}, accuracy metrics: {})'.format(
                time.strftime("%H:%M:%S", time.gmtime(elapsed_time)),
                time.strftime("%H:%M:%S", time.gmtime(elapsed_time_data_loading)),
                time.strftime("%H:%M:%S", time.gmtime(elapsed_time_tf_graph)),
                tf_graph_time_spent_str if tf_graph_verbose else '',
                time.strftime("%H:%M:%S", time.gmtime(elapsed_time_accuracy_metrics))
            )
            loss_str = 'loss: {}'.format(loss)
            loss_log_str = '{:<20}  {:<20}  {:<20}  {:<26}  {}'.format(self.val_fold_str, self.epoch_str, it_str,
                                                                       loss_str, time_spent_str)
            print(loss_log_str)

            if not self.train:
                if not self.dloader.val_stateful:
                    self.model.reset_states()
                else:
                    m_ext.reset_with_keep_states(self.model, keep_states)

        if self.train:
            final_acc, sens_spec_class_scene = acc_u.train_accuracy(scene_instance_id_metrics_dict, metric=self.metric)

            scene_instance_id_metrics_dict_counts = None
        else:

            scene_instance_id_metrics_dict_counts = copy.deepcopy(scene_instance_id_metrics_dict) \
                if self.code_test_mode else None

            # TODO: can get a mismatch here, as number of returned values may change depending on parameter 'ret'
            final_acc, final_acc_bac2, class_accuracies, class_accuracies_bac2, \
            class_scene_accuracies, class_scene_accuracies_bac2, \
            scene_accuracies, scene_accuracies_bac2, \
            sens_spec_class_scene, sens_spec_class = \
                acc_u.val_accuracy(scene_instance_id_metrics_dict, metric=('BAC', 'BAC2'), ret=self.ret)
            self.class_accs.append(class_accuracies)
            self.accs_bac2.append(final_acc_bac2)
            self.class_accs_bac2.append(class_accuracies_bac2)
            self.class_scene_accs.append(class_scene_accuracies)
            self.class_scene_accs_bac2.append(class_scene_accuracies_bac2)
            self.scene_accs.append(scene_accuracies)
            self.scene_accs_bac2.append(scene_accuracies_bac2)
            self.sens_spec_class.append(sens_spec_class)
        self.accs.append(final_acc)
        self.sens_spec_class_scene.append(sens_spec_class_scene)

        acc_str = '{}_accuracy: {}'.format(self.prefix, final_acc)
        acc_log_str = '{:<20}  {:<20}  {:<20}  {:<20}'.format(self.val_fold_str, self.epoch_str, '', acc_str)
        print(acc_log_str)

        # increase epoch
        self.e += 1

        return False, scene_instance_id_metrics_dict_counts
