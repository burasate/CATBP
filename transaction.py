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

def getPortfolio (*_):
    sheetName = 'Portfolio'
    sheetData = gSheet.getAllDataS(sheetName)
    column = gSheet.getWorksheetColumnName(sheetName)
    df = pd.DataFrame.from_records(sheetData)

    if df.empty:
        for col in column:
            df[col] = []

        df['idName'] = list(configJson)
        df['coin'].fillna('THB',inplace=True)
        df['available'].fillna(1000000.0, inplace=True)
        df['reserved'].fillna(0.0,inplace=True)

        csvPath = dataPath + '/portfolio.csv'
        df.to_csv(csvPath,index=False)
        gSheet.updateFromCSV(csvPath, sheetName)
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

getLastEntry('user1')