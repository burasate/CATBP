import pandas as pd
import numpy as np
import json,os,time
import datetime as dt
import gSheet
import kbApi
import lineNotify


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
mornitorFilePath = dataPath + '/mornitor.csv'
transacFilePath = dataPath + '/transaction.csv'

def isInternetConnect(*_):
    url = 'http://google.com'
    connectStatus = requests.get(url).status_code
    if connectStatus == 200:
        return True
    else:
        return False

def Reset(*_):
    print('---------------------\nReset\n---------------------')
    global mornitorFilePath
    if not os.path.exists(mornitorFilePath):
        return None
    df = pd.read_csv(mornitorFilePath)
    deleteList = []
    for user in df['User'].unique().tolist():
        systemName = configJson[user]['system']
        if not user in list(configJson):
            deleteList.append(user)
        elif bool(configJson[user]['reset']):
            deleteList.append(user)
            gSheet.setValue('Config',findKey='idName',findValue=user,key='reset',value=0)
            gSheet.setValue('Config', findKey='idName', findValue=user, key='lastReport', value=time.time())
            text = '[ Reset Portfoilo ]\n' +\
                   'User ID : {} \n'.format(user) +\
                   'Preset ID : {} \n'.format(configJson[user]['preset']) +\
                   'System ID : {} \n'.format(systemName) +\
                   'Size : {} \n'.format(systemJson[systemName]['size']) +\
                   'Take Profit By : {} \n'.format(systemJson[systemName]['takeProfitBy']) +\
                   'Target Profit : {}%'.format(systemJson[systemName]['percentageProfitTarget'])
            lineNotify.sendNotifyMassage(configJson[user]['lineToken'],text)
            print(text)

    for user in deleteList:
        df = df[df['User'] != user]
    df.to_csv(mornitorFilePath,index=False)
    print('User Reset')

def Transaction(idName,code,symbol,change):
    global transacFilePath
    date_time = str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    data = {
        'dateTime' : [date_time],
        'User' : [idName],
        'Code' : [code],
        'Symbol' : [symbol],
        'Change%' : [change]
    }
    col = ['dateTime']
    if not os.path.exists(transacFilePath):
        df = pd.DataFrame(columns=list(data))
        df.to_csv(transacFilePath, index=False)
    df = pd.read_csv(transacFilePath)

    # Checking Column
    for c in list(data):
        if not c in df.columns.tolist():
            df[c] = None
    rec = pd.DataFrame(data)
    df = df.append(rec,ignore_index=True)
    df.to_csv(transacFilePath,index=False)

def MornitoringUser(idName,sendNotify=True):
    isActive = bool(configJson[idName]['active'])
    isReset = bool(configJson[idName]['reset'])
    if isActive == False:
        return None
    print('---------------------\n[ {} ]  Monitoring\n---------------------'.format(idName))
    now = round(time.time())
    reportHourDuration = round( float(((now - configJson[idName]['lastReport'])/60)/60),2 )
    preset = configJson[idName]['preset']
    system = configJson[idName]['system']
    token = configJson[idName]['lineToken']
    size = int(systemJson[system]['size'])
    profitTarget = float(systemJson[system]['percentageProfitTarget'])
    print('Last Report  {} Hour Ago / Report Every {} H'.format(reportHourDuration, configJson[idName]['reportEveryHour']))

    signal_df = pd.read_csv(dataPath+'/signal.csv')
    signal_df = signal_df[signal_df['Rec_Date'] == signal_df['Rec_Date'].max()]

    # Select Entry
    df = signal_df
    df['Change4HR%_Abs'] = df['Change4HR%'].abs()
    df = df[
        ( df['Rec_Date'] == df['Rec_Date'].max() ) &
        ( df['Signal'] == 'Entry' ) &
        ( df['Preset'] == preset ) &
        ( df['Change4HR%'] >= 0 ) &
        ( df['Close'] < df['BreakOut_M'] )
    ]
    df = df.sort_values(['Change4HR%_Abs','Value_M'], ascending=[True,False])
    #df = df.sort_values(['Change4HR%','Value_M'], ascending=[False,False])
    df = df.head(size) # Select Count
    df.reset_index(inplace=True)
    #print(df) # Signal Checking

    # New Column
    df['User'] = idName
    df['Buy'] = df['Close']
    df['Market'] = df['Close']
    df['Profit%'] = ( ( df['Market'] - df['Buy'] ) / df['Buy'] ) * 100
    df['Max_Drawdown%'] =  0.0

    colSelect = ['User','Symbol','Signal','Buy','Market','Profit%','Max_Drawdown%','Change4HR%','Value_M','BreakOut_H','BreakOut_L','Rec_Date']
    df = df[colSelect]
    #print(df[['Symbol','Signal','Change4HR%']])
    print('Select Entry {}'.format(df['Symbol'].to_list()))

    # Mornitor data frame
    global mornitorFilePath
    if not os.path.exists(mornitorFilePath):
        morn_df = pd.DataFrame(columns=colSelect)
        morn_df.to_csv(mornitorFilePath,index=False)
    morn_df = pd.read_csv(mornitorFilePath)

    # Checking Column
    for c in colSelect:
        if not c in morn_df.columns.tolist():
            morn_df[c] = None

    #Portfolio
    portfolioList = morn_df[morn_df['User'] == idName]['Symbol'].tolist()
    print('{} Portfolio have {}'.format(idName, portfolioList))

    # Buy Notify
    # ==============================
    for i in range(df['Symbol'].count()):
        row = df.iloc[i]
        buy_condition =  (
            (len(portfolioList) < size) and  #Port is not full
            (not row['Symbol'] in portfolioList) and # Not Symbol in Port
            (row['Buy'] > row['BreakOut_L']) # Price Not Equal Break Low
        )
        if buy_condition: # Buy Condition
            text = '[ Buy ] {}\n{} Bath'.format(row['Symbol'],row['Buy'])
            quote = row['Symbol'].split('_')[-1]
            imgFilePath = imgPath + os.sep + '{}_{}.png'.format(preset,quote)
            print(text)
            print(imgFilePath)
            if sendNotify:
                lineNotify.sendNotifyImageMsg(token, imgFilePath, text)
            morn_df = morn_df.append(row,ignore_index=True)
            portfolioList.append(row['Symbol'])
            Transaction(idName, 'Buy', row['Symbol'], (systemJson[system]['percentageComission']/100) * -1)
        elif len(portfolioList) >= size: # Port is Full
            print('Can\'t Buy More\nportfolio is full')
            break
        # Update Break out When Entry Symbol in Port Exist
        if row['Symbol'] in portfolioList:
            morn_df = morn_df.append(row, ignore_index=True)
            print('updated preset indicator ( {} )'.format(row['Symbol']))
    morn_df = morn_df[colSelect]
    # ==============================

    # Ticker ( Update Last Price as 'Market' )
    ticker = kbApi.getTicker()
    for sym in ticker:
        if not sym in morn_df['Symbol'].unique().tolist():
            continue
        morn_df.loc[morn_df['Symbol'] == sym, 'Market'] = ticker[sym]['last']
    print('Update Market Price')

    # Calculate in Column
    print('Profit Calculating...')
    morn_df['Buy'] = morn_df.groupby(['User','Symbol']).transform('first')['Buy']
    morn_df['Profit%'] = ((morn_df['Market'] - morn_df['Buy']) / morn_df['Buy']) * 100
    morn_df['Profit%'] = morn_df['Profit%'].round(2)
    morn_df.loc[(morn_df['Profit%'] < 0.0) & (morn_df['Max_Drawdown%'] == 0.0), 'Max_Drawdown%'] = morn_df['Profit%'].abs()
    morn_df.loc[(morn_df['Profit%'] > 0.0) & (morn_df['Max_Drawdown%'] == 0.0), 'Max_Drawdown%'] = 0.0
    morn_df.loc[(morn_df['Profit%'] < 0.0) & (morn_df['Profit%'] < morn_df['Max_Drawdown%'].abs()*-1),
                'Max_Drawdown%'] = morn_df['Profit%'].abs()
    morn_df['Max_Drawdown%'] = morn_df.groupby(['User', 'Symbol'])['Max_Drawdown%'].transform('max')
    morn_df.drop_duplicates(['User','Symbol'],keep='last',inplace=True)
    morn_df.to_csv(mornitorFilePath, index=False)

    # Reload mornitor again
    morn_df = pd.read_csv(mornitorFilePath)
    morn_df = morn_df.sort_values(['User','Profit%'], ascending=[True,False])
    holdList = morn_df[
        (morn_df['User'] == idName) &
        (morn_df['Profit%'] > 0.0)
    ].head(size)['Symbol'].tolist()

    # Sell Notify
    # ==============================
    sell_df = signal_df[
        (signal_df['Signal'] == 'Exit') &
        (signal_df['Preset'] == preset)
        ]
    sellList = []
    for i in range(morn_df['Symbol'].count()):
        row = morn_df.iloc[i]
        text = '[ Sell ] {}\n{} Bath ({}%)'.format(row['Symbol'], row['Market'],row['Profit%'])
        sell_condition = (
                ( row['Market'] < row['BreakOut_L'] ) &
                ( row['User'] == idName )
                )
        if sell_condition:
            print(text)
            if sendNotify:
                lineNotify.sendNotifyMassage(token, text)
            sellList.append(
                {
                    'User': row['User'],
                    'Symbol' : row['Symbol']
                 }
            )
    # ==============================

    #Report
    report_df = morn_df[morn_df['User'] == idName]
    report_df = report_df.sort_values(['Profit%'], ascending=[False])

    #Portfolio report
    if report_df['Symbol'].count() != 0 and reportHourDuration >= configJson[idName]['reportEveryHour']:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='lastReport', value=time.time())
        text = '[ Report ]\n' +\
                '{}\n'.format( ' , '.join(report_df['Symbol'].tolist()) ) +\
                'Profit Sum {}%\n'.format(report_df['Profit%'].sum().round(2)) + \
               'Profit Average {}%'.format(report_df['Profit%'].mean().round(2))
        print(text)
        if sendNotify:
            lineNotify.sendNotifyMassage(token, text)

    #Take profit all
    profit_condition = report_df['Profit%'].mean() >= profitTarget
    if systemJson[system]['takeProfitBy'] == 'Sum':
        profit_condition = report_df['Profit%'].sum() >= profitTarget
    if profit_condition:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='reset', value=1)
        configJson[idName]['reset'] = 1
        text = '[ Take Profit ]\n' + \
               'Target Profit {}%\n'.format(profitTarget) + \
               'Profit Sum {}%\n'.format(report_df['Profit%'].sum().round(2)) + \
               'Profit Average {}%'.format(report_df['Profit%'].mean().round(2))
        print(text)
        if sendNotify:
            lineNotify.sendNotifyMassage(token, text)

    # Prepare Sell When Take Profit or Reset
    if profit_condition or isReset:
        for sym in report_df['Symbol'].tolist():
            if sym in sellList:
                continue
            sellList.append(
                {
                    'User': idName,
                    'Symbol': sym
                }
            )

    # Sell And Delete Symbol
    for i in sellList:
        profit = morn_df[(morn_df['User'] == i['User']) & (morn_df['Symbol'] == i['Symbol'])]['Profit%'].tolist()[0]
        morn_df = morn_df.drop(
            morn_df[(morn_df['User'] == i['User']) & (morn_df['Symbol'] == i['Symbol'])].index
        )
        Transaction( i['User'], 'Sell', i['Symbol'], ((systemJson[system]['percentageComission'] / 100) * -1) + profit )

    #Finish
    morn_df.to_csv(mornitorFilePath, index=False)
    print('{} Update Finished'.format(idName))

def AllUser(*_):
    os.system('cls||clear')
    global mornitorFilePath
    global transacFilePath
    for user in configJson:
        if os.name == 'nt':
            print('[For Dev Testing...]')
            MornitoringUser(user,sendNotify=False)
        else:
            try:
                MornitoringUser(user)
            except Exception as e:
                print('Error To Record : {}  then skip'.format(e))
                continue
    while isInternetConnect and not os.name == 'nt':
        try:
            #print('Uploading mornitoring data...')
            if os.path.exists(mornitorFilePath):
                gSheet.updateFromCSV(mornitorFilePath, 'Mornitor')
            #print('Upload mornitoring data finish')
            #print('Uploading Transaction data...')
            if os.path.exists(transacFilePath):
                gSheet.updateFromCSV(transacFilePath, 'Transaction')
            #print('Upload Transaction data finish')
        except:
            pass
        else:
            break
        time.sleep(10)
        #if gSheet.getAllDataS('Mornitor') != []:
            #break

if __name__ == '__main__' :
    import update
    #update.updateConfig()
    #configJson = json.load(open(configPath))
    #update.updateSystem()
    #systemJson = json.load(open(systemPath))

    #Reset()
    #MornitoringUser('CryptoBot')
    #MornitoringUser('user1')
    AllUser()
    #Transaction('idName', 'code', 'symbol', 'change')
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
