import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import pandas as pd

from os import path


def plot_metrics(metrics, save_dir):
    if 'best_val_class_accs_over_folds' in metrics.keys():
        _plot_acc_over_folds(metrics, save_dir)
    else:
        epochs_done = len(metrics['train_accs'])
        for metric_name, data in metrics.items():
            if type(data) is str:
                continue
            if 'scene' in metric_name:
                if 'sens' in metric_name or 'spec' in metric_name:
                    _plot_sens_spec(metric_name, data, save_dir)
                continue
            if 'gradient' in metric_name:
                continue
            if 'class' in metric_name:
                if 'sens' in metric_name or 'spec' in metric_name:
                    _plot_sens_spec_class(metric_name, data, save_dir)
                _plot_loss_and_acc(metric_name, data, save_dir, over_classes=True)
            else:
                _plot_loss_and_acc(metric_name, data, save_dir, over_classes=False, epochs_done=epochs_done)


def _plot_sens_spec_class(metric_name, data, save_dir):
    x = np.arange(1, data.shape[0] + 1, 1)

    labels = ['alarm', 'baby', 'femaleSpeech',  'fire', 'crash', 'dog', 'engine', 'footsteps', 'knock', 'phone',
              'piano', 'maleSpeech', 'femaleScreammaleScream']
    colors = np.linspace(0, 1, len(labels))
    cmap = plt.get_cmap('tab20')
    colors = [cmap(val) for val in colors]

    fig, ax = plt.subplots(figsize=(13, 13))

    for class_ind in range(data.shape[1]):

        ax.plot(x, data[:, class_ind, 0], '.-', label='sens.: ' + labels[class_ind],
                c=colors[class_ind])
        ax.plot(x, data[:, class_ind, 1], '.--', label='spec.: ' + labels[class_ind],
                c=colors[class_ind])

    ax.set_title(metric_name)
    handles, plt_labels = ax.get_legend_handles_labels()
    plt.legend(handles, plt_labels, loc='lower center', ncol=data.shape[1] // 2, bbox_to_anchor=(0.5, -0.13),
               fontsize='small')
    plt.savefig(path.join(save_dir, metric_name) + '.pdf')
    plt.close()


def _plot_acc_over_folds(metrics, save_dir):
    for bac2 in (False, True):

        metrics_class_accs = dict()
        metrics_acc = dict()

        for metric_name, data in metrics.items():
            if not bac2:
                if 'bac2' in metric_name:
                    continue
            else:
                if 'bac2' not in metric_name:
                    continue

            if 'class' in metric_name:
                metrics_class_accs[metric_name] = data
            else:
                metrics_acc[metric_name] = data

        x = np.arange(1, len(metrics['best_val_class_accs_over_folds{}'.format('' if not bac2 else '_bac2')]) +1, 1)
        plt.figure(figsize=(15, 15))

        labels = ['alarm', 'baby', 'femaleSpeech',  'fire', 'crash', 'dog', 'engine', 'footsteps', 'knock', 'phone',
                  'piano', 'maleSpeech', 'femaleScreammaleScream']
        colors = np.linspace(0, 1, len(labels))
        cmap = plt.get_cmap('tab20')
        colors = [cmap(val) for val in colors]
        for metric_name, data in metrics_class_accs.items():
            if 'mean' not in metric_name and 'std' not in metric_name:
                for row in range(data.shape[1]):
                    plt.plot(x, data[:, row], '.-', label=labels[row], c=colors[row])
            if 'mean' in metric_name:
                for row in range(data.shape[0]):
                    plt.plot((0, x[-1]), (data[row], data[row]), '.-', c=colors[row], alpha=0.3)
            if 'std' in metric_name:
                for row in range(data.shape[0]):
                    mean = metrics_class_accs['best_val_class_accs_mean_over_folds{}'.format('' if not bac2 else '_bac2')][row]
                    plt.plot((0, x[-1]), (mean + data[row], mean + data[row]), '.--', c=colors[row], alpha=0.3)
                    plt.plot((0, x[-1]), (mean - data[row], mean - data[row]), '.--', c=colors[row], alpha=0.3)

        name = 'best_val_class_accs_over_folds_{}'.format('BAC' if not bac2 else 'BAC2')
        plt.legend(loc=1, ncol=2)
        plt.title(name)
        plt.xticks(x)
        plt.xlabel('folds')
        plt.ylabel('BAC' if not bac2 else 'BAC2')
        plt.savefig(path.join(save_dir, name) + '.pdf')
        plt.close()

        x = np.arange(1, len(metrics['best_val_class_accs_over_folds{}'.format('' if not bac2 else '_bac2')]) + 1, 1)
        plt.figure(figsize=(15, 15))

        labels = ['weighted average']
        for metric_name, data in metrics_acc.items():
            if 'mean' not in metric_name and 'std' not in metric_name:
                plt.plot(x, data, '.-', label=labels[0], c=colors[0])
            if 'mean' in metric_name:
                plt.plot((0, x[-1]), (data, data), '.-', c=colors[0], alpha=0.3)
            if 'std' in metric_name:
                mean = metrics_acc['best_val_acc_mean_over_folds{}'.format('' if not bac2 else '_bac2')]
                plt.plot((0, x[-1]), (mean + data, mean + data), '.--', c=colors[0], alpha=0.3)
                plt.plot((0, x[-1]), (mean - data, mean - data), '.--', c=colors[0], alpha=0.3)

        name = 'best_val_acc_over_folds_{}'.format('BAC' if not bac2 else 'BAC2')
        plt.legend(loc=1, ncol=2)
        plt.title(name)
        plt.xticks(x)
        plt.xlabel('folds')
        plt.ylabel('BAC' if not bac2 else 'BAC2')
        plt.savefig(path.join(save_dir, name) + '.pdf')
        plt.close()


def _plot_loss_and_acc(metric_name, data, save_dir, over_classes=False, epochs_done=None):
    x = np.arange(1, len(data) + 1, 1)
    plt.figure(figsize=(15, 15))

    bac2 = 'bac2' in metric_name

    if over_classes:
        labels = ['alarm', 'baby', 'femaleSpeech',  'fire', 'crash', 'dog', 'engine', 'footsteps', 'knock', 'phone',
                  'piano', 'maleSpeech', 'femaleScreammaleScream']
    else:
        data = data[:, np.newaxis]
        labels = ['weighted average'] if 'acc' in metric_name else [None]

    colors = np.linspace(0, 1, len(labels))
    cmap = plt.get_cmap('tab20')
    colors = [cmap(val) for val in colors]

    for row in range(data.shape[1]):
        plt.plot(x, data[:, row], '.-', label=labels[row], c=colors[row], alpha=1 if 'loss' not in metric_name else 0.2)
        if 'loss' in metric_name:
            pd_data = pd.Series(data[:, row])
            data_smooth = pd_data.rolling(data[:, row].shape[0] // epochs_done).mean()
            plt.plot(x, data_smooth, '.-', label=labels[row], c='black',
                     alpha=1)
    if 'loss' not in metric_name:
        plt.legend(loc=1, ncol=2)
    plt.title(metric_name)
    # plt.xticks(x)
    if 'acc' in metric_name:
        plt.xlabel('epochs')
        plt.ylabel('BAC' if not bac2 else 'BAC2')
    else:
        plt.xlabel('iterations')
        plt.ylabel('loss')
        plt.ylim((0., 3.0))
    plt.savefig(path.join(save_dir, metric_name) + '.pdf')
    plt.close()


def _plot_sens_spec(metric_name, data, save_dir):
    x = np.arange(0, data.shape[0], 1)

    gridshape = (5, 4)
    gridsize = gridshape[0] * gridshape[1]

    n_plots = data.shape[1] // gridsize

    labels = ['alarm', 'baby', 'femaleSpeech',  'fire', 'crash', 'dog', 'engine', 'footsteps', 'knock', 'phone',
              'piano', 'maleSpeech', 'femaleScreammaleScream']
    colors = np.linspace(0, 1, len(labels))
    cmap = plt.get_cmap('tab20')
    colors = [cmap(val) for val in colors]

    for n in range(n_plots):
        grid_plot, axes = plt.subplots(nrows=gridshape[0], ncols=gridshape[1],
                                       figsize=(5 * gridshape[0], 5 * gridshape[1]))
        # grid_plot.suptitle('Sensitivity and Specificity')

        for n_sp in range(gridsize):
            row = n_sp // gridshape[1]
            col = n_sp % gridshape[1]
            scene_ind = n*gridsize + n_sp
            for label_ind in range(data.shape[2]):
                axes[row][col].plot(x, data[:, scene_ind, label_ind, 0], '.-', label='sens.: ' + labels[label_ind],
                        c=colors[label_ind])
                axes[row][col].plot(x, data[:, scene_ind, label_ind, 1], '.--', label='spec.: ' + labels[label_ind],
                        c=colors[label_ind])
            axes[row][col].set_title('Scene: ' + str(scene_ind+1))

        handles, plt_labels = axes[0, 0].get_legend_handles_labels()
        plt.legend(handles, plt_labels, loc='upper center', bbox_to_anchor=(-1.35, -0.15), ncol=data.shape[2])
        plt.savefig(path.join(save_dir, metric_name) + '_' + str(n) + '.pdf')
        plt.close()

def _test_plot_sens_spec_class():
    import pickle
    save_dir = '/mnt/antares_raid/home/spiess/twoears_proj/models/heiner/model_directories/LDNN_v1/hcomb_25/val_fold3/'
    with open(path.join(save_dir, 'metrics.pickle'), 'rb') as handle:
        metrics = pickle.load(handle)
    metric_name = 'val_sens_spec_class'
    data = metrics[metric_name]
    # data = np.random.rand(1, 80, 13, 2)
    _plot_sens_spec_class(metric_name, data, save_dir)

def _test_plot_loss():
    import pickle
    save_dir = '/mnt/antares_raid/home/spiess/twoears_proj/models/heiner/model_directories/LDNN_v1/hcomb_25/val_fold3/'
    with open(path.join(save_dir, 'metrics.pickle'), 'rb') as handle:
        metrics = pickle.load(handle)

    metric_name = 'train_losses'
    epochs_done = len(metrics['train_accs'])
    _plot_loss_and_acc(metric_name, metrics[metric_name], save_dir, over_classes=False, epochs_done=epochs_done)

def plot_global_gradient_norm(global_gradient_norms, save_dir, epochs_done=None):
    x = np.arange(1, len(global_gradient_norms)+1, 1)
    plt.figure(figsize=(15, 15))

    data = global_gradient_norms

    plt.plot(x, data, alpha=1 if epochs_done is None else 0.3)
    if epochs_done is not None:
        pd_data = pd.Series(data)
        data_smooth = pd_data.rolling(data.shape[0] // epochs_done).mean()
        plt.plot(x, data_smooth, '.-', c='black', alpha=1)
    # plt.xticks(x)
    plt.xlabel('iterations')
    plt.ylabel('norm')
    plt.savefig(path.join(save_dir, 'global_gradient_norm') + '.pdf')
    plt.close()

def _test_plot_global_gradient_norm():
    import pickle
    save_dir = '/mnt/antares_raid/home/spiess/twoears_proj/models/heiner/model_directories/LDNN_v1/hcomb_25/val_fold3/'
    with open(path.join(save_dir, 'metrics.pickle'), 'rb') as handle:
        metrics = pickle.load(handle)

    metric_name = 'global_gradient_norm'
    epochs_done = len(metrics['train_accs'])

    plot_global_gradient_norm(metrics[metric_name], save_dir, epochs_done=epochs_done)

#test_plot_global_gradient_norm()
# test_plot_sens_spec()
if __name__ == '__main__':
    # import pickle
    # save_dir = '/mnt/antares_raid/home/spiess/twoears_proj/models/heiner/model_directories/LDNN_v1/hcomb_25/val_fold3/'
    # with open(path.join(save_dir, 'metrics.pickle'), 'rb') as handle:
    #     metrics = pickle.load(handle)
    #
    # plot_metrics(metrics, save_dir)

    # _test_plot_loss()

    # _test_plot_global_gradient_norm()

    _test_plot_sens_spec_class()
#
# for key, metric in metrics.items():
#     metrics[key] = np.array(metric)
# plot_metrics(metrics, '/home/spiess/twoears_proj/models/heiner/model_directories/LDNN_v1/hcomb_0/val_fold1/')
#
# with open('/home/spiess/twoears_proj/models/heiner/model_directories/LDNN_v1/hcomb_0/metrics.pickle',
#           'rb') as handle:
#     metrics = pickle.load(handle)
#
# for key, metric in metrics.items():
#     if type(metric) is list:
#         metrics[key] = np.array(metric)
# plot_metrics(metrics, '/home/spiess/twoears_proj/models/heiner/model_directories/LDNN_v1/hcomb_0/')