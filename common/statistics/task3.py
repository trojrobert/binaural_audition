from SceneInstance import SceneInstance
from Scene import *
from Group import *






sI = SceneInstance("train",1,"generalSoundsNI.alarm.Alarm_FactoryBuzzer_Loop_SFX-KIT.wav.mat") 
sI.plotMergedLabelLengthDistribution()

sI = SceneInstance("train",2,"generalSoundsNI.alarm.Alarm_FactoryBuzzer_Loop_SFX-KIT.wav.mat") 
sI.plotMergedLabelLengthDistribution()

#todo: 3Sources
#todo: 4Sources








s = Scene("train", 1)
s.plotMergedLabelLengthDistribution()

s = Scene("train", 2)
s.plotMergedLabelLengthDistribution()

#todo: 3Sources
#todo: 4Sources



#g = Group("train")
#g.plotMergedLabelLengthDistribution()
