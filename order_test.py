#Transaction Testing
import os,json,requests,time
from datetime import datetime as dt
import pandas as pd
import kbApi
import gSheet

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
histPath = dataPath + '/hist'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))
systemPath = dataPath + '/system.json'
systemJson = json.load(open(systemPath))

balancePath = dataPath + '/balance.csv'
balanceSheet = 'Balance'
progressPath = dataPath + '/progress.csv'
progressSheet = 'progress'

def getBalance(idName):
    sheetData = gSheet.getAllDataS(balanceSheet)
    column = gSheet.getWorksheetColumnName(balanceSheet)
    df = pd.DataFrame.from_records(sheetData)

    if df.empty:
        for col in column:
            df[col] = []

        df['idName'] = list(configJson)
        df['coin'].fillna('THB',inplace=True)
        df['available'].fillna(1000000.0, inplace=True)

    df.to_csv(balancePath, index=False)

    df = df[df['idName'] == idName]
    return df

def getLastEntry(idName):
    preset = configJson[idName]['preset']
    system = configJson[idName]['system']
    symbol_count = systemJson[system]['symbolCount']

    print ('Get Entry Signal For {}  {}  {}'.format(idName,preset,system))
    df = pd.read_csv(dataPath + '/signal.csv')
    df = df[df['Preset'] == preset]
    last_date = df['Rec_Date'].tail(1).tolist()[0]
    #print(last_date)
    df = df[df['Rec_Date'] == last_date]
    df = df.sort_values(['Change4HR%'], ascending=[True])
    df = df.head(symbol_count)
    df.reset_index(inplace=True)

    #print(df)
    #print(df[['Symbol','Close']])
    print('Found {} Entry Signal\nWill return as dataframe'.format(df.shape[0]))
    return df

def testBuy(idName,symbol,amount,rate):
    coin = symbol.split('_')[-1]
    system = configJson[idName]['system']
    commission = systemJson[system]['percentageComission'] / 100
    userDF = getBalance(idName)

    if not coin in userDF['coin'].tolist():
        data = {
            'idName' : [idName],
            'coin' : [coin],
            'available' : [0.0]
        }
        userDF = userDF.append(pd.DataFrame(data))

    # Wallet Checking
    thb = userDF.loc[userDF['coin'] == 'THB']['available']
    thb = float(thb)
    coin_available = userDF.loc[userDF['coin'] == coin]['available']
    coin_available = float(coin_available)
    if amount > thb:
        return None

    userDF.loc[userDF['coin'] == coin,['available']] = (amount/rate) + coin_available
    userDF.loc[userDF['coin'] == 'THB',['available']] = (thb-amount) - (amount*commission)

    #Update Data
    df = pd.read_csv(balancePath)
    df = df.append(userDF)
    df.drop_duplicates(['idName','coin'], keep='last', inplace=True)
    df.reindex()
    df.to_csv(balancePath,index=False)
    gSheet.updateFromCSV(balancePath,balanceSheet)



#getLastEntry('user1')
testBuy('user1','THB_DOGE',100,16.5)