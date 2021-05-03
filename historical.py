import os,json,requests
from datetime import datetime as dt
import pandas as pd
import kbApi
import gSheet

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))

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

    df = pd.DataFrame()
    df = df.append(getHistDataframe())

    date_hour = dt.now().strftime('%Y-%m-%d %H:00:00')
    date = dt.now().strftime('%Y-%m-%d')
    hour = dt.now().strftime('%H')

    os.system('cls||clear')
    for data in symbols:
        sym = data['symbol']
        if not sym in ticker:
            continue

        print('{}  last {}'.format(sym,ticker[sym]['last']))

        rowData = {
            'dateHour': date_hour,
            'date': date,
            'hour': hour,
            'symbol': sym
        }
        for colName in ticker[sym]:
            rowData[colName] = [ticker[sym][colName]]
        df = df.append(
            pd.DataFrame(rowData), ignore_index=True
        )

    # delet duplicate
    df.drop_duplicates(['symbol', 'date'], keep='last', inplace=True)
    df.sort_index(inplace=True)
    # print(df)

    histPath = dataPath + '/cryptoHist.csv'
    df.to_csv(histPath, index=False)

    gSheet.updateFromCSV(histPath, 'History')

if __name__ == '__main__':
    updateGSheetHistory()

