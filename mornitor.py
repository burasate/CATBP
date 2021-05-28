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

def Reset(*_):
    mornitorFilePath = dataPath + '/mornitor.csv'
    if not os.path.exists(mornitorFilePath):
        return None
    df = pd.read_csv(mornitorFilePath)
    deleteList = []
    for user in df['User'].unique().tolist():
        if not user in list(configJson):
            deleteList.append(user)
        elif bool(configJson[user]['reset']):
            deleteList.append(user)
            gSheet.setValue('Config',findKey='idName',findValue=user,key='reset',value=0)
            gSheet.setValue('Config', findKey='idName', findValue=user, key='lastReport', value=time.time())
            #configJson[user]['reset'] = 0
            #json.dump(configJson, open(configPath, 'w'), indent=4)

    for user in deleteList:
        df = df[df['User'] != user]
    df.to_csv(mornitorFilePath,index=False)
    print('User Reset')

def MornitoringUser(idName):
    isActive = bool(configJson[idName]['active'])
    if isActive == False:
        return None
    print('---------------------\n[ {} ]  Monitoring\n---------------------'.format(idName))
    now = round(time.time())
    reportHourDuration = round( float(((now - configJson[idName]['lastReport'])/60)/60),2 )
    print('Last Report  {} Hour Ago / Report Every {}H'.format(reportHourDuration,configJson[idName]['lastReport']))
    preset = configJson[idName]['preset']
    system = configJson[idName]['system']
    token = configJson[idName]['lineToken']
    size = int(systemJson[system]['size'])
    profitTarget = float(systemJson[system]['percentageProfitTarget'])

    signal_df = pd.read_csv(dataPath+'/signal.csv')
    signal_df = signal_df[signal_df['Rec_Date'] == signal_df['Rec_Date'].max()]

    # Select Entry
    df = signal_df
    df['Change4HR%_Abs'] = df['Change4HR%'].abs()
    df = df[
        ( df['Rec_Date'] == df['Rec_Date'].max() ) &
        ( df['Signal'] == 'Entry' ) &
        ( df['Preset'] == preset )
    ]
    df = df.sort_values(['Change4HR%_Abs','Value_M'], ascending=[True,False])
    #df = df.sort_values(['Change4HR%','Value_M'], ascending=[False,False])
    df = df.head(1) # Select Count
    df.reset_index(inplace=True)

    # New Column
    df['User'] = idName
    df['Buy'] = df['Close']
    df['Market'] = df['Close']
    df['Profit%'] = ( ( df['Market'] - df['Buy'] ) / df['Buy'] ) * 100
    df['Max_Drawdown%'] =  0.0

    colSelect = ['User','Symbol','Signal','Buy','Market','Profit%','Max_Drawdown%','Change4HR%','Value_M','BreakOut_H','BreakOut_L']
    df = df[colSelect]
    print(df[['Symbol','Signal','Change4HR%']])
    print('Select Entry {}'.format(df['Symbol'].to_list()))

    # Mornitor data frame
    mornitorFilePath = dataPath + '/mornitor.csv'
    if not os.path.exists(mornitorFilePath):
        morn_df = pd.DataFrame(columns=colSelect)
        morn_df.to_csv(mornitorFilePath,index=False)
    morn_df = pd.read_csv(mornitorFilePath)

    # Buy Notify
    portfolioList = morn_df[morn_df['User']==idName]['Symbol'].tolist()
    print('{} Portfolio have {}'.format(idName,portfolioList))
    for i in range(df['Symbol'].count()):
        row = df.iloc[i]
        print(row['Symbol'])
        print( not row['Symbol'] in portfolioList )
        if (not row['Symbol'] in portfolioList) and (len(portfolioList) <= size):
            text = '△  Buy  {}    {}'.format(row['Symbol'],row['Buy'])
            quote = row['Symbol'].split('_')[-1]
            imgFilePath = imgPath + os.sep + '{}_{}.png'.format(preset,quote)
            print(text)
            print(imgFilePath)
            #lineNotify.sendNotifyImageMsg(token, imgFilePath, text)
            morn_df = morn_df.append(row)

    # Calculate in Column
    morn_df['Buy'] = morn_df.groupby(['User','Symbol']).transform('first')['Buy']
    morn_df['Profit%'] = ((morn_df['Market'] - morn_df['Buy']) / morn_df['Buy']) * 100
    morn_df['Profit%'] = morn_df['Profit%'].round(2)
    morn_df['Max_Drawdown%'] = morn_df['Max_Drawdown%'].min()
    morn_df.loc[morn_df['Max_Drawdown%'] > 0.0,'Max_Drawdown%'] = 0.0
    morn_df['Max_Drawdown%'] = morn_df['Max_Drawdown%'].abs()
    morn_df['Max_Drawdown%'] = morn_df.groupby(['User', 'Symbol']).transform('max')['Max_Drawdown%']
    morn_df.drop_duplicates(['User','Symbol'],keep='last',inplace=True)
    morn_df.to_csv(mornitorFilePath, index=False)

    # Reload mornitor again
    morn_df = pd.read_csv(mornitorFilePath)
    morn_df = morn_df.sort_values(['User','Profit%'], ascending=[True,False])
    holdList = morn_df[
        (morn_df['User'] == idName) &
        (morn_df['Profit%'] > 0.0)
    ].head(size+2)['Symbol'].tolist()

    # Sell Notify
    sell_df = signal_df[
        (signal_df['Signal'] == 'Exit') &
        (signal_df['Preset'] == preset)
        ]
    sellList = []
    for i in range(morn_df['Symbol'].count()):
        row = morn_df.iloc[i]
        text = '▽  Sell  {}   {}'.format(row['Symbol'], row['Market'])
        sell_condition = (
                (row['Market'] < row['BreakOut_L'])
                )
        if sell_condition:
            print(text)
            #lineNotify.sendNotifyMassage(token, text)
            sellList.append(
                {
                    'User': row['User'],
                    'Symbol' : row['Symbol']
                 }
            )
    for i in sellList:
        morn_df = morn_df.drop(
            morn_df[( morn_df['User'] == i['User'] ) & ( morn_df['Symbol'] == i['Symbol'] )].index
        )

    #Report
    report_df = morn_df[morn_df['User'] == idName]
    report_df = report_df.sort_values(['Profit%'], ascending=[False])
    report_df = report_df.head(size)

    #portfolio report
    if reportHourDuration >= float(configJson[idName]['reportEveryHour']) and report_df['Symbol'].count() != 0:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='lastReport', value=time.time())
        text = '[Holding]\n' +\
                '{}\n'.format( ' , '.join(report_df['Symbol'].tolist()) ) +\
                'Profit {}%'.format( report_df['Profit%'].sum() )
        print(text)
        lineNotify.sendNotifyMassage(token, text)
        #lineNotify.sendNotifyMassage(token, str(reportHourDuration))

    #take profit all
    if report_df['Profit%'].sum() >= profitTarget:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='reset', value=1)
        configJson[idName]['reset'] = 1
        text = '[Take Profit]:\n' + \
               'Target Profit {}%\n'.format(profitTarget) + \
               'Now Profit {}%'.format(report_df['Profit%'].sum())
        print(text)
        lineNotify.sendNotifyMassage(token, text)

    morn_df.to_csv(mornitorFilePath, index=False)

def AllUser(*_):
    os.system('cls||clear')
    mornitorFilePath = dataPath + '/mornitor.csv'
    for user in configJson:
        try:
            MornitoringUser(user)
        except Exception as e:
            print(e)
            continue
    while isInternetConnect:
        try:
            print('uploading mornitoring data...')
            gSheet.updateFromCSV(mornitorFilePath, 'Mornitor')
            print('upload mornitoring data finish')
        except:
            pass
        time.sleep(5)
        if gSheet.getAllDataS('Mornitor') != []:
            break

if __name__ == '__main__' :
    import update
    update.updateConfig()
    configJson = json.load(open(configPath))

    #Reset()
    #MornitoringUser('CryptoBot')
    MornitoringUser('user1')
    #AllUser()
    """
    morn_df = pd.read_csv(dataPath + '/mornitor.csv')
    morn_df = morn_df.sort_values(['User', 'Profit%'], ascending=[True, False])
    holdList = morn_df[
        (morn_df['User'] == 'CryptoBot') &
        (morn_df['Profit%'] >= 0.0)
        ].head(5)['Symbol'].tolist()
    print(holdList)
    """

    pass
