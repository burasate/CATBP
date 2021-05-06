import os,json,requests,time
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
    print('load history data from google sheet...')
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

    date = dt.now().strftime('%Y-%m-%d')
    hour = int(dt.now().strftime('%H'))
    epoch = time.time()
    minute = int(dt.now().strftime('%M'))
    second = int(dt.now().strftime('%S'))
    date_time = dt.now().strftime('%Y-%m-%d %H:%M:%S')

    #backup hist
    backupPath = dataPath + '/hist_backup/cryptoHist_{}.csv'.format(date.replace('-','_'))
    df.to_csv(backupPath, index=False)

    os.system('cls||clear')
    for data in symbols:
        sym = data['symbol']
        if not sym in ticker:
            continue

        print('{}   {} Baht'.format(sym,ticker[sym]['last']))

        rowData = {
            'epoch': epoch,
            'date': date,
            'hour': hour,
            'minute': minute,
            'second': second,
            'symbol': sym,
            'dateTime': date_time
        }

        for colName in ticker[sym]:
            rowData[colName] = [ticker[sym][colName]]
        df = df.append(
            pd.DataFrame(rowData), ignore_index=True
        )

    # delet duplicate
    df.drop_duplicates(['symbol','date','hour','minute'], keep='last', inplace=True)
    df.sort_index(inplace=True)
    #limit row
    df = df.tail(15000)
    # print(df)

    histPath = dataPath + '/cryptoHist.csv'
    df.to_csv(histPath, index=False)

    print('uploading history data...')
    gSheet.updateFromCSV(histPath, 'History')
    print('upload history data finish')

def createSymbolHistory(symbol,timeFrame = 'minute'):
    print('create price history ... {}'.format(symbol))
    df = pd.DataFrame(
        {
            'Day' : [],
            'Date' : [],
            'Open' : [],
            'High' : [],
            'Low' : [],
            'Close' : [],
            'adjClose' : [],
            'Volume' : []
        }
    )

    histPath = histPath = dataPath + '/cryptoHist.csv'
    histDF = pd.read_csv(histPath)
    histDF = histDF[histDF['symbol'] == symbol]

    #set timeframe
    if timeFrame == 'minute':
        group = ['symbol','date','hour','minute']
    elif timeFrame == 'hour':
        group = ['symbol','date','hour']
    elif timeFrame == 'day':
        group = ['symbol','date']

    #transfrom low high by timeframe grp
    histDF['low'] = histDF.groupby(group)['last'].transform('min')
    histDF['high'] = histDF.groupby(group)['last'].transform('max')
    histDF['open'] = histDF.groupby(group)['last'].head(1)
    histDF['open'] = histDF['open'].fillna(method='ffill')
    histDF['close'] = histDF.groupby(group)['last'].tail(1)
    histDF['close'] = histDF['close'].fillna(method='ffill')

    #delete sub timeframe duplicate and clean up
    histDF.drop_duplicates(group, keep='last', inplace=True)
    histDF = histDF.tail(101)
    histDF.reset_index(inplace=True)

    # assign df
    df['Date'] = histDF['date']
    df['Close'] = histDF['close'].round(2)
    df['adjClose'] = histDF['close'].round(2)
    df['Open'] = histDF['open'].round(2)
    df['Low'] = histDF['low'].round(2)
    df['High'] = histDF['high'].round(2)
    df['Volume'] = histDF['baseVolume'].round(0)
    df['Day'] = histDF.index

    #revese index and save
    df = df.sort_index(ascending=False)
    symbolPath = dataPath + '/hist/' + symbol + '.csv'
    df.to_csv(symbolPath,index=False)

def loadAllHist(timeFrame = 'minute'):
    symbols = kbApi.getSymbol()
    for data in symbols:
        sym = data['symbol']
        createSymbolHistory(sym,timeFrame)

if __name__ == '__main__':
    #updateGSheetHistory()
    #createSymbolHistory('THB_DOGE')
    loadAllHist(timeFrame='minute')
