import time,os

rootPath = os.path.dirname(os.path.abspath(__file__))

print('BitPy')

if not os.name == 'nt':
    time.sleep(60)
    import update
    update.updateAllFile()
    update.updateConfig()
    update.updatePreset()
    update.updateSystem()
    
import historical
historical.updateGSheetHistory()
historical.loadAllHist(timeFrame='hour')

import analysis
analysis.getSignalAllPreset()