import json,requests,os
import pandas as pd
import numpy as np

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
histPath = dataPath+'/hist/'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))
histFileList = os.listdir(histPath)
imgPath = dataPath+'/analysis_img/'
ImgFiles = os.listdir(imgPath)

url = 'https://notify-api.line.me/api/notify'

def sendNotifyMassage (token,text):
    print('Sending Massage')
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.post(url, headers=headers , data = {'message':'\n'+text})
    print (r.text)

def sendNotifyImageMsg (token,imagePath,text):
    print('Sending Image {}'.format(imagePath))
    headers = {'Authorization': 'Bearer ' + token}
    r = requests.post(url, headers=headers ,data = {'message':'\n'+text}, files = {'imageFile':open(imagePath,'rb')})
    print (r.text)

def signalReportToUser(*_):
    import datetime as dt
    date = dt.date.today().strftime('%d/%m/%Y')
    import stockAnalysis
    for user in configJson:
        if bool(configJson[user]['active']):
            token = configJson[user]['lineToken']
            preset = configJson[user]['preset']
            description = configJson[user]['description']

            # Load Preset
            ps_value = presetJson[preset]["value"]
            ps_priceMin = presetJson[preset]["priceMin"]
            ps_priceMax = presetJson[preset]["priceMax"]
            ps_sma_s = presetJson[preset]["smaS"]
            ps_sma_l = presetJson[preset]["smaL"]
            ps_breakout_high = presetJson[preset]["breakOutH"]
            ps_breakout_low = presetJson[preset]["breakOutL"]

            print('sending to {} ({}) preset \"{}\"'.format(user, description, preset))

            # Load Signal Data
            df = pd.read_csv(dataPath + os.sep + 'signal.csv')
            df = df[df['Rec_Date'] == df['Rec_Date'].max()]

            df =  df[df['Preset']==preset]
            entry_list =  df[df['Signal']=='Entry']['Quote'].tolist()
            exit_list =  df[df['Signal']=='Exit']['Quote'].tolist()
            #print(entry_list)
            #print(exit_list)


            # Message Text
            text_buy = 'Trade Entry △ \n   {}\n'.format(' '.join(entry_list))
            text_sell = 'Trade Exit ▽ \n   {}\n'.format(' '.join(exit_list))

            msg_signal = date + '\n' +\
                        'Preset Name \"{}\" '.format(preset) +\
                        '\n' + text_buy + text_sell
            #print(msg_signal)
            sendNotifyMassage(token, msg_signal)

            #Send Images
            for i in range(df[df['Preset'] == preset]['Preset'].count()):
                select = df[df['Preset'] == preset].iloc[i]
                q_msg = '▹ {} {}   \n'.format(select['Quote'], select['Close'])+\
                        'Month Chg {}% \n'.format(select['Chang_M%'])+\
                        'Break Out {}/{}\n'.format(select['BreakOut_L'],select['BreakOut_H'])+\
                        'Risk {}% - {}%\n'.format(select['NDay_Drawdown%'].round(1),
                                                        select['Max_Drawdown%'].round(1))+ \
                        'Value {} m'.format(select['Value_M'])
                #print (q_msg)

                # try send image with timeout checking
                timeOut = 10
                for i in range(timeOut):
                    try:
                        imgFile = '{}_{}.png'.format(preset,select['Quote'])
                        sendNotifyImageMsg(token, imgPath + imgFile, q_msg)
                        break
                    except:
                        if i >= timeOut:
                            break
                        else:
                            pass


if __name__=='__main__':
    #sendNotifyMassage('Fq2uIz8AnqmCS2J9eA6ttmVhY1dfDdPp7lzAlsrDc44','test')
    #sendNotifyImageMsg('Fq2uIz8AnqmCS2J9eA6ttmVhY1dfDdPp7lzAlsrDc44','C:/Users/DEX3D_I7/Pictures/UglyDolls2_1.mp4_snapshot_01.17.998.jpg',"asfdfas")
    #import update
    #update.updatePreset()
    #presetPath = dataPath + '/preset.json'
    #presetJson = json.load(open(presetPath))
    #signalReportToUser()
    pass
