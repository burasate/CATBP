import historical
import time
import update

update.updateAllFile()

if __name__ == '__main__':
    pass

while True:
    time.sleep(10)
    historical.updateGSheetHistory()

