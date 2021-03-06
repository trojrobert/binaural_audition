import glob
import numpy as np
from os import path
from tqdm import tqdm
from tensorflow.python.ops.nn_impl import weighted_cross_entropy_with_logits

import pickle

import settings

np.seterr(divide='ignore', invalid='ignore')



def get_loss_weights(fold_nbs, scene_nbs, label_mode, path_pattern=settings.dir,
                     location='train', name='train_weights'):
    name += '_' + label_mode + '.npy'
    save_path = path.join(path_pattern, location, name)
    if not path.exists(save_path):
        _create_weights_array(save_path)
    weights_array = np.load(save_path)
    if type(fold_nbs) is int:
        l = list()
        l.append(fold_nbs)
        fold_nbs = l
    if type(scene_nbs) is int:
        l = list()
        l.append(scene_nbs)
        scene_nbs = l

    weights_array = weights_array[fold_nbs, :, :, :]
    weights_array = weights_array[:, scene_nbs, :, :]
    class_pos_neg_counts = np.sum(weights_array, axis=(0, 1))
    # weight on positive = negative count / positive count
    return class_pos_neg_counts[:, 1] / class_pos_neg_counts[:, 0]


def _create_weights_array(save_path):
    path_to_file, filename = path.split(save_path)
    if filename.__contains__('blockbased'):
        label_mode = 'y_block'
    elif filename.__contains__('instant'):
        label_mode = 'y'
    else:
        raise ValueError("label_mode has to be either 'instant' or 'blockbased'")
    if path_to_file.__contains__('train'):
        folds = 6
        scenes = 80
    elif path_to_file.__contains__('test'):
        print("weights of 'test' data shall not be used.")
        folds = 2
        scenes = 168
    else:
        raise ValueError("location has to be either 'train' or 'test'")
    classes = 13
    weights_array = np.zeros((folds, scenes, classes, 2))
    for fold in tqdm(range(0, folds), desc='fold_loop'):
        for scene in tqdm(range(0, scenes), desc='scene_loop'):
            filenames = glob.glob(path.join(path_to_file, 'fold'+str(fold+1), 'scene'+str(scene+1), '*.npz'))
            for filename in tqdm(filenames, desc='file_loop'):
                with np.load(filename) as data:
                    labels = data[label_mode]
                    n_pos = np.count_nonzero(labels == 1, axis=(0, 1))
                    n_neg = np.count_nonzero(labels == 0, axis=(0, 1))
                    weights_array[fold, scene, :, 0] += n_pos
                    weights_array[fold, scene, :, 1] += n_neg
    np.save(save_path, weights_array)


def mask_from(y_true, mask_val):
    from keras import backend as K

    mask = K.cast(K.not_equal(y_true, mask_val), 'float32')
    count_unmasked = K.sum(mask)
    return mask, count_unmasked


def my_loss_builder(mask_val, loss_weights):
    from keras import backend as K

    def my_loss(y_true, y_pred):
        entropy = weighted_cross_entropy_with_logits(y_true, y_pred, K.constant(loss_weights, dtype='float32'))
        mask, count_unmasked = mask_from(y_true, mask_val)
        masked_entropy = entropy * mask
        loss = K.sum(masked_entropy) / count_unmasked
        return loss
    return my_loss


def my_accuracy_builder(mask_val, output_threshold, metric='bac2'):
    from keras import backend as K
    def my_accuracy_per_batch(y_true, y_pred):
        y_pred_labels = K.cast(K.greater_equal(y_pred, output_threshold), 'float32')
        mask, count_unmasked = mask_from(y_true, mask_val)

        count_positives = K.sum(y_true * mask)  # just the +1 labels are added, the rest is 0
        count_positives = K.switch(count_positives, count_positives, 1.0)
        # count_positives = K.print_tensor(count_positives, message='count_positives: ')
        sensitivity = 0.0
        specificity = 0.0

        if metric in ('bac2', 'bac', 'sensitivity'):
            sensitivity = K.sum(y_pred_labels * y_true * mask) / count_positives  # true positive rate
            if metric == 'sensitivity':
                return sensitivity
        if metric in ('bac2', 'bac', 'specificity'):
            count_negatives = count_unmasked - count_positives  # count_unmasked are all valid labels
            count_negatives = K.switch(count_negatives, count_negatives, 1.0)
            # count_negatives = K.print_tensor(count_negatives, message='count_negatives: ')
            specificity = K.sum((y_pred_labels - 1) * (y_true - 1) * mask) / count_negatives
            if metric == 'specificity':
                return specificity
        if metric == 'bac2':
            bac2 = 1 - K.sqrt(((K.square(1 - sensitivity) + K.square(1 - specificity)) / 2))
            return bac2
        if metric == 'bac':
            bac = (sensitivity + specificity) / 2
            return bac
        raise ValueError("'metric' has to be either 'bac2', 'bac', 'sensitivity' or 'specificity'")
    return my_accuracy_per_batch


def get_index_in_loader_len(loader_len, epoch, iteration):
    index = 0
    act_e = 0
    while act_e < epoch-1:
        index += loader_len[act_e]
    index += iteration


def pickle_metrics(metrics_dict, folder_path):
    with open(path.join(folder_path, 'metrics.pickle'), 'wb') as handle:
        pickle.dump(metrics_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)


def latest_training_state(model_save_dir):
    all_available_weights = glob.glob(path.join(model_save_dir, 'model_ckp_*.hdf5'))

    if len(all_available_weights) == 0:
        return None, None, None

    all_available_weights.sort()
    latest_weights_path = all_available_weights[-1]

    def find_start(filename, key):
        return filename.rfind(key) + len(key) + 1

    epoch_start = find_start(latest_weights_path, 'epoch')
    val_acc_start = find_start(latest_weights_path, 'val_acc')
    epochs_finished = int(latest_weights_path[epoch_start:epoch_start + 2])
    val_acc = float(latest_weights_path[val_acc_start:val_acc_start + 5])

    return latest_weights_path, epochs_finished, val_acc

