import gspread
import csv
import os
from oauth2client.service_account import ServiceAccountCredentials


rootPath = os.path.dirname(os.path.abspath(__file__))
dataPath = os.path.join(rootPath, 'data')
jsonKeyPath = os.path.join(dataPath, 'gSheet.json')
sheetName = 'BitPy'


def connect():
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    credential = ServiceAccountCredentials.from_json_keyfile_name(jsonKeyPath, scope)
    return gspread.authorize(credential)


def getWorksheetColumnName(workSheet):
    sheet = connect().open(sheetName).worksheet(workSheet)
    return sheet.row_values(1)


def updateFromCSV(csvPath, workSheet, newline=''):
    sheet = connect().open(sheetName).worksheet(workSheet)

    with open(csvPath, 'r', newline=newline, encoding='utf-8') as f:
        tableList = list(csv.reader(f))

    try:
        sheet.clear()
        print(f'update data to {workSheet} please don\'t exit!')
        sheet.update(tableList, value_input_option='USER_ENTERED')
    except Exception as e:
        raise RuntimeError(f'Update Sheet Error: {e}') from e


def addRow(workSheet, column):
    sheet = connect().open(sheetName).worksheet(workSheet)
    sheet.append_row(column, value_input_option='USER_ENTERED')


def deleteRow(workSheet, colName, value):
    sheet = connect().open(sheetName).worksheet(workSheet)
    dataS = sheet.get_all_records()

    for idx, data in enumerate(dataS, start=2):
        if data.get(colName) == value:
            sheet.delete_rows(idx)
            print(f'Sheet "{workSheet}" Deleted Row {idx}')
            return


def getAllDataS(workSheet):
    sheet = connect().open(sheetName).worksheet(workSheet)
    return sheet.get_all_records()


def setValue(workSheet, findKey=None, findValue=None, key=None, value=None):
    sheet = connect().open(sheetName).worksheet(workSheet)
    headers = getWorksheetColumnName(workSheet)

    if key not in headers:
        return None

    colIndex = headers.index(key) + 1
    dataS = sheet.get_all_records()

    for idx, data in enumerate(dataS, start=2):
        if data.get(findKey) == findValue:
            sheet.update_cell(row=idx, col=colIndex, value=value)
            print(f'update cell in > row : {idx}  column : \'{key}\'  value : {value}')
            return


def sortFisrtColumn(workSheet):
    sheet = connect().open(sheetName).worksheet(workSheet)
    sheet.sort((1, 'asc'))


if __name__ == '__main__':
    pass
    #import pprint
    #pprint.pprint(getAllDataS('Config'))
