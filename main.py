import time,os,sys
import importlib
rootPath = os.path.dirname(os.path.abspath(__file__))

os.system('cls||clear')
print('BitPy')
time.sleep(15)
import update

if not os.name == 'nt':
    time.sleep(15)
    update.updateAllFile()

while True:
    try:
        update.updateConfig()
        update.updatePreset()
        update.updateSystem()

        import mornitor
        mornitor.Reset()

        import historical
        importlib.reload(historical)
        historical.updateGSheetHistory()
        historical.loadAllHist(timeFrame='hour')

        import analysis
        importlib.reload(analysis)
        analysis.getSignalAllPreset()

        importlib.reload(mornitor)
        mornitor.AllUser()

    except Exception as e:
        print('!!!! ==========================')
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print('Error Type {}\nFile {}\n Line {}'.format(exc_type, fname, exc_tb.tb_lineno))
        print('!!!! ==========================')
    finally:
        time.sleep(60*5)
        pass