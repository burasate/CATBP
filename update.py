import os,json, pprint
import requests
import gSheet

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
configPath = dataPath + '/config.json'
presetPath = dataPath + '/preset.json'
systemPath = dataPath + '/system.json'

updateListURL = 'https://raw.githubusercontent.com/burasate/BitPy/master/update.json'
while True:
    connectStatus = requests.get(updateListURL).status_code
    if connectStatus == 200:
        updateFilePath = requests.get(updateListURL).text
        break
fileNameSet = json.loads(updateFilePath)

def updateAllFile(*_):
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

def updateConfig(*_):
    print('updating config...')
    dataSheet = gSheet.getAllDataS('Config')

    dataS = {}
    for row in dataSheet:
        dataS[row['idName']] = row
    pprint.pprint(dataS)

    json.dump(dataS, open(configPath, 'w'), indent=4)

def updatePreset(*_):
    print('updating preset...')
    dataSheet = gSheet.getAllDataS('Preset')

    dataS = {}
    for row in dataSheet:
        dataS[row['preset']] = row
    pprint.pprint(dataS)

    json.dump(dataS, open(presetPath, 'w'), indent=4)

def updateSystem(*_):
    print('updating system...')
    dataSheet = gSheet.getAllDataS('System')

    dataS = {}
    for row in dataSheet:
        dataS[row['system']] = row
    pprint.pprint(dataS)

    json.dump(dataS, open(systemPath, 'w'), indent=4)

if __name__ == '__main__':
    updateConfig()
    updatePreset()
    updateSystem()
    #updateAllFile()
