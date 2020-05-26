import csv
g_cycle = 10
g_difficulty = 2
g_bcFileName = "blockchain.csv"
importedBlockchain = []

with open(g_bcFileName, 'r',  newline='') as file:
    blockReader = csv.reader(file)
    for line in blockReader:
        importedBlockchain.append([line[0], line[1], line[2], line[3], line[4], line[5]])

def countZero(previousdiff):
    for i in range(1,64):
        checkzero = previousdiff[0:i].count("0")
        print(checkzero)
        if (checkzero != i):
            return i-1


def calculateDifficulty(blockchainPath = importedBlockchain, difficulty = g_difficulty, visitValue = g_cycle):

    blockchain = blockchainPath
    sumTime = 0

    previousdiff= blockchain[-1][4]
    print(previousdiff)

    #제네시스 블록생성시 예외
    if(int(blockchain[-1][0])<visitValue):
        return difficulty
    else:

        if (int(blockchain[-1][0])%visitValue == 0):
            endblockIndex = int(blockchain[-1][0])
            startblockIndex = endblockIndex - visitValue
            timegap = int(blockchain[endblockIndex][2]) - int(blockchain[startblockIndex][2])
#             for i in range(startblockIndex-1, endblockIndex):
#                 #수정필요, 합이 아닌 마지막 스탬프와 처음스탬프의 차만 있으면됨
#                 sumTime += int(blockchain[i][2])
            problemDiff = countZero(previousdiff)
            print(timegap)
            print(visitValue)
            if(timegap > visitValue*700):
                difficulty = problemDiff -1
                return difficulty
            elif(timegap >= visitValue*500):
                return difficulty
            else:
                difficulty = problemDiff + 1
                return difficulty
        else:
            return difficulty



calculateDifficulty()
