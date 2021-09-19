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
    if balance['error'] != 0:
        return None
    if balance['error'] == 0 :
        for sym in balance['result']:
            if balance['result'][sym]['available'] > 0 :
                available = balance['result'][sym]['available']
                available_h = max([
                    available,
                    configJson[idName]['available'],
                    configJson[idName]['availableHigh']
                ])
                p_drawdown = (abs(available_h-available)/available_h)*100
                p_drawdown = round(p_drawdown,2)
                data[sym] = {
                    'available' : available,
                    'reserved' : balance['result'][sym]['reserved']
                }
                #update balance data sheet
                if sym == 'THB' and available != configJson[idName]['available']:
                    gSheet.setValue( 'Config', findKey='idName', findValue=idName, key='available', value=available )
                    gSheet.setValue( 'Config', findKey='idName', findValue=idName, key='availableHigh',value=available_h )
                    gSheet.setValue( 'Config', findKey='idName', findValue=idName, key='percentageDrawdown',value=p_drawdown )
    return data

def CreateSellOrder(idName,symbol,count=1):
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
    if countLeft <= 0 :
        print('count left = 0')
        return None
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
    size = int(configJson[idName]['portSize'])
    portSize = len(list(balance))-1 #Real Port
    buySize = int(configJson[idName]['buySize'])
    history = bitkub.my_open_history(sym=symbol)

    if len(history['result']) != 0:
        for data in history['result']:
            data_select = history['result'][0]
            buyHourDuration = (time.time() - data['ts']) / 60 / 60 #hour
            if buyHourDuration < configJson[idName]['buyEveryHour'] and data['side'].lower() == 'buy':
                print('Order Cancel')
                print(data['date'])
                print(data['side'])
                print(buyHourDuration)
                return None

    portSymList = []
    for sym in portfoiloList:  # Chane Symbol to Sym
        q = sym.replace('THB_', '')
        portSymList.append(q)

    #print('size {}'.format(size))
    #print('portSize {}'.format(portSize))
    print('countLeft {}'.format(countLeft))
    budget = balance['THB']['available']
    #sizedBudget = ( (budget / (size-portSize)) /countLeft) * (percentageBalanceUsing/100)
    sizedBudget =  ( budget/countLeft ) * (percentageBalanceUsing/100)
    print('sizedBudget {}'.format(sizedBudget))
    print('sending order for buy {}'.format(symbol))
    result = bitkub.place_bid(sym=symbol, amt=sizedBudget, typ='market')
    print(result)
    return result

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
            for sym in balance:
                if sym == 'THB':
                    continue
                symbol = 'THB_{}'.format(sym)
                print(symbol)
                print('Sell {} {}'.format(balance[sym]['available'],sym))
                CreateSellOrder(user, symbol, count=1)


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
    epoch = round(time.time())
    data = {
        'dateTime' : [date_time],
        'epoch' : [epoch],
        'User' : [idName],
        'Code' : [code],
        'Symbol' : [symbol],
        'Change%' : [change],
        'CashBalance' : [configJson[idName]['available']]
    }
    #col = ['dateTime']
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
    entry_df = entry_df.tail(12000)
    entry_df.to_csv(transacFilePath,index=False)

def Realtime(idName,sendNotify=True):
    isActive = bool(configJson[idName]['active'])
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
    dipTraget = systemJson[system]['dipPercentage']
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
        new_lossTarget = 10.0
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
    port_df = pd.read_csv(mornitorFilePath)
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
    print(buy_df[['Symbol','Signal','Market','BreakOut_MH','BreakOut_ML']])
    #Buy Condition
    for i in buy_df.index.tolist():
        row = buy_df.loc[i]
        text = '[ Buy ] {}\n{} Bath'.format(row['Symbol'], row['Buy'])
        if row['Symbol'] in dislikeList:
            continue
        if row['Symbol'] in port_df['Symbol'].tolist(): #Symbol is in portfolio already
            #print('  Checking buy count')
            symbol_index = port_df[port_df['Symbol'] == row['Symbol']].index.tolist()[0]
            buyHourDuration = round(float(((now - port_df.loc[symbol_index,'Last_Buy']) / 60) / 60), 2)
            if port_df.loc[symbol_index,'Count'] < buySize : #Buy position size is not full
                if buyHourDuration >= configJson[idName]['buyEveryHour']: #if Duration geater than Buy Hour
                    dipPrice = port_df.loc[symbol_index, 'Buy'] - (port_df.loc[symbol_index, 'Buy'] * (dipTraget / 100))
                    if row['Market'] <= dipPrice or dipTraget == 0: #Buy on Dip or Not Dip
                        # Do Buy
                        print('Buy {} more'.format(row['Symbol']))
                        portfolioList = port_df['Symbol'].tolist()
                        countLeft = (buySize * portSize) - (port_df['Count'].sum())
                        buyOrder = CreateBuyOrder(idName, row['Symbol'], portfolioList, countLeft)
                        if buyOrder is None:
                            continue
                        Transaction(idName, 'Buy', row['Symbol'], (configJson[idName]['percentageComission'] / 100) * -1)
                        if sendNotify:
                            lineNotify.sendNotifyMassage(token, text)
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
                buyOrder = CreateBuyOrder(idName, row['Symbol'], portfolioList, countLeft)
                if buyOrder is None:
                    continue
                Transaction(idName, 'Buy', row['Symbol'], (configJson[idName]['percentageComission'] / 100) * -1)
                if sendNotify:
                    quote = row['Symbol'].split('_')[-1]
                    imgFilePath = imgPath + os.sep + '{}_{}.png'.format(preset, quote)
                    lineNotify.sendNotifyImageMsg(token, imgFilePath, text)
                    #lineNotify.sendNotifyMassage(token, text)
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
        profitTextList = port_df['Profit%'].tolist()
        spList = []
        for i in range(len(symbolTextList)):
            sp = '  - {}      ({}%)'.format(
                symbolTextList[i],
                profitTextList[i]
            )
            spList.append(sp)
        text = '[ Report ]\n' + \
               '{}'.format('\n'.join(spList)) + \
               '\nAvg Profit {}%'.format(port_df['Profit%'].mean().round(2))
        print(text)
        if sendNotify:
            lineNotify.sendNotifyMassage(token, text)

        #Adaptive Loss Update
        if adaptiveLoss and abs(lossTarget) > new_lossTarget:
            gSheet.setValue('Config', findKey='idName', findValue=idName, key='percentageLossTarget',
                            value=new_lossTarget)
            if sendNotify:
                lineNotify.sendNotifyMassage(token, 'New Loss Target : {}'.format(new_lossTarget))


    print('---------------------\nSelling\n---------------------')
    #Sell Condition
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
            #new_lossTarget = abs(row['Profit%'])
            #new_lossTarget = ( abs(port_df['Max_Drawdown%'].mean()) + abs(row['Profit%']) ) * 0.5
            #new_lossTarget = signal_df_all['Avg_Drawdown%'].max()
            #print('new loss target = {}'.format(new_lossTarget))
            #if not np.isnan(new_lossTarget): # new_lossTarget Not Nan
            #new_lossTarget = round(new_lossTarget, 2)
            gSheet.setValue('Config', findKey='idName', findValue=idName, key='percentageLossTarget',
                            value=new_lossTarget)
            if sendNotify:
                lineNotify.sendNotifyMassage(token, 'New Loss Target : {}'.format(new_lossTarget))

        if triggerSellPos == 'Lower':
            sell_signal = (
                (row['Signal'] == triggerSell) and
                (row['Market'] < row['BreakOut_ML']) and
                (row['Profit%'] > 0.15*profitTarget) and
                (row['Profit%'] > 1)
            )
        elif triggerSellPos == 'Upper':
            sell_signal = (
                (row['Signal'] == triggerSell) and
                (row['Market'] > row['BreakOut_MH']) and
                (row['Profit%'] > 0.15*profitTarget) and
                (row['Profit%'] > 1)
            )
        elif triggerSellPos == 'Middle':
            sell_signal = (
                (row['Signal'] == triggerSell) and
                (row['Market'] > row['BreakOut_M']) and
                (row['Profit%'] > 0.15*profitTarget) and
                (row['Profit%'] > 1)
            )

        if sell_profit or sell_signal or sell_loss or isReset or sell_dislike or sell_trailing : #Sell
            text = '[ Sell ] {}\n{} Bath ({}%)'.format(row['Symbol'], row['Market'], row['Profit%'])
            print(text)

            if isReset or sell_dislike or sell_profit or sell_trailing or sell_loss:
                port_df.loc[i, 'Count'] = 0 # Sell All
            else:
                port_df.loc[i, 'Count'] -= 1

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
            CreateSellOrder(idName, row['Symbol'],count=count)
            time.sleep(1)
            profit = (( row['Profit%'] / buySize ) * row['Count']) / portSize #real percentage of total cost
            Transaction(idName, 'Sell', row['Symbol'],
                        ((configJson[idName]['percentageComission'] / 100) * -1) + profit)
            if sendNotify:
                lineNotify.sendNotifyMassage(token, text)

        if port_df.loc[i, 'Count'] <= 0 : #Delete symbol if no count
            port_df = port_df[port_df['Symbol'] != row['Symbol']]

    print('---------------------\nAuto Preset\n---------------------')
    if autoPreset:
        dayScore = 5
        tran_df = pd.read_csv(transacFilePath)
        tran_df = tran_df[
            tran_df['epoch'] >= now - ((1 * 60 * 60 * 24) * dayScore)
            ]
        tran_df['Change%'] = tran_df.groupby(['User'])['Change%'].transform('sum')
        tran_df.drop_duplicates(subset=['User'], keep='last', inplace=True)
        tran_df = tran_df.sort_values(['Change%'], ascending=[False])
        # Delete if Use Auto Preset
        for user in configJson:
            if bool(configJson[user]['autoPreset']):
                tran_df = tran_df[tran_df['User'] != user]
        # Select Top User
        topUser = tran_df.iloc[0]['User']
        aPreset = configJson[topUser]['preset']
        aSystem = configJson[topUser]['system']
        # Apply New Preset and System
        if configJson[topUser]['preset'] != configJson[idName]['preset']:
            gSheet.setValue('Config', findKey='idName', findValue=idName, key='preset', value=aPreset)
            if sendNotify:
                lineNotify.sendNotifyMassage(token, 'Change Preset to {}\n{}'.format(aPreset,presetJson[aPreset]['description']))
        if configJson[topUser]['system'] != configJson[idName]['system']:
            gSheet.setValue('Config', findKey='idName', findValue=idName, key='system', value=aSystem)
            if sendNotify:
                lineNotify.sendNotifyMassage(token, 'Change System to {}\n{}'.format(aSystem,systemJson[aSystem]['description']))

    print('---------------------\nBalance Checking\n---------------------')
    # Clear Wrong Balnace
    balance = getBalance(idName)
    if balance != None:  # Have Secret API
        portfolioList = port_df['Symbol'].tolist()
        balanceList = []
        dropList = []
        for sym in balance:  # Check Real Balance
            if balance[sym]['available'] != 0 and sym != 'THB':  # if not THB and have available
                symbol = 'THB_{}'.format(sym)
                if not symbol in portfolioList:  # Not balace in mornitor
                    CreateSellOrder(idName, symbol, count=1)
                    if sendNotify:
                        lineNotify.sendNotifyMassage(token, 'Clear {} in Balance'.format(symbol))
                    balanceList.append(symbol)
        """
        for i in port_df.index.tolist():  # Check Mornitor
            row = port_df.loc[i]
            if not row['Symbol'] in balanceList:
                dropList.append(row['Symbol'])
        for symbol in dropList:  # Delete Fake Mornitor for User who have KeyAPI
            port_df = port_df[port_df['Symbol'] != symbol]
            if sendNotify:
                lineNotify.sendNotifyMassage(token, 'Clear {} in Mornitor'.format(symbol))
        """

    #Finish
    if 'index' in port_df.columns.tolist():
        port_df.drop(columns=['index'],inplace=True)
    if 'level_0' in port_df.columns.tolist():
        port_df.drop(columns=['level_0'], inplace=True)
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
    """
    import update
    update.updateConfig()
    update.updatePreset()
    update.updateSystem()
    configJson = json.load(open(configPath))
    presetJson = json.load(open(presetPath))
    systemJson = json.load(open(systemPath))
    """

    """
    idName='user1'
    API_KEY = configJson[idName]['bk_apiKey']
    API_SECRET = configJson[idName]['bk_apiSecret']
    bitkub = Bitkub()
    bitkub.set_api_key(API_KEY)
    bitkub.set_api_secret(API_SECRET)
    """
    #result = bitkub.place_bid(sym='THB_NEAR', amt=100, typ='market')
    #print(result)
    """
    CreateBuyOrder('user10', 'THB_WAN',
                   [
                       'THB_USDT',
                       'THB_USDC',
                       'THB_WAN',
                       'THB_AAVE',
                       'THB_NEAR',
                       'THB_XLM'
                   ]
    , 80)
    """
    Realtime('user1', sendNotify=False)

    pass