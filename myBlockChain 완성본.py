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

from multiprocessing import Process, Lock

lock = Lock()

PORT_NUMBER = 8671
g_txFileName = "txData.csv"
g_bcFileName = "blockchain.csv"
g_nodelstFileName = "nodelst.csv"
g_receiveNewBlock = "/node/receiveNewBlock"
g_difficulty = 2
g_maximumTry = 100
g_nodeList = {'trustedServerAddress': '8666'}
# KHJ
g_txPoolAddress = '127.0.0.1:8672'


class Block:

    def __init__(self, index, previousHash, timestamp, merkleRoot, currentHash, proof):
        self.index = index
        self.previousHash = previousHash
        self.timestamp = timestamp
        # self.data = data
        self.merkleRoot = merkleRoot
        self.currentHash = currentHash
        self.proof = proof

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


# class txData:
#
#     def __init__(self, commitYN, sender, amount, receiver, uuid):
#         self.commitYN = commitYN
#         self.sender = sender
#         self.amount = amount
#         self.receiver = receiver
#         self.uuid =  uuid

# KHJ
class txData:

    def __init__(self, commitYN, listener, music, copyrightHolder, uuid):
        self.commitYN = commitYN
        self.listener = listener
        self.music = music
        self.copyrightHolder = copyrightHolder
        self.uuid = uuid


def generateGenesisBlock():
    print("generateGenesisBlock is called")
    timestamp = time.time()
    print("time.time() => %f \n" % timestamp)
    tempHash = calculateHash(0, '0', timestamp, "Genesis Block", 0)
    print(tempHash)
    return Block(0, '0', timestamp, "Genesis Block", tempHash, 0)


def calculateHash(index, previousHash, timestamp, merkleRoot, proof):
    value = str(index) + str(previousHash) + str(timestamp) + str(merkleRoot) + str(proof)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())


def calculateHashForBlock(block):
    return calculateHash(block.index, block.previousHash, block.timestamp, block.merkleRoot, block.proof)


def getLatestBlock(blockchain):
    return blockchain[len(blockchain) - 1]


def generateNextBlock(blockchain, blockData, timestamp, proof):
    previousBlock = getLatestBlock(blockchain)
    nextIndex = int(previousBlock.index) + 1
    nextTimestamp = timestamp
    nextHash = calculateHash(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, proof)
    # index, previousHash, timestamp, data, currentHash, proof
    return Block(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, nextHash, proof)


def writeBlockchain(blockchain):
    blockchainList = []

    for block in blockchain:
        blockList = [block.index, block.previousHash, str(block.timestamp), block.merkleRoot, block.currentHash,
                     block.proof]
        blockchainList.append(blockList)

    try:
        with open(g_bcFileName, 'r', newline='') as file:
            blockReader = csv.reader(file)
            last_line_number = row_count(g_bcFileName)
            for line in blockReader:
                if blockReader.line_num == last_line_number:
                    lastBlock = Block(line[0], line[1], line[2], line[3], line[4], line[5])

        if int(lastBlock.index) + 1 != int(blockchainList[-1][0]):
            print("index sequence mismatch")
            if int(lastBlock.index) == int(blockchainList[-1][0]):
                print("db(csv) has already been updated")
            return
    except:
        print("file open error in check current db(csv) \n or maybe there's some other reason")
        pass
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
                    # KHJ: updateTxPool로 변경-> mineNewBlock에서 수행(예정이었음)
                    # for block in blockchain:
                    #     updateTx(block)
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


def readBlockchain(blockchainFilePath, mode='internal'):
    print("readBlockchain")
    importedBlockchain = []

    try:
        with open(blockchainFilePath, 'r', newline='') as file:
            blockReader = csv.reader(file)
            for line in blockReader:
                block = Block(line[0], line[1], line[2], line[3], line[4], line[5])
                importedBlockchain.append(block)

        print("Pulling blockchain from csv...")

        return importedBlockchain

    except:
        if mode == 'internal':
            blockchain = generateGenesisBlock()
            importedBlockchain.append(blockchain)
            writeBlockchain(importedBlockchain)
            return importedBlockchain
        else:
            return None


# KHJ
# def updateTxPool(usedUuidDict):  # 파라미터: [commitYN, uuid]로 구성된 이중리스트


# def updateTx(blockData) :
#
#     phrase = re.compile(r"\w+[-]\w+[-]\w+[-]\w+[-]\w+") # [6b3b3c1e-858d-4e3b-b012-8faac98b49a8]UserID hwang sent 333 bitTokens to UserID kim.
#     matchList = phrase.findall(blockData.data)
#
#     if len(matchList) == 0 :
#         print ("No Match Found! " + str(blockData.data) + "block idx: " + str(blockData.index))
#         return
#
#     tempfile = NamedTemporaryFile(mode='w', newline='', delete=False)
#
#     with open(g_txFileName, 'r') as csvfile, tempfile:
#         reader = csv.reader(csvfile)
#         writer = csv.writer(tempfile)
#         for row in reader:
#             if row[4] in matchList:
#                 print('updating row : ', row[4])
#                 row[0] = 1
#             writer.writerow(row)
#
#     shutil.move(tempfile.name, g_txFileName)
#     csvfile.close()
#     tempfile.close()
#     print('txData updated')


# KHJ
def writeTx(txRawData):
    print(g_txFileName)
    txDataList = []
    txOriginalList = []
    for txDatum in txRawData:
        txList = [txDatum.commitYN, txDatum.listener, txDatum.music, txDatum.copyrightHolder, txDatum.uuid]
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
        try:
            with open(g_txFileName, "w", newline='') as file:
                writer = csv.writer(file)
                writer.writerows(txDataList)
        except:
            return 0
    return 1
    print('txData written to txData.csv.')


# KHJ: readTx를 중앙서버에서 읽어 오는 것으로 수정할 필요
def readTx(txFilePath):
    print("readTx")
    importedTx = []

    try:
        with open(txFilePath, 'r', newline='') as file:
            txReader = csv.reader(file)
            for row in txReader:
                if row[0] == '0':
                    importedTx.append(row)
        print("Pulling txData from csv...")
        return importedTx
    except:
        # KHJ
        # return []
        return ''


# KHJ: 머클루트로 대체
# def getTxData():
#     strTxData = ''
#     importedTx = readTx(g_txFileName)
#     if len(importedTx) > 0 :
#         for i in importedTx:
#             print(i.__dict__)
#             transaction = "["+ i.uuid + "]" "UserID " + i.sender + " sent " + i.amount + " bitTokens to UserID " + i.receiver + ". " #
#             print(transaction)
#             strTxData += transaction
#
#     return strTxData


# KHJ: 머클루트 계산에 사용된 uuid만 추출해서 사용되었는지 기록하는 로직 추가 필요
def hashTx():
    # readTx를 중앙서버에서 읽어 오는 것으로 수정할 필요
    importedTx = readTx(g_txFileName)
    if importedTx == '':
        return ''
    else:
        totalList = []
        hashedTxList = []
        uuidList = []
        for eachTx in importedTx:
            value = str(eachTx[0]) + str(eachTx[1]) + str(eachTx[2]) + str(eachTx[3]) + str(eachTx[4])
            sha = str(hashlib.sha256(value.encode('utf-8')).hexdigest())
            hashedTxList.append(sha)
            uuidList.append(str(eachTx[4]))
        totalList.append(hashedTxList)
        totalList.append(uuidList)
        return totalList


# KHJ
def calculateMerkleParent(childList):  # 파라미터:[해쉬값, 해쉬값, ...]
    if len(childList) % 2 == 1:
        childList.append(childList[-1])
    merkleParentList = []
    for i in range(0, len(childList) - 1, 2):
        parent = childList[i] + childList[i + 1]
        merkleParent = str(hashlib.sha256(parent.encode('utf-8')).hexdigest())
        merkleParentList.append(merkleParent)
    return merkleParentList


# KHJ
def calculateMerkleRoot(childList):
    if childList == '':
        return childList
    else:
        if (len(childList) > 1):
            while len(childList) > 1:
                childList = calculateMerkleParent(childList)
            return childList
        elif (len(childList) == 1):  # txData가 1개인 경우
            return childList


# KHJ
# def broadcastUpdatedTx(usedUuidList):


# KHJ
def mineNewBlock(difficulty=g_difficulty, blockchainPath=g_bcFileName):
    blockchain = readBlockchain(blockchainPath)
    # strTxData = getTxData()

    totalList = hashTx()
    if totalList == '':
        childList = ''
    else:
        childList = totalList[0]
        # usedUuidList = totalList[1]

    merkleRoot = calculateMerkleRoot(childList)
    if merkleRoot == '':
        print('No TxData Found. Mining aborted')
        return

    timestamp = time.time()
    proof = 0
    newBlockFound = False

    print('Mining a block...')

    while not newBlockFound:
        newBlockAttempt = generateNextBlock(blockchain, merkleRoot, timestamp, proof)
        if newBlockAttempt.currentHash[0:difficulty] == '0' * difficulty:
            stopTime = time.time()
            timer = stopTime - timestamp
            print('New block found with proof', proof, 'in', round(timer, 2), 'seconds.')
            newBlockFound = True
        else:
            proof += 1
    # broadcastUpdatedTx(usedUuidList)
    blockchain.append(newBlockAttempt)
    writeBlockchain(blockchain)


def mine():
    mineNewBlock()


def isSameBlock(block1, block2):
    if str(block1.index) != str(block2.index):
        return False
    elif str(block1.previousHash) != str(block2.previousHash):
        return False
    elif str(block1.timestamp) != str(block2.timestamp):
        return False
    elif str(block1.merkleRoot) != str(block2.merkleRoot):
        return False
    elif str(block1.currentHash) != str(block2.currentHash):
        return False
    elif str(block1.proof) != str(block2.proof):
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


# KHJ 채굴되지 않은 tx로만 채굴할 수 있도록 검증하는 로직 추가 필요
def broadcastNewTx(newtxData):  # 파라미터: 이중 리스트(json)
    reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
    reqBody = []
    reqBody.append(newtxData)
    try:
        URL = "http://" + g_txPoolAddress + "/recordTxPool"  # http://서버아이피:포트/recordTxPool
        res = requests.post(URL, headers=reqHeader, data=json.dumps(reqBody))
        if res.status_code == 200:
            print(URL + " recorded your playback.")
            print("Response Message " + res.text)
        else:
            print(URL + " responding error " + res.status_code)
            print(URL + " is not responding. It is failed to play music")
    except:
        print(URL + " is not responding. It is failed to play music")


# KHJ
def newtx(txToMining):
    newtxData = []
    # print(txToMining)
    # post로 날릴 때 [[{},{}]]처럼 배열이 이중으로 생기는 오류가 발생하여 txToMining[0]으로 하드코딩
    for line in txToMining[0]:
        tx = txData(0, line['listener'], line['music'], line['copyrightHolder'], uuid.uuid4())
        # tx = txData(0, line['sender'], line['amount'], line['receiver'], uuid.uuid4())
        newtxData.append(tx)

    # limitation check : max 5 tx
    # if len(newtxData) > 5 :
    #     print('number of requested tx exceeds limitation')
    #     return -1

    if writeTx(newtxData) == 0:
        print("file write error on txData")
        return -2
    return 1


def isValidChain(bcToValidate):
    genesisBlock = []
    bcToValidateForBlock = []

    try:
        with open(g_bcFileName, 'r', newline='') as file:
            blockReader = csv.reader(file)
            for line in blockReader:
                block = Block(line[0], line[1], line[2], line[3], line[4], line[5])
                genesisBlock.append(block)
    #           break
    except:
        print("file open error in isValidChain")
        return False

    for line in bcToValidate:
        # index, previousHash, timestamp, data, currentHash, proof
        block = Block(line['index'], line['previousHash'], line['timestamp'], line['merkleRoot'], line['currentHash'],
                      line['proof'])
        bcToValidateForBlock.append(block)

    if not genesisBlock:
        print("fail to read genesisBlock")
        return False

    if not isSameBlock(bcToValidateForBlock[0], genesisBlock[0]):
        print('Genesis Block Incorrect')
        return False

    for i in range(0, len(bcToValidateForBlock)):
        if isSameBlock(genesisBlock[i], bcToValidateForBlock[i]) == False:
            return False

    return True


def addNode(queryStr):
    # save
    previousList = []
    nodeList = []
    nodeList.append([queryStr[0], queryStr[1], 0])

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
        with open(filePath, 'r', newline='') as file:
            txReader = csv.reader(file)
            for row in txReader:
                line = [row[0], row[1]]
                importedNodes.append(line)
        print("Pulling txData from csv...")
        return importedNodes
    except:
        return []


def broadcastNewBlock(blockchain):
    importedNodes = readNodes(g_nodelstFileName)
    reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
    reqBody = []
    for i in blockchain:
        reqBody.append(i.__dict__)

    if len(importedNodes) > 0:
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
                tempfile = NamedTemporaryFile(mode='w', newline='', delete=False)
                try:
                    with open(g_nodelstFileName, 'r', newline='') as csvfile, tempfile:
                        reader = csv.reader(csvfile)
                        writer = csv.writer(tempfile)
                        for row in reader:
                            if row:
                                if row[0] == node[0] and row[1] == node[1]:
                                    print("connection failed " + row[0] + ":" + row[1] + ", number of fail " + row[2])
                                    tmp = row[2]
                                    if int(tmp) > g_maximumTry:
                                        print(row[0] + ":" + row[
                                            1] + " deleted from node list because of exceeding the request limit")
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

# HHB
def compareMerge(bcDict):

    heldBlock = []
    bcToValidateForBlock = []

    try:
        with open(g_bcFileName, 'r',  newline='') as file:
            blockReader = csv.reader(file)
            for line in blockReader:
                block = Block(line[0], line[1], line[2], line[3], line[4], line[5])
                heldBlock.append(block)

    except:
        print("file open error in compareMerge or No database exists")
        print("call initSvr if this server has just installed")
        return -2

    for line in bcDict:
        block = Block(line['index'], line['previousHash'], line['timestamp'], line['merkleRoot'], line['currentHash'], line['proof'])
        bcToValidateForBlock.append(block)

    if not isSameBlock(bcToValidateForBlock[0], heldBlock[0]):
        print('Genesis Block Incorrect')
        return -1

    if len(heldBlock) == len(bcToValidateForBlock):
        for i in range(1, len(heldBlock)):
            if isSameBlock(heldBlock[i], bcToValidateForBlock[i]) == False:
                print("Each Block dose not match")
                return -1
            elif isValidNewBlock(bcToValidateForBlock[i], bcToValidateForBlock[i - 1]) == False:
                print("Block Chain info incorrected")
                return -1

        print('Block Chain is already updated')
        return 2

    if len(heldBlock) < len(bcToValidateForBlock):
        for i in range(0, len(heldBlock)):
            if isSameBlock(heldBlock[i], bcToValidateForBlock[i]) == False:
                print("Each Block dose not match")
                return -1
        for i in range(1, len(bcToValidateForBlock)):
            if isValidNewBlock(bcToValidateForBlock[i], bcToValidateForBlock[i - 1]) == False:
                print("Block Chain info incorrected")
                return -1

        newBlock = []
        lenNewBlocklen = len(bcToValidateForBlock) - len(heldBlock)
        for i in range(1, lenNewBlocklen + 1):
            newBlock.append([bcToValidateForBlock[-i].index, bcToValidateForBlock[-i].previousHash,
                             str(bcToValidateForBlock[-i].timestamp), bcToValidateForBlock[-i].merkleRoot,
                             bcToValidateForBlock[-i].currentHash, bcToValidateForBlock[-i].proof])
            newBlock.reverse()
        with open(g_bcFileName, "a", newline='') as file:
            writer = csv.writer(file)
            for i in range(0, len(newBlock)):
                writer.writerow(newBlock[i])
                print("Block Chain is updated")
                return 1

    if len(heldBlock) > len(bcToValidateForBlock):
        print("We have a longer chain")
        return 3


def initSvr():
    print("init Server")
    last_line_number = row_count(g_nodelstFileName)
    if last_line_number == 0:
        for key, value in g_nodeList.items():
            URL = 'http://' + key + ':' + value + '/node/getNode'
            try:
                res = requests.get(URL)
            except requests.exceptions.ConnectionError:
                continue
            if res.status_code == 200:
                print(res.text)
                tmpNodeLists = json.loads(res.text)
                for node in tmpNodeLists:
                    addNode(node)

    last_line_number = row_count(g_bcFileName)
    blockchainList = []
    if last_line_number == 0:
        for key, value in g_nodeList.items():
            URL = 'http://' + key + ':' + value + '/block/getBlockData'
            try:
                res = requests.get(URL)
            except requests.exceptions.ConnectionError:
                continue
            if res.status_code == 200:
                print(res.text)
                tmpbcData = json.loads(res.text)
                for line in tmpbcData:
                    block = [line['index'], line['previousHash'], line['timestamp'], line['merkleRoot'],
                             line['currentHash'], line['proof']]
                    blockchainList.append(block)
                try:
                    with open(g_bcFileName, "w", newline='') as file:
                        writer = csv.writer(file)
                        writer.writerows(blockchainList)
                except Exception as e:
                    print("file write error in initSvr() " + e)

    return 1


class myHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        data = []  # response json data
        if None != re.search('/block/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/block/getBlockData', self.path):

                block = readBlockchain(g_bcFileName, mode='external')

                if block == None:
                    print("No Block Exists")
                    data.append("no data exists")
                else:
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
        else:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

    def do_POST(self):

        if None != re.search('/block/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/block/validateBlock/*', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])

                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)
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
                    # KHJ
                    # res = newtx(tempDict)
                    broadcastNewTx(tempDict)
                    # if res == 1:
                    #     tempDict.append("accepted : it will be mined later")
                    #     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    # KHJ
                    # elif res == -1 :
                    #     tempDict.append("declined : number of request txData exceeds limitation")
                    #     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    # elif res == -2:
                    #     tempDict.append("declined : error on data read or write")
                    #     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    # else:
                    #     tempDict.append("error : requested data is abnormal")
                    #     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

        # KHJ : newtx 날릴 때마다 등록된 메인서버로 /recordTxPool 날리도록 코딩
        elif None != re.search('/recordTxPool', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            receivedData = post_data.decode('utf-8')
            tempDict = json.loads(receivedData)
            print(tempDict)
            newtx(tempDict)


        # KHJ : mineNewBlock 될 때마다 서버의 txData의 commitYN을 수정
        # elif None != re.search('/updateTxPool', self.path):

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
                if res == -2:  # internal error
                    tempDict.append("internal error")
                elif res == -1:  # block chain info incorrect
                    tempDict.append("block chain info incorrect")
                elif res == 1:  # normal
                    tempDict.append("block chain is updated")
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