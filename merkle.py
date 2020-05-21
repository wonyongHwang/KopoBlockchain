def calculateHash(index, previousHash, timestamp, data, proof):
    value = str(index) + str(previousHash) + str(timestamp) + str(data) + str(proof)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())


def calculateHashtwo(index, previousHash):
    value = str(index) + str(previousHash)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())


def calculateHashone(index):
    value = str(index)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())


strTxData = []

temptHashList = []

# 거래장부 전체, 문자열 변환

importedTx = ["b", "c", "d", "e", "g"]

# 전체 거래장부(정규표현식)
checker = True
if len(importedTx) > 0:
    strTxData = importedTx

    while (checker == True):

        if (len(strTxData)//16 >= 1):
            tonerList = []
            while (innerChecker == True):
                originToner = strTxData
                if (len(strTxData) > 16):
                    numToner = len(strTxData // 16)
                    restToner = len(strTxData % 16)
                    #for문 넣을때, 문자열 더하기 및 중복 문자에 rep 삽입 여부
                    #해쉬값을 돌리면서 임시 temptHashList에 담는 것 구현
                    if(resToner >= 2):
                        firstTonerAdd = random.sample(strTxData, 1)
                        filter(lambda a: a != firstTonerAdd, strTxData)
                        secondTonerAdd = random.sample(strTxData, 1)
                        filter(lambda a: a != firstTonerAdd, strTxData)
                        restToner = restToner - 2
                        firstToner.append(firstTonerAdd)
                        secondToner.append(secondTonerAdd)
                    elif(resToner == 1):
                        firstTonerAdd = random.sample(strTxData, 1)
                        filter(lambda a: a != firstTonerAdd, strTxData)
                        secondTonerAdd = random.sample(originToner, 1)
                        ##복제 변수 적용할 때 문자열 앞에 rep. 붙이는것은?
                        resToner = resToner -1
                        firstToner.append(firstTonerAdd)
                        secondToner.append(secondTonerAdd)
                    elif(restToner == 0):
                        firstToner = random.sample(strTxData, numToner)
                        filter(lambda a: a != firstToner, strTxData)
                        secondToner = random.sample(strTxData, numToner)
                        filter(lambda a: a != secondToner, strTxData)
        elif (len(strTxData)//16 < 1 && len(strTxData)//8 > 0):
        elif (len(strTxData)//16 < 1 && len(strTxData)//8 < 1 && len(strTxData)//4 > 0):
        else:
            numToner = len(strTxData // 2)
            restToner = len(strTxData % 2)
            if (restToner == 1):
            elif(resToner == 0):





            ### 다시 써야하는 함수 그룹
            tempt = calculateHashtwo(a, b)

            temptHashList.append(tempt)


            strTxData = temptHashList
            if (len(temptHashList) == 1):
                checker = False
                print(strTxData)

            elif (len(temptHashList) == 0):
                print("abnormal calculate")
                break
