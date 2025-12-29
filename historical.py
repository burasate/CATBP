import os, json, requests, time, subprocess
from datetime import datetime as dt
import pandas as pd
import numpy as np
import kbApi
import gSheet

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

base_path = os.path.dirname(os.path.abspath(__file__))
dataPath = base_path+'/data'
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
    sheet_rec = gSheet.getAllDataS('History')
    print('row count {}'.format(len(sheet_rec)))
    all_hist_path  = dataPath + '/cryptoHist.csv'
    if sheet_rec == []: # Will update for Empty gsheet
        gSheet.updateFromCSV(all_hist_path, 'History')
        df = pd.read_csv(all_hist_path)
    elif not 'epoch' in sheet_rec[0]: # Will update if no collums
        gSheet.updateFromCSV(all_hist_path, 'History')
        df = pd.read_csv(all_hist_path)
    else:
        df = pd.DataFrame.from_records(sheet_rec)
        df = df.dropna(subset=['epoch'])
    return df

def updateGSheetHistory(days_limit = 6):
    ticker = kbApi.getTicker()
    sym_count = len(list(ticker))
    symbols = kbApi.getSymbol()

    df = pd.DataFrame()
    df = pd.concat([df, getHistDataframe()], ignore_index=True)

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
    backup_list = sorted(os.listdir(dataPath + '/hist_backup'))
    backup_sel = backup_list[-20:]
    clear_backup_list = [i for i in os.listdir(dataPath + '/hist_backup') if not i in backup_sel]
    for f in backup_sel:
        file_path = dataPath + '/hist_backup/{}'.format(f)
        print('Load : {}'.format(os.path.basename(file_path)))
        try:
            df = pd.concat([df, pd.read_csv(file_path).sort_values(['dateTime'],ascending=[True]).tail(5000)], ignore_index=True)
        except:
            print('Can\'t Read {}   Column DateTime..'.format(file_path))
        else:
            pass
    # remove longtime backup
    for f in clear_backup_list:
        file_path = dataPath + '/hist_backup/{}'.format(f)
        os.remove(file_path)

    # Append all hist csv
    all_hist_path = dataPath + '/cryptoHist.csv'
    if not df.empty:
        df = pd.concat([df, pd.read_csv(all_hist_path).tail(3000)], ignore_index=True)

    os.system('cls||clear')
    column_ls = []
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
            #print('sinal csv is EMPTY : ', signal_df.empty)
        except:
            signal_df = pd.read_csv(dataPath + '/signal_gsheet.csv')

        try:
            signal_df = signal_df[
                (signal_df['Rec_Date'] == signal_df['Rec_Date'].max()) &
                (signal_df['Symbol'] == sym)
                ]

            sma_s = signal_df['SMA_S'].mean().round(2)
            sma_l = signal_df['SMA_L'].mean().round(2)
            rowData['percentChangeAverage'] = ((sma_s - sma_l) / sma_l) * 100
            rowData['percentChangeAverage'] = round(rowData['percentChangeAverage'],1)
            #print('macd {}/{}   {}%'.format(sma_s,sma_l,rowData['percentChangeAverage']))
        except Exception as e:
            import traceback
            print('* load indicator error')
            rowData['percentChangeAverage'] = 0.0
            #print(str(traceback.format_exc()).split('\n')[-1])
            pass
        else:
            rowData['isTopGain'] = 'No'
            pass

        #append data row
        df = pd.concat([df, pd.DataFrame(rowData)], ignore_index=True)

        if column_ls != list(rowData):
            column_ls = list(rowData)

    # delete duplicate
    df.drop_duplicates(['symbol','date','hour','minute'], keep='last', inplace=True)
    #cleanup & sort
    epoch_limit = time.time() - (((days_limit*24)*60)*60)
    df.dropna(subset=['dateTime'],inplace=True)
    df.dropna(subset=['epoch'],inplace=True)
    df['epoch'] = pd.to_numeric(df['epoch'], errors='coerce')
    df['dateTime'] = df['dateTime'].astype(str)
    df = df[df['dateTime'] != 'nan']
    #df = df.sort_values(['epoch'], ascending=[True])
    df = df.sort_values(['epoch', 'date'], ascending=[True, True])
    df.sort_index(inplace=True)
    df = df.drop( df[(df['date'].str.isdigit() == True)].index )
    df = df.drop( df[(df['dateTime'].str.isdigit() == True)].index )
    df = df.drop( df[(df['epoch'] < epoch_limit)].index )
    #Limit row
    df = df.tail(days_limit * 24 * 60 * sym_count)
    df.reset_index(inplace=True)

    #top gain
    topGain = df.drop_duplicates(subset=['symbol'], keep='last').dropna()
    topGain = topGain.sort_values(['percentChangeAverage'], ascending=[False])
    topGain = topGain.head(10)['symbol'].tolist()
    df['isTopGain'] = 'No'
    for symbol in topGain:
        df.loc[df['symbol'] == symbol, 'isTopGain'] = 'Yes'

    print('Save Historical Data...')
    df.dropna(inplace=True)
    if column_ls != []:
        print('- Check column {}'.format(column_ls))
        df = df[column_ls]
    for i in ['index', 'level_0']:
        if i in df.columns.tolist():
            df.drop(columns=[i], inplace=True)
    print('- Clean up data')
    df.to_csv(all_hist_path, index=False)
    df.tail(10000).to_csv(backupPath, index=False)

    #ticker update
    print('Save Ticker Data...')
    tickerPath = dataPath + '/ticker.csv'
    ticker_df = df
    ticker_df.drop_duplicates(subset=['symbol'], keep='last', inplace=True)
    ticker_df = ticker_df[ticker_df['date'] == ticker_df['date'].max()]
    ticker_df = ticker_df[ticker_df['hour'] == ticker_df['hour'].max()]
    ticker_df.to_csv(tickerPath, index=False)

    '''
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
    '''
    subproc_update_gsheet_hist()

def update_gsheet_hist(gsheet_row_limit = 30000):
    all_hist_path = dataPath + '/cryptoHist.csv'
    gsheet_all_hist_path = dataPath + '/crypto_hist_gsheet.csv'
    ticker_path = dataPath + '/ticker.csv'

    #Prepare gsheet csv
    hist_df = pd.read_csv(all_hist_path)
    hist_df = hist_df.sort_values(['epoch', 'date'], ascending=[True, True])
    hist_df.drop_duplicates(['symbol','date','hour'], keep='last', inplace=True)
    hist_df.reset_index(inplace=True, drop=True)
    hist_df = hist_df.tail(gsheet_row_limit)
    hist_df.to_csv(gsheet_all_hist_path, index=False)

    st_time = time.time()
    while True:
        print('Uploading.....')
        try:
            if not os.name == 'nt':  # for raspi
                print('uploading history data...')
                gSheet.updateFromCSV(gsheet_all_hist_path, 'History')
                gSheet.updateFromCSV(ticker_path, 'Ticker')
                print('upload history data finish')
        except:
            pass
        time.sleep(15)  # Waiting Upload
        if gSheet.getAllDataS('History') != []:
            break
    print('uploading duration {} minute'.format((time.time() - st_time) / 60))
    time.sleep(2)

def subproc_update_gsheet_hist():
    import shlex
    command = '''
import sys, os
if not \'{0}\' in sys.path:
    sys.path.insert(0,\'{0}\')
import historical
historical.update_gsheet_hist()
    '''.format(base_path)

    is_posix = os.name == 'posix'  # raspi os
    if is_posix:
        venv_path = os.path.expanduser('~/.env/bin/activate')

        if os.path.exists(venv_path):
            cmd = f'source {venv_path} && python3 -c {shlex.quote(command)}'
        else:
            cmd = f'python3 -c {shlex.quote(command)}'
        subprocess.call([
            'lxterminal',
            '--geometry=75x1+0+0',
            '-e',
            'bash',
            '-c',
            cmd
        ])
    else:
        subprocess.call(
            [r'D:\GDrive\Documents\2021\bitkubPy\venv\Scripts\python.exe', '-c', command]
        )  # for testing
        # ,creationflags=subprocess.CREATE_NEW_CONSOLE) # for run on pc

def createSymbolHistory(symbol,timeFrame = 'minute'):
    csv_path = histPath + os.sep + symbol + '.csv'
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
    histDF['open'] = histDF['open'].ffill()
    histDF['close'] = histDF.groupby(group)['last'].tail(1)
    histDF['close'] = histDF['close'].ffill()

    #delete sub timeframe duplicate and clean up
    histDF.drop_duplicates(group, keep='last', inplace=True)
    histDF = histDF.tail(201)
    histDF.reset_index(inplace=True)

    if histDF['close'].index.tolist() == []:
        if os.path.exists(csv_path):
            os.remove(csv_path)
        return None
    if histDF['close'].index.tolist()[-1] < 50:
        if os.path.exists(csv_path):
            os.remove(csv_path)
        print('!! WARNNING ROW < 50:\nrow count is less than 50\nCheck Hist Data!')
        return None

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
    df.to_csv(csv_path,index=False)
    print('total hours ',df.shape[0])
    time.sleep(0.05)

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

def rec_price(*_):
    all_hist_path = dataPath + '/cryptoHist.csv'
    try:
        df = pd.read_csv(all_hist_path)
    except:
        backup_dir = dataPath + '/hist_backup'
        backup_path_list = [backup_dir + '/' + i for i in sorted(os.listdir(backup_dir))]
        df = pd.read_csv(backup_path_list[-2])
    if df.empty:
        print(f'\nError - {all_hist_path}\nDataframe is empty Please check csv file or using backup')
    #print(df.columns.tolist())

    ticker = kbApi.getTicker()
    ticker_count = len(list(ticker))
    #print(ticker)

    for sym in ticker:
        data = {
            'date': dt.now().strftime('%Y-%m-%d'),
            'hour': int(dt.now().strftime('%H')),
            'epoch': time.time(),
            'minute': int(dt.now().strftime('%M')),
            'second': int(dt.now().strftime('%S')),
            'symbol': sym,
            'dateTime': dt.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        for i in ticker[sym]:
            data[i] = ticker[sym][i]
        #import pprint
        #pprint.pprint(data)
        df = pd.concat([df, pd.DataFrame.from_records([data])], ignore_index=True)

    df.reset_index(inplace=True, drop=True)
    for i in ['index', 'level_0']:
        if i in df.columns.tolist():
            df.drop(columns=[i], inplace=True)
    df.to_csv(all_hist_path, index=False)
    print( df.tail(ticker_count)[['symbol', 'dateTime', 'last']] )
    time.sleep(0.5)

if __name__ == '__main__':
    #createSymbolHistory('THB_WAN','hour')
    #updateGSheetHistory()
    #loadAllHist(timeFrame='hour')
    #subproc_update_gsheet_hist()
    #update_gsheet_hist()
    print(getHistDataframe())
    #rec_price()
    pass
