import time,os

rootPath = os.path.dirname(os.path.abspath(__file__))

print('BitPy')

import update
if not os.name == 'nt':
    time.sleep(60)
    update.updateAllFile()

update.updateConfig()
update.updatePreset()
update.updateSystem()


import historical
historical.updateGSheetHistory()
historical.loadAllHist(timeFrame='hour')

import analysis
analysis.getSignalAllPreset()
