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

        import historical
        importlib.reload(historical)
        historical.updateGSheetHistory()
        historical.loadAllHist(timeFrame='hour')

        import analysis
        importlib.reload(analysis)
        analysis.getSignalAllPreset()

        import mornitor
        importlib.reload(mornitor)
        mornitor.AllUser()
        mornitor.Reset()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
    finally:
        #time.sleep(60*5)
        time.sleep(60*1)
        pass