import pickle
from copy import deepcopy
from os import path
from operator import add
from collections import deque

import numpy as np
import portalocker


class H:
    def __init__(self, ID=-1, N_CLASSES=13, TIME_STEPS=2000, N_FEATURES=160, BATCH_SIZE=64, MAX_EPOCHS=50,
                 UNITS_PER_LAYER_LSTM=None, UNITS_PER_LAYER_MLP=None, LEARNING_RATE=0.001,
                 RECURRENT_DROPOUT=0.25, INPUT_DROPOUT=0., LSTM_OUTPUT_DROPOUT=0.25, MLP_OUTPUT_DROPOUT=0.25,
                 OUTPUT_THRESHOLD=0.5, TRAIN_SCENES=range(1, 81),
                 PATIENCE_IN_EPOCHS=5,
                 ALL_FOLDS=range(1, 7), STAGE=1,
                 LABEL_MODE='blockbased',
                 MASK_VAL=-1, VAL_STATEFUL=True, METRIC='BAC',
                 HOSTNAME=''):
        ################################################################################################################

        self.ID = ID

        # Not by Random Search
        self.N_CLASSES = N_CLASSES
        self.N_FEATURES = N_FEATURES

        self.TIME_STEPS = TIME_STEPS
        self.BATCH_SIZE = BATCH_SIZE

        self.MAX_EPOCHS = MAX_EPOCHS

        self.OUTPUT_THRESHOLD = OUTPUT_THRESHOLD

        self.TRAIN_SCENES = list(TRAIN_SCENES)

        self.ALL_FOLDS = list(ALL_FOLDS)

        self.STAGE = STAGE

        self.LABEL_MODE = LABEL_MODE
        self.MASK_VAL = MASK_VAL

        self.VAL_STATEFUL = VAL_STATEFUL

        self.PATIENCE_IN_EPOCHS = PATIENCE_IN_EPOCHS

        ################################################################################################################

        # Random Search
        if UNITS_PER_LAYER_LSTM is None:
            self.UNITS_PER_LAYER_LSTM = [581, 581, 581]
        else:
            self.UNITS_PER_LAYER_LSTM = UNITS_PER_LAYER_LSTM

        if UNITS_PER_LAYER_MLP is None:
            self.UNITS_PER_LAYER_MLP = []
        else:
            self.UNITS_PER_LAYER_MLP = UNITS_PER_LAYER_MLP
        self.UNITS_PER_LAYER_MLP.append(self.N_CLASSES)

        assert self.UNITS_PER_LAYER_MLP[-1] == self.N_CLASSES, \
            'last output layer should have %d (number of classes) units' % self.N_CLASSES

        self.LEARNING_RATE = LEARNING_RATE

        self.RECURRENT_DROPOUT = RECURRENT_DROPOUT
        self.INPUT_DROPOUT = INPUT_DROPOUT
        self.LSTM_OUTPUT_DROPOUT = LSTM_OUTPUT_DROPOUT
        self.MLP_OUTPUT_DROPOUT = MLP_OUTPUT_DROPOUT


        self.METRIC = METRIC

        self.HOSTNAME = HOSTNAME
        ################################################################################################################

        # Metrics
        self.epochs_finished = [0] * len(self.ALL_FOLDS)

        self.best_epochs = [0] * len(self.ALL_FOLDS)

        self.val_acc = [0] * len(self.ALL_FOLDS)

        self.val_acc_mean = -1

        self.val_acc_std = -1

        # indicates whether this combination is already finished
        self.finished = False

        self.elapsed_time_minutes = -1

    def save_to_dir(self, model_dir):
        filepath = path.join(model_dir, 'hyperparameters.pickle')
        attr_val_dict = self.__dict__
        with open(filepath, 'wb') as handle:
            pickle.dump(attr_val_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)

        # attr_val_df = pd.DataFrame.from_dict(attr_val_dict, orient='index', columns=['value'])
        # with open(filepath, 'w+') as file:
        #     file.write(attr_val_df.to_csv())

    def load_from_dir(self, model_dir):
        filepath = path.join(model_dir, 'hyperparameters.pickle')
        with open(filepath, 'rb') as handle:
            attr_val_dict = pickle.load(handle)
            for attr, val in attr_val_dict.items():
                self.__setattr__(attr, val)
        # attr_val_df = pd.DataFrame.from_csv(filepath)
        # attr_val_dict = attr_val_df.to_dict(orient='index')

    @property
    def VAL_FOLDS(self):
        if self.STAGE == 1:
            return [3]
        elif self.STAGE == 2:
            # just retrain the model on this cross-validation fold setup
            # use just this validation fold for early stopping
            # mean the performance over stage 1 and stage 2
            return [4]
        elif self.STAGE == 3:
            return [2]
        else:
            return self.ALL_FOLDS

    @property
    def K_SCENES_TO_SUBSAMPLE(self):
        # no more subsampling
        return -1
        if self.STAGE == 1 or self.STAGE == 2:
            return 12
        else:
            return 20


class HCombManager:

    def __init__(self, save_path, timeout=60):
        self.save_path = save_path

        self.timeout = timeout

        pickle_name = 'hyperparameter_combinations.pickle'
        self.filepath = path.join(self.save_path, pickle_name)
        if not path.exists(self.filepath):
            with portalocker.Lock(self.filepath, mode='ab', timeout=self.timeout) as handle:
                hcomb_list = []
                self._write_hcomb_list(hcomb_list, handle)

        pickle_name_to_run = 'hyperparameter_combinations_to_run.pickle'
        self.filepath_to_run = path.join(self.save_path, pickle_name_to_run)

    def poll_hcomb(self, timeout=60):
        self.timeout = timeout

        if not path.exists(self.filepath_to_run):
            raise ValueError('Filepath "{}" should exist beforehand. '.format(self.filepath_to_run))

        with portalocker.Lock(self.filepath_to_run, mode='r+b', timeout=self.timeout) as handle:
            hcombs_to_run = pickle.load(handle)

            if len(hcombs_to_run) == 0:
                return None

            hcomb_to_run = hcombs_to_run[0]
            hcombs_to_run = hcombs_to_run[1:]
            self._write_hcomb_list(hcombs_to_run, handle)
            return hcomb_to_run

    def get_hcomb_id(self, h, always_append_hcombs=False):
        with portalocker.Lock(self.filepath, mode='r+b', timeout=self.timeout) as handle:
            hcomb_list = self._read_hcomb_list(handle)

            h = h.__dict__

            hcomb_list_copy = deepcopy(hcomb_list)
            for hcomb in hcomb_list_copy:
                self._make_comparable(hcomb, h)
            if h in hcomb_list_copy and not always_append_hcombs:
                index = hcomb_list_copy.index(h)
                already_contained = True
            else:
                h['ID'] = len(hcomb_list)
                hcomb_list.append(h)
                index = hcomb_list.index(h)
                already_contained = False

            self._write_hcomb_list(hcomb_list, handle)

            return index, hcomb_list[index], already_contained

    def set_hostname_and_batch_size(self, id_, h, hostname, batch_size):
        with portalocker.Lock(self.filepath, mode='r+b', timeout=self.timeout) as handle:
            hcomb_list = self._read_hcomb_list(handle)

            h = h.__dict__

            h['HOSTNAME'] = hostname
            h['BATCH_SIZE'] = batch_size

            self.replace_at_id(hcomb_list, id_, h)

            self._write_hcomb_list(hcomb_list, handle)

    def _make_comparable(self, hcomb, h):
        hcomb['ID'] = h['BATCH_SIZE']
        hcomb['STAGE'] = h['STAGE']
        hcomb['BATCH_SIZE'] = h['BATCH_SIZE']
        hcomb['HOSTNAME'] = h['HOSTNAME']
        hcomb['finished'] = h['finished']
        hcomb['epochs_finished'] = h['epochs_finished']
        hcomb['best_epochs'] = h['best_epochs']
        hcomb['METRIC'] = h['METRIC']
        hcomb['val_acc'] = h['val_acc']
        hcomb['val_acc_mean'] = h['val_acc_mean']
        hcomb['val_acc_std'] = h['val_acc_std']
        hcomb['elapsed_time_minutes'] = h['elapsed_time_minutes']

    def finish_hcomb(self, id_, h, val_acc_mean, val_acc_std, elapsed_time_minutes):
        with portalocker.Lock(self.filepath, mode='r+b', timeout=self.timeout) as handle:
            hcomb_list = self._read_hcomb_list(handle)

            h = h.__dict__

            h['finished'] = True
            h['elapsed_time_minutes'] = elapsed_time_minutes
            self._update_val_metrics_mean_std(h, val_acc_mean, val_acc_std)

            if h['STAGE'] == 2:
                self._merge_with_stage_1(h)

            self.replace_at_id(hcomb_list, id_, h)

            self._write_hcomb_list(hcomb_list, handle)

    def finish_epoch(self, id_, h, val_acc, fold_ind, best_epoch, elapsed_time_minutes):
        with portalocker.Lock(self.filepath, mode='r+b', timeout=self.timeout) as handle:
            hcomb_list = self._read_hcomb_list(handle)

            h = h.__dict__

            h['epochs_finished'][fold_ind] += 1
            h['best_epochs'][fold_ind] = best_epoch
            h['elapsed_time_minutes'] = elapsed_time_minutes
            self._update_val_metrics(h, val_acc, fold_ind)

            self.replace_at_id(hcomb_list, id_, h)

            self._write_hcomb_list(hcomb_list, handle)

    def _update_val_metrics(self, h, val_acc, fold_ind):
        h['val_acc'][fold_ind] = val_acc

    def _update_val_metrics_mean_std(self, h, val_acc_mean, val_acc_std):
        h['val_acc_mean'] = val_acc_mean
        h['val_acc_std'] = val_acc_std

    def replace_at_id(self, hcomb_list, id_, h):
        if type(h) is not dict:
            h = h.__dict__

        hcomb_list[id_] = h

    # IMPORTANT: happens if hcomb finished
    def _merge_with_stage_1(self, h):
        with portalocker.Lock(self.filepath, mode='r+b', timeout=self.timeout) as handle:
            hcomb_list = self._read_hcomb_list(handle)

            hcomb_list_copy = deepcopy(hcomb_list)
            for hcomb in hcomb_list_copy:
                self._make_comparable(hcomb, h)
                hcomb['STAGE'] = h['STAGE']
            if h in hcomb_list_copy:
                index = hcomb_list_copy.index(h)
                h['epochs_finished'] = list(map(add, h['epochs_finished'], hcomb_list[index]['epochs_finished']))
                h['best_epochs'] = list(zip(hcomb_list[index]['best_epochs'], h['best_epochs']))
                h['val_acc'] = list(map(add, h['val_acc'], hcomb_list[index]['val_acc']))
                h['val_acc_mean'] = np.mean(h['val_acc'])
                h['val_acc_std'] = np.std(h['val_acc'])
                h['elapsed_time_minutes'] += hcomb_list[index]['elapsed_time_minutes']
            else:
                raise ValueError('Cannot find HComb in Stage 1')

            self.replace_at_id(hcomb_list, index, h)

            self._write_hcomb_list(hcomb_list, handle)

    def _read_hcomb_list(self, handle):
        return pickle.load(handle)

    def _write_hcomb_list(self, hcomb_list, handle):
        handle.seek(0)
        handle.truncate()
        pickle.dump(hcomb_list, handle, protocol=pickle.HIGHEST_PROTOCOL)

class RandomSearch:

    def __init__(self, metric_used='BAC', STAGE=1, time_steps=1000):

        # random search stage
        self.STAGE = STAGE

        # ARCH -> don't sample

        self.MAXIMUM_NEURONS_LSTM = 2100    # is upper limit with 3 layers as reference
        self.MAXIMUM_NEURONS_MLP = 1200     # is upper limit with 1 layers as reference

        # Regularization

        # comb: (Input, Recurrent, LSTM Output, MLP Output) -> factors for global regularization strength
        self.RANGE_REGULARIZATION_COMBINATION = [
            (0, 0.5, 0.5, 1),  # 0.5 -> later, now uniformly
            (0, 1, 1, 1),         # 0.1
            (0, 1, 0, 1),           # 0.1
            (0, 0, 0, 0)            # 0.1
        ]

        # LSTM
        self.RANGE_NUMBER_OF_LSTM_LAYERS = [3, 4, 5]
        # MLP
        self.RANGE_NUMBER_OF_MLP_LAYERS = [1, 2]

        self.RANGE_LSTM_NEURON_RATIO = [0.75, 0.5, 0.25]


        # SAMPLE

        # total no of neurons in network
        # self.SAMPLING_WEIGHTS = np.array([0.15, 0.1, 0.1, 0.3, 0.2, 0.1, 0.05]) * 10
        #
        # self.SAMPLING_WEIGHTS = np.round(self.SAMPLING_WEIGHTS).astype(np.int32)
        # assert np.isclose(np.sum(self.SAMPLING_WEIGHTS), 10)
        # self.TOTAL_NO_OF_NEURONS = [500] * self.SAMPLING_WEIGHTS[0] \
        #                            + [1000] * self.SAMPLING_WEIGHTS[1] \
        #                            + [1500] * self.SAMPLING_WEIGHTS[2] \
        #                            + [2000] * self.SAMPLING_WEIGHTS[3] \
        #                            + [2500] * self.SAMPLING_WEIGHTS[4] \
        #                            + [3000] * self.SAMPLING_WEIGHTS[5] \
        #                            + [3500] * self.SAMPLING_WEIGHTS[6]

        self.RANGE_TOTAL_NO_OF_NEURONS = (500, 3000)

        self.RANGE_GLOBAL_REGULARIZATION_STRENGTH = (0.25, 0.75)

        #TODO: implement in model
        # self.RANGE_L2 = None
        # TODO: check values
        # gradient clipping

        # TODO: to determine
        self.PATIENCE_IN_EPOCHS = 5     # patience for early stopping


        # Data characteristics
        self.RANGE_TIME_STEPS = [1000, 500, 50]  # one frame = 10ms = 0.01 s
        if time_steps in self.RANGE_TIME_STEPS:
            self.TIME_STEPS = time_steps
        else:
            print('Given time_steps: {} not in range of expected {}. Using {} nevertheless.'
                  .format(time_steps, self.RANGE_TIME_STEPS, time_steps))
            self.TIME_STEPS = time_steps
        self.BATCH_SIZE = 128

        self.metric_used = metric_used

    def _sample_hcomb(self, number_of_lstm_layers, number_of_mlp_layers, lstm_neuron_ratio, regularization_combination):

        # sampling
        total_number_of_neurons = int(np.random.uniform(*self.RANGE_TOTAL_NO_OF_NEURONS))
        global_regularization_strength = np.random.uniform(*self.RANGE_GLOBAL_REGULARIZATION_STRENGTH)

        lstm_total_neurons = int(total_number_of_neurons*lstm_neuron_ratio)
        mlp_total_neurons = total_number_of_neurons - lstm_total_neurons

        units_per_layer_lstm = [int(min(self.MAXIMUM_NEURONS_LSTM, lstm_total_neurons) // number_of_lstm_layers)] * number_of_lstm_layers

        units_per_layer_mlp = [int(min(self.MAXIMUM_NEURONS_MLP, mlp_total_neurons) // number_of_mlp_layers)] * number_of_mlp_layers

        # DROPOUT

        input_factor, recurrent_factor, output_factor = regularization_combination
        input_dropout = input_factor * global_regularization_strength
        recurrent_dropout = recurrent_factor * global_regularization_strength
        lstm_output_dropout = output_factor * global_regularization_strength
        mlp_output_dropout = output_factor * global_regularization_strength

        return H(UNITS_PER_LAYER_LSTM=units_per_layer_lstm, UNITS_PER_LAYER_MLP=units_per_layer_mlp,
                 PATIENCE_IN_EPOCHS=self.PATIENCE_IN_EPOCHS,
                 BATCH_SIZE=self.BATCH_SIZE, TIME_STEPS=self.TIME_STEPS,
                 INPUT_DROPOUT=input_dropout, RECURRENT_DROPOUT=recurrent_dropout,
                 LSTM_OUTPUT_DROPOUT=lstm_output_dropout, MLP_OUTPUT_DROPOUT=mlp_output_dropout,
                 METRIC=self.metric_used, STAGE=self.STAGE)

    def _get_hcombs_to_run(self, number_of_hcombs):
        from itertools import product

        # TODO: delete because this favors expensive networks -> for finding expensive hyperparam comb.
        # self.RANGE_NUMBER_OF_LSTM_LAYERS = [3, 4, 5]
        # self.RANGE_NUMBER_OF_MLP_LAYERS = [1, 2]

        architecture_params_list = list(product(self.RANGE_REGULARIZATION_COMBINATION, self.RANGE_NUMBER_OF_LSTM_LAYERS, self.RANGE_NUMBER_OF_MLP_LAYERS,
                                           self.RANGE_LSTM_NEURON_RATIO))
        return list(set([self._sample_hcomb(*architecture_params) for architecture_params in architecture_params_list[:number_of_hcombs]]))

    def save_hcombs_to_run(self, save_path, number_of_hcombs):

        # name has to be same as in HCombManager
        pickle_name = 'hyperparameter_combinations_to_run.pickle'

        filepath = path.join(save_path, pickle_name)

        if not path.exists(filepath):
            with open(filepath, 'wb') as handle:
                pickle.dump(self._get_hcombs_to_run(number_of_hcombs), handle, protocol=pickle.HIGHEST_PROTOCOL)
        else:
            with open(filepath, 'rb') as handle:
                hcombs_old = pickle.load(handle)
            hcombs_old += self._get_hcombs_to_run(number_of_hcombs)
            hcombs_new = list(set(hcombs_old))
            with open(filepath, 'wb') as handle:
                pickle.dump(hcombs_new, handle, protocol=pickle.HIGHEST_PROTOCOL)