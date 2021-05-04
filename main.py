import time,os

rootPath = os.path.dirname(os.path.abspath(__file__))

import historical
historical.updateGSheetHistory()
historical.loadAllHist()