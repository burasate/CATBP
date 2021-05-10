import json,hashlib,os,hmac,requests
import pprint
import pandas as pd

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))

host = 'https://api.bitkub.com'

def json_encode(data):
	return json.dumps(data, separators=(',', ':'), sort_keys=True)

def sign(idName,data):
    user = getKeySecret(idName)
    secret = bytes(user['secret'],'utf-8')

    j = json_encode(data)
    print('Signing payload: ' + j)

    h = hmac.new(secret, msg=j.encode(), digestmod=hashlib.sha256)
    return h.hexdigest()

def getKeySecret(idName):
    data = {
        'key' : configJson[idName]['bk_apiKey'],
        'secret' : configJson[idName]['bk_apiSecret']
    }
    return data

def getSymbol(*_):
    response = requests.get(host+'/api/market/symbols')
    #pprint.pprint(response.text)
    data = response.json()
    if data['error'] == 0:
        return data['result']

def getTicker(*_):
    response = requests.get(host+'/api/market/ticker')
    data = response.json()
    return data

def getBalance(idName):
    user = getKeySecret(idName)

    # check server time
    response = requests.get(host + '/api/servertime')
    ts = int(response.text)
    print('Server time: ' + response.text)

    # check balances
    header = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-BTK-APIKEY': user['key'],
    }
    data = {
        'ts': ts,
    }
    signature = sign(idName,data)
    data['sig'] = signature

    print('Payload with signature: ' + json_encode(data))
    response = requests.post(host + '/api/market/balances', headers=header, data=json_encode(data))

    print('Balances: ' + response.text)

def getBids(symbol,limit=30,dataframe=True):
    data = {'sym' : symbol,
            'lmt' : limit
            }
    response = requests.get(host + '/api/market/bids',data)
    resultData = response.json()
    dataList = []
    for row in resultData['result']:
        dataList.append(
            {
                'id' : row[0],
                'timestamp' : row[1],
                'volume' : row[2],
                'rate' : row[3],
                'amount' : row[4]
             }
        )
    if dataframe:
        return pd.DataFrame.from_records(dataList)
    else:
        return dataList

def getAsks(symbol,limit=30,dataframe=True):
    data = {'sym' : symbol,
            'lmt' : limit
            }
    response = requests.get(host + '/api/market/asks',data)
    resultData = response.json()
    dataList = []
    for row in resultData['result']:
        dataList.append(
            {
                'id' : row[0],
                'timestamp' : row[1],
                'volume' : row[2],
                'rate' : row[3],
                'amount' : row[4]
             }
        )
    if dataframe:
        return pd.DataFrame.from_records(dataList)
    else:
        return dataList

if __name__ == '__main__':
    getBalance('user1')
    #x = getAsks('THB_DOGE',limit=10)
    #print(x)
    #symbols = getSymbol()
