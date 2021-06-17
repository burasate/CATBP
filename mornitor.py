import pandas as pd
import numpy as np
import json,os,time
import datetime as dt
import gSheet
import kbApi
import lineNotify
from bitkub import Bitkub

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

def getBalance(idName):
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return None
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = bitkub.balances()
    data = {}
    if balance['error'] == 0 :
        for sym in balance['result']:
            if balance['result'][sym]['available'] > 0 :
                data[sym] = {
                    'available' : balance['result'][sym]['available'],
                    'reserved' : balance['result'][sym]['reserved']
                }
    return data

def CreateSellOrder(idName,symbol):
    if not symbol.__contains__('THB_'):
        print('symbol name need contains THB_')
        return None
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return None
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = getBalance(idName)
    sym = symbol.replace('THB_','')
    if not sym in list(balance):
        print('not found [{}] in balance'.format(sym))
        return None
    amount = balance[sym]['available']
    result = bitkub.place_ask(sym=symbol, amt=amount, typ='market')
    print(result)

def CreateBuyOrder(idName,symbol,portfoiloList):
    if not symbol.__contains__('THB_'):
        print('symbol name need contains THB_')
        return None
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return None
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = getBalance(idName)
    percentageBalanceUsing = configJson[idName]['percentageBalanceUsing']
    system = configJson[idName]['system']
    size = int(systemJson[system]['size'])
    portSize = len(list(balance))-1

    portSymList = []
    for symbol in portfoiloList:  # Chane Symbol to Sym
        q = symbol.replace('THB_', '')
        portSymList.append(q)
    if portSize >= size: #checking except symbol
        for sym in list(balance):
            if (not sym in portSymList) and (sym != 'THB'):
                CreateSellOrder(idName,'THB_'+sym)
                time.sleep(5)
                balance = getBalance(idName)
                portSize = len(list(balance)) - 1

    print('size {}'.format(size))
    print('portSize {}'.format(portSize))
    budget = balance['THB']['available']
    sizedBudget = (budget / (size-portSize)) * (percentageBalanceUsing/100)
    print(sizedBudget)
    result = bitkub.place_bid(sym=symbol, amt=sizedBudget, typ='market')
    print(result)

def Reset(*_):
    print('---------------------\nReset\n---------------------')
    global mornitorFilePath
    global transacFilePath
    if not os.path.exists(mornitorFilePath):
        return None
    m_df = pd.read_csv(mornitorFilePath)
    t_df = pd.read_csv(transacFilePath)
    deleteList = []

    m_user_list = m_df['User'].unique().tolist()
    t_user_list = t_df['User'].unique().tolist()
    for user in m_user_list:
        print('Checking User {} in Mornitor {}'.format(user,m_user_list))
        if not user in list(configJson):
            deleteList.append(user)
    for user in t_user_list:
        print('Checking User {} in Transaction {}'.format(user, t_user_list))
        if not user in list(configJson):
            deleteList.append(user)

    #Sending Restart
    for user in list(configJson):
        systemName = configJson[user]['system']
        if bool(configJson[user]['reset']):
            gSheet.setValue('Config',findKey='idName',findValue=user,key='reset',value=0)
            gSheet.setValue('Config', findKey='idName', findValue=user, key='lastReport', value=time.time())
            text = '[ Reset Portfoilo ]\n' +\
                   'User ID : {} \n'.format(user) +\
                   'Preset ID : {} \n'.format(configJson[user]['preset']) +\
                   'System ID : {} \n'.format(systemName) +\
                   'Size : {} \n'.format(systemJson[systemName]['size']) +\
                   'Target Profit : {}%'.format(systemJson[systemName]['percentageProfitTarget'])
            lineNotify.sendNotifyMassage(configJson[user]['lineToken'],text)
            print(text)

    for user in deleteList:
        print('delete [ {} ]'.format(user))
        m_df = m_df[m_df['User'] != user]
        t_df = t_df[t_df['User'] != user]

    m_df.to_csv(mornitorFilePath,index=False)
    t_df.to_csv(transacFilePath, index=False)
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
        entry_df = pd.DataFrame(columns=list(data))
        entry_df.to_csv(transacFilePath, index=False)
    entry_df = pd.read_csv(transacFilePath)

    # Checking Column
    for c in list(data):
        if not c in entry_df.columns.tolist():
            entry_df[c] = None
    rec = pd.DataFrame(data)
    entry_df = entry_df.append(rec,ignore_index=True)
    entry_df.to_csv(transacFilePath,index=False)

def MornitoringUser(idName,sendNotify=True):
    isActive = bool(configJson[idName]['active'])
    isReset = bool(configJson[idName]['reset'])
    if isActive == False:
        return None
    print('---------------------\n[ {} ]  Monitoring\n---------------------'.format(idName))
    ticker = kbApi.getTicker()
    now = round(time.time())
    reportHourDuration = round( float(((now - configJson[idName]['lastReport'])/60)/60),2 )
    preset = configJson[idName]['preset']
    system = configJson[idName]['system']
    token = configJson[idName]['lineToken']
    size = int(systemJson[system]['size'])
    profitTarget = float(systemJson[system]['percentageProfitTarget'])
    duplicateBuyCount = 2
    secondaryBuy = bool(systemJson[system]['secondaryBuy'])
    print('Last Report  {} Hour Ago / Report Every {} H'.format(reportHourDuration, configJson[idName]['reportEveryHour']))

    signal_df = pd.read_csv(dataPath+'/signal.csv')
    signal_df = signal_df[
        (signal_df['Rec_Date'] == signal_df['Rec_Date'].max()) &
        (signal_df['Preset'] == preset)
    ]
    signal_df.reset_index(inplace=True)

    # New Column For Signal DF
    signal_df['User'] = idName
    signal_df['Buy'] = signal_df['Close']
    signal_df['Market'] = signal_df['Close']
    signal_df['Profit%'] = ((signal_df['Market'] - signal_df['Buy']) / signal_df['Buy']) * 100
    signal_df['Max_Drawdown%'] = 0.0
    signal_df['Buy_Count'] = 0
    for sym in ticker:
        signal_df.loc[(signal_df['Symbol'] == sym), 'Buy'] = ticker[sym]['last']

    # Select Entry
    entry_df = signal_df
    #entry_df['Change4HR%_Abs'] = entry_df['Change4HR%'].abs()
    entry_df = entry_df[
        ( entry_df['Rec_Date'] == entry_df['Rec_Date'].max() ) &
        ( entry_df['Signal'] == 'Entry' ) &
        ( entry_df['Preset'] == preset )
        #( entry_df['Change4HR%'] >= 0 ) &
        #( entry_df['Close'] <= entry_df['BreakOut_M'] )
    ]
    #entry_df = entry_df.sort_values(['Change4HR%_Abs','Value_M'], ascending=[True,False])
    entry_df = entry_df.sort_values(['Change4HR%','Value_M'], ascending=[False,False])
    #entry_df = entry_df.head(size) # Select Count
    entry_df.reset_index(inplace=True)
    #print(entry_df) # Signal Checking

    """
    # New Column For Entry DF
    entry_df['User'] = idName
    entry_df['Buy'] = entry_df['Close']
    entry_df['Market'] = entry_df['Close']
    entry_df['Profit%'] = ( ( entry_df['Market'] - entry_df['Buy'] ) / entry_df['Buy'] ) * 100
    entry_df['Max_Drawdown%'] =  0.0
    """

    colSelect = ['User','Symbol','Signal','Buy','Market',
                 'Profit%','Max_Drawdown%','Change4HR%',
                 'Value_M','BreakOut_H','BreakOut_MH','BreakOut_M',
                 'BreakOut_ML','BreakOut_L','Low','High','Rec_Date',
                 'Buy_Count']
    entry_df = entry_df[colSelect]
    #print(entry_df[['Symbol','Signal','Change4HR%']])
    print('Select Entry {}'.format(entry_df['Symbol'].to_list()))

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
    portfolioCount = morn_df[morn_df['User'] == idName]['Buy_Count'].sum()
    print('{} Portfolio have {}'.format(idName, portfolioList))

    # Buy Notify (by Singnal)
    # ==============================
    for i in range(entry_df['Symbol'].count()):
        if isReset :
            break
        row = entry_df.iloc[i]
        buy_condition = (
                (not row['Symbol'] in portfolioList) and
                (portfolioCount < size) and  # Port is not full
                (row['BreakOut_ML'] != row['BreakOut_L']) and
                (row['Low'] != row['BreakOut_ML']) and
				(row['Low'] < row['BreakOut_M'])
        )

        if buy_condition and not row['Symbol'] in portfolioList : # Buy Primary
            row['Buy_Count'] = 1
            text = '[ Buy ] {}\n{} Bath'.format(row['Symbol'],row['Buy'])
            quote = row['Symbol'].split('_')[-1]

            #entry_df['Buy_Count'].iloc[i] = row['Buy_Count']+1
            imgFilePath = imgPath + os.sep + '{}_{}.png'.format(preset,quote)
            print(text)
            print(imgFilePath)
            if sendNotify:
                lineNotify.sendNotifyImageMsg(token, imgFilePath, text)
            morn_df = morn_df.append(row,ignore_index=True)
            morn_df['Buy'] = morn_df.groupby(['User', 'Symbol']).transform('first')['Buy']

            portfolioList.append(row['Symbol'])
            portfolioCount += 1

            CreateBuyOrder(idName, row['Symbol'], portfolioList)
            Transaction(idName, 'Buy', row['Symbol'], (systemJson[system]['percentageComission'] / 100) * -1)
        elif portfolioCount >= size or row['Symbol'] in portfolioList : # Port is Full or Duplicate Buy is Limited
            print('Can\'t Buy More Because Size is Full...')
            break
    # ==============================

    # Update Checking
    for i in range(signal_df['Symbol'].count()):
        if isReset :
            break
        row = signal_df.iloc[i]
        port_df = morn_df[(morn_df['User'] == idName) & (morn_df['Symbol'] == row['Symbol'])]
        if port_df['Symbol'].count() != 0 : #Have Symbol in Port
            buy_low_condition = (
                    secondaryBuy and
                    (row['Symbol'] in portfolioList) and #is already in port
                    (portfolioCount < size) and  # size is not full
                    (row['BreakOut_ML'] != row['BreakOut_L']) and
                    (row['BreakOut_ML'] < row['BreakOut_M']) and
                    (row['Market'] < row['BreakOut_ML']) and
                    (port_df['Buy_Count'].tolist()[0] >= 1) and
                    (port_df['Buy_Count'].tolist()[0] < 2)
            )
            if buy_low_condition: # Secondary Buying
                row['Buy_Count'] = 1
                text = '[ Secondary Buy ] {}\n{} Bath\nStop Loss {} Bath'.format(row['Symbol'], row['Market'],row['BreakOut_L'])
                if sendNotify:
                    lineNotify.sendNotifyMassage(token, text)
                morn_df = morn_df.append(row, ignore_index=True)
                morn_df['Buy'] = morn_df.groupby(['User', 'Symbol']).transform('mean')['Buy']
                CreateBuyOrder(idName, row['Symbol'], portfolioList)
                Transaction(idName, 'Buy', row['Symbol'], (systemJson[system]['percentageComission'] / 100) * -1)
            # Update Trailing
            trailing_condition = (
                    (row['Symbol'] in portfolioList) and
                    (ticker[row['Symbol']]['last'] > row['BreakOut_M'])
            )
            if trailing_condition:
                morn_df = morn_df.append(row, ignore_index=True)
                print('Updated Trailing ( {} )'.format(row['Symbol']))
    # ==============================

    morn_df = morn_df[colSelect]

    # Ticker ( Update Last Price as 'Market' )
    for sym in ticker:
        if not sym in morn_df['Symbol'].unique().tolist():
            continue
        morn_df.loc[morn_df['Symbol'] == sym, 'Market'] = ticker[sym]['last']
    print('Update Market Price')

    # Calculate in Column
    print('Profit Calculating...')
    morn_df['Buy_Count'] = morn_df.groupby(['User', 'Symbol']).transform('sum')['Buy_Count']
    morn_df['Buy'] = morn_df.groupby(['User','Symbol']).transform('first')['Buy']
    #if morn_df['Buy_Count'].max() > 1:
        #morn_df['Buy'] = morn_df.groupby(['User','Symbol']).transform('mean')['Buy']
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
    """
    sell_df = signal_df[
        (signal_df['Signal'] == 'Exit') &
        (signal_df['Preset'] == preset)
        ]
    """
    sellList = []
    for i in range(morn_df['Symbol'].count()):
        row = morn_df.iloc[i]
        text = '[ Sell ] {}\n{} Bath ({}%)'.format(row['Symbol'], row['Market'],row['Profit%'])
        sell_condition = ( # Sell Default
                ( row['Market'] < row['BreakOut_L'] ) and
                ( row['User'] == idName )
                ) or (
                ( row['User'] == idName ) and
                (row['Profit%'] > profitTarget)
                )
        if ( row['Profit%'] <= 0.0 ) : # Fast Cut Loss if no profit
            sell_condition = ( # Sell Default
                ( row['Market'] < row['BreakOut_ML'] ) and
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

    #Take profit all (Clear Portfolio)
    profit_condition = report_df['Profit%'].mean() >= profitTarget
    if ( profit_condition or isReset ) and report_df['Profit%'].count() != 0 :
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='reset', value=1)
        text = '[ Take Profit ]\n' + \
               'Target Profit {}%\n'.format(profitTarget) + \
               'Profit Average {}%'.format(report_df['Profit%'].mean().round(2))
        print(text)
        if sendNotify:
            lineNotify.sendNotifyMassage(token, text)

        # Prepare Sell When Take Profit or Reset
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
        profit = profit/size
        morn_df = morn_df.drop(
            morn_df[(morn_df['User'] == i['User']) & (morn_df['Symbol'] == i['Symbol'])].index
        )
        CreateSellOrder(i['User'], i['Symbol'])
        Transaction( i['User'], 'Sell', i['Symbol'], ((systemJson[system]['percentageComission'] / 100) * -1) + profit )

    #Finish
    morn_df.to_csv(mornitorFilePath, index=False)
    print('{} Update Finished\n'.format(idName))

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
                print('\nError To Record ! : {}  then skip\n'.format(e))
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
    #import update
    #update.updateConfig()
    #configJson = json.load(open(configPath))
    #update.updateSystem()
    #systemJson = json.load(open(systemPath))

    #Reset()
    #MornitoringUser('CryptoBot')
    #MornitoringUser('user1')
    #CreateBuyOrder('user1','THB_USDC')
    #CreateSellOrder('user1','THB_USDC')
    #AllUser()
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
