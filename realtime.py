import os,json,requests,time
from datetime import datetime as dt
import pandas as pd
import gSheet
from bitkub import Bitkub

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
histPath = dataPath + '/hist'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))

bitkub = Bitkub()

print(bitkub.ticker())