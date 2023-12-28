import pandas as pd
import numpy as np
import json,os,time,sys,pprint,shutil
import datetime as dt
import gSheet
import lineNotify
#from bitkub import Bitkub #have no updated v2

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

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
mornitorFilePath = dataPath + '/mornitor.csv'
transacFilePath = dataPath + '/transaction.csv'

""""""
# BITKUB API V2 PATCH
""""""
class bitkub_version_contol:
    @staticmethod
    def get_endpoints(ENDPOINTS, version=2):
        '''
        #https://github.com/appcorner/bitkub/blob/master/bitkub/constants.py
        :param ENDPOINTS: (from Bitkub Module)
        :return: new replaced API_ROOT
        '''
        new_endpoints = {
            "MARKET_PLACE_BID" : "/api/market/v{}/place-bid".format(version),
            "MARKET_PLACE_ASK" : "/api/market/v{}/place-ask".format(version),
            "MARKET_CANCEL_ORDER": "/api/market/v{}/cancel-order".format(version),
            "MARKET_BALANCES": "/api/v{}/market/balances".format(version)
        }
        for k in new_endpoints:
            ENDPOINTS[k] = new_endpoints[k]
        return ENDPOINTS

    @staticmethod
    def get_api_version(API_KEY):
        result = True if len(API_KEY) > 32 else False
        if result:
            return 3
        else:
            return 2

""""""
# BITKUB API Vxxx INIT
""""""
import bitkub as bk
bk.bitkub.ENDPOINTS = bitkub_version_contol.get_endpoints(bk.bitkub.ENDPOINTS)
Bitkub = bk.Bitkub

""""""
# REALTIME TRADER FUNC
""""""
def getBalance(idName):
    global Bitkub, bk
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return None
    API_VER = bitkub_version_contol.get_api_version(API_KEY)
    if API_VER == 3:
        bk.bitkub.ENDPOINTS = bitkub_version_contol.get_endpoints(bk.bitkub.ENDPOINTS, version=3)
        Bitkub = bk.Bitkub
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = bitkub.balances()
    ticker = bitkub.ticker()
    data = {}
    if balance['error'] != 0:
        return None
    if balance['error'] == 0 :
        total = 0.0
        for sym in balance['result']:
            if balance['result'][sym]['available'] > 0 :
                available = balance['result'][sym]['available']
                """
                available_h = max([
                    available,
                    configJson[idName]['available'],
                    configJson[idName]['availableHigh']
                ])
                """
                #p_drawdown = (abs(available_h-available)/available_h)*100
                #p_drawdown = round(p_drawdown,2)
                data[sym] = {
                    'available' : available,
                    'reserved' : balance['result'][sym]['reserved']
                }
                # calulate total value
                if sym == 'THB':
                    total += available
                elif not '{}_{}'.format('THB',sym) in ticker :
                    continue
                else:
                    total += ( ticker['{}_{}'.format('THB',sym)]['last'] * available )
                #update balance data sheet
                if sym == 'THB' and round(available,0) != round(configJson[idName]['available'],0):
                    gSheet.setValue( 'Config', findKey='idName', findValue=idName, key='available', value=available )
                    #gSheet.setValue( 'Config', findKey='idName', findValue=idName, key='availableHigh',value=available_h )
                    #gSheet.setValue( 'Config', findKey='idName', findValue=idName, key='percentageDrawdown',value=p_drawdown )
        #update total value sheet
        if round(configJson[idName]['totalValue']*.1,0) != round(total*.1,0):
            gSheet.setValue('Config', findKey='idName', findValue=idName, key='totalValue', value=total)
    return data

def CreateSellOrder(idName,symbol,count=1):
    global Bitkub, bk
    result = {}
    def return_true():
        return [True, result]
    def return_false():
        return [False, result]

    if not symbol.__contains__('THB_'):
        print('symbol name need contains THB_')
        return return_false()
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return return_false()
    API_VER = bitkub_version_contol.get_api_version(API_KEY)
    if API_VER == 3:
        bk.bitkub.ENDPOINTS = bitkub_version_contol.get_endpoints(bk.bitkub.ENDPOINTS, version=3)
        Bitkub = bk.Bitkub
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = getBalance(idName)
    sym = symbol.replace('THB_','')

    if not sym in list(balance):
        print('not found [{}] in balance'.format(sym))
        return return_false()

    amount = balance[sym]['available'] / count
    if count <= 1:
        amount = balance[sym]['available']
    result = bitkub.place_ask(sym=symbol, amt=amount, typ='market')
    print(result)
    return return_true()

def CreateBuyOrder(idName,symbol,portfoiloList,countLeft):
    global Bitkub, bk
    result = {}
    def return_true():
        return [True, result]
    def return_false():
        return [False, result]

    if countLeft <= 0 :
        print('count left = 0')
        return return_false()
    if not symbol.__contains__('THB_'):
        print('symbol name need contains THB_')
        return return_false()
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    if API_KEY == '' or API_SECRET == '' :
        print('this user have no API KEY or API SECRET to send order')
        return return_true() #True When Bot is using
    API_VER = bitkub_version_contol.get_api_version(API_KEY)
    if API_VER == 3:
        bk.bitkub.ENDPOINTS = bitkub_version_contol.get_endpoints(bk.bitkub.ENDPOINTS, version=3)
        Bitkub = bk.Bitkub
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    balance = getBalance(idName)
    percentageBalanceUsing = configJson[idName]['percentageBalanceUsing']
    system = configJson[idName]['system']
    size = int(configJson[idName]['portSize'])
    portSize = len(list(balance))-1 if balance !=None else 0 #Real Port
    buySize = int(configJson[idName]['buySize'])
    history = bitkub.my_open_history(sym=symbol)

    #history {'error' : 0, 'result': []}
    if not 'result' in history:
        err_msg = '''
        'can\'t connect to Bitkub API please check key and secret.
        {0}
        KEY : {1}
        SECRET : {2}
        API VERSION : {3}
        '''.strip().format(history, API_KEY, API_SECRET, API_VER)
        raise Warning(err_msg)
    if len(history['result']) != 0:
        for data in history['result']:
            data_select = history['result'][0]
            buyHourDuration = (time.time() - data['ts']) / 60 / 60 #hour
            if buyHourDuration < configJson[idName]['buyEveryHour'] and data['side'].lower() == 'buy':
                print('Order Cancel')
                print(data['date'])
                print(data['side'])
                print(buyHourDuration)
                return return_false()

    portSymList = []
    for sym in portfoiloList:  # Chane Symbol to Sym
        q = sym.replace('THB_', '')
        portSymList.append(q)

   # User&Bot Balance Check
    is_bot_bl = balance == None
    is_user_bl = not is_bot_bl and 'THB' in balance
    if is_bot_bl: # Verify Bot
        return return_true()
    elif not is_user_bl: # Verify User but Have no THB
        return return_false()

    #print('size {}'.format(size))
    #print('portSize {}'.format(portSize))
    print('countLeft {}'.format(countLeft))
    if not 'THB' in balance:
        print('cannot found THB in balance')
        return return_false()
    budget = balance['THB']['available']
    #sizedBudget = ( (budget / (size-portSize)) /countLeft) * (percentageBalanceUsing/100)
    sizedBudget =  ( budget/countLeft ) * ( percentageBalanceUsing/100 )
    print('sizedBudget {}'.format(sizedBudget))
    print('sending order for buy {}'.format(symbol))
    result = bitkub.place_bid(sym=symbol, amt=sizedBudget, typ='market')
    print(result)
    return return_true()

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
        print('Checking User {} in Mornitor'.format(user))
        if not user in list(configJson):
            deleteList.append(user)
    for user in t_user_list:
        print('Checking User {} in Transaction'.format(user))
        if not user in list(configJson):
            deleteList.append(user)

    #Sending Restart
    for user in list(configJson):
        if bool(configJson[user]['reset']):
            text = '[ Reset Portfoilo ]\n' +\
                   'User ID : {} \n'.format(user) +\
                   'Preset ID : {} \n'.format(configJson[user]['preset']) +\
                   'System ID : {} \n'.format(configJson[user]['system']) +\
                   'Portfolio Size : {} \n'.format(configJson[user]['portSize']) +\
                   'Position Size : {} \n'.format(configJson[user]['buySize']) +\
                   'Target Profit : {}%'.format(configJson[user]['percentageProfitTarget'])
            lineNotify.sendNotifyMassage(configJson[user]['lineToken'],text)
            gSheet.setValue('Config', findKey='idName', findValue=user, key='reset', value=0)
            gSheet.setValue('Config', findKey='idName', findValue=user, key='lastReport', value=time.time())
            print(text)

            #Clear all real portfolio
            API_KEY = configJson[user]['bk_apiKey']
            API_SECRET = configJson[user]['bk_apiSecret']
            bitkub = Bitkub()
            bitkub.set_api_key(API_KEY)
            bitkub.set_api_secret(API_SECRET)
            balance = getBalance(user)
            #print(balance)
            if balance == None:
                continue
            for sym in balance:
                if sym == 'THB':
                    continue
                symbol = 'THB_{}'.format(sym)
                print(symbol)
                print('Sell {} {}'.format(balance[sym]['available'],sym))
                sell_order = CreateSellOrder(user, symbol, count=1)

    for user in deleteList:
        print('delete [ {} ]'.format(user))
        m_df = m_df[m_df['User'] != user]
        t_df = t_df[t_df['User'] != user]

    m_df.to_csv(mornitorFilePath,index=False)
    t_df.to_csv(transacFilePath, index=False)
    print('User Reset')

def rec_transaction(idName,code,symbol,change,result_msg=''):
    global transacFilePath
    date_time = str(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    epoch = round(time.time())
    data = {
        'dateTime' : [date_time],
        'epoch' : [epoch],
        'User' : [idName],
        'Code' : [code],
        'Symbol' : [symbol],
        'Change%' : [change],
        'CashBalance' : [configJson[idName]['available']],
        'TotalValue' : [configJson[idName]['totalValue']],
        'Result' : [result_msg],
    }
    #col = ['dateTime']
    if not os.path.exists(transacFilePath):
        entry_df = pd.DataFrame(columns=list(data))
        entry_df.to_csv(transacFilePath, index=False)

    try: #Use Main file
        entry_df = pd.read_csv(transacFilePath)
    except: #Use Backup file
        alluser_df = pd.read_csv(
            backup_version(transacFilePath, rollback_version=True)
        )

    # Checking Column
    for c in list(data):
        if not c in entry_df.columns.tolist():
            entry_df[c] = None
    rec = pd.DataFrame(data)
    entry_df = entry_df.append(rec,ignore_index=True)
    entry_df = entry_df.tail(15000)
    entry_df.to_csv(transacFilePath,index=False)

def Realtime(idName,sendNotify=True):
    # Backup
    mornitor_backup_dir = dataPath + '/mornitor_backup'
    mornitor_backup_list_dir = [i for i in os.listdir(mornitor_backup_dir) if i.endswith('.csv')]

    isActive = bool(configJson[idName]['active'])
    isReset = bool(configJson[idName]['reset'])
    if isActive == False:
        return None
    print('---------------------\n[ {} ]  Monitoring\n---------------------'.format(idName))
    bitkub = Bitkub()
    ticker = bitkub.ticker()
    now = round(time.time())
    reportHourDuration = round(float(((now - configJson[idName]['lastReport']) / 60) / 60), 2)
    preset = configJson[idName]['preset']
    system = configJson[idName]['system']
    token = configJson[idName]['lineToken']
    portSize = int(configJson[idName]['portSize'])
    buySize = int(configJson[idName]['buySize'])
    profitTarget = float(configJson[idName]['percentageProfitTarget'])
    lossTarget = float(configJson[idName]['percentageLossTarget']) * (-1)
    triggerBuy = systemJson[system]['triggerBuy']
    triggerSell = systemJson[system]['triggerSell']
    triggerBuyPos = systemJson[system]['triggerBuyPosition']
    triggerSellPos = systemJson[system]['triggerSellPosition']
    adaptiveLoss = bool(configJson[idName]['adaptiveLoss'])
    autoPreset = bool(configJson[idName]['autoPreset'])
    minAdaptiveLoss = configJson[idName]['minAdaptiveLoss']
    print('Portfolio Size : {} | Buy Position Size : {}'.format(portSize, buySize))
    print('Buy : {} | Sell : {}'.format(triggerBuy,triggerSell))
    print('Trigger Buy : {} | Trigger Sell : {}'.format(triggerBuyPos,triggerSellPos))
    favoriteList = []
    dislikeList = []
    try:favoriteList = configJson[idName]['favorite'].split(',')
    except:print('favorite isn\'t readable!')
    try:dislikeList = configJson[idName]['dislike'].split(',')
    except:print('dislike isn\'t readable!')
    if favoriteList == ['']:
        favoriteList = []
    if dislikeList == ['']:
        dislikeList = []
    print('Favorite : {}\nDislike : {}'.format(favoriteList, dislikeList))

    colSelect = ['User', 'Symbol', 'Signal', 'Buy', 'Market',
                 'Profit%', 'Max_Drawdown%', 'Change4HR%',
                 'Volume', 'BreakOut_H', 'BreakOut_MH', 'BreakOut_M',
                 'BreakOut_ML', 'BreakOut_L', 'Low', 'High', 'Rec_Date','Count'
                 ,'Last_Buy','Max_Profit%']

    #Signal Dataframe
    signal_df = pd.read_csv(dataPath + '/signal.csv')
    signal_df = signal_df[
        (signal_df['Rec_Date'] == signal_df['Rec_Date'].max()) &
        (signal_df['Preset'] == preset)
        ]
    signal_df = signal_df.sort_values(['Change4HR%','Volume','Risk%'], ascending=[True,False,True])
    signal_df.reset_index(inplace=True)
    # Signal All Dataframe
    signal_df_all = signal_df
    new_lossTarget = signal_df_all['Avg_Drawdown%'].max()
    if np.isnan(new_lossTarget):
        print('adaptive loss error !! new loss target is {}'.format(new_lossTarget))
        new_lossTarget = 15.0
    if new_lossTarget <= minAdaptiveLoss:
        new_lossTarget = minAdaptiveLoss
    new_lossTarget = round(new_lossTarget, 2)

    #print(signal_df_all['Drawdown%'].mean())
    #print(signal_df_all['NDay_Drawdown%'].mean())
    #print(signal_df_all['Avg_Drawdown%'].mean())

    # New Column For Signal DF
    signal_df['User'] = idName
    signal_df['Buy'] = signal_df['Close']
    signal_df['Market'] = signal_df['Close']
    signal_df['Profit%'] = ((signal_df['Market'] - signal_df['Buy']) / signal_df['Buy']) * 100
    signal_df['Max_Drawdown%'] = 0.0
    signal_df['Max_Profit%'] = 0.0
    signal_df['Count'] = 1
    signal_df['Last_Buy'] = now
    for sym in ticker:
        signal_df.loc[(signal_df['Symbol'] == sym), 'Buy'] = ticker[sym]['last']
        signal_df.loc[(signal_df['Symbol'] == sym), 'Market'] = ticker[sym]['last']
    #print(signal_df[colSelect])

    #Portfolio File Checking
    if not os.path.exists(mornitorFilePath):
        port_df = pd.DataFrame(columns=colSelect)
        port_df.to_csv(mornitorFilePath,index=False)

    #Read User Portfolio
    try: #Use main File
        port_df = pd.read_csv(mornitorFilePath)
    except: #Use Backup file
        port_df = pd.read_csv(
            backup_version(mornitorFilePath, rollback_version=True)
        )

    port_df = port_df[
        (port_df['User'] == idName)
    ]
    port_df.reset_index(inplace=True)

    # Update Favorite Symbol
    for symbol in port_df['Symbol'].tolist():
        if symbol in favoriteList:
            favoriteList.remove(symbol)

    print('Portfolio')
    print(port_df['Symbol'].tolist())

    print('---------------------\nBuying\n---------------------')
    #Find New Buy
    buy_df = None
    if triggerBuyPos == 'Lower':
        buy_df = signal_df[
                (signal_df['Signal'] == triggerBuy) &
                (signal_df['Market'] < signal_df['BreakOut_ML']) &
                (signal_df['NDay_Drawdown%'] > signal_df['Avg_Drawdown%'])
            ][colSelect]
    elif triggerBuyPos == 'Upper':
        buy_df = signal_df[
                (signal_df['Signal'] == triggerBuy) &
                (signal_df['Market'] > signal_df['BreakOut_MH'])&
                (signal_df['NDay_Drawdown%'] > signal_df['Avg_Drawdown%'])
            ][colSelect]
    elif triggerBuyPos == 'Middle':
        buy_df = signal_df[
                (signal_df['Signal'] == triggerBuy) &
                (signal_df['Market'] < signal_df['BreakOut_M'])&
                (signal_df['NDay_Drawdown%'] > signal_df['Avg_Drawdown%'])
            ][colSelect]

    #buy_df = buy_df.head(portSize)
    #print('Buy Data Frame')
    print(buy_df[['Symbol','Signal','Market','BreakOut_MH','BreakOut_ML']].head(5))
    #Buy Condition
    for i in buy_df.index.tolist():
        #Reset Port df index
        port_df.reset_index(inplace=True, drop=True)

        row = buy_df.loc[i]
        text = '[ Buy ] {}\n{} Bath'.format(row['Symbol'].replace('THB_',''), row['Buy'])
        if row['Symbol'] in dislikeList:
            continue
        if row['Symbol'] in port_df['Symbol'].tolist(): #Symbol is in portfolio already
            #print('  Checking buy count')
            symbol_index = port_df[port_df['Symbol'] == row['Symbol']].index.tolist()[0]
            #print('now',now)
            #print('port_df.loc[symbol_index,\'Last_Buy\']',port_df.loc[symbol_index,'Last_Buy'])
            buyHourDuration = round(float(((now - port_df.loc[symbol_index,'Last_Buy']) / 60) / 60), 2)
            if port_df.loc[symbol_index,'Count'] < buySize : #Buy position size is not full
                if buyHourDuration >= configJson[idName]['buyEveryHour']: #if Duration geater than Buy Hour

                    # dip target calculate
                    dipTarget = (abs(lossTarget)/buySize)
                    if dipTarget < 20.0:
                        dipTarget = 20.0
                        if abs(lossTarget) > dipTarget:
                            dip_loss_rate = abs(lossTarget) * 0.3
                            dipTarget = 20.0 + dip_loss_rate  # avg value , weight
                        dipTarget = round(dipTarget, 3)
                    dipPrice = port_df.loc[symbol_index, 'Buy'] - (port_df.loc[symbol_index, 'Buy'] * (dipTarget / 100))

                    if row['Market'] <= dipPrice: #Buy on Dip or Not Dip
                        # Do Buy
                        print('Buy {} more'.format(row['Symbol']))
                        portfolioList = port_df['Symbol'].tolist()
                        countLeft = (buySize * portSize) - (port_df['Count'].sum())
                        buy_order = CreateBuyOrder(idName, row['Symbol'], portfolioList, countLeft)
                        if not buy_order[0]:
                            continue
                        rec_transaction(
                            idName, 'Buy', row['Symbol'],(configJson[idName]['percentageComission'] / 100) * -1,
                            result_msg=json.dumps(buy_order[1], sort_keys=True))
                        if sendNotify:
                            lineNotify.sendNotifyMassage(token, text + '\nOn dip lower {}%'.format(dipTarget))
                        port_df.loc[symbol_index, 'Count'] += 1
                        port_df.loc[symbol_index, 'Rec_Date'] = row['Rec_Date']
                        port_df.loc[symbol_index, 'Last_Buy'] = row['Last_Buy']
                        if port_df.loc[symbol_index, 'Count'] > 2 : # Price Average
                            port_df.loc[symbol_index, 'Buy'] = round(
                                ((port_df.loc[symbol_index, 'Buy']*2) + row['Buy']) * (1/3), 2)
                        else:
                            port_df.loc[symbol_index, 'Buy'] = round(
                                (port_df.loc[symbol_index, 'Buy'] + row['Buy']) * (1/2), 2)

        elif not row['Symbol'] in port_df['Symbol'].tolist(): #Symbol isn't in portfolio
            #print('  Checking port is not full')
            newPortSize = portSize
            if not row['Symbol'] in favoriteList:
                newPortSize = portSize - len(favoriteList)
                if newPortSize < 0 :
                    newPortSize = 0
            if port_df['Symbol'].count() < newPortSize:  #Portfolio isn't full
                # Do Buy
                print('Buy {} as new symbol'.format(row['Symbol']))
                portfolioList = port_df['Symbol'].tolist()
                countLeft = (buySize * portSize) - (port_df['Count'].sum())
                buy_order = CreateBuyOrder(idName, row['Symbol'], portfolioList, countLeft)
                if not buy_order[0]:
                    continue
                rec_transaction(
                    idName, 'Buy', row['Symbol'], (configJson[idName]['percentageComission'] / 100) * -1,
                    result_msg=json.dumps(buy_order[1], sort_keys=True))
                if sendNotify:
                    quote = row['Symbol'].split('_')[-1]
                    img_file_path = imgPath + os.sep + '{}_{}.png'.format(preset, quote)
                    if os.path.exists(img_file_path):
                        #lineNotify.sendNotifyImageMsg(token, img_file_path, text)
                        lineNotify.sendNotifyMassage(token, text)
                    else:
                        lineNotify.sendNotifyMassage(token, text)
                port_df = port_df.append(row, ignore_index=False)
    #Finish Buy
    port_df.reset_index(drop=True,inplace=True)

    print('---------------------\nProfit Calulating\n---------------------')
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
            port_df.loc[symbol_index, 'Max_Profit%'] = max([
                port_df.loc[symbol_index, 'Profit%'],
                port_df.loc[symbol_index, 'Max_Profit%']
            ])

    # Portfolio report
    print('---------------------\nReport\n---------------------')
    if port_df['Symbol'].count() != 0 and reportHourDuration >= configJson[idName]['reportEveryHour']:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='lastReport', value=time.time())
        symbolTextList = port_df['Symbol'].tolist()
        countTextList = port_df['Count'].tolist()
        profitTextList = port_df['Profit%'].tolist()
        spList = []
        available = round(configJson[idName]['available'])
        total = round(configJson[idName]['totalValue'])
        unrealize = round(total - available)
        for i in range(len(symbolTextList)):
            sp = '{}   ({}/{}) ({}%)'.format(
                symbolTextList[i].replace('THB_',''),
                countTextList[i],
                buySize,
                profitTextList[i]
            )
            spList.append(sp)
        text = '[ Report ]\n' + \
               '{}'.format('\n'.join(spList)) + \
               '\n' + \
               '\nAvg Profit {}%'.format(port_df['Profit%'].mean().round(2)) + \
               '\nLoss Target {}%'.format(abs(lossTarget)) + \
               '\n' + \
               '\nAvailable {:,.2f} B.'.format(available) + \
               '\nUnrealized {:,.2f} B.'.format(unrealize) + \
               '\nTotal Value {:,.2f} B.'.format(total)

        if sendNotify:
            lineNotify.sendNotifyMassage(token, text)

        #Adaptive Loss Update
        if adaptiveLoss and abs(lossTarget) > new_lossTarget:
            gSheet.setValue('Config', findKey='idName', findValue=idName, key='percentageLossTarget',
                            value=new_lossTarget)
            #if sendNotify:
                #lineNotify.sendNotifyMassage(token, 'New Loss Target : {}%'.format(new_lossTarget))

    print('---------------------\nSelling\n---------------------')
    new_loss_list = []
    for i in port_df.index.tolist():
        row = port_df.loc[i]
        sell_signal = False
        sell_profit = row['Profit%'] > profitTarget
        sell_loss = row['Profit%'] < lossTarget
        sell_dislike = row['Symbol'] in dislikeList
        sell_trailing = (
            (row['Profit%'] > 1) and
            (row['Profit%'] > 0.15*profitTarget) and
            (row['Profit%'] < profitTarget) and
            (row['Count'] >= buySize) and
            ((row['Max_Profit%'] - row['Profit%']) > profitTarget*0.5)
        )

        #Adaptive Loss After Selling
        if adaptiveLoss and sell_loss:
            new_loss_list.append(new_lossTarget)

        if triggerSellPos == 'Lower':
            sell_signal = (
                (row['Signal'] == triggerSell) and
                (row['Market'] < row['BreakOut_ML']) and
                (row['Profit%'] > 0.15*profitTarget) and
                (row['Profit%'] > 3.5)
            )
        elif triggerSellPos == 'Upper':
            sell_signal = (
                (row['Signal'] == triggerSell) and
                (row['Market'] > row['BreakOut_MH']) and
                (row['Profit%'] > 0.15*profitTarget) and
                (row['Profit%'] > 3.5)
            )
        elif triggerSellPos == 'Middle':
            sell_signal = (
                (row['Signal'] == triggerSell) and
                (row['Market'] > row['BreakOut_M']) and
                (row['Profit%'] > 0.15*profitTarget) and
                (row['Profit%'] > 3.5)
            )

        #if sell_profit or sell_signal or sell_loss or isReset or sell_dislike or sell_trailing : #Sell
        if sell_profit or sell_signal or isReset or sell_dislike or sell_trailing : #Sell no Cut Loss
            text = '[ Sell ] {}\n{} Bath ({}%)'.format(row['Symbol'].replace('THB_',''), row['Market'], row['Profit%'])
            print(text)

            if isReset or sell_dislike or sell_profit or sell_trailing or sell_loss:
                port_df.loc[i, 'Count'] = 0 # Sell All
            else:
                port_df.loc[i, 'Count'] -= 1
            if port_df.loc[i, 'Count'] > buySize:
                port_df.loc[i, 'Count'] = buySize
            if port_df.loc[i, 'Count'] < 0:
                port_df.loc[i, 'Count'] = 0

            #text condition
            if isReset:
                text = text + '\nby Reset'
            elif sell_signal:
                text = text + '\nby Signal'
            elif sell_profit:
                text = text + '\nby Profit'
            elif sell_loss:
                text = text + '\nby Stop Loss'
            elif sell_dislike:
                text = text + '\nby Dislike'
            elif sell_trailing:
                text = text + '\nby Trailing Stop'

            # Do Sell
            count = port_df.loc[i, 'Count'] + 1
            sell_order = CreateSellOrder(idName, row['Symbol'],count=count)
            time.sleep(1)
            profit = (( row['Profit%'] / buySize ) * row['Count']) / portSize #real percentage of total cost
            rec_transaction(
                idName, 'Sell', row['Symbol'],((configJson[idName]['percentageComission'] / 100) * -1) + profit,
                result_msg=json.dumps(sell_order[1], sort_keys=True))
            if sendNotify:
                quote = row['Symbol'].split('_')[-1]
                img_file_path = imgPath + os.sep + '{}_{}.png'.format(preset, quote)
                if os.path.exists(img_file_path) and port_df.loc[i, 'Count'] <= 0: # Send Image at last count
                    lineNotify.sendNotifyImageMsg(token, img_file_path, text)
                else:
                    lineNotify.sendNotifyMassage(token, text)

        if port_df.loc[i, 'Count'] <= 0 : #Delete symbol if no count
            port_df = port_df[port_df['Symbol'] != row['Symbol']]
    if new_loss_list != []:
        gSheet.setValue('Config', findKey='idName', findValue=idName, key='percentageLossTarget',
                        value=sum(new_loss_list)/len(new_loss_list))
        #if sendNotify:
            #lineNotify.sendNotifyMassage(token, 'New Loss Target : {}%'.format(new_lossTarget))

    print('---------------------\nAuto Preset\n---------------------')
    if autoPreset:
        days_score = 3
        tran_df = pd.read_csv(transacFilePath)
        tran_df = tran_df[tran_df['epoch'] >= now - ((1 * 60 * 60 * 24) * days_score)]
        tran_df['Change%'] = tran_df.groupby(['User'])['Change%'].transform('sum')
        tran_df.drop_duplicates(subset=['User'], keep='last', inplace=True)
        tran_df = tran_df[tran_df['CashBalance'] == 0.0]
        tran_df = tran_df.sort_values(['Change%'], ascending=[False])
        # Delete if Use Auto Preset
        for user in configJson:
            if bool(configJson[user]['autoPreset']):
                tran_df = tran_df[tran_df['User'] != user]
        # Select Top User
        tran_df.reset_index(inplace=True, drop=True)
        if not tran_df.empty:
            top_user = tran_df.iloc[0]['User']
            top_chg = tran_df.iloc[0]['Change%'].round(2)
            print('highest score bot user in {} days : {} : {} %'.format(days_score, top_user, top_chg))
            aPreset = configJson[top_user]['preset']
            aSystem = configJson[top_user]['system']
            # Apply New Preset and System
            if configJson[top_user]['preset'] != configJson[idName]['preset']:
                gSheet.setValue('Config', findKey='idName', findValue=idName, key='preset', value=aPreset)
                if sendNotify:
                    lineNotify.sendNotifyMassage(token, 'Change Preset to {}\n{}'.format(aPreset,presetJson[aPreset]['description']))
            if configJson[top_user]['system'] != configJson[idName]['system']:
                gSheet.setValue('Config', findKey='idName', findValue=idName, key='system', value=aSystem)
                if sendNotify:
                    lineNotify.sendNotifyMassage(token, 'Change System to {}\n{}'.format(aSystem,systemJson[aSystem]['description']))

    print('---------------------\nBalance Checking\n---------------------')
    # Clear Wrong Balnace
    balance = getBalance(idName)
    if balance != None:  # Have Secret API
        print('{} Real Porfolio {}'.format(idName, list(balance)))
        portfolioList = port_df['Symbol'].tolist()
        #balanceList = []
        dropList = []
        for sym in balance:  # Check Real Balance -> Mornitor Balance
            if balance[sym]['available'] != 0 and sym != 'THB':  # if not THB and have available
                symbol = 'THB_{}'.format(sym)
                if not symbol in portfolioList:  # Not balance in mornitor
                    sell_order = CreateSellOrder(idName, symbol, count=1)
                    #balanceList.append(symbol)
        for symbol in portfolioList: # Check Mornitor Balance -> Real Balance
            sym = symbol.replace('THB_','')
            if not sym in balance: # Not found Symbol in real balance get sync
                #port_df = port_df[port_df['Symbol'] != symbol]
                print('Not found Symbol in real balance', sym, list(balance))
                pass

    # ===============Finish========================
    for i in ['index', 'level_0']:
        if i in port_df.columns.tolist():
            port_df.drop(columns=[i], inplace=True)

    try: #Use Main file
        alluser_df = pd.read_csv(mornitorFilePath)
    except: #Use Backup file
        alluser_df = pd.read_csv(
            backup_version(mornitorFilePath, rollback_version=True)
        )

    alluser_df = alluser_df[alluser_df['User'] != idName]
    alluser_df = alluser_df.append(port_df)
    for i in ['index', 'level_0']:
        if i in alluser_df.columns.tolist():
            alluser_df.drop(columns=[i], inplace=True)
    alluser_df.to_csv(mornitorFilePath,index=False)

    #Backup
    backup_version(mornitorFilePath, rollback_version=False)
    backup_version(transacFilePath, rollback_version=False)
    print('---------------------\nFinish\n---------------------\n')

def backup_version(df_path, rollback_version=False):
    if not df_path.endswith('.csv'): return None
    backup_dir = os.path.dirname(df_path) + os.sep + os.path.basename(df_path).split('.')[0] + '_backup'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    if rollback_version: #Get latest backup file
        backup_list_dir = os.listdir(backup_dir)
        if os.path.exists(backup_dir) and backup_list_dir != []:
            last_mornitor_fp = [backup_dir + '/' + i for i in backup_list_dir][-2]  # Select before 1H
            return last_mornitor_fp
        else:
            raise Warning('cannot rollback version of {}'.format(os.path.basename(df_path)))

    if not rollback_version: # Backup mode
        date_str = str(dt.datetime.now().strftime('%Y_%m_%d_%H'))
        new_name = os.path.basename(df_path).replace('.csv', '_{}.csv'.format(date_str))
        new_path = backup_dir + os.sep + new_name
        shutil.copy(df_path, new_path)

        # Clear Backup
        backup_list = [i for i in os.listdir(backup_dir) if '.csv' in i]
        backup_path_list = [backup_dir + os.sep + i for i in backup_list]
        backup_f_limit = 24 * 5
        if len(backup_path_list) > backup_f_limit:
            backup_path_list = sorted(backup_path_list)[-backup_f_limit:]
            for fp in [backup_dir + os.sep + i for i in backup_list]:
                if not fp in backup_path_list:
                    os.remove(fp)

def run_all_user(*_):
    def isInternetConnect(*_):
        url = 'http://google.com'
        connectStatus = requests.get(url).status_code
        if connectStatus == 200:
            return True
        else:
            return False

    os.system('cls||clear')
    global mornitorFilePath
    global transacFilePath
    error_dict = {}
    for user in configJson:
        if os.name == 'nt':
            print('[For Dev Testing...]')
            Realtime(user,sendNotify=False)
        else:
            try:
                Realtime(user)
            except Exception as e:
                import traceback
                error_str = str(traceback.format_exc())
                print('!!!! ==========================')
                print(error_str)
                print('!!!! ==========================')
                error_dict[user] = error_str
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
    print('---------------------\nError Chicking\n---------------------\n')
    if error_dict == {}:
        print('no error...')
        time.sleep(1.5 * 60)
    else:
        for user in error_dict:
            print('------------\nUSER {}\n-------------\n'.format(user.upper()))
            print(error_dict[user])
        time.sleep(5 * 60)

if __name__ == '__main__' :
    run_all_user()
    ''' 
    sell data
    {'error': 0, 'result': {'id': 44454663, 'hash': 'fwQ6do9eqwAuC6bEXp3nXdpjCMy', 'typ': 'market',
     'amt': 0.33796304, 'rat': 1, 'fee': 0, 'cre': 0, 'rec': 0, 'ts': 1674790919}}
     if error
     {'error': 2}
    '''
    #pass
    ''' # Check Bot or User by Balance Check
    for user in ['bot0', 'user0']:
        bl = getBalance(user)
        print(user, bl)

        is_bot_bl = bl == None
        is_user_bl = not is_bot_bl and 'THB' in bl
        if is_bot_bl:
            print('bot')
        elif not is_user_bl:
            print('user no money')
        else:
            print('user have money')
    '''
