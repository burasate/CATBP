import os,json
import requests
import gSheet

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
configPath = dataPath + '/config.json'
configJson = json.load(open(configPath))
presetPath = dataPath + '/preset.json'
presetJson = json.load(open(presetPath))

updateListURL = 'https://raw.githubusercontent.com/burasate/StockPy/main/update/update.json'
while True:
    connectStatus = requests.get(updateListURL).status_code
    if connectStatus == 200:
        updateFilePath = requests.get(updateListURL).text
        break
fileNameSet = json.loads(updateFilePath)

def updateAllFile(*_):
    pass
    """
    for file in fileNameSet:
        print('Updating {} from {}'.format(file,fileNameSet[file]))
        url = fileNameSet[file]
        while True:
            connectStatus = requests.get(url).status_code
            print('connecting...')
            if connectStatus == 200:
                mainWriter = open(rootPath + os.sep + file, 'w')
                urlReader = requests.get(url).text
                mainWriter.writelines(urlReader)
                mainWriter.close()
                break
    print('System Updated')
    """

def updateConfig(*_):
    print('updating config...')
    dataSheet = gSheet.getAllDataS('Config')
    #print(configSheet)

    dataS = {}
    for row in dataSheet:
        dataS[row['idName']] = row
    print(dataS)

    json.dump(dataS, open(configPath, 'w'), indent=4)

def updatePreset(*_):
    print('updating preset...')
    dataSheet = gSheet.getAllDataS('Preset')

    dataS = {}
    for row in dataSheet:
        dataS[row['preset']] = row
    print(dataS)

    json.dump(dataS, open(presetPath, 'w'), indent=4)

if __name__ == '__main__':
    updateConfig()
    updatePreset()
    #updateAllFile()
