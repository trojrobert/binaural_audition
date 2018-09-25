# this plotting code is shared by heiner/changbin/moritz
# function that should be used: evaluate_testset (uses the other functions)


import numpy as np
import matplotlib.pyplot as plt
import os

# scene specifications from binAudLSTM_testSceneParameters.txt
def get_test_scene_params():
    # test scenes (list index = scene id-1)
    # list elements are 3 tuples: nsrc, snr, azimuth
    scenes = []    # nSrc  # SNR                 # azimuths
    scenes.append((1,      0,                    0)) # scene id 1
    scenes.append((1,      0,                    45)) # scene id 2
    scenes.append((1,      0,                    90)) # scene id 3
    scenes.append((2,      [0,0],                [0,0])) # scene id 4
    scenes.append((3,      [0,0,0],              [0,0,0])) # scene id 5
    scenes.append((4,      [0,0,0,0],            [0,0,0,0])) # scene id 6
    scenes.append((2,      [0,0],                [-10,10])) # scene id 7
    scenes.append((3,      [0,0,0],              [-10,10,30])) # scene id 8
    scenes.append((4,      [0,0,0,0],            [-10,10,30,50])) # scene id 9
    scenes.append((2,      [0,0],                [0,20])) # scene id 10
    scenes.append((3,      [0,0,0],              [0,20,40])) # scene id 11
    scenes.append((4,      [0,0,0,0],            [0,20,40,60])) # scene id 12
    scenes.append((2,      [0,0],                [35,55])) # scene id 13
    scenes.append((3,      [0,0,0],              [25,45,65])) # scene id 14
    scenes.append((4,      [0,0,0,0],            [15,35,55,75]))  # scene id 15
    scenes.append((2,      [0,0],                [80,100]))  # scene id 16
    scenes.append((3,      [0,0,0],              [70,90,110]))  # scene id 17
    scenes.append((4,      [0,0,0,0],            [60,80,100,120]))  # scene id 18
    scenes.append((2,      [0,0],                [-22.5,22.5]))  # scene id 19
    scenes.append((3,      [0,0,0],              [-22.5,22.5,67.5]))  # scene id 20
    scenes.append((4,      [0,0,0,0],            [-22.5,22.5,67.5,112.5]))  # scene id 21
    scenes.append((2,      [0,0],                [0,45]))  # scene id 22
    scenes.append((3,      [0,0,0],              [0,45,90]))  # scene id 23
    scenes.append((4,      [0,0,0,0],            [0,45,90,135]))  # scene id 24
    scenes.append((2,      [0,0],                [22.5,67.5]))  # scene id 25
    scenes.append((2,      [0,0],                [67.5,112.5]))  # scene id 26
    scenes.append((3,      [0,0,0],              [45,90,135]))  # scene id 27
    scenes.append((4,      [0,0,0,0],            [22.5,65.5,112.5,157.5]))  # scene id 28
    scenes.append((2,      [0,0],                [-45,45]))  # scene id 29
    scenes.append((3,      [0,0,0],              [-45,45,135]))  # scene id 30
    scenes.append((4,      [0,0,0,0],            [-45,45,135,225]))  # scene id 31
    scenes.append((2,      [0,0],                [0,90]))  # scene id 32
    scenes.append((3,      [0,0,0],              [0,90,180]))  # scene id 33
    scenes.append((4,      [0,0,0,0],            [0,90,180,270]))  # scene id 34
    scenes.append((4,      [0,0,0,0],            [-90,0,90,180]))  # scene id 35
    scenes.append((2,      [0,0],                [45,135]))  # scene id 36
    scenes.append((2,      [0,-20],              [0,0]))  # scene id 37
    scenes.append((2,      [0,-10],              [0,0]))  # scene id 38
    scenes.append((2,      [0,10],               [0,0]))  # scene id 39
    scenes.append((2,      [0,20],               [0,0]))  # scene id 40
    scenes.append((3,      [0,-20,-20],          [0,0,0]))  # scene id 41
    scenes.append((3,      [0,-10,-10],          [0,0,0]))  # scene id 42
    scenes.append((3,      [0,10,10],            [0,0,0]))  # scene id 43
    scenes.append((3,      [0,20,20],            [0,0,0]))  # scene id 44
    scenes.append((4,      [0,-20,-20,-20],      [0,0,0,0]))  # scene id 45
    scenes.append((4,      [0,-10,-10,-10],      [0,0,0,0]))  # scene id 46
    scenes.append((4,      [0,10,10,10],         [0,0,0,0]))  # scene id 47
    scenes.append((4,      [0,20,20,20],         [0,0,0,0]))  # scene id 48
    scenes.append((2,      [0,-20],              [-10,10]))  # scene id 49
    scenes.append((2,      [0,-10],              [-10,10]))  # scene id 50
    scenes.append((2,      [0,10],               [-10,10]))  # scene id 51
    scenes.append((2,      [0,20],               [-10,10]))  # scene id 52
    scenes.append((3,      [0,-20,-20],          [-10,10,30]))  # scene id 53
    scenes.append((3,      [0,-10,-10],          [-10,10,30]))  # scene id 54
    scenes.append((3,      [0,10,10],            [-10,10,30]))  # scene id 55
    scenes.append((3,      [0,20,20],            [-10,10,30]))  # scene id 56
    scenes.append((4,      [0,-20,-20,-20],      [-10,10,30,50]))  # scene id 57
    scenes.append((4,      [0,-10,-10,-10],      [-10,10,30,50]))  # scene id 58
    scenes.append((4,      [0,10,10,10],         [-10,10,30,50]))  # scene id 59
    scenes.append((4,      [0,20,20,20],         [-10,10,30,50]))  # scene id 60
    scenes.append((2,      [0,-20],              [0,20]))  # scene id 61
    scenes.append((2,      [0,-10],              [0,20]))  # scene id 62
    scenes.append((2,      [0,10],               [0,20]))  # scene id 63
    scenes.append((2,      [0,20],               [0,20]))  # scene id 64
    scenes.append((3,      [0,-20,-20],          [0,20,40]))  # scene id 65
    scenes.append((3,      [0,-10,-10],          [0,20,40]))  # scene id 66
    scenes.append((3,      [0,10,10],            [0,20,40]))  # scene id 67
    scenes.append((3,      [0,20,20],            [0,20,40]))  # scene id 68
    scenes.append((4,      [0,-20,-20,-20],      [0,20,40,60]))  # scene id 69
    scenes.append((4,      [0,-10,-10,-10],      [0,20,40,60]))  # scene id 70
    scenes.append((4,      [0,10,10,10],         [0,20,40,60]))  # scene id 71
    scenes.append((4,      [0,20,20,20],         [0,20,40,60]))  # scene id 72
    scenes.append((2,      [0,-20],              [35,55]))  # scene id 73
    scenes.append((2,      [0,-10],              [35,55]))  # scene id 74
    scenes.append((2,      [0,10],               [35,55]))  # scene id 75
    scenes.append((2,      [0,20],               [35,55]))  # scene id 76
    scenes.append((3,      [0,-20,-20],          [25,45,65]))  # scene id 77
    scenes.append((3,      [0,-10,-10],          [25,45,65]))  # scene id 78
    scenes.append((3,      [0,10,10],            [25,45,65]))  # scene id 79
    scenes.append((3,      [0,20,20],            [25,45,65]))  # scene id 80
    scenes.append((4,      [0,-20,-20,-20],      [15,35,55,75]))  # scene id 81
    scenes.append((4,      [0,-10,-10,-10],      [15,35,55,75]))  # scene id 82
    scenes.append((4,      [0,10,10,10],         [15,35,55,75]))  # scene id 83
    scenes.append((4,      [0,20,20,20],         [15,35,55,75]))  # scene id 84
    scenes.append((2,      [0,-20],              [80,100]))  # scene id 85
    scenes.append((2,      [0,-10],              [80,100]))  # scene id 86
    scenes.append((2,      [0,10],               [80,100]))  # scene id 87
    scenes.append((2,      [0,20],               [80,100]))  # scene id 88
    scenes.append((3,      [0,-20,-20],          [70,90,110]))  # scene id 89
    scenes.append((3,      [0,-10,-10],          [70,90,110]))  # scene id 90
    scenes.append((3,      [0,10,10],            [70,90,110]))  # scene id 91
    scenes.append((3,      [0,20,20],            [70,90,110]))  # scene id 92
    scenes.append((4,      [0,-20,-20,-20],      [60,80,100,120]))  # scene id 93
    scenes.append((4,      [0,-10,-10,-10],      [60,80,100,120]))  # scene id 94
    scenes.append((4,      [0,10,10,10],         [60,80,100,120]))  # scene id 95
    scenes.append((4,      [0,20,20,20],         [60,80,100,120]))  # scene id 96
    scenes.append((2,      [0,-20],              [-22.5,22.5]))  # scene id 97
    scenes.append((2,      [0,-10],              [-22.5,22.5]))  # scene id 98
    scenes.append((2,      [0,10],               [-22.5,22.5]))  # scene id 99
    scenes.append((2,      [0,20],               [-22.5,22.5]))  # scene id 100
    scenes.append((3,      [0,-20,-20],          [-22.5,22.5,67.5]))  # scene id 101
    scenes.append((3,      [0,-10,-10],          [-22.5,22.5,67.5]))  # scene id 102
    scenes.append((3,      [0,10,10],            [-22.5,22.5,67.5]))  # scene id 103
    scenes.append((3,      [0,20,20],            [-22.5,22.5,67.5]))  # scene id 104
    scenes.append((4,      [0,-20,-20,-20],      [-22.5,22.5,67.5,112.5]))  # scene id 105
    scenes.append((4,      [0,-10,-10,-10],      [-22.5,22.5,67.5,112.5]))  # scene id 106
    scenes.append((4,      [0,10,10,10],         [-22.5,22.5,67.5,112.5]))  # scene id 107
    scenes.append((4,      [0,20,20,20],         [-22.5,22.5,67.5,112.5]))  # scene id 108
    scenes.append((2,      [0,-20],              [0,45]))  # scene id 109
    scenes.append((2,      [0,-10],              [0,45]))  # scene id 110
    scenes.append((2,      [0,10],               [0,45]))  # scene id 111
    scenes.append((2,      [0,20],               [0,45]))  # scene id 112
    scenes.append((3,      [0,-20,-20],          [0,45,90]))  # scene id 113
    scenes.append((3,      [0,-10,-10],          [0,45,90]))  # scene id 114
    scenes.append((3,      [0,10,10],            [0,45,90]))  # scene id 115
    scenes.append((3,      [0,20,20],            [0,45,90]))  # scene id 116
    scenes.append((4,      [0,-20,-20,-20],      [0,45,90,135]))  # scene id 117
    scenes.append((4,      [0,-10,-10,-10],      [0,45,90,135]))  # scene id 118
    scenes.append((4,      [0,10,10,10],         [0,45,90,135]))  # scene id 119
    scenes.append((4,      [0,20,20,20],         [0,45,90,135]))  # scene id 120
    scenes.append((2,      [0,-20],              [22.5,67.5]))  # scene id 121
    scenes.append((2,      [0,-10],              [22.5,67.5]))  # scene id 122
    scenes.append((2,      [0,10],               [22.5,67.5]))  # scene id 123
    scenes.append((2,      [0,20],               [22.5,67.5]))  # scene id 124
    scenes.append((2,      [0,-20],              [67.5,112.5]))  # scene id 125
    scenes.append((2,      [0,-10],              [67.5,112.5]))  # scene id 126
    scenes.append((2,      [0,10],               [67.5,112.5]))  # scene id 127
    scenes.append((2,      [0,20],               [67.5,112.5]))  # scene id 128
    scenes.append((3,      [0,-20,-20],          [45,90,135]))  # scene id 129
    scenes.append((3,      [0,-10,-10],          [45,90,135]))  # scene id 130
    scenes.append((3,      [0,10,10],            [45,90,135]))  # scene id 131
    scenes.append((3,      [0,20,20],            [45,90,135]))  # scene id 132
    scenes.append((4,      [0,-20,-20,-20],      [22.5,65.5,112.5,157.5]))  # scene id 133
    scenes.append((4,      [0,-10,-10,-10],      [22.5,65.5,112.5,157.5]))  # scene id 134
    scenes.append((4,      [0,10,10,10],         [22.5,65.5,112.5,157.5]))  # scene id 135
    scenes.append((4,      [0,20,20,20],         [22.5,65.5,112.5,157.5]))  # scene id 136
    scenes.append((2,      [0,-20],              [-45,45]))  # scene id 137
    scenes.append((2,      [0,-10],              [-45,45]))  # scene id 138
    scenes.append((2,      [0,10],               [-45,45]))  # scene id 139
    scenes.append((2,      [0,20],               [-45,45]))  # scene id 140
    scenes.append((3,      [0,-20,-20],          [-45,45,135]))  # scene id 141
    scenes.append((3,      [0,-10,-10],          [-45,45,135]))  # scene id 142
    scenes.append((3,      [0,10,10],            [-45,45,135]))  # scene id 143
    scenes.append((3,      [0,20,20],            [-45,45,135]))  # scene id 144
    scenes.append((4,      [0,-20,-20,-20],      [-45,45,135,225]))  # scene id 145
    scenes.append((4,      [0,-10,-10,-10],      [-45,45,135,225]))  # scene id 146
    scenes.append((4,      [0,10,10,10],         [-45,45,135,225]))  # scene id 147
    scenes.append((4,      [0,20,20,20],         [-45,45,135,225]))  # scene id 148
    scenes.append((2,      [0,-20],              [0,90]))  # scene id 149
    scenes.append((2,      [0,-10],              [0,90]))  # scene id 150
    scenes.append((2,      [0,10],               [0,90]))  # scene id 151
    scenes.append((2,      [0,20],               [0,90]))  # scene id 152
    scenes.append((3,      [0,-20,-20],          [0,90,180]))  # scene id 153
    scenes.append((3,      [0,-10,-10],          [0,90,180]))  # scene id 154
    scenes.append((3,      [0,10,10],            [0,90,180]))  # scene id 155
    scenes.append((3,      [0,20,20],            [0,90,180]))  # scene id 156
    scenes.append((4,      [0,-20,-20,-20],      [0,90,180,270]))  # scene id 157
    scenes.append((4,      [0,-10,-10,-10],      [0,90,180,270]))  # scene id 158
    scenes.append((4,      [0,10,10,10],         [0,90,180,270]))  # scene id 159
    scenes.append((4,      [0,20,20,20],         [0,90,180,270]))  # scene id 160
    scenes.append((4,      [0,-20,-20,-20],      [-90,0,90,180]))  # scene id 161
    scenes.append((4,      [0,-10,-10,-10],      [-90,0,90,180]))  # scene id 162
    scenes.append((4,      [0,10,10,10],         [-90,0,90,180]))  # scene id 163
    scenes.append((4,      [0,20,20,20],         [-90,0,90,180]))  # scene id 164
    scenes.append((2,      [0,-20],              [45,135]))  # scene id 165
    scenes.append((2,      [0,-10],              [45,135]))  # scene id 166
    scenes.append((2,      [0,10],               [45,135]))  # scene id 167
    scenes.append((2,      [0,20],               [45,135]))  # scene id 168

    return scenes

def get_class_names():
    return ['alarm', 'baby', 'femaleSpeech',  'fire', 'crash',
            'dog', 'engine', 'footsteps', 'knock', 'phone',
            'piano', 'maleSpeech', 'femaleScreammaleScream']

def get_metric(sens_per_scene_class, spec_per_scene_class, metric_name, class_avg=False):
    if metric_name == 'BAC':
        metric_per_class_scene = (sens_per_scene_class + spec_per_scene_class)/2.
    elif metric_name == 'sens':
        metric_per_class_scene = sens_per_scene_class
    elif metric_name == 'spec':
        metric_per_class_scene = spec_per_scene_class
    else: # remark: BAC2 is not required for test set evaluation
        raise ValueError('the metric {} is not supported (need one of BAC, sens, spec)'.format(metric_name))

    if class_avg:
        return np.mean(metric_per_class_scene, axis=1) # here: only class averages
    else:
        return metric_per_class_scene


# this function should be called 3x in the evaluation: metric_name='BAC' (and ='sens' and ='spec)
def plot_metric_over_snr_per_nsrc(sens_per_scene_class, spec_per_scene_class, metric_name):
    metric_per_scene = get_metric(sens_per_scene_class, spec_per_scene_class, metric_name)
    test_scenes = get_test_scene_params()

    # plot metric over SNR for nSrc=1,2,3,4 (4 lines)
    #   - metric is averaged over all azimuths for the SNR/nSrc combination
    #   - metric is averaged over classes
    # wishlist: additionally two standard deviations would be nice :
    #   - std of metric w.r.t. classes (after averaging over azimuths)
    #   - std of metric w.r.t azimuths (after averaging over classes)

    colors = {1: 'black', 2: 'green', 3: 'blue', 4: 'red'} # key: nSrc
    SNRs_all = [-20, -10, 0, 10, 20]

    metric = {}
    metric_both_mean = {} # avg over azimuth and class
    metric_class_std = {} # avg over azimuth, std over class
    metric_azimuth_std = {} # avg over class, std over azimuth
    no_azimuths = {} # no of azimuths (to indicate std statistics samplesize)
    for nSrc in [1, 2, 3, 4]:
        if nSrc == 1:
            SNRs = [0]
        else:
            SNRs = SNRs_all

        for SNR in SNRs:
            metric[(nSrc,SNR)] = []
            # append all scenes with nSrc,SNR to the previous list
            for sceneid, (nSrc_scene, SNR_scene, azimuth_scene) in enumerate(test_scenes):
                # correction: nSrc 1 => SNR fixed 0; nSrc >1 => second element contains SNR w.r.t master
                SNR_scene = 0 if nSrc == 1 else SNR_scene[1]
                if nSrc == nSrc_scene and SNR == SNR_scene:
                     metric[(nSrc, SNR)].append(metric_per_scene[sceneid, :]) # classes still retained

            metric_class_mean = [np.mean(m) for m in metric[(nSrc, SNR)]] # only temporary needed
            metric_class_std[(nSrc, SNR)] = np.std(np.mean(metric[(nSrc, SNR)], axis=0))
            metric_azimuth_std[(nSrc, SNR)] = np.std(metric_class_mean)
            no_azimuths[(nSrc, SNR)] = len(metric_class_mean)
            metric_both_mean[(nSrc, SNR)] = np.mean(metric_class_mean)

        metric_both_mean_plot = [metric_both_mean[(nSrc, SNR)] for SNR in SNRs]
        metric_class_std_plot = [metric_class_std[(nSrc, SNR)] for SNR in SNRs]
        metric_azimuth_std_plot = [metric_azimuth_std[(nSrc, SNR)] for SNR in SNRs]
        if nSrc == 1:
            # extend nSrc 1 plot to cover whole SNR range (alternative: only marker at SNR=0)
            metric_both_mean_plot = metric_both_mean_plot * len(SNRs_all)
            metric_class_std_plot = metric_class_std_plot * len(SNRs_all)
            metric_azimuth_std_plot = metric_azimuth_std_plot * len(SNRs_all)

        metric_both_mean_plot = np.array(metric_both_mean_plot)
        metric_class_std_plot = np.array(metric_class_std_plot)
        metric_azimuth_std_plot = np.array(metric_azimuth_std_plot)
        no_azimuths_str = ' '.join([str(no_azimuths[(nSrc, SNR)] for SNR in SNRs)])

        # plot mean (class and azimuth)
        plt.plot(SNRs_all, metric_both_mean_plot, color=colors[nSrc],
                 label='nSrc {}'.format(nSrc))

        # plot std over class (azimuth avg)
        plt.fill_between(SNRs_all, metric_both_mean_plot+metric_class_std_plot,
                         metric_both_mean_plot-metric_class_std_plot,
                         facecolor=colors[0], alpha=0.4,
                         label=None if nSrc>1 else 'class std (azimuth avg)')

        # plot std over azimuths (class avg)
        plt.plot(SNRs_all, metric_both_mean_plot+metric_azimuth_std_plot, color=colors[0],
                 linestyle='dashed', label='azimuth std {} (class avg)'.format(no_azimuths_str))
        plt.plot(SNRs_all, metric_both_mean_plot-metric_azimuth_std_plot, color=colors[0],
                 linestyle='dashed')

    plt.title('test set '+metric_name+' over SNR (class/azimuth averaged)')
    plt.legend(loc='best')
    plt.ylabel(metric_name)
    plt.xlabel('SNR')

# this function should be called 3x in the evaluation: metric_name='BAC' (and ='sens' and ='spec)
def plot_metric_over_snr_per_class(sens_per_scene_class, spec_per_scene_class, metric_name):
    metric_per_class_scene = get_metric(sens_per_scene_class, spec_per_scene_class, metric_name)
    test_scenes = get_test_scene_params()

    # TODO: plotting stuff here -- without plt.figure / without plt.savefig


# this function should be called 3x in the evaluation: metric_name='BAC' (and ='sens' and ='spec)
def plot_metric_over_nsrc_per_class(sens_per_scene_class, spec_per_scene_class, metric_name):
    metric_per_class_scene = get_metric(sens_per_scene_class, spec_per_scene_class, metric_name)
    test_scenes = get_test_scene_params()

    # TODO: plotting stuff here -- without plt.figure / without plt.savefig

# plot testset evaluation and save csv files
# => input: sensitivity and specificity per scene per class each
#           of the two as array with shape (nscenes, nclasses) = (168, 13)
def evaluate_testset(sens_per_scene_class, spec_per_scene_class, name, folder):
    plt.figure()
    plt.suptitle('test set evaluation: {}'.format(name))

    # TODO: save all plotted arrays also to a file in folder that can be loaded in python or matlab (e.g. hdf5)
    # => the functions called below could save these arrays by themselves or return an array
    #    that is collected and written to disk

    plt.subplot(3, 3, 1)
    plt.title('BAC')
    plot_metric_over_snr_per_nsrc(sens_per_scene_class, spec_per_scene_class, 'BAC')
    plt.subplot(3, 3, 2)
    plt.title('sensitivity')
    plot_metric_over_snr_per_nsrc(sens_per_scene_class, spec_per_scene_class, 'sens')
    plt.subplot(3, 3, 3)
    plt.title('specificity')
    plot_metric_over_snr_per_nsrc(sens_per_scene_class, spec_per_scene_class, 'spec')

    plt.subplot(3, 3, 4)
    plot_metric_over_snr_per_class(sens_per_scene_class, spec_per_scene_class, 'BAC')
    plt.subplot(3, 3, 5)
    plot_metric_over_snr_per_class(sens_per_scene_class, spec_per_scene_class, 'sens')
    plt.subplot(3, 3, 6)
    plot_metric_over_snr_per_class(sens_per_scene_class, spec_per_scene_class, 'spec')

    plt.subplot(3, 3, 7)
    plot_metric_over_nsrc_per_class(sens_per_scene_class, spec_per_scene_class, 'BAC')
    plt.subplot(3, 3, 8)
    plot_metric_over_nsrc_per_class(sens_per_scene_class, spec_per_scene_class, 'sens')
    plt.subplot(3, 3, 9)
    plot_metric_over_nsrc_per_class(sens_per_scene_class, spec_per_scene_class, 'spec')

    plt.savefig(os.path.join(folder, 'testset_evaluation.png'))
