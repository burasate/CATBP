import time,os

rootPath = os.path.dirname(os.path.abspath(__file__))

print('BitPy')

import update
if not os.name == 'nt':
    time.sleep(60)
    update.updateAllFile()

while True:
    try:
        update.updateConfig()
        update.updatePreset()
        update.updateSystem()

        import historical
        historical.updateGSheetHistory()
        historical.loadAllHist(timeFrame='hour')

        import analysis
        analysis.getSignalAllPreset()

        import mornitor
        mornitor.AllUser()
    except Exception as e:
        print(e)
    finally:
        time.sleep(30)