import os,json,requests,time
from datetime import datetime as dt
import pandas as pd
import numpy as np
import kbApi
import gSheet

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
histPath = dataPath + '/hist'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))

def isInternetConnect(*_):
    url = 'http://google.com'
    connectStatus = requests.get(url).status_code
    if connectStatus == 200:
        return True
    else:
        return False

def getHistDataframe(*_):
    print('load history data from google sheet...')
    sheetData = gSheet.getAllDataS('History')
    print('row count {}'.format(len(sheetData)))
    if sheetData == []:
        allHistPath = dataPath + '/cryptoHist.csv'
        gSheet.updateFromCSV(allHistPath, 'History')
        df = pd.read_csv(allHistPath)
    else:
        df = pd.DataFrame.from_records(sheetData)
    return df

def updateGSheetHistory(limit = 47000):
    ticker = kbApi.getTicker()
    symbols = kbApi.getSymbol()

    df = pd.DataFrame()
    df = df.append(getHistDataframe())

    date = dt.now().strftime('%Y-%m-%d')
    hour = int(dt.now().strftime('%H'))
    minute = int(dt.now().strftime('%M'))
    second = int(dt.now().strftime('%S'))
    date_time = str(dt.now().strftime('%Y-%m-%d %H:%M:%S'))

    #backup hist
    backupPath = dataPath + '/hist_backup/cryptoHist_{}_{}.csv'.format(date.replace('-','_'),0)
    if hour >= 8 and hour <= 16 :
        backupPath = dataPath + '/hist_backup/cryptoHist_{}_{}.csv'.format(date.replace('-', '_'), 1)
    elif hour > 16 :
        backupPath = dataPath + '/hist_backup/cryptoHist_{}_{}.csv'.format(date.replace('-', '_'), 2)
    df.to_csv(backupPath, index=False)
    #spare backup path
    backupPath = dataPath + '/hist_backup/cryptoHist_{}_{}.csv'.format(date.replace('-', '_'), 3)

    # append backup
    backupList = os.listdir(dataPath + '/hist_backup')
    backupList.sort()
    if len(backupList) > 10:
        backupList = backupList[-10:]
    for f in backupList:
        filePath = dataPath + '/hist_backup/{}'.format(f)
        print('Read [ {} ]'.format(filePath))
        try:
            df = df.append(
                pd.read_csv(filePath).sort_values(['dateTime'],ascending=[True]).tail(5000), ignore_index=True
            )
        except:
            print('Can\'t Read {}   Column DateTime..'.format(filePath))
        else:
            pass

    os.system('cls||clear')
    for data in symbols:
        sym = data['symbol']
        if not sym in ticker:
            continue

        print('{}   {} Baht'.format(sym,ticker[sym]['last']))

        epoch = float(time.time())
        rowData = {
            'epoch': epoch,
            'date': date,
            'hour': hour,
            'minute': minute,
            'second': second,
            'symbol': sym,
            'dateTime': date_time
        }

        #bitkub api data
        for colName in ticker[sym]:
            rowData[colName] = [ticker[sym][colName]]

        #signal data
        #indicator (signal in metric)
        try:
            signal_df = pd.read_csv(dataPath + '/signal.csv')
            print('sinal csv is EMPTY : ',signal_df.empty)
            if signal_df.empty:
                signal_df = pd.read_csv(dataPath + '/signal_gsheet.csv')
            signal_df = signal_df[
                (signal_df['Rec_Date'] == signal_df['Rec_Date'].max()) &
                (signal_df['Symbol'] == sym)
                ]

            sma_s = signal_df['SMA_S'].mean().round(2)
            sma_l = signal_df['SMA_L'].mean().round(2)
            rowData['percentChangeAverage'] = ((sma_s - sma_l) / sma_l) * 100
            #print('macd {}/{}   {}%'.format(sma_s,sma_l,rowData['percentChangeAverage']))
        except Exception as e:
            import traceback
            print('* load indicator error')
            #print(str(traceback.format_exc()).split('\n')[-1])
            pass
        else:
            rowData['isTopGain'] = 'No'
            pass

        #append data row
        df = df.append(
            pd.DataFrame(rowData), ignore_index=True
        )

    # delete duplicate
    df.drop_duplicates(['symbol','date','hour','minute'], keep='last', inplace=True)
    #cleanup & sort
    epoch_limit = time.time() - (((5*24)*60)*60)
    df.dropna(subset=['epoch','dateTime'],inplace=True)
    df['epoch'] = pd.to_numeric(df['epoch'], errors='coerce')
    df['dateTime'] = df['dateTime'].astype(str)
    df = df[df['dateTime'] != 'nan']
    #df = df.sort_values(['epoch'], ascending=[True])
    df = df.sort_values(['epoch', 'date'], ascending=[True, True])
    df.sort_index(inplace=True)
    df = df.drop( df[(df['date'].str.isdigit() == True)].index )
    df = df.drop( df[(df['dateTime'].str.isdigit() == True)].index )
    df = df.drop( df[(df['epoch'] < epoch_limit)].index )
    #limit row
    df = df.tail(limit)
    df.reset_index(inplace=True)

    #top gain
    topGain = df.drop_duplicates(subset=['symbol'], keep='last').dropna()
    topGain = topGain.sort_values(['percentChangeAverage'], ascending=[False])
    topGain = topGain.head(10)['symbol'].tolist()
    df['isTopGain'] = 'No'
    for symbol in topGain:
        df.loc[df['symbol'] == symbol, 'isTopGain'] = 'Yes'

    print('Save Historical Data...')
    allHistPath = dataPath + '/cryptoHist.csv'
    df = df[list(rowData)]
    df.to_csv(allHistPath, index=False)
    df.tail(5000).to_csv(backupPath, index=False)

    #ticker update
    print('Save Ticker Data...')
    tickerPath = dataPath + '/ticker.csv'
    ticker_df = df
    ticker_df.drop_duplicates(subset=['symbol'], keep='last', inplace=True)
    ticker_df = ticker_df[ticker_df['date'] == ticker_df['date'].max()]
    ticker_df = ticker_df[ticker_df['hour'] == ticker_df['hour'].max()]
    ticker_df.to_csv(tickerPath, index=False)

    st_time = time.time()
    while True:
        print('Uploading.....')
        try:
            if not os.name == 'nt': #for raspi
                print('uploading history data...')
                gSheet.updateFromCSV(allHistPath, 'History')
                gSheet.updateFromCSV(tickerPath, 'Ticker')
                print('upload history data finish')
        except: pass
        time.sleep(15) #Waiting Upload
        if gSheet.getAllDataS('History') != []:
            break
    print('uploading duration {} minute'.format( (time.time() - st_time)/60 ))
    time.sleep(2)

def createSymbolHistory(symbol,timeFrame = 'minute'):
    os.system('cls||clear')
    print('create price history ... {}  time frame {}'.format(symbol,timeFrame.upper()))
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

    allHistPath = dataPath + '/cryptoHist.csv'
    histDF = pd.read_csv(allHistPath)
    histDF = histDF[histDF['symbol'] == symbol]
    histDF = histDF.sort_values(['epoch'], ascending=[True])
    histDF.reset_index(inplace=True)

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
    df['Date'] = histDF['dateTime']
    df['Close'] = histDF['close'].round(2)
    df['adjClose'] = histDF['close'].round(2)
    df['Open'] = histDF['open'].round(2)
    df['Low'] = histDF['low'].round(2)
    df['High'] = histDF['high'].round(2)
    df['Volume'] = ((histDF['baseVolume'] + histDF['quoteVolume'])/2).diff(4).abs()
    df['Volume'] = df['Volume'].fillna(0)
    #df['Volume'] = histDF['baseVolume']-histDF['baseVolume'].abs()
    #df['Volume'] = df['Volume'].abs()
    #df['Volume'] = histDF['baseVolume']
    df['Day'] = histDF.index

    #revese index and save
    df = df.sort_index(ascending=False)
    symbolPath = histPath + os.sep + symbol + '.csv'
    df.to_csv(symbolPath,index=False)

def loadAllHist(timeFrame = 'minute'):
    """
    for f in os.listdir(histPath):
        os.remove(histPath + os.sep + f)
    """

    ticker = kbApi.getTicker()
    symbols = kbApi.getSymbol()
    for data in symbols:
        sym = data['symbol']
        if not sym in ticker:
            continue
        createSymbolHistory(sym,timeFrame)

if __name__ == '__main__':
    #createSymbolHistory('THB_WAN','hour')
    updateGSheetHistory()
    #loadAllHist(timeFrame='hour')
    pass
