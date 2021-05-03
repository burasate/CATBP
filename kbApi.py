import json,hashlib,os,hmac,requests
import pprint

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))

host = 'https://api.bitkub.com'

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

if __name__ == '__main__':
    print(getTicker())
    pass
    #x = getKeySecret('user1')
    #print(x)
    #symbols = getSymbol()
