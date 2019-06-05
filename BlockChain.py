import hashlib
import time
import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import json
import re
from urllib.parse import parse_qs
from urllib.parse import urlparse
import threading
import cgi
import uuid
import requests  # for sending new block to other nodes
import pandas as pd
import pymysql
from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:root@127.0.0.1:3306/test')
PORT_NUMBER = 8099
g_txTableName = 'txdata'
g_bcTableName = 'blockchain'
g_nodelistTableName = 'nodelist'
g_receiveNewBlock = "/node/receiveNewBlock"
g_difficulty = 2
g_maximumTry = 100
g_nodeList = {'trustedServerAddress': '8099'}  # trusted server list, should be checked manually

class Block:

    def __init__(self, index, previousHash, timestamp, data, currentHash, proof, fee, signature):
        self.index = index
        self.previousHash = previousHash
        self.timestamp = timestamp
        self.data = data
        self.currentHash = currentHash
        self.proof = proof
        self.fee = fee
        self.signature = signature

    def toJSON(self): # 20190605 Hyun Gong Block to json
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class txData:

    def __init__(self, commitYN, sender, amount, receiver, uuid, fee, message, txTime):
        self.commitYN = commitYN
        self.sender = sender
        self.amount = amount
        self.receiver = receiver
        self.uuid = uuid
        self.fee = fee
        self.message = message
        self.txTime = txTime

# 20190604 Hyun Gong automatic timer
# Block mining every 10 minutes using threading
def execute_func(second=1.0):
    end = False
    if end:
        return
    mineNewBlock()
    threading.Timer(second, execute_func, [second]).start()

# 20190604 Hyun Gong mysql_Query
def selectTable(tableName):
    table = pd.read_sql_query('select * from {}'.format(tableName), engine)
    table.rename(columns=lambda x: x.lower(), inplace=True)
    return table

def insertBlockchain(block):
    try:
        pd.read_sql_query("insert into blockchain values ({}, '{}', '{}', '{}', '{}', {}, {}, '{}')".format(block.index, block.previousHash, block.timestamp, block.data, block.currentHash, block.proof, block.fee, block.signature), engine)
    except:
        pass

def insertTxdata(tx):
    try:
        pd.read_sql_query("insert into txdata values ({}, '{}', {}, '{}', '{}', {}, '{}', '{}')".format(tx.commitYN, tx.sender, tx.amount, tx.receiver, tx.uuid, tx.fee, tx.message, tx.txTime), engine)
    except:
        pass

def insertNodelist(ip, port):
    try:
        pd.read_sql_query("insert into nodelist (ip, port, trial) values ('{}', '{}', 0)".format(ip, port), engine)
    except:
        pass

def generateGenesisBlock():
    print("generateGenesisBlock is called")
    timestamp = time.time()
    print("time.time() => %f \n" % timestamp)
    tempHash = calculateHash(0, '0', timestamp, "Genesis Block", 0, 0, 'Genesis')
    print(tempHash)
    return Block(0, '0', timestamp, "Genesis Block", tempHash, 0, 0, 'Genesis')

def calculateHash(index, previousHash, timestamp, data, proof, fee, signature):
    value = str(index) + str(previousHash) + str(timestamp) + str(data) + str(proof) + str(fee) + str(signature)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())

# 20190604 Hyun Gong txData message hash
# Hash message content using sha256
def messageHash():
    temp = ''
    importedTx = readTx(g_txTableName).reset_index(drop=True)
    if len(importedTx) > 0:
        for i in (range(len(importedTx))):
            temp += importedTx.message[i]
    sha = hashlib.sha256(temp.encode('utf-8'))
    return str(sha.hexdigest())

def calculateHashForBlock(block):
    return calculateHash(block.index, block.previousHash, block.timestamp, block.data, block.proof, block.fee,
                         block.signature)

def getLatestBlock(blockchain):
    latestBlock = Block(blockchain.no[len(blockchain) - 1], blockchain.previoushash[len(blockchain) - 1], blockchain.timestamp[len(blockchain) - 1], blockchain.data[len(blockchain) - 1], blockchain.currenthash[len(blockchain) - 1], blockchain.proof[len(blockchain) - 1], blockchain.fee[len(blockchain) - 1], blockchain.signature[len(blockchain) - 1])
    return latestBlock

def generateNextBlock(blockchain, blockData, timestamp, proof, fee, signature):
    previousBlock = getLatestBlock(blockchain)
    nextIndex = int(previousBlock.index) + 1
    nextTimestamp = timestamp
    nextHash = calculateHash(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, proof, fee, signature)

    return Block(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, nextHash, proof, fee, signature)

def writeBlockchain(blockchain):

    # [STARAT] check current DB if broadcasted block data has already been updated
    lastBlock = None
    try:
        blockReader = selectTable(g_bcTableName)
        lastLine = blockReader[len(blockReader) -1, len(blockReader), :]
        lastBlock = Block(lastLine.no[0], lastLine.previoushash[0], lastLine.timestamp[0], lastLine.data[0], lastLine.currenthash[0], lastLine.proof[0], lastLine.fee[0], lastLine.signature[0])

        if int(lastBlock.index) + 1 != int(blockchain.no[len(blockchain) - 1]):
            print("index sequence mismatch")
            if int(lastBlock.index) == int(blockchain.no[len(blockchain) - 1]):
                print("db has already been updated")
            return
    except:
        print("file open error in check current db(csv) \n or maybe there's some other reason")
        pass
        # return
    # [END] check current DB

    newBlock = Block(blockchain.no[len(blockchain) - 1], blockchain.previoushash[len(blockchain) - 1], blockchain.timestamp[len(blockchain) - 1], blockchain.data[len(blockchain) - 1],
                     blockchain.currenthash[len(blockchain) - 1], blockchain.proof[len(blockchain) - 1], blockchain.fee[len(blockchain) - 1], blockchain.signature[len(blockchain) - 1])

    # 20190604 Hyun Gong newBlock insert_query
    insertBlockchain(newBlock)
    updateTx(newBlock)
    print('Blockchain written to db.')

    # print('Broadcasting new block to other nodes')
    # broadcastNewBlock(blockchain)

def readBlockchain(g_bcTableName, mode='internal'):
    print("readBlockchain")
    importedBlockchain = pd.DataFrame()

    try:
        importedBlockchain = selectTable(g_bcTableName)
        print("Pulling blockchain from db...")
        return importedBlockchain

    except:
        if mode == 'internal':
            blockchain = generateGenesisBlock()
            importedBlockchain = pd.DataFrame()
            importedBlockchain.loc[0] = [blockchain.index, blockchain.previousHash, blockchain.timestamp,
                                         blockchain.data, blockchain.currentHash, blockchain.proof, blockchain.fee,
                                         blockchain.signature]
            writeBlockchain(importedBlockchain)
            return importedBlockchain
        else:
            return 0

def readPagingBlockchain(g_bcTableName, start, end, mode='internal'):
    print("readBlockchain")

    importedBlockchain = pd.DataFrame()
    if start > end:
        return 0
    try:
        # 20190604 Hyun Gong paging blockdata
        importedBlockchain = selectTable(g_bcTableName)
        if start > len(importedBlockchain) or start < 1:
            return 0
        else:
            # 20190604 Hyun Gong limitation check : max 100 blockchain
            if end - start < 100:
                importedBlockchain = importedBlockchain.iloc[start - 1:end, :]
                print("Pulling blockchain from db...")
                return importedBlockchain
            else:
                return 0

    except:
        if mode == 'internal':
            blockchain = generateGenesisBlock()
            importedBlockchain = pd.DataFrame()
            importedBlockchain.loc[0] = [blockchain.index, blockchain.previousHash, blockchain.timestamp,
                                         blockchain.data, blockchain.currentHash, blockchain.proof, blockchain.fee,
                                         blockchain.signature]
            writeBlockchain(importedBlockchain)
            return importedBlockchain
        else:
            return 0

def updateTx(blockData):
    phrase = re.compile(
        r"\w+[-]\w+[-]\w+[-]\w+[-]\w+")  # [6b3b3c1e-858d-4e3b-b012-8faac98b49a8]UserID hwang sent 333 bitTokens to UserID kim.
    matchList = phrase.findall(blockData.data)

    if len(matchList) == 0:
        print("No Match Found! " + str(blockData.data) + "block idx: " + str(blockData.index))
        return

    reader = selectTable(g_txTableName)
    for i in range(len(reader)):
        if reader.uuid[i] in matchList:
            print('updating row : ', reader.uuid[i])
            try:
                # 20190604 Hyun Gong txData commintYN update_query
                pd.read_sql_query("update txdata set commityn = 1 where uuid = '{}'".format(reader.uuid[i]), engine)
            except:
                pass

    print('txData updated')

def writeTx(txRawData):
    print(g_txTableName)
    count = 0
    # 20190604 Hyun Gong txData insert_query
    try:
        for i in txRawData:
            insertTxdata(i)
            count += 1
    # 20190604 Hyun gong except txData : delete
    except:
        try:
            for i in txRawData[count]:
                pd.read_sql_query("delete txdata where uuid = '{}'".format(i.uuid))
        except:
            return 0
    return 1
    print('txData written to DB')

def readTx(txTablePath):
    print("readTx")
    try:
        importedTx = selectTable(txTablePath)

        # 20190604 Hyun Gong sort : txData fee
        # It brings something that is not mined(commityn==0 means not mined block)
        importedTx = importedTx[importedTx.commityn == 0].sort_values(['fee', 'txtime'], ascending = [False, False]).reset_index(drop=True)
        print(len(importedTx))
        print("Pulling txData from db...")
        return importedTx
    except:
        return pd.DataFrame

def readPagingTx(g_txTableName, count):
    print("readBlockchain")

    importedTx = pd.DataFrame()
    if int(count) <= 0:
        return 0
    try:
        importedTx = selectTable(g_txTableName)

        # 20190604 Hyun Gong sort : txData fee
        # Columns output of only necessary lines from the table
        importedTx = importedTx[importedTx.commityn == 0].sort_values(['fee', 'txtime'], ascending = [False, False]).reset_index(drop=True)
        importedTx = importedTx.iloc[0:int(count), :]

        print("Pulling blockchain from db...")
        return importedTx
    except:
        return 0

def getTxData():
    strTxData = ''
    importedTx = readTx(g_txTableName)

    if len(importedTx) > 0:
        for i in range(len(importedTx)):
            transaction = "[" + importedTx.uuid[i] + "]" "UserID " + importedTx.sender[i] + " sent " + str(importedTx.amount[i]) + " bitTokens to UserID " + importedTx.receiver[i] + " fee: " + str(importedTx.fee[i]) + "message: " + importedTx.message[i] + ", time : " + importedTx.txtime[i]  #
            print(transaction)
            strTxData += transaction

    return strTxData

def getCountedTxData(count):
    strTxData = ''
    importedTx = readPagingTx(g_txTableName, int(count))

    if type(importedTx) != int:
        if len(importedTx) > 0:
            for i in range(len(importedTx)):
                transaction = "[" + importedTx.uuid[i] + "]" "UserID " + importedTx.sender[i] + " sent " + str(importedTx.amount[i]) + " bitTokens to UserID " + importedTx.receiver[i] + " fee: " + str(importedTx.fee[i]) + "message: " + importedTx.message[i] + ", time : " + importedTx.txtime[i]  #
                print(transaction)
                strTxData += transaction

    return strTxData

# 20190604 Hyun Gong getFee in Block
# Add as much fee as you want

def getCountedFeeData(count):
    temp = 0
    importedTx = readPagingTx(g_txTableName, int(count)).reset_index(drop=True)
    if type(importedTx) != int:
        if len(importedTx) > 0:
            for i in range(len(importedTx)):
                temp += importedTx.fee[i]
    return temp

# 20190604 Hyun Gong getFee in Block
# add up all the fees
def getFeeData():
    temp = 0
    importedTx = readTx(g_txTableName).reset_index(drop=True)
    if len(importedTx) > 0:
        for i in range(len(importedTx)):
            temp += importedTx.fee[i]
    return temp

def mineNewBlock(difficulty=g_difficulty, blockchainPath=g_bcTableName):
    blockchain = readBlockchain(blockchainPath)
    strTxData = getTxData()

    if len(blockchain) == 0:
        insertBlockchain(generateGenesisBlock())

    elif len(blockchain) != 0:
        if strTxData == '':
            print('No TxData Found. Mining aborted')
            return
        else:
            timestamp = time.time()
            proof = 0
            fee = getFeeData()
            signature = messageHash()
            newBlockFound = False

            print('Mining a block...')

            while not newBlockFound:
                newBlockAttempt = generateNextBlock(blockchain, strTxData, timestamp, proof, fee, signature)
                if newBlockAttempt.currentHash[0:difficulty] == '0' * difficulty:
                    stopTime = time.time()
                    timer = stopTime - timestamp
                    print('New block found with proof', proof, 'in', round(timer, 2), 'seconds.')
                    newBlockFound = True
                else:
                    proof += 1

            blockchain.loc[len(blockchain)] = [newBlockAttempt.index, newBlockAttempt.previousHash, newBlockAttempt.timestamp, newBlockAttempt.data, newBlockAttempt.currentHash, newBlockAttempt.proof, newBlockAttempt.fee, newBlockAttempt.signature]
            writeBlockchain(blockchain)

def mineCountedNewBlock(count, difficulty=g_difficulty, blockchainPath=g_bcTableName):
    blockchain = readBlockchain(blockchainPath)
    strTxData = getCountedTxData(count)

    if len(blockchain) == 0:
        insertBlockchain(generateGenesisBlock())

    elif len(blockchain) != 0:
        if strTxData == '':
            print('No TxData Found. Mining aborted')
            return
        else:
            timestamp = time.time()
            proof = 0
            fee = getCountedFeeData(count)
            signature = messageHash()
            newBlockFound = False

            print('Mining a block...')

            while not newBlockFound:
                newBlockAttempt = generateNextBlock(blockchain, strTxData, timestamp, proof, fee, signature)
                if newBlockAttempt.currentHash[0:difficulty] == '0' * difficulty:
                    stopTime = time.time()
                    timer = stopTime - timestamp
                    print('New block found with proof', proof, 'in', round(timer, 2), 'seconds.')
                    newBlockFound = True
                else:
                    proof += 1

            blockchain.loc[len(blockchain)] = [newBlockAttempt.index, newBlockAttempt.previousHash, newBlockAttempt.timestamp, newBlockAttempt.data, newBlockAttempt.currentHash, newBlockAttempt.proof, newBlockAttempt.fee, newBlockAttempt.signature]
            writeBlockchain(blockchain)

def mine():
    mineNewBlock()

def mineCounted(count):
    mineCountedNewBlock(count)

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
    elif str(block1.fee) != str(block2.fee):
        return False
    elif str(block1.signature) != str(block2.signature):
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
# 20190604 Hyun Gong The part that creates the new txdata
def newtx(txToMining):
    newtxData = []
    # transform given data to txData object
    for line in txToMining:
        txTime = time.time()
        tx = txData(0, line['sender'], line['amount'], line['receiver'], uuid.uuid4(), line['fee'], line['message'], txTime)
        newtxData.append(tx)

    # limitation check : max 5 tx
    if len(newtxData) > 5:
        print('number of requested tx exceeds limitation')
        return -1

    if writeTx(newtxData) == 0:
        print("file write error on txData")
        return -2
    return 1

# def isValidChain(bcToValidate):
#     genesisBlock = []
#     bcToValidateForBlock = []
#
#     # Read GenesisBlock
#     try:
#         with open(g_bcFileName, 'r', newline='') as file:
#             blockReader = csv.reader(file)
#             for line in blockReader:
#                 block = Block(line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7])
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
#                       line['proof'], line['fee'], line['signature'])
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
#     for i in range(0, len(bcToValidateForBlock)):
#         if isSameBlock(genesisBlock[i], bcToValidateForBlock[i]) == False:
#             return False
#
#     return True

def addNode(queryStr):
    inputNodeIp = queryStr[0]
    inputNodePort = queryStr[1]

    importedNodeList = selectTable(g_nodelistTableName)

    # 20190604 Hyun Gong check nodeIP, nodePort
    # Check that the node in the table and the input node are the same
    try:
        if len(importedNodeList) == 0:
            insertNodelist(inputNodeIp, inputNodePort)
        else:
            for i in range(len(importedNodeList)):
                if inputNodeIp == importedNodeList.ip[i] and inputNodePort == importedNodeList.port[i]:
                    print("requested node is already exists")
                    return -1
            insertNodelist(inputNodeIp, inputNodePort)
            return 1
    except:
        return 0

    print('new node written to DB')

def readNodes(g_nodelstTableName):
    print("read Nodes")

    try:
        importedNodeList = selectTable(g_nodelstTableName)
        return importedNodeList
    except:
        return None

# def broadcastNewBlock(blockchain):
#     # newBlock  = getLatestBlock(blockchain) # get the latest block
#     importedNodes = selectTable(g_nodelistTableName)  # get server node ip and port
#     reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
#     reqBody = []
#     for i in range(len(blockchain)):
#         Dict = {'no': str(blockchain.no[i]), 'previousHash': blockchain.previoushash[i],
#                 'timestamp': blockchain.timestamp[i], 'data': blockchain.data[i],
#                 'currentHash': blockchain.currenthash[i], 'proof': str(blockchain.proof[i]), 'fee': str(blockchain.fee[i]),
#                 'signature': blockchain.signature[i]}
#         reqBody.append(Dict)
#
#     if len(importedNodes) > 0:
#         for i in range(len(importedNodes)):
#             try:
#                 URL = "http://" + importedNodes.ip[i] + ":" + importedNodes.port[
#                     i] + g_receiveNewBlock  # http://ip:port/node/receiveNewBlock
#                 res = requests.post(URL, headers=reqHeader, data=json.dumps(reqBody))
#                 if res.status_code == 200:
#                     print(URL + " sent ok.")
#                     print("Response Message " + res.text)
#                 else:
#                     print(URL + " responding error " + res.status_code)
#             except:
#                 print(URL + " is not responding.")
#                 # write responding results
#                 try:
#                     reader = selectTable(g_nodelistTableName)
#                     for j in range(len(reader)):
#                         if j:
#                             if reader.ip[j] == importedNodes.ip[i] and reader.port[j] == importedNodes.port[j]:
#                                 print("connection failed " + reader.ip[j] + ":" + reader.port[j] + ", number of fail " +
#                                       reader.trial[j])
#                                 tmp = reader.trial[j]
#                                 # too much fail, delete node
#                                 if int(tmp) > g_maximumTry:
#                                     print(reader.ip[j] + ":" + reader.port[
#                                         j] + " deleted from node list because of exceeding the request limit")
#                                 else:
#                                     reader.trial[j] = int(tmp) + 1
#                                     pd.read_sql_query("update nodelist set trial={} where ip='{}' and port='{}'".format(
#                                         reader.trial[j], reader.ip[j], reader.port[j]), engine)
#
#                 except:
#                     print("caught exception while updating node list")

def row_count(tableName):
    table = selectTable(tableName)
    return len(table)

def compareMerge(bcDict):
    heldBlock = []
    bcToValidateForBlock = []

    # Read GenesisBlock
    try:
        blockReader = selectTable(g_bcTableName)
        # last_line_number = row_count(g_bcFileName)
        for i in range(len(blockReader)):
            block = Block(blockReader.no[i], blockReader.previoushash[i], blockReader.timestamp[i], blockReader.data[i], blockReader.currenthash[i], blockReader.proof[i], blockReader.fee[i], blockReader.signature[i])
            heldBlock.append(block)

    except:
        print("file open error in compareMerge or No database exists")
        print("call initSvr if this server has just installed")
        return -1

    # if it fails to read block data from db
    if len(heldBlock) == 0:
        print("fail to read")
        return -2

    # transform given data to Block object
    for line in bcDict:
        # print(type(line))
        block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'],
                      line['proof'], line['signature'])
        bcToValidateForBlock.append(block)

    # compare the given data with genesisBlock
    if not isSameBlock(bcToValidateForBlock[0], heldBlock[0]):
        print('Genesis Block Incorrect')
        return -1

    # check if broadcasted new block,1 ahead than > last held block
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

            # 20190604 Hyun Gong need Trouble Shooting......
            # tempBlockchain = pd.DataFrame()
            # tempBlockchain.columns = ['index', 'previoushash', 'timestamp', 'data', 'currenthash', 'proof', 'fee', 'signature']
            # for block in bcToValidateForBlock:
            #     blockList = [block.index, block.previousHash, str(block.timestamp), block.data,
            #                  block.currentHash, block.proof, block.fee, block.signature]
            #     tempBlockchain.loc[len(tempBlockchain)] = blockList
            # tempBlockchain.to_sql(g_bcTableName, engine, if_exists='replace', index=False)

            return 1
        elif len(bcToValidateForBlock) < len(heldBlock):
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
        # [START] save it to DB
        tempBlockchain = pd.DataFrame()
        tempBlockchain.columns = ['index', 'previoushash', 'timestamp', 'data', 'currenthash', 'proof', 'fee',
                                  'signature']
        for block in bcToValidateForBlock:
            blockList = [block.index, block.previousHash, str(block.timestamp), block.data,
                         block.currentHash, block.proof, block.fee, block.signature]
            tempBlockchain.loc[len(tempBlockchain)] = blockList
        tempBlockchain.to_sql(g_bcTableName, engine, if_exists='replace', index=False)
        # [END] save it to DB
        return 1

def initSvr():
    print("init Server")
    # 1. check if we have a node list file
    last_line_number = row_count(g_nodelistTableName)
    # if we don't have, let's request node list
    if last_line_number == 0:
        # get nodes...
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

    # 2. check if we have a blockchain data file
    last_line_number = row_count(g_bcTableName)
    blockchainList = []
    if last_line_number == 0:
        # get Block Data...
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
                    block = [line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'],
                             line['proof'], line['fee'], line['signature']]
                    blockchainList.append(block)
                try:
                    # 20190604 Hyun Gong The part that reads all blockchain data is read.
                    # Compare blocks with other nodes
                    table = selectTable(g_bcTableName)
                    print(type(table))
                    for i in range(len(blockchainList)):
                        table.loc[len(table)] = blockchainList[i]
                except Exception as e:
                    print("file write error in initSvr() " + e)

    return 1

# This class will handle any incoming request from
# a browser
class myHandler(BaseHTTPRequestHandler):

    # def __init__(self, request, client_address, server):
    #    BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    # Handler for the GET requests
    def do_GET(self):
        data = []  # response json data
        if None != re.search('/block/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/block/getBlockData', self.path): # OK
                # TODO: range return (~/block/getBlockData?from=1&to=300)
                queryString = urlparse(self.path).query.split('?')[-1].split('&')
                print(queryString)

                # 20190604 Hyun Gong the part that determines how many blocks to load.
                if len(queryString) > 1:
                    try:
                        queryStringFrom = int(queryString[0].split('=')[1])
                        queryStringTo = int(queryString[1].split('=')[1])
                        if queryStringFrom != '' and queryStringTo != '' :
                            block = readPagingBlockchain(g_bcTableName, queryStringFrom, queryStringTo, mode='external')  # DataFrame
                        else:
                            block = None
                    except:
                        block = readBlockchain(g_bcTableName, mode='external')  # DataFrame
                else:
                    block = readBlockchain(g_bcTableName, mode='external')  # DataFrame

                if type(block) == int:
                    print("No Block Exists")
                    data.append("no data exists")
                else:
                    if type(block) != int and len(block) == 0:
                        print("No Block Exists")
                        data.append("no data exists")
                    else:
                        for i in range(len(block)):
                            Dict = {'no': str(block.no[i]), 'previousHash': block.previoushash[i],
                                    'timestamp': block.timestamp[i], 'data': block.data[i],
                                    'currentHash': block.currenthash[i], 'proof': str(block.proof[i]),
                                    'fee': str(block.fee[i]),
                                    'signature': block.signature[i]}
                            print(Dict)
                            data.append(Dict)

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            elif None != re.search('/block/generateBlock', self.path): # OK
                queryString = urlparse(self.path).query.split('count=')

                # 20190604 Hyun Gong The part that determines how many blocks to create.
                if queryString[-1] == "":
                    t = threading.Thread(target=mine)
                    t.start()
                    data.append("{mining is underway:check later by calling /block/getBlockData}")
                    self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))
                elif queryString[-1] != "":
                    count = queryString[-1]
                    t = threading.Thread(target=mineCounted(count))
                    t.start()
                    data.append("{mining is underway:check later by calling /block/getBlockData}")
                    self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))
                else:
                    data.append("{info:no such api}")
                    self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

        elif None != re.search('/txdata/getTxdata', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # TODO: range return (~/block/getBlockData?from=1&to=300)
            queryString = urlparse(self.path).query.split('?')
            print(queryString)

            # 20190604 Hyun Gong Bring as many txdata as you want
            if queryString[0].count('count') > 0:
                try:
                    count = queryString[0].split('=')[-1]
                    print(count)
                    txdata = readPagingTx(g_txTableName, count)  # DataFrame
                except:
                    txdata = 0  # DataFrame
            else:
                txdata = readTx(g_txTableName)  # DataFrame

            # 20190604 Hyun Gong When there is no txdata
            if type(txdata) == int:
                print("No txData Exists")
                data.append("no txData exists")
            else:
                if type(txdata) != int and len(txdata) == 0:
                    print("No txData Exists")
                    data.append("no txData exists")
                elif len(txdata) == 0:
                    print("No txData Exists")
                    data.append("no txData exists")

                # 20190604 Hyun Gong txdata to Dictionary
                else:
                    for i in range(len(txdata)):
                        Dict = {'commitYN': str(txdata.commityn[i]), 'sender': txdata.sender[i],
                                'amount': str(txdata.amount[i]), 'receiver': txdata.receiver[i],
                                'uuid': txdata.uuid[i], 'fee': str(txdata.fee[i]),
                                'message': txdata.message[i],
                                'txTime': txdata.txtime[i]}
                        print(Dict)
                        data.append(Dict)

            self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

        elif None != re.search('/node/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            if None != re.search('/node/addNode', self.path):
                queryStr = urlparse(self.path).query.split(':')
                print("client ip : " + self.client_address[0] + " query ip : " + queryStr[0])

                res = addNode(queryStr)
                if res == 1:
                    data.append("node added okay")
                elif res == 0:
                    data.append("caught exception while saving")
                elif res == -1:
                    data.append("requested node is already exists")
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            elif None != re.search('/node/getNode', self.path):
                importedNodes = readNodes(g_nodelistTableName)

                for i in range(len(importedNodes)):
                    Dict = {'ip': str(importedNodes.ip[i]), 'port': importedNodes.port[i]}
                    print(Dict)
                    data.append(Dict)

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
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.end_headers()

            # if None != re.search('/block/validateBlock/*', self.path):
            #     ctype, pdict = cgi.parse_header(self.headers['content-type'])
            #     # print(ctype) #print(pdict)
            #
            #     if ctype == 'application/json':
            #         content_length = int(self.headers['Content-Length'])
            #         post_data = self.rfile.read(content_length)
            #         receivedData = post_data.decode('utf-8')
            #         print(type(receivedData))
            #         tempDict = json.loads(receivedData)  # load your str into a list #print(type(tempDict))
            #         if isValidChain(tempDict) == True:
            #             tempDict.append("validationResult:normal")
            #             self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
            #         else:
            #             tempDict.append("validationResult:abnormal")
            #             self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
            if None != re.search('/block/newtx', self.path): # Doing
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
    # 20190604 Hyun Gong Automated mining every 10 minutes
    execute_func(600.0)
    # Wait forever for incoming http requests
    server.serve_forever()

except (KeyboardInterrupt, Exception) as e:
    print('^C received, shutting down the web server')
    print(e)
    server.socket.close()
