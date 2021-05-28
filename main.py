import time,os
import importlib

rootPath = os.path.dirname(os.path.abspath(__file__))

print('BitPy')
time.sleep(15)
import update
if not os.name == 'nt':
    time.sleep(45)
    update.updateAllFile()

while True:
    try:
        update.updateConfig()
        update.updatePreset()
        update.updateSystem()

        #import historical
        #importlib.reload(historical)
        #historical.updateGSheetHistory()
        #historical.loadAllHist(timeFrame='hour')

        #import analysis
        #importlib.reload(analysis)
        #analysis.getSignalAllPreset()

        import mornitor
        importlib.reload(mornitor)
        mornitor.Reset()
        mornitor.AllUser()
    except Exception as e:
        print(e)
    finally:
        #time.sleep(60*5)
        time.sleep(60*1)
        pass
    if not os.name == 'nt':
        update.updateAllFile()
