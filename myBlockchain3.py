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
import socket

IP_NUMBER = "127.0.0.1"
# socket.gethostbyname(socket.getfqdn())
PORT_NUMBER = 8099

#Set the information in the database that will be linked to this code.
DATABASE_SVR_NAME = "databasebc"
DATABASE_SVR_IP = 'localhost'
DATABASE_SVR_PORT = 3300
DATABASE_SVR_USER = "root"
DATABASE_SVR_PW = "root"
DATABASE_BC_TABLE = "blockchain"
DATABASE_ND_TABLE = "node"

#Set the ip aderess and port number of the transaction pool database.
DATABASE_TPSVR_IP = "http://localhost:8089"

#Set the ip address and port number of the miner list.
#miner list = The IP address and port number where the code is running.
DATABASE_MINER_LIST_IP = "http://localhost"
DATABASE_MINER_LIST_PORT = 8081

#a variable that determines whether it is a 'master' or a 'serve'.
MASTER = True
SERVE = False

g_difficulty = 2

class Block:

    def __init__(self, index, previousHash, timestamp, data, currentHash, proof, merkleHash):
        self.index = index
        self.previousHash = previousHash
        self.timestamp = timestamp
        self.data = data
        self.currentHash = currentHash
        self.proof = proof
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

#Generates the Genesis block.
def generateGenesisBlock(timestamp, proof):
    isSuccess = True
    newBlock = None
    GenesisTxData = [{"commitYN" : "0", "sender": "Genesis Block", "amount": "0", \
              "receiver": "kim", "fee": "0"}]

    reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
    try:
        URL = DATABASE_TPSVR_IP + "/txData/new"
        res = requests.post(URL, headers=reqHeader, data=json.dumps(GenesisTxData))
        if res.status_code == 200:
            print("Genesis txData sent ok.")

            txData, txTF = getTxData(0)

            merkleHash = calculateMerkleHash(txData)
            tempHash = calculateHash(0, '0', timestamp, proof, merkleHash)
            genesisBlockData = getStrTxData(txData)

            newBlock = Block(0, '0', timestamp, genesisBlockData, tempHash, proof, merkleHash)
        else:
            print(URL + " responding error " + 404)
            isSuccess = False
    except:
        print("transaction_pool server :  " + DATABASE_TPSVR_IP + " is not responding.")
        isSuccess = False
    finally:
        if isSuccess:
            print("Success to generate genesis block : \n" + str(newBlock.__dict__))

    return newBlock, isSuccess

#Creates a hash of the block.
def calculateHash(index, previousHash, timestamp, proof, merkleHash):
    value = str(index) + str(previousHash) + str(timestamp) + str(proof) + merkleHash
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())

#Returns a list of txData objects in a single string.
def getStrTxData(txData) :
    strTxData = ''
    if len(txData) > 0:
        for i in txData:
            transaction = "[" + i['uuid'] + "]" "UserID " + i['sender'] + " sent " + i['amount'] + " bitTokens to UserID " + \
i['receiver'] + " fee "+ i['fee'] + " transaction time " + str(i['transactionTime']) + ". "
            print(transaction)
            strTxData += transaction
    return strTxData

#Create a Muckle hash.
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

#Create and return a muckle hash through recursion.
def rcGetMerkleHash(target) :
    strBinaryTxData = ""
    #check
    print("current len of Target =  " + str(len(target)))
    endIndexOfTarget = len(target) - 1
    if len(target) <= 1 :
        sha = hashlib.sha256(target[0].encode('utf-8'))
        return str(sha.hexdigest())
    else :
        newTarget = []
        for i in range(endIndexOfTarget - 1):
            if i % 2 == 0 :
                strBinaryTxData = strBinaryTxData + target[i] + target[i+1]
                sha = hashlib.sha256(target[i].encode('utf-8'))
                newTarget.append(str(sha.hexdigest()))

        if (len(target) % 2) != 0:
            sha = hashlib.sha256(target[endIndexOfTarget].encode('utf-8'))
            newTarget.append(str(sha.hexdigest()))

        else :
            strBinaryTxData = strBinaryTxData + target[endIndexOfTarget-1] + target[endIndexOfTarget]
            sha = hashlib.sha256(strBinaryTxData.encode('utf-8'))
            newTarget.append(str(sha.hexdigest()))

        return rcGetMerkleHash(newTarget)

#Calculate and return the hash based on the information in the block.
def calculateHashForBlock(block):
    return calculateHash(block.index, block.previousHash, block.timestamp, block.proof, block.merkleHash)

#Returns the most recently created block.
def getLatestBlock(blockchain):
    lengthOfBlockChain = len(blockchain) - 1
    if len(blockchain) == 0 :
        lengthOfBlockChain = 0;
    return blockchain[lengthOfBlockChain]

#Generate the next block.
def generateNextBlock(blockList, txData, timestamp, proof):
    print("Trying to generate next block...........")
    isSuccess = True
    newBlock = None

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
        print("Fail to mine next block")
        isSuccess = False

    if isSuccess :
        print("Success to generate next block : \n" + str(newBlock.__dict__))
    return newBlock, isSuccess

#Enter the information of the block into the table in the linked database.
def writeBlockchain(blockchain):
    print("Trying write block to blockchain table..........")
    tableBlockList, readSuccess = readBlockchain()

    isSuccess = True

    if readSuccess :
        if len(tableBlockList) != 0 :
            lastBlock = getLatestBlock(tableBlockList)

            if lastBlock.index + 1 != blockchain.index :
                print("Failed to write new block to database. new block is invalid.")
                isSuccess = False

        if isSuccess :
            conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER, passwd=DATABASE_SVR_PW, \
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
                print("Failed to insert new block on database.")
            finally:
                conn.close()

    else :
        print("Failed to read blockchain data from database")
        isSuccess = False

    if isSuccess :
        print("Succeed to write new block on database.")
    return isSuccess

#Insert the block information of the block object list in the table of the linked database.
def writeAllBlockchain(blockchainList):

    result = 1
    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER, passwd=DATABASE_SVR_PW, \
                           database=DATABASE_SVR_NAME)
    try:
        print("Trying delete all data on table " + DATABASE_BC_TABLE + " for renewal...........")
        with conn.cursor() as curs:
            sql = "DELETE FROM " + DATABASE_BC_TABLE
            curs.execute(sql)
            conn.commit()
    except:
        print("Failed to delete all data.")
        result = -1
    finally:
        conn.close()

    print("Trying write block to blockchain table..........")
    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER, passwd=DATABASE_SVR_PW, \
                               database=DATABASE_SVR_NAME, charset = 'utf8')

    try:
        for blockchain in blockchainList:
            with conn.cursor() as curs:
                print(blockchain.index, blockchain.previousHash, str(blockchain.timestamp), \
                                    blockchain.data, blockchain.currentHash, blockchain.proof, blockchain.merkleHash)
                sql = "INSERT INTO " + DATABASE_BC_TABLE + " VALUES (%s,%s,%s,%s,%s,%s,%s)"
                curs.execute(sql,(blockchain.index, blockchain.previousHash, str(blockchain.timestamp), \
                                        blockchain.data, blockchain.currentHash, blockchain.proof, blockchain.merkleHash))
            conn.commit()
    except :
        print("Failed to insert new block on database.")
        result = -1
    finally:
        conn.close()

    if result == 1 :
        print("Succeed to write new block on database.")
    return result

#Returns all block information in the table in the database.
def readBlockchain():
    print("readBlockchain")
    isSuccess = False
    blockDataList = []
    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER, password=DATABASE_SVR_PW, \
                           db=DATABASE_SVR_NAME, charset='utf8')

    try:
        print("Trying to read blockchain data from " + DATABASE_BC_TABLE + " on " + DATABASE_SVR_NAME + "...........")
        with conn.cursor() as cursor :
            sql = "select * from " + DATABASE_BC_TABLE
            cursor.execute(sql)
            rows = cursor.fetchall()

            for data in rows:
                block = Block(data[0], data[1], data[2], data[3], data[4], data[5], data[6])
                blockDataList.append(block)
            isSuccess = True
    except:
        print("Failed to read blockchain data from " + DATABASE_BC_TABLE + " on " + DATABASE_SVR_NAME)
    finally:
        conn.close()

    if isSuccess :
        print("Success to read blockchain data from " + DATABASE_BC_TABLE + " on " + DATABASE_SVR_NAME)
    return blockDataList, isSuccess

#Request an update for the transaction details used to create the block to The transaction pool server.
def updateTx(blockData, mode = 'update'):

    isSuccess = True

    if mode == 'update' :
        query = '/txData/update'
        print("response update mode : 0 -> 1")
    else :
        query = '/txData/rollBack'
        print("response rollback mode : 1 -> 0")

    phrase = re.compile(
        r"\w+[-]\w+[-]\w+[-]\w+[-]\w+")

    print(blockData.data)
    matchList = phrase.findall(blockData.data)
    print(matchList)
    if len(matchList) == 0:
        print("No Match Found! " + str(blockData.data) + "block idx: " + str(blockData.index))
        isSuccess = False
    else :
        reqHeader = {'Content-Type': 'application/json; charset=utf-8'}

        blockDict = []
        blockDict.append(blockData.__dict__)
        print(blockDict)
        try:
            URL = DATABASE_TPSVR_IP + query
            print(URL)
            res = requests.post(URL, headers=reqHeader, data=json.dumps(blockDict))
            if res.status_code == 200:
                print("sent ok.")
            else:
                print(URL + " responding error " + 404)
                isSuccess = False
        except:
            print("transaction Server " + URL + " is not responding.")
            isSuccess = False

    if isSuccess :
        if mode == 'update' :
            print('Succeed to update')
        else :
            print('Succeed to rollback')
    return isSuccess

#Request transaction details with a value of zero 'commitYN' or the entire transaction details.
def getTxData(chooseData):

    url = DATABASE_TPSVR_IP + "/getTxData/zero"
    if (chooseData == 1) :
        url = DATABASE_TPSVR_IP + "/getTxData/all"
    txData = []
    isSuccess = True
    try :
        print("Trying to get txData from " + DATABASE_TPSVR_IP + "...........")
        res = requests.get(url=url)
        if res.status_code == 200 :
            txData = json.loads(res.text)

            res.close()
        else :
            isSuccess = False
    except:
        isSuccess = False

    return txData, isSuccess

#Mining new blocks.
def mineNewBlock():
    blockList, blockTF = readBlockchain()
    urlData, txTF = getTxData(0)
    timestamp = time.time()
    proof = 0

    if blockTF and txTF :
        if len(blockList) == 0 :
            newBlock, generateSuccessBc = generateGenesisBlock(timestamp, proof)
        else:
            newBlock, generateSuccessBc = generateNextBlock(blockList, urlData, timestamp, proof)
            print(newBlock, generateSuccessBc)

        if generateSuccessBc :
            upResult = updateTx(newBlock, mode = 'update')
        else :
            print("mineNewBlock : Failed to generate NewBlock")
            return

        if upResult :
            wrResult = writeBlockchain(newBlock)
        else :
            print("mineNewBlock : Failed to update txdata on transaction pool table used create block")
            rollBackSuccess = updateTx(newBlock, mode = 'rollback')
            if rollBackSuccess :
                print("mineNewBlock : Succeed to rollback txData")
            return

        if wrResult :
            print("mineNewBlock : Succeed to write new block on table ")
            broadResult = broadcastNewBlock(newBlock)
        else :
            print("mineNewBlock : Fail to write new block on table ")
            rollBackSuccess = updateTx(newBlock, mode='rollback')
            if rollBackSuccess :
                print("mineNewBlock : Succeed to rollback txData")
            return

        if broadResult :
            print("mineNewBlock : Succeed broadcasting new block")
            return
        else :
            print("mineNewBlock : Failed to broadcasting new block")
            syncSuccess = syncBlockChain()

        if (syncSuccess == 1) or (syncSuccess == 2) or (syncSuccess == -2) or (syncSuccess == -1):
            print("mineNewBlock : Succeed to sync all block data")
        else :
            print("mineNewBlock : Failed to sync all block data")
            rollBackSuccess = updateTx(newBlock, mode='rollback')
            if rollBackSuccess :
                print("mineNewBlock : Succeed to rollback txData")
            return
    else :
        print("mineNewBlock : There's no Transaction pool data in Url.")
        return

def mine():
    mineNewBlock()

#Validate blocks.
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
    elif str(block1.merkleHash) != str(block2.merkleHash):
        return False
    return True

#Validate newly generated blocks.
def isValidNewBlock(newBlock, previousBlock):
    if int(previousBlock.index) + 1 != int(newBlock.index):
        print('Indices Do Not Match Up')
        return False
    # 체이닝이 맞는지
    elif previousBlock.currentHash != newBlock.previousHash:
        print("Previous hash does not match")
        return False
    # 해쉬검증
    elif calculateHashForBlock(newBlock) != newBlock.currentHash:
        print("Hash is invalid")
        return False
    elif newBlock.currentHash[0:g_difficulty] != '0' * g_difficulty:
        print("Hash difficulty is invalid")
        return False
    return True

#Validate the validity of the blockchain.
def isValidChain(bcToValidate):
    genesisBlock = []
    bcToValidateForBlock = []

    # Read GenesisBlock
    try:
        blockReader, readSuccess = readBlockchain()
        for line in blockReader:
            block = Block(line[0], line[1], line[2], line[3], line[4], line[5], line[6])
            genesisBlock.append(block)
    except:
        print("file open error in isValidChain")
        return False

    # transform given data to Block object
    for line in bcToValidate:
        # print(type(line))
        # index, previousHash, timestamp, data, currentHash, proof
        block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'],
                      line['proof'], line['merkleHash'])
        bcToValidateForBlock.append(block)

    # if it fails to read block data  from db(csv)
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

#Insert the requested ip address and port number into the node table of the  linked database.
#Ask each server for the requested ip address and port number to synchronize the node tables of each server's database.
def addNode(recievedNode, mode='new'):

    isSuccess = True

    for getNode in recievedNode :
        if mode == 'new':
            newNode = Node(getNode['ip'], str(getNode['port']), "0")
        else:
            newNode = Node(getNode['ip'], str(getNode['port']), str((getNode['tryConnect'])))

    sameNodeFound = False
    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER, passwd=DATABASE_SVR_PW, \
                           database=DATABASE_SVR_NAME, charset='utf8')
    try:
        print("Trying to find new node on database...........")
        with conn.cursor() as cursor:
            sql = "Select ip, port FROM " + DATABASE_ND_TABLE + " WHERE ip = %s AND port = %s"
            cursor.execute(sql, (newNode.ip, newNode.port))
            rows = cursor.fetchall()
            conn.commit()
        if len(rows) != 0:
            print("new node is already existed.")
            sameNodeFound = True
    except:
        print("Failed to access nodelist database.")
        isSuccess = False
    finally:
        conn.close()

    if not sameNodeFound :
        conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                               passwd=DATABASE_SVR_PW, \
                               database=DATABASE_SVR_NAME, charset='utf8')
        try:
            print("Trying to add new node on database...........")
            with conn.cursor() as curs:
                sql = "INSERT INTO " + DATABASE_ND_TABLE + " VALUES (%s,%s,%s)"
                curs.execute(sql, (newNode.ip, newNode.port, newNode.tryConnect))
                conn.commit()
            print('Success to write new node on' + DATABASE_ND_TABLE + ".")
        except:
            print("Failed to access nodelist database.")
            isSuccess = False
        finally:
            conn.close()
    else:
        isSuccess = False

    if mode == 'new' :
        reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
        newNodeList = []
        newNodeList.append(newNode.__dict__)

        serverData = []
        query = "serverList/get"
        URL = DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + "/" + query
        try:
            print("Trying to get serverList from " + DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + "...........")
            print(URL)
            res = requests.get(URL)
            if res.status_code == 200:
                serverData = json.loads(res.text)
                print("sent ok.")
            else:
                print(URL + " responding error " + 404)
                isSuccess = False
        except:
            print("serverlist Server " + URL + " is not responding.")
            isSuccess = False

        for i in serverData:
            if IP_NUMBER == i['ip'] and str(PORT_NUMBER) == i['port']:
                continue
            else:
                URL = "http://" + i['ip'] + ":" + i['port'] + "/postNode/newSvr"
                print(URL)
                try:
                    print("trying send added node to " + i['ip'] + ":" + i['port'] + " in SVR_LIST...........")
                    res = requests.post(URL, headers=reqHeader, data=json.dumps(newNodeList))
                    if res.status_code == 200:
                        print("sent ok.")
                    else:
                        print("Failed to send new node to " + i['ip'] + ":" + i['port'] + " in SVR_LIST >> 404")
                except:
                    print("Failed to send new node to " + i['ip'] + ":" + i['port'] + " in SVR_LIST >> not responding")

    return isSuccess

#Returns all data in the nodelist table in the database.
def readNodes() :
    nodeDictList = []
    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                           passwd=DATABASE_SVR_PW, \
                           database=DATABASE_SVR_NAME)

    sql = "SELECT * FROM " + DATABASE_ND_TABLE
    try :
        with conn.cursor() as curs :
            curs.execute(sql)
            nodeList = curs.fetchall()

            for line in nodeList :
                node = Node(line[0], line[1], line[2])
                nodeDictList.append(node.__dict__)
    except:
        print("Failed to get node data from database.")
    finally:
        conn.close()

    return nodeDictList

#Counts rows in the database.
def row_count():
    try:
        list, readSuccess = readBlockchain()
        return len(list)
    except:
        return 0

#Compare the block data contained in the requested URL with your block data
#and synchronize the data according to the results.
def compareMerge(bcDict):

    bcToValidateForBlock = []
    heldBlock = []

    try:
        blockchainList, readSuccess = readBlockchain()
        heldBlock = blockchainList
    except:
        print("file open error in compareMerge or No database exists")
        return -1

    if len(heldBlock) == 0:
        print("fail to read")
        return -2

    for line in bcDict:

        block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'],
                      line['proof'], line['merkleHash'])

        bcToValidateForBlock.append(block)

    #Compare the requested URL's Genesis block with mine's.
    if not isSameBlock(bcToValidateForBlock[0], heldBlock[0]):
        print('Genesis Block Incorrect')
        return -1

    if not isValidNewBlock(bcToValidateForBlock[-1], heldBlock[-1]):

        #Compare the requested URL's the latest block with my latest's.
        if isSameBlock(heldBlock[-1], bcToValidateForBlock[-1]):
            print('latest block == broadcasted last block, already updated')
            return 2

        #Compare the length of block data
        elif len(bcToValidateForBlock) > len(heldBlock):
            if not isSameBlock(heldBlock[0], bcToValidateForBlock[0]):

                print("Block Information Incorrect #1")
                return -1

            tempBlocks = [bcToValidateForBlock[0]]

            for i in range(1, len(heldBlock)):

                if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                    tempBlocks.append(bcToValidateForBlock[i])
                else:
                    return -1

            for j in range(len(heldBlock), len(bcToValidateForBlock)) :
                tempBlocks.append(bcToValidateForBlock[j])

            writeAllBlockchain(bcToValidateForBlock)
            return 1

        elif len(bcToValidateForBlock) < len(heldBlock):
            tempBlocks = [heldBlock[0]]

            for i in range(1, len(bcToValidateForBlock)):
                if isValidNewBlock(heldBlock[i], tempBlocks[i - 1]):
                    tempBlocks.append(heldBlock[i])
                else:
                    return -1

            print(len(heldBlock))
            for j in range(len(bcToValidateForBlock), len(heldBlock)):
                print(j)
                tempBlocks.append(heldBlock[j])


            print("We have a better chain")
            return 3

        elif len(bcToValidateForBlock) == len(heldBlock) :

            for i in range (len(heldBlock) - 1, 0, -1):

                if float(bcToValidateForBlock[i]['timestamp']) > float(heldBlock[i]['timestamp']) :
                    tempBlocks = [heldBlock[0]]
                    for i in range(1, len(heldBlock)):
                        if isValidNewBlock(heldBlock[i], tempBlocks[i - 1]):
                            tempBlocks.append(heldBlock[i])
                        else:
                            return -1
                    print("We have a better chain")
                    return 3

                elif float(bcToValidateForBlock[i]['timestamp']) < float(heldBlock[i]['timestamp']):
                    tempBlocks = [bcToValidateForBlock[0]]
                    for i in range(1, len(bcToValidateForBlock)):
                        if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                            tempBlocks.append(bcToValidateForBlock[i])
                        else:
                            return -1
                    writeAllBlockchain(bcToValidateForBlock)
                    return 1

            print("Block Information Incorrect")
            return -2

        else:
            print("Block Information Incorrect #2")
            return -1

    else:  # very normal case (ex> we have index 100 and receive index 101 ...)
        tempBlocks = [bcToValidateForBlock[0]]
        for i in range(1, len(bcToValidateForBlock)):
            if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                tempBlocks.append(bcToValidateForBlock[i])
            else:
                print("Block Information Incorrect #2 \n" + tempBlocks.__dict__)
                return -1

        print("new block good")

        # validation
        for i in range(0, len(heldBlock)):
            if isSameBlock(heldBlock[i], bcToValidateForBlock[i]) == False:
                print("Block Information Incorrect #1")
                return -1
        # [START] save it to csv
        writeAllBlockchain(bcToValidateForBlock)
        return 1

#Notifies servers in the list of servers that a new block has been created.
def broadcastNewBlock(block):

    isSuccess = True

    blockDictList = []
    blockDictList.append(block.__dict__)

    query = "serverList/get"
    URL = DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + "/" + query
    try:
        print("Trying to get serverList from " + DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + "...........")
        res = requests.get(URL)
        if res.status_code == 200:
            serverData = json.loads(res.text)
            print("sent ok.")
        else:
            print(URL + " responding error " + 404)
            isSuccess = False
    except:
        print("serverlist Server " + URL + " is not responding.")
        isSuccess = False

    if isSuccess :
        # request.post로 SVR_LIST의 모든 ip에 /validatedBock으로 보낸다.
        reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
        resDictData = {'validationResult': 'abnormal'}

        try:
            for i in serverData :
                if IP_NUMBER == i['ip'] and str(PORT_NUMBER) == i['port']:
                    continue
                else:
                    print("Trying to send blockchain data to " + i['ip'] + " : " + i['port'] + " in SVR_LIST...........")
                    URL = "http://" + i['ip'] + ":" + i['port'] + "/postBlock/validateBlock"
                    print("Trying to send : " + URL)
                    res = requests.post(URL, headers=reqHeader, data=json.dumps(blockDictList))
                    if res.status_code == 200:
                        print("sent ok.")
                        resDictData = json.loads(res.text)
                        print(resDictData)
                    else:
                        print("Failed to send blockchain data to " + i['ip'] + " : " + i['port'] + " in SVR_LIST >> not responding : 404")
                        isSuccess = False
        except:
            print("Failed to send blockchain data in SVR_LIST >> not responding")
            isSuccess = False

            #응답이 abnormal 이라면 블록체인의 채굴에 실패로 간주 한다.

        resultDict = resDictData.get('validationResult', 'abnormal')
        print("current result : " + resultDict)
        if resultDict == 'abnormal' :
            print("Failed to broadcast new block")
            isSuccess = False
        # 응답에 리스트가 []이거나 nomal 이라면  브로드캐스팅에 성공, 채굴을 완료한다.
        else :
            print("Succeed to broadcast new block")

    return isSuccess

#Synchronize my block data with the block data of servers in the list of servers.
#The synchronization process is based on the results of comareMerge executed on the server
#from which the request was sent.
def syncBlockChain() :
    print("Trying to sync blockchain data with SVR_LIST...........")
    blockList, readSuccess = readBlockchain()

    result = 0
    lengthCount = 0

    blockDictList = []

    for block in blockList :
        blockDictList.append(block.__dict__)

    query = "serverList/get"
    URL = DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + "/" + query
    try:
        print("Trying to get serverList from " + DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + "...........")
        print(URL)
        res = requests.get(URL)
        if res.status_code == 200:
            serverData = json.loads(res.text)
            print("sent ok.")
        else:
            print(URL + " responding error " + 404)
            result.append = -1
    except:
        print("serverlist Server " + URL + " is not responding.")
        result -1

    if result == 1:

        reqHeader = {'Content-Type': 'application/json; charset=utf-8'}

        blockData = []
        for i in serverData :
            if IP_NUMBER == i['ip'] and str(PORT_NUMBER) == i['port']:
                continue
            else:
                print("Trying to send blockchain data to " + i['ip'] + " : " + i['port'] + " in SVR_LIST...........")
                URL = "http://" + i['ip'] + ":" + i['port'] + "/postBlock/sync"
                try :
                    res = requests.post(URL, headers=reqHeader, data=json.dumps(blockDictList))
                    if res.status_code == 200:
                        print("sent ok.")
                        resData = json.loads(res.text)

                        if (resData[-1] == "we have a better chain"):

                            resData.pop()

                            if (len(resData) > lengthCount):
                                lengthCount = len(resData)
                                blockData = resData

                            elif (len(resData) == lengthCount):
                                for i in range(len(resData) - 1, 0, -1):

                                    if float(resData[i]['timestamp']) < float(blockData[i]['timestamp']):
                                        lengthCount = len(resData)
                                        blockData = resData
                            if result == 3 or result == 0 :
                                result = 3

                        else:
                            resData = json.loads(res.text)
                            print("resData : " + str(resData[-1]))

                            if resData[-1] =="block chain info incorrect" :
                                result = -2
                            elif resData[-1] == "internal server error" :
                                result = -1
                            elif resData[-1] == "accepted" :
                                result = 1
                            else :
                               result = 2

                    else:
                        print("Failed to send blockchain data to " + i['ip'] + " : " + i['port']
                             + " in SVR_LIST >> not responding : 404")
                        result = -1

                except:
                    print("Failed to send blockchain data to in SVR_LIST >> not responding")
                    result = -1

        if (len(blockData) > 0):
            receivedBlock = []
            for line in blockData:
                block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'],
                              line['currentHash'], \
                              line['proof'], line['merkleHash'])
                receivedBlock.append(block)
            writeAllBlockchain(receivedBlock)
            if result == 3 or result == 0 :
                result = 3

    if result == 1 :
        print("Succeed to sync blockchain")
    return result

#Create blockchain and model list tables in the linked database and
#synchronize tables sequentially with servers in the list of servers for services.
def initSvr():

    #Decide directly whether master or serve.
    isMasterSvr = MASTER
    if isMasterSvr :
        print("server : MASTER mode")
    else :
        print("server : SERVE mode")

    #create blockchain table and nodelist table.
    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                           password=DATABASE_SVR_PW, db=DATABASE_SVR_NAME, charset='utf8')

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

    #Ask to insert your ip address and port number into the server that manages the list of miners.
    serverData = []

    query = "/serverList/add"
    URL = DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + query
    portDict = {"port" : PORT_NUMBER}

    try:
        print("Trying to add my ip and port to serverList : " + DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + "...........")
        res = requests.get(URL, params=portDict)
        if res.status_code == 200:
            serverData = json.loads(res.text)
            print("sent ok.")
        else:
            print(URL + " responding error " + 404)
    except:
        print("serverlist Server " + URL + " is not responding.")

    if serverData[-1] == 'success' :
        print("Suceed regstering my ip and port to serverlist database.")
    elif serverData[-1] == 'exist' :
        print("My ip and port already exist on serverlist database.")
    else :
        print("Failed regstering my ip and port to serverlist database.")

    #Synchronize the table of blockchain and the table of the nodelist sequentially with
    #all servers in the server table of the server list server.
    #The rule is that a server with the largest amount of data has highly reliable data.
    if not isMasterSvr :
        #blockchain table
        myBlockCount = 0

        conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                               password=DATABASE_SVR_PW, \
                               db=DATABASE_SVR_NAME, charset='utf8')

        sql = "SELECT COUNT(*) FROM " + DATABASE_BC_TABLE
        try:
            with conn.cursor() as curs:
                curs.execute(sql)
                myBlockCount = curs.fetchone()

            print("Success to get blockchain rowCount from my database, count >> " + str(myBlockCount[0]))
        except:
            print("Failed to get blockchain rowCount from my database >>" + DATABASE_SVR_IP + " : " + str(
                DATABASE_SVR_PORT) + " : " + DATABASE_SVR_NAME)
        finally:
            conn.close()

        query = "/serverList/get"
        try:
            print("Trying to get serverData from serverlist database...........")
            URL = DATABASE_MINER_LIST_IP + ":" + str(DATABASE_MINER_LIST_PORT) + query
            print("Trying to send : " + URL)
            res = requests.get(URL)

            if res.status_code == 200:
                print("sent ok.")
                resServerDictData = json.loads(res.text)
                print(str(resServerDictData))
            else:
                print("Failed to access serverlist >> not responding : 404")
        except:
            print("Failed to access serverlist >> not responding")

        if myBlockCount[0] == 0:

            maxBlockCount = 0

            try:
                blocklist = []

                for i in resServerDictData:
                    if IP_NUMBER == i['ip'] and str(PORT_NUMBER) == i['port'] :
                        continue
                    else :
                        print("Trying to get blockchain data from table on " + i['ip'] + ":" + i['port'] + "...........")
                        URL = "http://" + i['ip'] + ":" + str(i['port']) + "/block/getBlockData"
                        res = requests.get(URL)
                        if res.status_code == 200:
                            print("Success to get blockchain data")
                            resBlockDictData = json.loads(res.text)

                            if resBlockDictData[-1] == "no data exists" :
                                resBlockDictData = []

                            if len(resBlockDictData) > maxBlockCount:

                                for line in resBlockDictData:
                                    block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'],
                                                  line['currentHash'],
                                                  line['proof'], line['merkleHash'])

                                    blocklist.append(block)

                                writeAllBlockchain(blocklist)

                                maxBlockCount = len(blocklist)
                        else:
                            print("Failed to get blockchain data from " + i['ip'] + ":" + str(i['port']))
            except:
                print("Failed to access serverlist >> not responding")
        else :
            pass

        #nodelist table
        myNnodeCount = 0

        conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT, user=DATABASE_SVR_USER,
                               password=DATABASE_SVR_PW, \
                               db=DATABASE_SVR_NAME, charset='utf8')

        sql = "SELECT COUNT(*) FROM " + DATABASE_ND_TABLE
        try:

            with conn.cursor() as curs:
                curs.execute(sql)
                myNnodeCount = curs.fetchone()

            print("Success to get node rowCount from my database, count >> " + str(myNnodeCount[0]))
        except:
            print("Failed to get nodelist from my database >> " + DATABASE_SVR_IP + " : " + str(DATABASE_SVR_PORT) + " : " + DATABASE_SVR_NAME)
        finally:
            conn.close()


        if myNnodeCount[0] == 0 :

            maxNodeCount = 0

            try:
                nodeList = []

                for i in resServerDictData:
                    if IP_NUMBER == i['ip'] and str(PORT_NUMBER) == i['port'] :
                        continue
                    else :
                        print("Trying to get node data from table on " + i['ip'] + ":" + i['port'] + "...........")
                        URL = "http://" + i['ip'] + ":" + i['port'] + "/node/getNode"
                        res = requests.get(URL)

                        if res.status_code == 200:
                            print("Success to get node data")
                            resNodeDictData = json.loads(res.text)

                            for line in resNodeDictData:
                                node = Node(line[0], line[1], line[2])

                                nodeList.append(node)

                                if len(nodeList) >= maxNodeCount:
                                    maxNodeCount = len(nodeList)

                                    conn = pymysql.connect(host=DATABASE_SVR_IP, port=DATABASE_SVR_PORT,
                                                           user=DATABASE_SVR_USER,
                                                           passwd=DATABASE_SVR_PW, \
                                                           database=DATABASE_SVR_NAME, charset='utf8')

                                    try:
                                        for node in nodeList:
                                            print("Trying to write node data on my database...........")
                                            with conn.cursor() as curs:
                                                sql = "INSERT INTO " + DATABASE_ND_TABLE + " VALUES (%s,%s,%s)"
                                                curs.execute(sql, (node.ip, node.port, node.tryConnect))
                                                conn.commit()
                                        print("Success to write node data on my database")
                                    except:
                                        print("Failed to write node data on my database")
                                    finally:
                                        conn.close()
                        else:
                            print("Failed to get node data from " + i['ip'] + ":" + i['port'])
            except:
                print("Failed to access serverlist >> not responding")

        else:
            pass

        print("initSvr setting Done.........")

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

            if None != re.search('/block/getBlockData', self.path):

                blockList, readSuccess = readBlockchain()

                if blockList == [] and readSuccess:

                    print("No Block Exists")

                    data.append("no data exists")
                else:
                    for i in blockList:
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
                queryDict =[{'ip' : self.client_address[0],'port':self.client_address[1]}]

                res = addNode(queryDict, mode = 'new')

                if res == 1:
                    importedNodes = readNodes()
                    data = importedNodes
                    print("node added okay")

                elif res == 0:
                    data.append("caught exception while saving")

                elif res == -1:
                    importedNodes = readNodes()
                    data = importedNodes
                    data.append("requested node is already exists")

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            elif None != re.search('/node/getNode', self.path):
                importedNodes = readNodes()
                data = importedNodes
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

        else:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
        # ref : https://mafayyaz.wordpress.com/2013/02/08/writing-simple-http-server-in-python-with-rest-and-json/

    def do_POST(self):

        if None != re.search('/postBlock/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/postBlock/validateBlock', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                # print(ctype) #print(pdict)

                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDictList = json.loads(receivedData)  # load your str into a list #print(type(tempDict))

                    for tempDict in tempDictList :
                        newBlock = Block(tempDict['index'], tempDict['previousHash'], tempDict['timestamp'], tempDict['data'], tempDict['currentHash'], \
                                         tempDict['proof'], tempDict['merkleHash'])


                    blockList, readSuccess = readBlockchain()

                    if len(blockList) > 0:
                        previousBlock = getLatestBlock(blockList)

                        if isValidNewBlock(newBlock, previousBlock) == True:
                            tempDict['validationResult'] = 'normal'
                            result = writeBlockchain(newBlock)

                            if result == 1 :
                                print("Succeed to insert new block on database.")
                                tempDict['validationResult'] = 'normal'
                            else :
                                print("Failed to insert new block on database.")
                                tempDict['validationResult'] = 'abnormal'
                        else:
                            tempDict['validationResult'] = 'abnormal'
                    else :
                        result = writeBlockchain(newBlock)

                        if result == 1:
                            print("Succeed to insert new block on database.")
                            tempDict['validationResult'] = 'normal'
                        else:
                            print("Failed to insert new block on database.")
                            tempDict['validationResult'] = 'abnormal'

                    self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

            if None != re.search('/postBlock/sync', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])

                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    tempDict = json.loads(receivedData)  # load your str into a list
                    print(tempDict)
                    res = compareMerge(tempDict)
                    if res == -2:  # internal error
                        tempDict.append("block chain info incorrect")
                    elif res == -1:  # block chain info incorrect
                        tempDict.append("internal server error")
                    elif res == 1:  # normal
                        tempDict.append("accepted")
                    elif res == 2:  # identical
                        tempDict.append("already updated")
                    elif res == 3:  # we have a longer chain
                        # 3을 받으면 tempDict를 초기화 하여 내 블록데이터 넣고 전송
                        blockList, isSuccess = readBlockchain()
                        tempDict = []
                        for line in blockList:
                            tempDict.append(line.__dict__)
                        tempDict.append("we have a better chain")

                    self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

        elif None != re.search('/postNode/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/postNode/newSvr', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                print("get response")
                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    tempDict = json.loads(receivedData)  # load your str into a list
                    if addNode(tempDict, mode='sync') == 1:
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else:
                        tempDict.append("error : cannot add node to sync")
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