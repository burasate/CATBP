import os,json,requests,time,random,sys
from datetime import datetime as dt
import kbApi
import gSheet

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath + '/data'
configPath = dataPath + '/config.json'
presetPath = dataPath + '/preset.json'
systemPath = dataPath + '/system.json'
configJson = json.load(open(configPath))
presetJson = json.load(open(presetPath))
systemJson = json.load(open(systemPath))

def getHistDataframe(*_):
    df = pd.DataFrame()
    sheetData = gSheet.getAllDataS('History')

    for row in sheetData:
        rowData = {}
        for colName in row:
            rowData[colName] = [row[colName]]
        df = df.append(
            pd.DataFrame(rowData),ignore_index=True
        )
    df.sort_index(inplace=True)
    return df

def updateGSheetHistory(*_):
    ticker = kbApi.getTicker()
    symbols = kbApi.getSymbol()
    header = gSheet.getWorksheetColumnName('History')

    isReverse = bool(random.randint(0, 1))
    if isReverse:
        symbols = symbols.reverse()

    os.system('cls||clear')

    for data in symbols:
        sym = data['symbol']
        if not sym in ticker:
            continue

        data = {
            'date': dt.now().strftime('%Y-%m-%d'),
            'hour': int(dt.now().strftime('%H')),
            'epoch': time.time(),
            'minute': int(dt.now().strftime('%M')),
            'second': int(dt.now().strftime('%S')),
            'symbol' : sym,
            'dateTime' : dt.now().strftime('%Y-%m-%d %H:%M:%S'),
            #'percentChangeAverage' : '',
            #'isTopGain' : ''
        }

        for i in ticker[sym]:
            data[i] = ticker[sym][i]
        #print(data)

        row = []
        for col in header:
            if not col in list(data):
                row.append('')
            else:
                row.append(data[col])
        print(row)

        gSheet.addRow('History',row)

print('BitPy Price Updater')
if not os.name == 'nt':
    time.sleep(30)
    import update
    update.updateAllFile()
    update.updateConfig()
    update.updatePreset()
    update.updateSystem()

    while True:
        try:
            updateGSheetHistory()
        except Exception as e:
            print('!!!! ==========================')
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print('Error Type {}\nFile {}\n Line {}'.format(exc_type, fname, exc_tb.tb_lineno))
            print('!!!! ==========================')
            time.sleep(5)
        else:
            time.sleep(60)


