import hashlib
import time
import csv
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import json
import re
from urllib.parse import parse_qs
from urllib.parse import urlparse
import threading
import cgi
import uuid
from tempfile import NamedTemporaryFile
import shutil
import requests
import pymysql
from sqlalchemy import create_engine
import pandas as pd

PORT_NUMBER = 8099
MAX_GET_DATA_LISTS = 10
MAX_NUMBER_OF_TX = 50
DATABASE_SVR_NAME = "bcSvr1" ####################
DATABASE_SVR_IP = "localhost"
DATABASE_SVR_PORT = 3301
DATABASE_SVR_USER = "root"
DATABASE_SVR_PW = "root"
DATABASE_BC_TABLE = "blockchain" ########################
DATABASE_ND_TABLE = "node"   ########################
DATABASE_TPSVR_IP = "http://192.168.110.22:8099"

g_difficulty = 2
SVR_LIST = {'127.0.0.1': 8096, '192.168.110.19' : 3300, '192.168.110.23' : 3300}
g_receiveNewBlock = "/node/receiveNewBlock"
g_maximumTry = 100
g_maximumGetTx = 50
g_nodeList = {'127.0.0.1': '8096'}  # trusted server list, should be checked manually
engine = create_engine("mysql+pymysql://root:root@192.168.110.16:3300/bcSvr1")

class Block:

    def __init__(self, index, previousHash, timestamp, data, currentHash, proof, merkleHash):
        self.index = index
        self.previousHash = previousHash
        self.timestamp = timestamp
        self.data = data
        self.currentHash = currentHash
        self.proof = proof
        # -----------------------------------------V01 : 완
        # 머클트리로 추출한 해쉬
        self.merkleHash = merkleHash

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class txData:

    def __init__(self, commitYN, sender, amount, receiver, fee, uuid, transactionTime):
        self.commitYN = commitYN
        self.sender = sender
        self.amount = amount
        self.receiver = receiver
        self.fee = fee
        self.uuid = uuid
        self.transactionTime = transactionTime

class Node:

    def __init__(self, ip, port, tryConnect):
        self.ip = ip
        self.port = port
        self.tryConnect = tryConnect

def generateGenesisBlock(timestamp, proof):
    isSuccess = True
    newBlock = None
    GenesisTxData = [{"commitYN" : "0", "sender": "Genesis Block", "amount": "0", \
              "receiver": "kim", "fee": "0"}]

    reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
    try:
        URL = DATABASE_TPSVR_IP + "/txData/new"
        print(URL)
        res = requests.post(URL, headers=reqHeader, data=json.dumps(GenesisTxData))
        if res.status_code == 200:
            #                 print(URL + " sent ok.")
            print("Genesis txData sent ok.")
        else:
            #                 print(URL + " responding error " + res.status_code)
            print(URL + " responding error " + 404)
            isSuccess = False
            return newBlock, isSuccess
    except:
        print("Trusted Server " + URL + " is not responding.")
        isSuccess = False
        return newBlock, isSuccess

    txData, txTF = getTxData(0)

    merkleHash = calculateMerkleHash(txData)
    tempHash = calculateHash(0, '0', timestamp, proof, merkleHash)
    genesisBlockData = getStrTxData(txData)
    return Block(0, '0', timestamp, genesisBlockData, tempHash, proof, merkleHash), isSuccess



def calculateHash(index, previousHash, timestamp, proof, merkleHash):
    value = str(index) + str(previousHash) + str(timestamp) + str(proof) + merkleHash
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())

def getStrTxData(txData) :
    strTxData = ''
    if len(txData) > 0:
        for i in txData:
            transaction = "[" + i['uuid'] + "]" "UserID " + i['sender'] + " sent " + i['amount'] + " bitTokens to UserID " + \
i['receiver'] + " fee "+ i['fee'] + " transaction time " + str(i['transactionTime']) + ". "
            print(transaction)
            strTxData += transaction
    return strTxData

def calculateMerkleHash(txData) :
    txDataList = []
    print("hash merkling..................")
    if len(txData) > 0:
        for i in txData:
            transaction = "[" + i['uuid'] + "]" "UserID " + i['sender'] + " sent " + i['amount'] + " bitTokens to UserID " + \
                            i['receiver'] + " fee "+ i['fee'] + " transaction time " + str(i['transactionTime']) + ". "
            print(transaction)
            txDataList.append(transaction)
    return rcGetMerkleHash(txDataList)


def rcGetMerkleHash(target) :
    strBinaryTxData = ""
    #check
    print("current len of Target =  " + str(len(target)))
    endIndexOfTarget = len(target) - 1
    if len(target) <= 1 :
        sha = hashlib.sha256(target[0].encode('utf-8'))
        return str(sha.hexdigest())
    #1개 이상이라면 1개가 될때까지 계속 해쉬화
    else :
        newTarget = []
        for i in range(endIndexOfTarget - 1):
            if i % 2 == 0 :
                strBinaryTxData = strBinaryTxData + target[i] + target[i+1]
                sha = hashlib.sha256(target[i].encode('utf-8'))
                newTarget.append(str(sha.hexdigest()))

        #target리스트의 길이가 홀수라면
        if (len(target) % 2) != 0:
            sha = hashlib.sha256(target[endIndexOfTarget].encode('utf-8'))
            newTarget.append(str(sha.hexdigest()))
        #짝수라면
        else :
            strBinaryTxData = strBinaryTxData + target[endIndexOfTarget-1] + target[endIndexOfTarget]
            sha = hashlib.sha256(strBinaryTxData.encode('utf-8'))
            newTarget.append(str(sha.hexdigest()))
        #재귀   
        return rcGetMerkleHash(newTarget)

def calculateHashForBlock(block):
    return calculateHash(block.index, block.previousHash, block.timestamp, block.proof, block.merkleHash)


def getLatestBlock(blockchain):
    return blockchain[len(blockchain) - 1]


def generateNextBlock(blockList, txData, timestamp, proof):
    print("generateNextBlockㅎㅎ")
    print(blockList)
    print(txData)
    print(timestamp)
    print(proof)
    isSuccess = True
    newBlock = None
    blockData = []
    try:
        previousBlock = getLatestBlock(blockList)
        nextIndex = int(previousBlock.index) + 1
        nextTimestamp = timestamp
        strTxData = getStrTxData(txData)
        merkleHash = calculateMerkleHash(txData)

        newBlockFound = False
        while not newBlockFound :
            nextHash = calculateHash(nextIndex, previousBlock.currentHash, nextTimestamp, proof, merkleHash)
            if nextHash[0:g_difficulty] == '0' * g_difficulty:
                newBlockFound = True
            else:
                proof += 1
        newBlock = Block(nextIndex, previousBlock.currentHash, nextTimestamp, strTxData, nextHash, proof, merkleHash)

    except :
        print("generateNextBlockㅎㅎexcept")
        isSuccess = False
    return newBlock, isSuccess


def writeBlockchain(blockchain):
    print(blockchain.index, blockchain.previousHash, str(blockchain.timestamp), "writeBlockchainㅎㅎ")
    tableBlockList, isSuccess = readBlockchain()
    print(tableBlockList, isSuccess, "ㅎㅎ")
    urlBlockList = []
    blockchainList = []
    blockchainList.append(blockchain)
    result = 1

    if isSuccess :
        try :
            for block in blockchainList:
                blockList = [block.index, block.previousHash, str(block.timestamp), block.data, block.currentHash, block.proof, block.merkleHash]
                urlBlockList.append(blockList)
            last_line_number = len(tableBlockList)
            print(last_line_number)
            for line in tableBlockList:
                print(tableBlockList.line_num, last_line_number, "g")
                if last_line_number == len(tableBlockList) :
                    lastBlock = Block(line[0], line[1], line[2], line[3], line[4], line[5], line[6])
            if int(lastBlock.index) + 1 != int(blockchainList[-1][0]):
                print("index sequence mismatch")
                if int(lastBlock.index) == int(blockchainList[-1][0]):
                    print("db has already been updated")
                    return
        except:
            print("Failed to in check current db \n or maybe there's some other reason")
            pass

        conn = pymysql.connect(
            host=DATABASE_SVR_IP,
            port=DATABASE_SVR_PORT,
            user=DATABASE_SVR_USER,
            passwd=DATABASE_SVR_PW,
            database=DATABASE_SVR_NAME)

        try:
            with conn.cursor() as curs:
                print(blockchain.index, blockchain.previousHash, str(blockchain.timestamp), \
                                    blockchain.data, blockchain.currentHash, blockchain.proof, blockchain.merkleHash)
                sql = "INSERT INTO " + DATABASE_BC_TABLE + " VALUES (%s,%s,%s,%s,%s,%s,%s)"
                curs.execute(sql,(blockchain.index, blockchain.previousHash, str(blockchain.timestamp), \
                                    blockchain.data, blockchain.currentHash, blockchain.proof, blockchain.merkleHash))
                conn.commit()
        except :
            print("fail to read blockchain table")
        finally:
            conn.close()


    else :
        print("Failed to read table")
        result = -1
    if result == 1 :
        print("Complete updating blockchain")
    return result

def readBlockchain():
    print("readBlockchain")
    result = False
    blockDataList = []
    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER, password=DATABASE_SVR_PW, \
                           db=DATABASE_SVR_NAME, charset='utf8')

    try:
        with conn.cursor() as cursor :
            sql = "select * from " + DATABASE_BC_TABLE
            cursor.execute(sql)
            rows = cursor.fetchall()

            for data in rows:
                block = Block(data[0], data[1], data[2], data[3], data[4], data[5], data[6])
                blockDataList.append(block)
            result = True
    except:
        print("connect failed or other reason")
    finally:
        conn.close()
    return blockDataList, result


def updateTx(blockData):
    phrase = re.compile(
        r"\w+[-]\w+[-]\w+[-]\w+[-]\w+")

    print(blockData.data)
    matchList = phrase.findall(blockData.data)
    print(matchList)
    if len(matchList) == 0:
        print("No Match Found! " + str(blockData.data) + "block idx: " + str(blockData.index))

        return
    reqHeader = {'Content-Type': 'application/json; charset=utf-8'}

    blockDict = []
    blockDict.append(blockData.__dict__)
    print(blockDict)
    try:
        URL = DATABASE_TPSVR_IP + "/txData/update"
        print(URL)
        res = requests.post(URL, headers=reqHeader, data=json.dumps(blockDict))
        if res.status_code == 200:
            #                 print(URL + " sent ok.")
            print("sent ok.")
            return 1
        else:
            #                 print(URL + " responding error " + res.status_code)
            print(URL + " responding error " + 404)
            return -1
    except:
        print("Trusted Server " + URL + " is not responding.")
        return -1
    print('txData updated')


def getTxData(chooseData):
    print("getTxData입니다.")
    url = DATABASE_TPSVR_IP + "/getTxData/zero"
    if (chooseData == 1) :
        url = DATABASE_TPSVR_IP + "/getTxData/all"
    txList = []
    try :
        r = requests.get(url=url)
        if r.status_code == 200 :
            print(200)
            print(r.url)
            tmpData = json.loads(r.text)
            return tmpData, True
        else :
            return [], False
    except:
        return [], False

def mineNewBlock(difficulty=g_difficulty):
    blockList, blockTF = readBlockchain()
    urlData, txTF = getTxData(0)
    print(urlData, txTF, "getTxData")
    timestamp = time.time()
    proof = 0

    if blockTF and txTF :
        if len(selectList) == 0 :
            newBlock, isSuccessBc = generateGenesisBlock(timestamp, proof) #gensis가 잘 생성됐으면
        else:  # txdata가 있으면
            newBlock, isSuccessBc = generateNextBlock(blockList, urlData, timestamp, proof)  ###if 처리 아직 안함
            print(newBlock, isSuccess)

        if isSuccessBc :
            upResult = updateTx(newBlock)
            if upResult == 1 :
                wrResult = writeBlockchain(newBlock)
                if wrResult == 1 :
                    broadcastNewBlock()
                else :
                    print("Fail to write new block on table ")
                    return
            else :
                print("Failed to update txdata on transaction pool table used create block")
                return
        else :
            print("Fail Generate NewBlock")
        return
    else :
        print("There's no Transaction pool data in Url.")
        return

def mine():
    mineNewBlock()


def isSameBlock(block1, block2):
    if str(block1.index) != str(block2.index):
        return False
    elif str(block1.previousHash) != str(block2.previousHash):
        return False
    elif str(block1.timestamp) != str(block2.timestamp):
        return False
    elif str(block1.data) != str(block2.data):
        return False
    elif str(block1.currentHash) != str(block2.currentHash):
        return False
    elif str(block1.proof) != str(block2.proof):
        return False
    elif str(block1.merkleHash) != str(block.merkleHash):
        return False
    return True


# # 외부에서 받은 블록들을 비교한다(순서 6개의 경우: [1,2], [2,3] ... [5,6]
# def isValidNewBlock(newBlock, previousBlock):
#     if int(previousBlock.index) + 1 != int(newBlock.index):
#         print('Indices Do Not Match Up')
#         return False
#     # 체이닝이 맞는지
#     elif previousBlock.currentHash != newBlock.previousHash:
#         print("Previous hash does not match")
#         return False
#     # 해쉬검증
#     elif calculateHashForBlock(newBlock) != newBlock.currentHash:
#         print("Hash is invalid")
#         return False
#     elif newBlock.currentHash[0:g_difficulty] != '0' * g_difficulty:
#         print("Hash difficulty is invalid")
#         return False
#     return True
#
# def isValidChain(bcToValidate):
#     genesisBlock = []
#     bcToValidateForBlock = []
#
#     # Read GenesisBlock
#     try:
#         with open(g_bcFileName, 'r', newline='') as file:
#             blockReader = csv.reader(file)
#             for line in blockReader:
#                 block = Block(line[0], line[1], line[2], line[3], line[4], line[5], line[6])
#                 genesisBlock.append(block)
#     #                break
#     except:
#         print("file open error in isValidChain")
#         return False
#
#     # transform given data to Block object
#     for line in bcToValidate:
#         # print(type(line))
#         # index, previousHash, timestamp, data, currentHash, proof
#         block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'],
#                       line['proof'], line['merkleHash'])
#         bcToValidateForBlock.append(block)
#
#     # if it fails to read block data  from db(csv)
#     if not genesisBlock:
#         print("fail to read genesisBlock")
#         return False
#
#     # compare the given data with genesisBlock
#     if not isSameBlock(bcToValidateForBlock[0], genesisBlock[0]):
#         print('Genesis Block Incorrect')
#         return False
#
#     # tempBlocks = [bcToValidateForBlock[0]]
#     # for i in range(1, len(bcToValidateForBlock)):
#     #    if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
#     #        tempBlocks.append(bcToValidateForBlock[i])
#     #    else:
#     #        return False
#
#     for i in range(0, len(bcToValidateForBlock)):
#         if isSameBlock(genesisBlock[i], bcToValidateForBlock[i]) == False:
#             return False
#
#     return True


def addNode(queryStr):
    result = 1
    conn = pymysql.connect(
        host=DATABASE_SVR_IP,
        port =DATABASE_SVR_PORT,
        user=DATABASE_SVR_USER,
        passwd=DATABASE_SVR_PW,
        database=DATABASE_SVR_NAME)
    try:
        with conn.cursor() as cursor:
            sql = '''Select ip, port FROM testnode1 WHERE ip = %s AND port = %s'''
            cursor.execute(sql,(queryStr[0], queryStr[1]))
            rows = cursor.fetchall()
            conn.commit()
        if len(rows) == 0 :
            try:
                with conn.cursor() as cursor:
                    sql = """insert into testnode1 VALUES (%s,%s,%s) """
                    cursor.execute(sql,(queryStr[0], queryStr[1], 0))
                    conn.commit()
                    print('new node written')
            except:
                result = 0
            finally:
                conn.close()
        else :
            print("requested node is already exists")
            result = -1
    except:
        result = 0
    return result

def row_count():
    list = []
    try:
        list = readBlockchain()
        return len(list)
    except:
        return 0

def compareMerge(bcDict):
    heldBlock = []
    bcToValidateForBlock = []


    try:
       heldBlock = readBlockchain()
    except:
        print("file open error in compareMerge or No database exists")
        print("call initSvr if this server has just installed")
        return -1

    # if it fails to read block data  from db(csv)
    if len(heldBlock) == 0:
        print("fail to read")
        return -2

    # transform given data to Block object
    for line in bcDict:

        block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'],
                      line['proof'], line['merkleHash'])

        bcToValidateForBlock.append(block)

    # compare the given data with genesisBlock
    if not isSameBlock(bcToValidateForBlock[0], heldBlock[0]):
        print('Genesis Block Incorrect')
        return -1

    if isValidNewBlock(bcToValidateForBlock[-1], heldBlock[-1]) == False:

        # latest block == broadcasted last block
        if isSameBlock(heldBlock[-1], bcToValidateForBlock[-1]) == True:
            print('latest block == broadcasted last block, already updated')
            return 2
        # select longest chain
        elif len(bcToValidateForBlock) > len(heldBlock):
            # validation
            if isSameBlock(heldBlock[0], bcToValidateForBlock[0]) == False:
                print("Block Information Incorrect #1")
                return -1
            tempBlocks = [bcToValidateForBlock[0]]
            for i in range(1, len(bcToValidateForBlock)):
                if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                    tempBlocks.append(bcToValidateForBlock[i])
                else:
                    return -1
            # [START] save it to database
            blockchainList = []
            for block in bcToValidateForBlock:
                blockList = [block.index, block.previousHash, str(block.timestamp), block.data,
                             block.currentHash, block.proof]
                blockchainList.append(blockList)
            writeBlockchain(blockchainList)
            # [END] save it to database
            return 1
        elif len(bcToValidateForBlock) < len(heldBlock):
            # validation
            # for i in range(0,len(bcToValidateForBlock)):
            #    if isSameBlock(heldBlock[i], bcToValidateForBlock[i]) == False:
            #        print("Block Information Incorrect #1")
            #        return -1
            tempBlocks = [bcToValidateForBlock[0]]
            for i in range(1, len(bcToValidateForBlock)):
                if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                    tempBlocks.append(bcToValidateForBlock[i])
                else:
                    return -1
            print("We have a longer chain")
            return 3
        else:
            print("Block Information Incorrect #2")
            return -1
    else:  # very normal case (ex> we have index 100 and receive index 101 ...)
        tempBlocks = [bcToValidateForBlock[0]]
        for i in range(1, len(bcToValidateForBlock)):
            if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                tempBlocks.append(bcToValidateForBlock[i])
            else:
                print("Block Information Incorrect #2 " + tempBlocks.__dict__)
                return -1

        print("new block good")

        # validation
        for i in range(0, len(heldBlock)):
            if isSameBlock(heldBlock[i], bcToValidateForBlock[i]) == False:
                print("Block Information Incorrect #1")
                return -1
        # [START] save it to csv
        blockchainList = []
        for block in bcToValidateForBlock:
            blockList = [block.index, block.previousHash, str(block.timestamp), block.data, block.currentHash,
                         block.proof]
            blockchainList.append(blockList)
        writeBlockchain(blockchainList)
        return 1

def broadcastNewBlock():
    #table의 블록데이터 전체를 읽어온다,
    #SVR_LIST에 순차적으로 url post로 보내준다.
    blockList = readBlockchain()

def initSvr():
    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                           password=DATABASE_SVR_PW, \
                           db=DATABASE_SVR_NAME, charset='utf8')

    try:
        sql = "CREATE TABLE " + DATABASE_BC_TABLE + "(" \
                                                    "idx int," \
                                                    "Hash varchar(255)," \
                                                    "timeStamp varchar(255)," \
                                                    "data longtext," \
                                                    "currentHash varchar(255)," \
                                                    "proof varchar(255)," \
                                                    "merkleHash varchar(255)" \
                                                    ")"

        with conn.cursor() as curs:
            curs.execute(sql)

        print("Success to create blockchain table " + DATABASE_BC_TABLE + " on " + DATABASE_SVR_NAME)
    except:
        print("Failed to create blockchain table " + DATABASE_BC_TABLE + " on " + DATABASE_SVR_NAME)
    finally:
        conn.close()

    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                           password=DATABASE_SVR_PW, \
                           db=DATABASE_SVR_NAME, charset='utf8')

    try:
        sql = "CREATE TABLE " + DATABASE_ND_TABLE + "(" \
                                                    "ip varchar(255)," \
                                                    "port varchar(255)," \
                                                    "tryConnect int" \
                                                    ")"

        with conn.cursor() as curs:
            curs.execute(sql)

        print("Success to create nodelist table " + DATABASE_ND_TABLE + " on " + DATABASE_SVR_NAME)
    except:
        print("Failed to create nodelist table " + DATABASE_ND_TABLE + " on " + DATABASE_SVR_NAME)
    finally:
        conn.close()
    ############################################################################################################## blockchain
    #내 서버의 mydb카운트를 가져온다
    myblockCount = 0

    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                           password=DATABASE_SVR_PW, \
                           db=DATABASE_SVR_NAME, charset='utf8')

    sql = "SELECT COUNT(*) FROM " + DATABASE_BC_TABLE
    try:
        with conn.cursor() as curs:
            curs.execute(sql)
            myBlockCount = curs.fetchone()
    except:
        print("Failed to get rowCount from mmy database :" + DATABASE_TPSVR_IP + ":" + DATABASE_SVR_PORT + ":" + DATABASE_SVR_NAME)
    finally:
        curs.close()

    #myDbCount 가 0이라면 쭉 실행
    if myblockCount == 0 :
        #svr리스트의 db에 접속
        maxDbCount = 0
        currentCount = 0
        maxCountIp = ""
        maxCountPort = 0

        for key, value in SVR_LIST.items() :
            conn = pymysql.connect(host= key, port= value, user=DATABASE_SVR_USER,
                                   password=DATABASE_SVR_PW, \
                                   db=DATABASE_SVR_NAME, charset='utf8')
        #순차적으로 count 쿼리 날림

            sql = "SELECT COUNT(*) FROM " + DATABASE_BC_TABLE
            try :
                with conn.cursor() as curs:
                    curs.execute(sql)
                    currentCount = curs.fetchone()

                    # 초기 count =0, 현재 count가 이전 count보다 높을 경우, maxCountIp와 포트번호를 교체
                    if currentCount > dbCount :
                        maxDbCount = currentCount
                        maxCountIp = key
                        maxCountPort = value
            except:
                print("Failed to get blockchain data from svr_list")
            finally:
                curs.close()
        #maxCountIp와 port로 접속
            conn = pymysql.connect(host=maxCountIp, port=maxCountPort, user=DATABASE_SVR_USER,
                                   password=DATABASE_SVR_PW, \
                                   db=DATABASE_SVR_NAME, charset='utf8')
            # selcet * 날리고 fetchall
            sql = "SELECT * FROM " + DATABASE_BC_TABLE
            try:
                with conn.cursor() as curs:
                    curs.execute(sql)
                    dbData = curs.fetchall()
            except:
                print("Failed to ")
            finally:
                curs.close()
        #가져온 dbData의 내용을 한행씩 해체하여 블록객체를 생성한 후 , 블록객체리스트에 담는다.
        getBlockList = []
        for line in dbData :
            row = Block(line[0],line[1],line[2],line[3],line[4],line[5],line[6])
            getBlockList.append(row)
        #나의 데이터베이스에 저장
        conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER, passwd=DATABASE_SVR_PW, \
                               database=DATABASE_SVR_NAME)

        for blockchain in getBlockList :
            try:
                with conn.cursor() as curs:
                    print(blockchain.index, blockchain.previousHash, str(blockchain.timestamp), \
                          blockchain.data, blockchain.currentHash, blockchain.proof, blockchain.merkleHash)
                    sql = "INSERT INTO " + DATABASE_BC_TABLE + " VALUES (%s,%s,%s,%s,%s,%s,%s)"
                    curs.execute(sql, (blockchain.index, blockchain.previousHash, str(blockchain.timestamp), \
                                       blockchain.data, blockchain.currentHash, blockchain.proof, blockchain.merkleHash))
                    conn.commit()
            except:
                print("fail to read blockchain table")
            finally:
                conn.close()
    else :
        pass
    ################################################################################################################ node
    #DATABASE_BC_TABLE 를 DATABASE_ND_TABLE 로 교체
    myNnodeCount = 0

    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                           password=DATABASE_SVR_PW, \
                           db=DATABASE_SVR_NAME, charset='utf8')

    sql = "SELECT COUNT(*) FROM " + DATABASE_ND_TABLE
    try:
        with conn.cursor() as curs:
            curs.execute(sql)
            myNnodeCount = curs.fetchone()
    except:
        print("Failed to get rowCount from mmy database :" + DATABASE_TPSVR_IP + ":" + DATABASE_SVR_PORT + ":" + DATABASE_SVR_NAME)
    finally:
        curs.close()

    # myDbCount 가 0이라면 쭉 실행
    if myNnodeCount == 0:
        # svr리스트의 db에 접속
        dbCount = 0
        currentCount = 0
        maxCountIp = ""
        maxCountPort = 0

        for key, value in SVR_LIST.items():
            conn = pymysql.connect(host=key, port=value, user=DATABASE_SVR_USER,
                                   password=DATABASE_SVR_PW, \
                                   db=DATABASE_SVR_NAME, charset='utf8')
            # 순차적으로 count 쿼리 날림

            sql = "SELECT COUNT(*) FROM " + DATABASE_ND_TABLE
            try:
                with conn.cursor() as curs:
                    curs.execute(sql)
                    currentCount = curs.fetchone()

                    # 초기 count =0, 현재 count가 이전 count보다 높을 경우, maxCountIp와 포트번호를 교체
                    if currentCount > dbCount:
                        dbCount = currentCount
                        maxCountIp = key
                        maxCountPort = value
            except:
                print("Failed to get blockchain data from svr_list")
            finally:
                curs.close()
            # maxCountIp와 port로 접속
            conn = pymysql.connect(host=maxCountIp, port=maxCountPort, user=DATABASE_SVR_USER,
                                   password=DATABASE_SVR_PW, \
                                   db=DATABASE_SVR_NAME, charset='utf8')
            # selcet * 날리고 fetchall
            sql = "SELECT * FROM " + DATABASE_ND_TABLE
            try:
                with conn.cursor() as curs:
                    curs.execute(sql)
                    dbData = curs.fetchall()
            except:
                print("Failed to ")
            finally:
                curs.close()
        # 가져온 dbData의 내용을 한행씩 해체하여 블록객체를 생성한 후 , 블록객체리스트에 담는다.
        getNodeList = []
        for line in dbData:
            row = Node(line[0],line[1],line[2])
            getNodeList.append(row)
        # 나의 데이터베이스에 저장
        conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                               passwd=DATABASE_SVR_PW, \
                               database=DATABASE_SVR_NAME)

        for node in getNodeList:
            try:
                with conn.cursor() as curs:
                    print()
                    sql = "INSERT INTO " + DATABASE_ND_TABLE + " VALUES (%s,%s,%s)"
                    curs.execute(sql, (node.ip, node.port, node.tryConnect))
                    conn.commit()
            except:
                print("fail to read node table")
            finally:
                conn.close()
    else:
        pass

    print("initSvr setting Done...")
    return 1

# This class will handle any incoming request from
# a browser
class myHandler(BaseHTTPRequestHandler):

    # def __init__(self, request, client_address, server):
    #    BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    # Handler for the GET requests
    # get방식으로 보내는 요청의 종류로는 블록체인의 데이터 요청, 블록 생성, 노드데이터 요청, 노드생성이 존재한다.
    def do_GET(self):
        data = []  # response json data
        if None != re.search('/block/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/block/getBlockData', self.path):

                blockList = readBlockchain()

                # block의 값이 None인 경우
                if blockList == None:

                    print("No Block Exists")

                    data.append("no data exists")
                else:
                    for i in blockList:
                        print(i.__dict__)
                        data.append(i.__dict__)

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            # 블럭을 생성하는 경우 (최초, 그 이후 전부)
            elif None != re.search('/block/generateBlock', self.path):
                t = threading.Thread(target=mine)
                t.start()
                data.append("{mining is underway:check later by calling /block/getBlockData}")
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))
            else:
                data.append("{info:no such api}")
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))


        elif None != re.search('/node/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/node/addNode', self.path):

                queryStr = urlparse(self.path).query.split(':')
                print("client ip : " + self.client_address[0] + " query ip : " + queryStr[0])

                if self.client_address[0] != queryStr[0]:
                    data.append("your ip address doesn't match with the requested parameter")

                else:
                    res = addNode(queryStr)

                    if res == 1:
                        importedNodes = readNodes(g_nodelstFileName)
                        data = importedNodes
                        print("node added okay")

                    elif res == 0:
                        data.append("caught exception while saving")

                    elif res == -1:
                        importedNodes = readNodes(g_nodelstFileName)
                        data = importedNodes
                        data.append("requested node is already exists")

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            elif None != re.search('/node/getNode', self.path):
                importedNodes = readNodes(g_nodelstFileName)
                data = importedNodes
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

        elif None != re.search('/txData/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/txData/getTxData', self.path):

                txDataList = getTxData(1)

                if txDataList == '':

                    print("No txData Exists")

                    data.append("no txData exists")
                else:
                    data = txDataList

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))
        else:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
        # ref : https://mafayyaz.wordpress.com/2013/02/08/writing-simple-http-server-in-python-with-rest-and-json/

    def do_POST(self):

        if None != re.search('/block/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/block/validateBlock/*', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                # print(ctype) #print(pdict)

                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)  # load your str into a list #print(type(tempDict))
                    if isValidChain(tempDict) == True:
                        tempDict.append("validationResult:normal")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else:
                        tempDict.append("validationResult:abnormal")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

            elif None != re.search('/block/newtx', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)
                    res = newtx(tempDict)
                    if res == 1:
                        tempDict.append("accepted : it will be mined later")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    elif res == -1:
                        tempDict.append("declined : number of request txData exceeds limitation")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    elif res == -2:
                        tempDict.append("declined : error on data read or write")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else:
                        tempDict.append("error : requested data is abnormal")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

            # -----------------------------------------V02 : 완
            # "/block/syncTx'" 로 오는 요청은 다시 sync과정을 거치지 않는다.
            elif None != re.search('/block/syncTx', self.path) :
                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)
                    res = newtx(tempDict, mode='sync')

                    if res == 1:
                        tempDict.append("accepted : it will be mined later")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    elif res == -1:
                        tempDict.append("declined : number of request txData exceeds limitation")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    elif res == -2:
                        tempDict.append("declined : error on data read or write")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else:
                        tempDict.append("error : requested data is abnormal")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

        elif None != re.search('/node/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search(g_receiveNewBlock, self.path):  # /node/receiveNewBlock
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                receivedData = post_data.decode('utf-8')
                tempDict = json.loads(receivedData)  # load your str into a list
                print(tempDict)
                res = compareMerge(tempDict)
                if res == -1:  # internal error
                    tempDict.append("internal server error")
                elif res == -2:  # block chain info incorrect
                    tempDict.append("block chain info incorrect")
                elif res == 1:  # normal
                    tempDict.append("accepted")
                elif res == 2:  # identical
                    tempDict.append("already updated")
                elif res == 3:  # we have a longer chain
                    tempDict.append("we have a longer chain")
                self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

try:

    # Create a web server and define the handler to manage the
    # incoming request
    # server = HTTPServer(('', PORT_NUMBER), myHandler)
    server = ThreadedHTTPServer(('', PORT_NUMBER), myHandler)
    print('Started httpserver on port ', PORT_NUMBER)

    initSvr()
    # Wait forever for incoming http requests
    server.serve_forever()

except (KeyboardInterrupt, Exception) as e:
    print('^C received, shutting down the web server')
    print(e)
    server.socket.close()