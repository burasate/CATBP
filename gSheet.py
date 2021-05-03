import gspread,csv,os
from oauth2client.service_account import ServiceAccountCredentials

rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = rootPath+'/data'
jsonKeyPath = dataPath + '/gSheet.json'
sheetName = 'BitkubPy'

def connect(*_):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credential = ServiceAccountCredentials.from_json_keyfile_name(jsonKeyPath, scope)
    gc = gspread.authorize(credential)
    return gc

def loadConfigData(idName):
    print('Loading config data from database....')
    sheet = connect().open(sheetName).worksheet('Config')
    configS = sheet.get_all_records()
    for r in configS :
        if r['idName'] == idName:
            print('config is loaded')
            return r
    print ('Can not found ID Name')
    return None

def getWorksheetColumnName(workSheet):
    sheet = connect().open(sheetName).worksheet(workSheet)
    header = sheet.row_values(1)
    return header

def updateFromCSV(csvPath, workSheet,newline=''):
    sheet = connect().open(sheetName).worksheet(workSheet)

    #load csv
    tableList = []
    with open(csvPath, 'r', newline=newline) as readfile:
        for row in csv.reader(readfile,delimiter=','):
            tableList.append(row)
        readfile.close()

    try:
        sheet.clear()
        sheet.update(tableList,value_input_option='USER_ENTERED')
    except:
        raise IOError('Update Sheet Error')

def addRow(workSheet,column):
    sheet = connect().open(sheetName).worksheet(workSheet)
    sheet.append_row(column,value_input_option='USER_ENTERED')

def deleteRow(workSheet,colName,value):
    sheet = connect().open(sheetName).worksheet(workSheet)
    dataS = sheet.get_all_records()
    rowIndex = 1
    for data in dataS:
        rowIndex += 1
        if data[colName] == value:
            sheet.delete_rows(rowIndex,rowIndex)
            print('Sheet "{}" Deleted Row {}'.format(workSheet,rowIndex))

def getAllDataS(workSheet):
    sheet = connect().open(sheetName).worksheet(workSheet)
    dataS = sheet.get_all_records()
    return dataS

def setValue(workSheet,findKey=None,findValue=None,key=None,value=None):
    dataS = getAllDataS(workSheet)
    rowIndex = 1
    for data in dataS:
        rowIndex += 1
        if not key in data:
            return None
        if data[findKey] == findValue and key in data:
            colIndex = 0
            for col in getWorksheetColumnName(workSheet):
                colIndex += 1
                if col == key:
                    sheet = connect().open(sheetName).worksheet(workSheet)
                    sheet.update_cell(row=rowIndex,col=colIndex,value=value)
                    print('update cell in > row : {}  column : \'{}\'  value : {}'.format(rowIndex,key,value))
                    break
            break

def sortFisrtColumn(workSheet):
    sheet = connect().open(sheetName).worksheet(workSheet)
    sheet.sort((1, 'asc'))

if __name__ == '__main__':
    import pprint
    #setValue('test',findKey='episode',findValue=2,key='cut_duration',value=20)
    pass