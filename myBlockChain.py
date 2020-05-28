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
import requests # for sending new block to other nodes

# 20190605 /(YuRim Kim, HaeRi Kim, JongSun Park, BohKuk Suh , HyeongSeob Lee, JinWoo Song)
from multiprocessing import Process, Lock # for using Lock method(acquire(), release())

# for Put Lock objects into variables(lock)
lock = Lock()

PORT_NUMBER = 8666
g_txFileName = "txData.csv"
g_bcFileName = "blockchain.csv"
g_nodelstFileName = "nodelst.csv"
g_receiveNewBlock = "/node/receiveNewBlock"
g_difficulty = 2
g_maximumTry = 100
g_nodeList = {'trustedServerAddress':'8666'} # trusted server list, should be checked manually

class Block:
    def __init__(self, index, previousHash, timestamp, data, currentHash, proof , merkleRoot):
        self.index = index
        self.previousHash = previousHash
        self.timestamp = timestamp
        self.data = data
        self.currentHash = currentHash
        self.proof = proof
        self.merkleRoot = merkleRoot

# class Block:
#
#     def __init__(self, index, previousHash, timestamp, data, currentHash, proof ):
#         self.index = index
#         self.previousHash = previousHash
#         self.timestamp = timestamp
#         self.data = data
#         self.currentHash = currentHash
#         self.proof = proof

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class txData:

    def __init__(self, commitYN, sender, amount, receiver, uuid):
        self.commitYN = commitYN
        self.sender = sender
        self.amount = amount
        self.receiver = receiver
        self.uuid =  uuid

def generateGenesisBlock():
    print("generateGenesisBlock is called")
    timestamp = time.time()
    print("time.time() => %f \n" % timestamp)
    tempHash = calculateHash(0, '0', timestamp, "Genesis Block", 0, 0)
    print(tempHash)
    return Block(0, '0', timestamp, "Genesis Block",  tempHash, 0, 0)


def calculateHash(index, previousHash, timestamp, data, proof, merkleRoot):
    value = str(index) + str(previousHash) + str(timestamp) + str(data) + str(proof) + str(merkleRoot)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())


def calculateHashForBlock(block):
    return calculateHash(block.index, block.previousHash, block.timestamp, block.data, block.proof, block.merkleRoot)

def getLatestBlock(blockchain):
    return blockchain[len(blockchain) - 1]


def generateNextBlock(blockchain, blockData, timestamp, proof, MerkleData):
    previousBlock = getLatestBlock(blockchain)
    nextIndex = int(previousBlock.index) + 1
    nextTimestamp = timestamp
    nextHash = calculateHash(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, proof, MerkleData)
    # index, previousHash, timestamp, data, currentHash, proof
    return Block(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, nextHash, proof, MerkleData)

# def generateNextBlock(blockchain, blockData, timestamp, proof):
#     previousBlock = getLatestBlock(blockchain)
#     nextIndex = int(previousBlock.index) + 1
#     nextTimestamp = timestamp
#     nextHash = calculateHash(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, proof)
#     # index, previousHash, timestamp, data, currentHash, proof
#     return Block(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, nextHash,proof)


# 20190605 / (YuRim Kim, HaeRi Kim, JongSun Park, BohKuk Suh , HyeongSeob Lee, JinWoo Song)
# /* WriteBlockchain function Update */
# If the 'blockchain.csv' file is already open, make it inaccessible via lock.acquire()
# After executing the desired operation, changed to release the lock.(lock.release())
# Reason for time.sleep ():
# prevents server overload due to repeated error message output and gives 3 seconds of delay to allow time for other users to wait without opening file while editing and saving csv file.
def writeBlockchain(blockchain):

    blockchainList = []

    for block in blockchain:

        blockList = [block.index, block.previousHash, str(block.timestamp), block.data, block.currentHash, block.proof, block.merkleRoot]
        blockchainList.append(blockList)

    #[STARAT] check current db(csv) if broadcasted block data has already been updated
    try:
        with open(g_bcFileName, 'r',  newline='') as file:
            blockReader = csv.reader(file)
            last_line_number = row_count(g_bcFileName)
            for line in blockReader:
                if blockReader.line_num == last_line_number:
                    lastBlock = Block(line[0], line[1], line[2], line[3], line[4], line[5], line[6])

        if int(lastBlock.index) + 1 != int(blockchainList[-1][0]):
            print("index sequence mismatch")
            if int(lastBlock.index) == int(blockchainList[-1][0]):
                print("db(csv) has already been updated")
            return
    except:
        print("file open error in check current db(csv) \n or maybe there's some other reason")
        pass
        #return
    # [END] check current db(csv)
    openFile = False
    while not openFile:
        if blockchainList != []:
            try:
                lock.acquire()
                with open(g_bcFileName, "w", newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(blockchainList)
                    blockchainList.clear()
                    print("write ok")
                    openFile = True
                    for block in blockchain:
                        updateTx(block)
                    print('Blockchain written to blockchain.csv.')
                    print('Broadcasting new block to other nodes')
                    broadcastNewBlock(blockchain)
                    lock.release()
            except:
                    time.sleep(3)
                    print("writeBlockchain file open error")
                    lock.release()
        else:
            print("Blockchain is empty")

def readBlockchain(blockchainFilePath, mode = 'internal'):
    print("readBlockchain")
    importedBlockchain = []

    try:
        with open(blockchainFilePath, 'r',  newline='') as file:
            blockReader = csv.reader(file)
            for line in blockReader:
                # 수정
                block = Block(line[0], line[1], line[2], line[3], line[4], line[5], line[6])
                importedBlockchain.append(block)

        print("Pulling blockchain from csv...")

        return importedBlockchain

    except:
        if mode == 'internal' :
            blockchain = generateGenesisBlock()
            importedBlockchain.append(blockchain)
            writeBlockchain(importedBlockchain)
            return importedBlockchain
        else :
            return None

def updateTx(blockData) :
    phrase = re.compile(r"\w+[-]\w+[-]\w+[-]\w+[-]\w+") # [6b3b3c1e-858d-4e3b-b012-8faac98b49a8]UserID hwang sent 333 bitTokens to UserID kim.
    matchList = phrase.findall(blockData.data)

    if len(matchList) == 0 :
        print ("No Match Found! " + str(blockData.data) + "block idx: " + str(blockData.index))
        return

    tempfile = NamedTemporaryFile(mode='w', newline='', delete=False)

    with open(g_txFileName, 'r') as csvfile, tempfile:
        reader = csv.reader(csvfile)
        writer = csv.writer(tempfile)
        for row in reader:
            if row[4] in matchList:
                print('updating row : ', row[4])
                row[0] = 1
            writer.writerow(row)

    shutil.move(tempfile.name, g_txFileName)
    csvfile.close()
    tempfile.close()
    print('txData updated')

# 20190605 /(YuRim Kim, HaeRi Kim, JongSun Park, BohKuk Suh , HyeongSeob Lee, JinWoo Song)
# /* writeTx function Update */
# If the 'txData.csv' file is already open, make it inaccessible via lock.acquire()
# After executing the desired operation, changed to release the lock.(lock.release())
# Reason for time.sleep ():
# prevents server overload due to repeated error message output and gives 3 seconds of delay to allow time for other users to wait without opening file while editing and saving csv file.
# Removed temp files to reduce memory usage and increase work efficiency.
def writeTx(txRawData):
    print(g_txFileName)
    txDataList = []
    txOriginalList = []
    for txDatum in txRawData:
        txList = [txDatum.commitYN, txDatum.sender, txDatum.amount, txDatum.receiver, txDatum.uuid]
        txDataList.append(txList)

    try:
        with open(g_txFileName, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                txOriginalList.append(row)

            openWriteTx = False
            while not openWriteTx:
                lock.acquire()
                try:
                    print("NewTxData lock.acquire")
                    with open(g_txFileName, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        # adding new tx
                        writer.writerows(txOriginalList)
                        writer.writerows(txDataList)
                        print("writeTx write ok")
                        csvfile.close()
                        openWriteTx = True
                        lock.release()

                except Exception as e:
                    print(e)
                    time.sleep(3)
                    print("file open error")
                    lock.release()
    except:
        # this is 1st time of creating txFile
        try:
            with open(g_txFileName, "w", newline='') as file:
                writer = csv.writer(file)
                writer.writerows(txDataList)
        except:
            return 0
    return 1
    print('txData written to txData.csv.')

def readMK(txFilePath):
    print("readMerkle")
    importedMK = []

    try:
        with open(txFilePath, 'r',  newline='') as file:
            txReader = csv.reader(file)
            for row in txReader:
                if row[0] == '0': # find unmined txData
                    line = row[1] + row[2] + row[3] + row[4]   # merkleRoot를 만들어 주기위해 tx객체대신 str이 요소인 importTx 리스트로 바꿔줌
                    importedMK.append(line)
        print("Pulling txData from csv...")
        return importedMK
    except:
        return []


def readTx(txFilePath):
    print("readTx")
    importedTx = []

    try:
        with open(txFilePath, 'r',  newline='') as file:
            txReader = csv.reader(file)
            for row in txReader:
                if row[0] == '0': # find unmined txData
                    line = txData(row[0],row[1],row[2],row[3],row[4])
                    importedTx.append(line)
        print("Pulling txData from csv...")
        return importedTx
    except:
        return []

# 머클루트

# transaction을 두개씩 묶어서 hash 처리와 16진수 변환 처리를 해줌
def culculateMerkle(tx1, tx2):
    hashTx = hashlib.sha256((tx1 + tx2).encode('utf-8')).hexdigest()
    return hashTx

##### error: maximum recursion depth exceeded in comparison
def getMerkleCycle(importedTx):

    if len(importedTx) == 0:
        return None

    if len(importedTx) == 1:
        return importedTx[0]

    newHashList = []
    # 홀수의 경우를 고려하여 마지막 transaction은 뺀 채로 쌍을 지어 hash 처리
    for i in range(0, len(importedTx) - 1, 2):
        newHashList.append(culculateMerkle(importedTx[i], importedTx[i + 1]))
    # 홀수일 경우, 마지막 transaction을 복제하여 hash 처리
    if len(importedTx) % 2 == 1:  # odd, hash last item twice
        newHashList.append(culculateMerkle(importedTx[-1], importedTx[-1]))
    # 해시값이 하나가 될 때까지 재귀적으로 getmerkle 함수를 실행
    return getMerkleCycle(newHashList)

# 해시한 transaction이 하나의 해시값이 될 때까지 재귀적으로 getmerkle 함수를 실행함
def getMerkle():
    importedMK = readMK(g_txFileName)
    merkleData = getMerkleCycle(importedMK)
    return merkleData

## 여기

# def readTx(txFilePath):
#     print("readTx")
#     importedTx = []
#
#     try:
#         with open(txFilePath, 'r',  newline='') as file:
#             txReader = csv.reader(file)
#             for row in txReader:
#                 if row[0] == '0': # find unmined txData
#                     line = txData(row[0],row[1],row[2],row[3],row[4])
#                     importedTx.append(line)
#         print("Pulling txData from csv...")
#         return importedTx
#     except:
#         return []


def getTxData():
    strTxData = ''
    importedTx = readTx(g_txFileName)
    if len(importedTx) > 0 :
        for i in importedTx:
            print(i.__dict__)
            transaction = "["+ i.uuid + "] . "
            print(transaction)
            strTxData += transaction

    return strTxData

def mineNewBlock(difficulty=g_difficulty, blockchainPath=g_bcFileName):
    blockchain = readBlockchain(blockchainPath)

    strTxData = getTxData()
    if strTxData == '' :
        print('No TxData Found. Mining aborted')
        return

    merkleData = getMerkle()
    timestamp = time.time()
    proof = 0
    newBlockFound = False

    print('Mining a block...')

    while not newBlockFound:
        newBlockAttempt = generateNextBlock(blockchain, strTxData, timestamp, proof, merkleData)
        # 삭제
        print(newBlockAttempt)
        if newBlockAttempt.currentHash[0:difficulty] == '0' * difficulty:
            stopTime = time.time()
            timer = stopTime - timestamp
            print('New block found with proof', proof, 'in', round(timer, 2), 'seconds.')
            newBlockFound = True
        else:
            proof += 1

    blockchain.append(newBlockAttempt)
    writeBlockchain(blockchain)

# def mineNewBlock(difficulty=g_difficulty, blockchainPath=g_bcFileName):
#     blockchain = readBlockchain(blockchainPath)
#     strTxData = getTxData()
#     if strTxData == '' :
#         print('No TxData Found. Mining aborted')
#         return
#
#     timestamp = time.time()
#     proof = 0
#     newBlockFound = False
#
#     print('Mining a block...')
#
#     while not newBlockFound:
#         newBlockAttempt = generateNextBlock(blockchain, strTxData, timestamp, proof)
#         if newBlockAttempt.currentHash[0:difficulty] == '0' * difficulty:
#             stopTime = time.time()
#             timer = stopTime - timestamp
#             print('New block found with proof', proof, 'in', round(timer, 2), 'seconds.')
#             newBlockFound = True
#         else:
#             proof += 1
#
#     blockchain.append(newBlockAttempt)
#     writeBlockchain(blockchain)

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
    elif str(block1.merkleRoot) != str(block2.merkleRoot):
        return False
    return True

def isValidNewBlock(newBlock, previousBlock):
    if int(previousBlock.index) + 1 != int(newBlock.index):
        print('Indices Do Not Match Up')
        return False
    elif previousBlock.currentHash != newBlock.previousHash:
        print("Previous hash does not match")
        return False
    elif calculateHashForBlock(newBlock) != newBlock.currentHash:
        print("Hash is invalid")
        return False
    elif newBlock.currentHash[0:g_difficulty] != '0' * g_difficulty:
        print("Hash difficulty is invalid")
        return False
    return True

def newtx(txToMining):

    newtxData = []
    # transform given data to txData object
    for line in txToMining:
        tx = txData(0, line['sender'], line['amount'], line['receiver'], uuid.uuid4())
        newtxData.append(tx)

    # limitation check : max 5 tx
    if len(newtxData) > 5 :
        print('number of requested tx exceeds limitation')
        return -1

    if writeTx(newtxData) == 0:
        print("file write error on txData")
        return -2
    return 1

def isValidChain(bcToValidate):
    genesisBlock = []
    bcToValidateForBlock = []

    # Read GenesisBlock
    try:
        with open(g_bcFileName, 'r',  newline='') as file:
            blockReader = csv.reader(file)
            for line in blockReader:
                block = Block(line[0], line[1], line[2], line[3], line[4], line[5], line[6])
                genesisBlock.append(block)
#                break
    except:
        print("file open error in isValidChain")
        return False

    # transform given data to Block object
    for line in bcToValidate:
        # print(type(line))
        # index, previousHash, timestamp, data, currentHash, proof
        block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'],
                      line['proof'], line['merkleRoot'])
        bcToValidateForBlock.append(block)

    #if it fails to read block data  from db(csv)
    if not genesisBlock:
        print("fail to read genesisBlock")
        return False

    # compare the given data with genesisBlock
    if not isSameBlock(bcToValidateForBlock[0], genesisBlock[0]):
        print('Genesis Block Incorrect')
        return False

    # tempBlocks = [bcToValidateForBlock[0]]
    # for i in range(1, len(bcToValidateForBlock)):
    #    if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
    #        tempBlocks.append(bcToValidateForBlock[i])
    #    else:
    #        return False

    for i in range(0, len(bcToValidateForBlock)):
        if isSameBlock(genesisBlock[i], bcToValidateForBlock[i]) == False:
            return False

    return True

# 20190605 / (YuRim Kim, HaeRi Kim, JongSun Park, BohKuk Suh , HyeongSeob Lee, JinWoo Song)
# /* addNode function Update */
# If the 'nodeList.csv' file is already open, make it inaccessible via lock.acquire()
# After executing the desired operation, changed to release the lock.(lock.release())
# Reason for time.sleep ():
# prevents server overload due to repeated error message output and gives 3 seconds of delay to allow time for other users to wait without opening file while editing and saving csv file.
# Removed temp files to reduce memory usage and increase work efficiency.
def addNode(queryStr):
    # save
    previousList = []
    nodeList = []
    nodeList.append([queryStr[0],queryStr[1],0]) # ip, port, # of connection fail

    try:
        with open(g_nodelstFileName, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:
                    if row[0] == queryStr[0] and row[1] == queryStr[1]:
                        print("requested node is already exists")
                        csvfile.close()
                        nodeList.clear()
                        return -1
                    else:
                        previousList.append(row)

            openFile3 = False
            while not openFile3:
                lock.acquire()
                try:
                    with open(g_nodelstFileName, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(nodeList)
                        writer.writerows(previousList)
                        csvfile.close()
                        nodeList.clear()
                        lock.release()
                        print('new node written to nodelist.csv.')
                        return 1
                except Exception as ex:
                    print(ex)
                    time.sleep(3)
                    print("file open error")
                    lock.release()

    except:
        # this is 1st time of creating node list
        try:
            with open(g_nodelstFileName, "w", newline='') as file:
                writer = csv.writer(file)
                writer.writerows(nodeList)
                nodeList.clear()
                print('new node written to nodelist.csv.')
                return 1
        except Exception as ex:
            print(ex)
            return 0

def readNodes(filePath):
    print("read Nodes")
    importedNodes = []

    try:
        with open(filePath, 'r',  newline='') as file:
            txReader = csv.reader(file)
            for row in txReader:
                line = [row[0],row[1]]
                importedNodes.append(line)
        print("Pulling txData from csv...")
        return importedNodes
    except:
        return []

def broadcastNewBlock(blockchain):
    #newBlock  = getLatestBlock(blockchain) # get the latest block
    importedNodes = readNodes(g_nodelstFileName) # get server node ip and port
    reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
    reqBody = []
    for i in blockchain:
        reqBody.append(i.__dict__)

    if len(importedNodes) > 0 :
        for node in importedNodes:
            try:
                URL = "http://" + node[0] + ":" + node[1] + g_receiveNewBlock  # http://ip:port/node/receiveNewBlock
                res = requests.post(URL, headers=reqHeader, data=json.dumps(reqBody))
                if res.status_code == 200:
                    print(URL + " sent ok.")
                    print("Response Message " + res.text)
                else:
                    print(URL + " responding error " + res.status_code)
            except:
                print(URL + " is not responding.")
                # write responding results
                tempfile = NamedTemporaryFile(mode='w', newline='', delete=False)
                try:
                    with open(g_nodelstFileName, 'r', newline='') as csvfile, tempfile:
                        reader = csv.reader(csvfile)
                        writer = csv.writer(tempfile)
                        for row in reader:
                            if row:
                                if row[0] == node[0] and row[1] ==node[1]:
                                    print("connection failed "+row[0]+":"+row[1]+", number of fail "+row[2])
                                    tmp = row[2]
                                    # too much fail, delete node
                                    if int(tmp) > g_maximumTry:
                                        print(row[0]+":"+row[1]+" deleted from node list because of exceeding the request limit")
                                    else:
                                        row[2] = int(tmp) + 1
                                        writer.writerow(row)
                                else:
                                    writer.writerow(row)
                    shutil.move(tempfile.name, g_nodelstFileName)
                    csvfile.close()
                    tempfile.close()
                except:
                    print("caught exception while updating node list")

def row_count(filename):
    try:
        with open(filename) as in_file:
            return sum(1 for _ in in_file)
    except:
        return 0

def compareMerge(bcDict):

    heldBlock = []
    bcToValidateForBlock = []

    # Read GenesisBlock
    try:
        with open(g_bcFileName, 'r',  newline='') as file:
            blockReader = csv.reader(file)
            #last_line_number = row_count(g_bcFileName)
            for line in blockReader:
                block = Block(line[0], line[1], line[2], line[3], line[4], line[5], line[6])
                heldBlock.append(block)
                #if blockReader.line_num == 1:
                #    block = Block(line[0], line[1], line[2], line[3], line[4], line[5])
                #    heldBlock.append(block)
                #elif blockReader.line_num == last_line_number:
                #    block = Block(line[0], line[1], line[2], line[3], line[4], line[5])
                #    heldBlock.append(block)

    except:
        print("file open error in compareMerge or No database exists")
        print("call initSvr if this server has just installed")
        return -2

    #if it fails to read block data  from db(csv)
    if len(heldBlock) == 0 :
        print("fail to read")
        return -2

    # transform given data to Block object
    for line in bcDict:
        # print(type(line))
        # index, previousHash, timestamp, data, currentHash, proof
        block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'], line['proof'], line['merkleRoot'])
        bcToValidateForBlock.append(block)

    # compare the given data with genesisBlock
    if not isSameBlock(bcToValidateForBlock[0], heldBlock[0]):
        print('Genesis Block Incorrect')
        return -1

    # check if broadcasted new block,1 ahead than > last held block

    if isValidNewBlock(bcToValidateForBlock[-1],heldBlock[-1]) == False:

        # latest block == broadcasted last block
        if isSameBlock(heldBlock[-1], bcToValidateForBlock[-1]) == True:
            print('latest block == broadcasted last block, already updated')
            return 2
        # select longest chain
        elif len(bcToValidateForBlock) > len(heldBlock):
            # validation
            if isSameBlock(heldBlock[0],bcToValidateForBlock[0]) == False:
                    print("Block Information Incorrect #1")
                    return -1
            tempBlocks = [bcToValidateForBlock[0]]
            for i in range(1, len(bcToValidateForBlock)):
                if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                    tempBlocks.append(bcToValidateForBlock[i])
                else:
                    return -1
            # [START] save it to csv
            blockchainList = []
            for block in bcToValidateForBlock:
                blockList = [block.index, block.previousHash, str(block.timestamp), block.data,
                             block.currentHash, block.proof, block.merkleRoot]
                blockchainList.append(blockList)
            with open(g_bcFileName, "w", newline='') as file:
                writer = csv.writer(file)
                writer.writerows(blockchainList)
            # [END] save it to csv
            return 1
        elif len(bcToValidateForBlock) < len(heldBlock):
            # validation
            #for i in range(0,len(bcToValidateForBlock)):
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
    else: # very normal case (ex> we have index 100 and receive index 101 ...)
        tempBlocks = [bcToValidateForBlock[0]]
        for i in range(1, len(bcToValidateForBlock)):
            if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                tempBlocks.append(bcToValidateForBlock[i])
            else:
                print("Block Information Incorrect #2 "+tempBlocks.__dict__)
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
            blockList = [block.index, block.previousHash, str(block.timestamp), block.data, block.currentHash, block.proof, block.merkleRoot]
            blockchainList.append(blockList)
        with open(g_bcFileName, "w", newline='') as file:
            writer = csv.writer(file)
            writer.writerows(blockchainList)
        # [END] save it to csv
        return 1

def initSvr():
    print("init Server")
    # 1. check if we have a node list file
    last_line_number = row_count(g_nodelstFileName)
    # if we don't have, let's request node list
    if last_line_number == 0:
        # get nodes...
        for key, value in g_nodeList.items():
            URL = 'http://'+key+':'+value+'/node/getNode'
            try:
                res = requests.get(URL)
            except requests.exceptions.ConnectionError:
                continue
            if res.status_code == 200 :
                print(res.text)
                tmpNodeLists = json.loads(res.text)
                for node in tmpNodeLists:
                    addNode(node)

    # 2. check if we have a blockchain data file
    last_line_number = row_count(g_bcFileName)
    blockchainList=[]
    if last_line_number == 0:
        # get Block Data...
        for key, value in g_nodeList.items():
            URL = 'http://'+key+':'+value+'/block/getBlockData'
            try:
                res = requests.get(URL)
            except requests.exceptions.ConnectionError:
                continue
            if res.status_code == 200 :
                print(res.text)
                tmpbcData = json.loads(res.text)
                for line in tmpbcData:
                    # print(type(line))
                    # index, previousHash, timestamp, data, currentHash, proof
                    block = [line['index'], line['previousHash'], line['timestamp'], line['data'],line['currentHash'], line['proof'], line['merkleRoot']]
                    blockchainList.append(block)
                try:
                    with open(g_bcFileName, "w", newline='') as file:
                        writer = csv.writer(file)
                        writer.writerows(blockchainList)
                except Exception as e:
                    print("file write error in initSvr() "+e)

    return 1

# This class will handle any incoming request from
# a browser
class myHandler(BaseHTTPRequestHandler):

    #def __init__(self, request, client_address, server):
    #    BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    # Handler for the GET requests
    def do_GET(self):
        data = []  # response json data
        if None != re.search('/block/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/block/getBlockData', self.path):
                # TODO: range return (~/block/getBlockData?from=1&to=300)
                # queryString = urlparse(self.path).query.split('&')

                block = readBlockchain(g_bcFileName, mode = 'external')

                if block == None :
                    print("No Block Exists")
                    data.append("no data exists")
                else :
                    for i in block:
                        print(i.__dict__)
                        data.append(i.__dict__)

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

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
                print("client ip : "+self.client_address[0]+" query ip : "+queryStr[0])
                if self.client_address[0] != queryStr[0]:
                    data.append("your ip address doesn't match with the requested parameter")
                else:
                    res = addNode(queryStr)
                    if res == 1:
                        importedNodes = readNodes(g_nodelstFileName)
                        data =importedNodes
                        print("node added okay")
                    elif res == 0 :
                        data.append("caught exception while saving")
                    elif res == -1 :
                        importedNodes = readNodes(g_nodelstFileName)
                        data = importedNodes
                        data.append("requested node is already exists")
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))
            elif None != re.search('/node/getNode', self.path):
                importedNodes = readNodes(g_nodelstFileName)
                data = importedNodes
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
                #print(ctype) #print(pdict)

                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)  # load your str into a list #print(type(tempDict))
                    if isValidChain(tempDict) == True :
                        tempDict.append("validationResult:normal")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else :
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
                    if  res == 1 :
                        tempDict.append("accepted : it will be mined later")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    elif res == -1 :
                        tempDict.append("declined : number of request txData exceeds limitation")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    elif res == -2 :
                        tempDict.append("declined : error on data read or write")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else :
                        tempDict.append("error : requested data is abnormal")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

        elif None != re.search('/node/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            if None != re.search(g_receiveNewBlock, self.path): # /node/receiveNewBlock
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                receivedData = post_data.decode('utf-8')
                tempDict = json.loads(receivedData)  # load your str into a list
                print(tempDict)
                res = compareMerge(tempDict)
                if res == -2: # internal error
                    tempDict.append("internal server error")
                elif res == -1 : # block chain info incorrect
                    tempDict.append("block chain info incorrect")
                elif res == 1: #normal
                    tempDict.append("accepted")
                elif res == 2: # identical
                    tempDict.append("already updated")
                elif res == 3: # we have a longer chain
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