import time,os

rootPath = os.path.dirname(os.path.abspath(__file__))

print('BitPy')

if not os.name == 'nt':
    import update
    update.updateConfig()
    update.updatePreset()
    update.updateAllFile()

import historical
historical.updateGSheetHistory()
historical.loadAllHist()
