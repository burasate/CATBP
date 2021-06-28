import pandas as pd
import numpy as np
import json,os,time,sys
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

def CreateSellOrder(idName,symbol,count):
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
    amount = balance[sym]['available'] / count
    if count <= 1:
        amount = balance[sym]['available']
    result = bitkub.place_ask(sym=symbol, amt=amount, typ='market')
    print(result)

def CreateBuyOrder(idName,symbol,portfoiloList,countLeft):
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
    size = int(systemJson[system]['portSize'])
    portSize = len(list(balance))-1 #Real Port
    buySize = int(systemJson[system]['buySize'])

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
    sizedBudget = ( (budget / (size-portSize)) /countLeft) * (percentageBalanceUsing/100)
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

def Realtime(idName,sendNotify=True):
    isActive = bool(configJson[idName]['active'])
    isActive = True
    isReset = bool(configJson[idName]['reset'])
    if isActive == False:
        return None
    print('---------------------\n[ {} ]  Monitoring\n---------------------'.format(idName))
    ticker = kbApi.getTicker()
    now = round(time.time())
    reportHourDuration = round(float(((now - configJson[idName]['lastReport']) / 60) / 60), 2)
    preset = configJson[idName]['preset']
    system = configJson[idName]['system']
    token = configJson[idName]['lineToken']
    portSize = int(systemJson[system]['portSize'])
    buySize = int(systemJson[system]['buySize'])
    profitTarget = float(systemJson[system]['percentageProfitTarget'])
    triggerBuy = systemJson[system]['triggerBuy']
    triggerSell = systemJson[system]['triggerSell']
    triggerBuyPos = systemJson[system]['triggerBuyPosition']
    triggerSellPos = systemJson[system]['triggerSellPosition']
    print('Portfolio Size : {} | Buy Position Size : {}'.format(portSize, buySize))
    print('Buy : {} | Sell : {}'.format(triggerBuy,triggerSell))
    print('Trigger Buy : {} | Trigger Sell : {}'.format(triggerBuyPos,triggerSellPos))
    #print(ticker)

    colSelect = ['User', 'Symbol', 'Signal', 'Buy', 'Market',
                 'Profit%', 'Max_Drawdown%', 'Change4HR%',
                 'Volume', 'BreakOut_H', 'BreakOut_MH', 'BreakOut_M',
                 'BreakOut_ML', 'BreakOut_L', 'Low', 'High', 'Rec_Date','Count']

    #Signal Dataframe
    signal_df = pd.read_csv(dataPath + '/signal.csv')
    signal_df = signal_df[
        (signal_df['Rec_Date'] == signal_df['Rec_Date'].max()) &
        (signal_df['Preset'] == preset)
        ]
    signal_df.sort_values(['Change4HR%','Volume'], ascending=[True,False])
    signal_df.reset_index(inplace=True)

    # New Column For Signal DF
    signal_df['User'] = idName
    signal_df['Buy'] = signal_df['Close']
    signal_df['Market'] = signal_df['Close']
    signal_df['Profit%'] = ((signal_df['Market'] - signal_df['Buy']) / signal_df['Buy']) * 100
    signal_df['Max_Drawdown%'] = 0.0
    signal_df['Count'] = 1
    for sym in ticker:
        signal_df.loc[(signal_df['Symbol'] == sym), 'Buy'] = ticker[sym]['last']
        signal_df.loc[(signal_df['Symbol'] == sym), 'Market'] = ticker[sym]['last']
    #print(signal_df[colSelect])

    #Portfolio File Checking
    if not os.path.exists(mornitorFilePath):
        port_df = pd.DataFrame(columns=colSelect)
        port_df.to_csv(mornitorFilePath,index=False)

    #Read User Portfolio
    port_df = pd.read_csv(mornitorFilePath)
    port_df = port_df[
        (port_df['User'] == idName)
    ]
    port_df.reset_index(inplace=True)
    print('Portfolio')
    print(port_df['Symbol'].tolist())

    #Find New Buy
    buy_df = None
    if triggerBuyPos == 'Lower':
        buy_df = signal_df[
                (signal_df['Signal'] == triggerBuy) &
                (signal_df['Market'] < signal_df['BreakOut_ML'])
            ][colSelect]
    elif triggerBuyPos == 'Upper':
        buy_df = signal_df[
                (signal_df['Signal'] == triggerBuy) &
                (signal_df['Market'] > signal_df['BreakOut_MH'])
            ][colSelect]
    buy_df = buy_df.head(portSize)
    print('Buy Data Frame')
    print(buy_df[['Symbol','Signal','Market','BreakOut_MH','BreakOut_ML']])

    #Buy Condition
    for i in buy_df.index.tolist():
        row = buy_df.loc[i]
        text = '[ Buy ] {}\n{} Bath'.format(row['Symbol'], row['Buy'])
        #print('Buying {} : {}'.format(row['Symbol'],row['Market']))
        if row['Symbol'] in port_df['Symbol'].tolist(): #Symbol is in portfolio already
            #print('  Checking buy count')
            symbol_index = port_df[port_df['Symbol'] == row['Symbol']].index.tolist()[0]
            if port_df.loc[symbol_index,'Count'] < buySize : #Buy position size is not full
                print('Buy {} more'.format(row['Symbol']))
                port_df.loc[symbol_index,'Count'] += 1
                port_df.loc[symbol_index,'Rec_Date'] = row['Rec_Date']
                port_df.loc[symbol_index,'Buy'] = round((port_df.loc[symbol_index,'Buy'] + row['Buy'])*0.5,2)

                # Do Buy
                portfolioList = port_df['Symbol'].tolist()
                countLeft = buySize - row['Count'] + 1
                CreateBuyOrder(idName, row['Symbol'], portfolioList, countLeft)
                Transaction(idName, 'Buy', row['Symbol'], (systemJson[system]['percentageComission'] / 100) * -1)
                if sendNotify:
                    imgFilePath = imgPath + os.sep + '{}_{}.png'.format(preset, quote)
                    lineNotify.sendNotifyImageMsg(token, imgFilePath, text)
        elif not row['Symbol'] in port_df['Symbol'].tolist(): #Symbol isn't in portfolio
            #print('  Checking port is not full')
            if port_df['Symbol'].count() < portSize:  #Portfolio isn't full
                print('Buy {} as new symbol'.format(row['Symbol']))
                port_df = port_df.append(row,ignore_index=False)

                # Do Buy
                portfolioList = port_df['Symbol'].tolist()
                countLeft = buySize - row['Count'] + 1
                CreateBuyOrder(idName, row['Symbol'], portfolioList, countLeft)
                Transaction(idName, 'Buy', row['Symbol'], (systemJson[system]['percentageComission'] / 100) * -1)
                if sendNotify:
                    lineNotify.sendNotifyMassage(token, text)

    #Market Update and Calculate Profit
    for i in signal_df.index.tolist():
        row = signal_df.loc[i]
        if row['Symbol'] in port_df['Symbol'].tolist():
            print('Profit Update {}'.format(row['Symbol']))
            symbol_index = port_df[port_df['Symbol'] == row['Symbol']].index.tolist()[0]
            port_df.loc[symbol_index, 'Market'] = row['Market']
            port_df.loc[symbol_index, 'Profit%'] = ((port_df.loc[symbol_index, 'Market'] - port_df.loc[symbol_index, 'Buy']) /
                                                    port_df.loc[symbol_index, 'Buy']) * 100
            port_df.loc[symbol_index, 'Profit%'] = round(port_df.loc[symbol_index, 'Profit%'],2)
            if (port_df.loc[symbol_index, 'Profit%'] < 0) and (abs(port_df.loc[symbol_index, 'Profit%']) > port_df.loc[symbol_index, 'Max_Drawdown%']):
                port_df.loc[symbol_index, 'Max_Drawdown%'] = abs(port_df.loc[symbol_index, 'Profit%'])
            port_df.loc[symbol_index, 'Change4HR%'] = row['Change4HR%']
            port_df.loc[symbol_index, 'Volume'] = row['Volume']
            port_df.loc[symbol_index, 'BreakOut_H'] = row['BreakOut_H']
            port_df.loc[symbol_index, 'BreakOut_MH'] = row['BreakOut_MH']
            port_df.loc[symbol_index, 'BreakOut_M'] = row['BreakOut_M']
            port_df.loc[symbol_index, 'BreakOut_ML'] = row['BreakOut_ML']
            port_df.loc[symbol_index, 'BreakOut_L'] = row['BreakOut_L']
            port_df.loc[symbol_index, 'Low'] = row['Low']
            port_df.loc[symbol_index, 'High'] = row['High']
            port_df.loc[symbol_index, 'Signal'] = row['Signal']

    # Portfolio report
    if port_df['Symbol'].count() != 0 and reportHourDuration >= configJson[idName]['reportEveryHour']:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='lastReport', value=time.time())
        text = '[ Report ]\n' + \
               '{}\n'.format(' , '.join(port_df['Symbol'].tolist())) + \
               'Avg Profit {}%'.format(port_df['Profit%'].mean().round(2))
        print(text)
        if sendNotify:
            lineNotify.sendNotifyMassage(token, text)

    #Sell Condition
    for i in port_df.index.tolist():
        row = port_df.loc[i]
        sell_signal = False
        sell_profit = row['Profit%'] > profitTarget
        if triggerSellPos == 'Lower':
            sell_signal = (
                (row['Signal'] == triggerSell) and
                (row['Market'] < row['BreakOut_ML'])
            )
        elif triggerSellPos == 'Upper':
            sell_signal = (
                (row['Signal'] == triggerSell) and
                (row['Market'] > row['BreakOut_MH'])
            )

        if sell_signal or sell_profit or isReset : #Sell
            port_df.loc[i, 'Count'] -= 1
            text = '[ Sell ] {}\n{} Bath ({}%)'.format(row['Symbol'], row['Market'], row['Profit%'])

            # Do Sell
            count = port_df.loc[i, 'Count'] + 1
            CreateSellOrder(idName, row['Symbol'],count)
            Transaction(idName, 'Sell', row['Symbol'],
                        ((systemJson[system]['percentageComission'] / 100) * -1) + profit)
            if sendNotify:
                lineNotify.sendNotifyMassage(token, text)

        if port_df.loc[i, 'Count'] <= 0 : #Delete symbol if no count
            port_df = port_df[port_df['Symbol'] != row['Symbol']]

    #Finish
    if 'index' in port_df.columns.tolist():
        port_df.drop(columns=['index'],inplace=True)
    alluser_df = pd.read_csv(mornitorFilePath)
    alluser_df = alluser_df[alluser_df['User'] != idName]
    alluser_df = alluser_df.append(port_df)
    alluser_df.to_csv(mornitorFilePath,index=False)
    print('---------------------\nFinish\n---------------------\n')

def AllUser(*_):
    os.system('cls||clear')
    global mornitorFilePath
    global transacFilePath
    for user in configJson:
        if os.name == 'nt':
            print('[For Dev Testing...]')
            Realtime(user,sendNotify=False)
        else:
            try:
                Realtime(user)
            except Exception as e:
                print('\nError To Record ! : {}  then skip\n'.format(e))
                print('!!!! ==========================')
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print('Error Type {}\nFile {}\n Line {}'.format(exc_type, fname, exc_tb.tb_lineno))
                print('!!!! ==========================')
    while isInternetConnect and not os.name == 'nt':
        try:
            if os.path.exists(mornitorFilePath):
                gSheet.updateFromCSV(mornitorFilePath, 'Mornitor')
            if os.path.exists(transacFilePath):
                gSheet.updateFromCSV(transacFilePath, 'Transaction')
        except:
            pass
        else:
            break
        time.sleep(10)

if __name__ == '__main__' :
    import update
    update.updateConfig()
    update.updatePreset()
    update.updateSystem()
    configJson = json.load(open(configPath))
    presetJson = json.load(open(presetPath))
    systemJson = json.load(open(systemPath))

    #Realtime('user1', sendNotify=False)
    #Realtime('user2', sendNotify=False)
    #Realtime('CryptoBot', sendNotify=False)