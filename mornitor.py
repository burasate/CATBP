import pandas as pd
import json
import os
import datetime as dt
import gSheet
import kbApi
import lineNotify
import time

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
histPath = dataPath + '/hist'
imgPath = dataPath + '/analysis_img'
configPath = dataPath + '/config.json'
presetPath = dataPath + '/preset.json'
systemPath = dataPath + '/system.json'
configJson = json.load(open(configPath))
presetJson = json.load(open(presetPath))
systemJson = json.load(open(systemPath))

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

def isInternetConnect(*_):
    url = 'http://google.com'
    connectStatus = requests.get(url).status_code
    if connectStatus == 200:
        return True
    else:
        return False

def MornitoringUser(idName):
    print('{}  Monitoring...'.format(idName))
    preset = configJson[idName]['preset']
    system = configJson[idName]['system']
    token = configJson[idName]['lineToken']

    signal_df = pd.read_csv(dataPath+'/signal.csv')
    signal_df = signal_df[signal_df['Rec_Date'] == signal_df['Rec_Date'].max()]

    df = signal_df
    df = df[
        ( df['Rec_Date'] == df['Rec_Date'].max() ) &
        ( df['Signal'] == 'Entry' ) &
        ( df['Preset'] == preset )
    ]
    df = df.sort_values(['Change4HR%','Value_M'], ascending=[False,False])
    df = df.head(5)
    df.reset_index(inplace=True)

    df['User'] = idName
    #df['Buy'] = df.groupby(['Symbol','Preset']).transform('first')['Close']
    df['Buy'] = df['Close']
    df['Market'] = df['Close']
    df['Profit%'] = ( ( df['Market'] - df['Buy'] ) / df['Buy'] ) * 100

    colSelect = ['User','Symbol','Signal','Buy','Market','Profit%','Change4HR%','Value_M','BreakOut_H','BreakOut_L']
    df = df[colSelect]
    print('Entry {}'.format(df['Symbol'].to_list()))

    mornitorFilePath = dataPath + '/mornitor.csv'
    if not os.path.exists(mornitorFilePath):
        morn_df = pd.DataFrame(columns=colSelect)
        morn_df.to_csv(mornitorFilePath,index=False)
    morn_df = pd.read_csv(mornitorFilePath)

    #Buy Notify
    for i in range(df['Symbol'].count()):
        row = df.iloc[i]
        if not row['Symbol'] in morn_df['Symbol'].tolist():
            text = '△  Buy  {}  at  {}'.format(row['Symbol'],row['Buy'])
            quote = row['Symbol'].split('_')[-1]
            imgFilePath = imgPath + os.sep + '{}_{}.png'.format(preset,quote)
            print(text)
            print(imgFilePath)
            lineNotify.sendNotifyImageMsg(token, imgFilePath, text)

    morn_df = morn_df.append(df)
    morn_df['Buy'] = morn_df.groupby(['User','Symbol']).transform('first')['Buy']
    morn_df['Profit%'] = ((morn_df['Market'] - morn_df['Buy']) / morn_df['Buy']) * 100
    morn_df['Profit%'] = morn_df['Profit%'].round(2)
    morn_df.drop_duplicates(['User','Symbol'],keep='last',inplace=True)
    #morn_df.reset_index(inplace=True)

    #Sell Notify
    sell_df = signal_df[
        (signal_df['Signal'] == 'Exit') &
        (signal_df['Preset'] == preset)
        ]
    for i in range(morn_df['Symbol'].count()):
        row = morn_df.iloc[i]
        text = '△  Sell  {}  at  {}'.format(row['Symbol'], row['Market'])
        sell_condition = (row['Symbol'] in sell_df['Symbol'].to_list()) or (row['Market'] < row['BreakOut_L'])
        if sell_condition:
            print(text)
            lineNotify.sendNotifyMassage(token, text)
            morn_df = morn_df.drop(
                morn_df[( morn_df['User'] == idName ) & ( morn_df['Symbol'] == row['Symbol'] )]
            )
    #Save Dataframe
    morn_df.to_csv(mornitorFilePath, index=False)

def AllUser(*_):
    mornitorFilePath = dataPath + '/mornitor.csv'
    for user in configJson:
        MornitoringUser(user)
    while isInternetConnect:
        try:
            print('uploading mornitoring data...')
            gSheet.updateFromCSV(mornitorFilePath, 'Mornitor')
            print('upload mornitoring data finish')
        except:
            pass
        time.sleep(10)
        if gSheet.getAllDataS('Mornitor') != []:
            break

if __name__ == '__main__' :
    MornitoringUser('user1')
