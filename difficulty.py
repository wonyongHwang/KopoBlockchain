###difficulty ver.0
###1. 디버깅 필요
###2. 해당함수 투입지점 필요(아마도 mine에 넣으면 될것으로 예상)

### m_cycle변수는 난이도 갱신주기
###calculateDifficulty 함수는 출력 시 m_difficulty를 변수로 받아서
###번역변수의 초기화 필요
###



def countZero(previousdiff):
    for i in range(1,64):
    checkzero = hashsample[0:i].count("0")
    print(checkzero)
    if (checkzero != i):
        return i-1


def calculateDifficulty(blockchainPath = g_bcFileName, difficulty = g_difficulty, visitValue = g_cycle):

    blockchain = readBlockchain(blockchainPath)
    sumTime = 0

    previousdiff= blockchain[-1].currentHash
    if(int(blockchain[-1]['index'])<visitValue):
        return difficulty
    else:

        if (int(blockchain[-1]['index'])%visitValue == 0):
            endblockIndex = int(blockchain[-1]['index'])
            startblockIndex = endblockIndex - visitValue
            for i in range(startblockIndex-1, endblockIndex):
                sumTime += blockchain[i]['timestamp']

            problemDiff = countZero(previousdiff)
            if(sumTime > visitValue*700):
                difficulty = problemDiff -1
                return difficulty
            elif(sumTime >= visitValue*500):
                return difficulty
            else:
                difficulty = problemDiff + 1
                return difficulty
        else:
            return difficulty
