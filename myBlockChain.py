
import hashlib
import time
import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import json
import re
from urllib.parse import urlparse
import threading
import cgi
import uuid
import requests
import pandas as pd
from sqlalchemy import create_engine
from enum import Enum


database = 'postgresql://postgres:postgres@127.0.0.1:5432/postgres'
engine1 = create_engine(database)

PORT_NUMBER = 8666
g_txDatabaseName = "db_txdata"
g_bcDatabaseName = "db_blockchain"
g_nodeDatabaseName = "db_node"
g_receiveNewBlock = "/node/receiveNewBlock"
g_difficulty = 4
g_maximumTry = 100
g_nodeList = {'trustedServerAds': '8666'}  # trusted server list, should be checked manually


class Block(Enum):
    index = 0
    previoushash = 1
    timestamp = 2
    data = 3
    currenthash = 4
    proof = 5

class TxData(Enum):
    commityn = 0
    sender = 1
    amount = 2
    receiver = 3
    uuid_str = 4

class Node(Enum):
    ip = 0
    port = 1

def createtable(engine):
    try :
        engine.execute("CREATE TABLE db_blockchain (index varchar(100),\
                                    previoushash varchar(100),\
                                    timestamp varchar(100),\
                                    data varchar(100),\
                                    currenthash varchar(100),\
                                    proof varchar(100));")
        engine.execute("CREATE TABLE db_txdata (commityn integer,\
                                    sender varchar(100),\
                                    amount varchar(100),\
                                    receiver varchar(100),\
                                    uuid_str varchar(100));")
        engine.execute("CREATE TABLE db_node (ip varchar(100),\
                                    port varchar(100),\
                                    failnum varchar(100));")
        return "success create table"

    except :
        return "already have table"

def toJSON(self):
    return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


def blockList(index, previousHash, timestamp, data, currentHash, proof):
    return [index, previousHash, timestamp, data, currentHash, proof]


def txDataList(commitYN, sender, amount, receiver, uuid):
    return [commitYN, sender, amount, receiver, uuid]


def generateGenesisBlock():
    print("generateGenesisBlock is called")
    timestamp = time.time()
    print("time.time() => %f \n" % timestamp)
    tempHash = calculateHash('0', '0', timestamp, "Genesis Block", '0')
    print(tempHash)
    return blockList('0', '0', str(timestamp), "Genesis Block", tempHash, '0')


def calculateHash(index, previousHash, timestamp, data, proof):
    value = str(index) + str(previousHash) + str(timestamp) + str(data) + str(proof)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())


def calculateHashForBlock(block):
    return calculateHash(block[Block.index.value], block[Block.previoushash.value], block[Block.timestamp.value], block[Block.data.value], block[Block.proof.value])


def getLatestBlock(blockchain):
    return blockchain[len(blockchain) - 1]


def generateNextBlock(blockchain, blockData, timestamp, proof):
    previousBlock = blockchain
    nextindex = str(int(previousBlock[Block.index.value]) + 1)
    nextTimestamp = timestamp
    nextHash = calculateHash(nextindex, previousBlock[Block.currenthash.value], nextTimestamp, blockData, proof)

    return blockList(nextindex, previousBlock[Block.currenthash.value], nextTimestamp, blockData, nextHash, proof)


def writeBlockchain(blockchain):
    # lastBlock = blockchain[-1]
    # 테이블 컬럼명 가져옴
    get_df_blockchain = (pd.read_sql("select * from {}".format(g_bcDatabaseName), con=engine1))
    columnList = list(get_df_blockchain)
    df_blcokchainList = get_df_blockchain.values.tolist()
    # lastBlock = df_blcokchainList[-1]

    try:
        df_blockchain = pd.DataFrame(blockchain, columns=columnList)
        # 디버깅용
        # print(df_blockchain)
        df_blockchain.to_sql(name=g_bcDatabaseName, con=engine1, index=False, if_exists='replace')

        if int(df_blcokchainList[-1][Block.index.value]) + 1 != int(blockchain[-1][Block.index.value]):
            print("index sequence mismatch")
            if int(df_blcokchainList[-1][Block.index.value]) == int(blockchain[-1][Block.index.value]):
                print("db(csv) has already been updated")
            return
    except(Exception) as e:
        print(e)
        print("file open error in check current db(csv) \n or maybe there's some other reason")
        pass
        # return

    blockUpdate = False
    for block in blockchain:
        updateTx(block)
        blockUpdate = True

    if (blockUpdate):
        print('Blockchain written to DB.')
        print('Broadcasting new block to other nodes')
        broadcastNewBlock(blockchain)


def readBlockchain(blockchainDB, mode='internal'):
    print("readBlockchain")
    # a = pd.read_sql("select * from {}".format(blockchainDB), engine1)
    # print(a)

    get_df_blockchain = pd.read_sql("select * from {}".format(blockchainDB), engine1)
    importedBlockchain = get_df_blockchain.values.tolist()
    print("Pulling blockchain from DB...")
    if len(importedBlockchain) > 0:
        return importedBlockchain

    print(get_df_blockchain)
    if importedBlockchain == None:
        print("ERROR")
        return None

    if mode == 'internal':
        genesisBlock = generateGenesisBlock()
        importedBlockchain.append(genesisBlock)
        # print(blockchain) # genesisBlock 확인가능
        writeBlockchain(importedBlockchain)
        return genesisBlock
    else:
        return None


def updateTx(blockData):
    phrase = re.compile(
        r"\w+[-]\w+[-]\w+[-]\w+[-]\w+")  # [6b3b3c1e-858d-4e3b-b012-8faac98b49a8]UserID hwang sent 333 bitTokens to UserID kim.
    matchList = phrase.findall(blockData[Block.data.value])

    if len(matchList) == 0:
        print("No Match Found! " + str(blockData[Block.data.value]) + "block idx: " + str(blockData[Block.index.value]))
        return

    get_df_txData = pd.read_sql("select * from {}".format(g_txDatabaseName), con=engine1)
    # df columnTitle
    columnTitle = list(get_df_txData)

    txdataList = get_df_txData.values.tolist()

    for tx in txdataList:
        if tx[TxData.uuid_str.value] in matchList:
            print('updating row : ', tx[TxData.uuid_str.value])
            tx[TxData.commityn.value] = 1

    new_df_txdataList = pd.DataFrame(data=txdataList, columns=columnTitle)

    new_df_txdataList.to_sql(name=g_txDatabaseName, con=engine1, index=False, if_exists='replace')

    print('txData updated')


def writeTx(txRawData):
    #   txData
    get_df_txData = pd.read_sql("select * from {}".format(g_txDatabaseName), engine1)

    columnTitle = list(get_df_txData)

    txdataList = pd.DataFrame(txRawData, columns=columnTitle)
    print(txdataList)
    try:
        txdataList.to_sql(name=g_txDatabaseName, con=engine1, index=False, if_exists="append")
    except (Exception) as e:
        print(e)
    print('txData written to DB.')
    return 1


def readTx(txFilePath):
    print("readTx")
    importedTx = []
    # txData in DB -> df
    get_df_txData = pd.read_sql("select * from {}".format(txFilePath), con=engine1)
    print(get_df_txData)
    # df -> list
    txdataList = get_df_txData.values.tolist()
    print("Pulling txData from DB...")
    for row in txdataList:
        if row[TxData.commityn.value] == 0:  # find unmined txData
            line = txDataList(row[TxData.commityn.value], row[TxData.sender.value], row[TxData.amount.value], row[TxData.receiver.value], row[TxData.uuid_str.value])
            importedTx.append(line)

    return importedTx


def getTxData():
    strTxData = ''
    importedTx = readTx(g_txDatabaseName)
    if len(importedTx) > 0:
        for i in importedTx:
            transaction = "[{}] UserID {} sent {} bitTokens to UserID {}.".format(i[TxData.uuid_str.value], i[TxData.sender.value], i[TxData.amount.value],
                                                                                  i[TxData.receiver.value])
            print(transaction)
            strTxData += transaction

    return strTxData


def mineNewBlock(difficulty=g_difficulty, blockchainPath=g_bcDatabaseName):
    blockchain = readBlockchain(blockchainPath)
    strTxData = getTxData()
    if strTxData == '':
        print('No TxData Found. Mining aborted')
        return

    timestamp = time.time()
    proof = 0
    newBlockFound = False

    print('Mining a block...')

    while not newBlockFound:
        newBlockAttempt = generateNextBlock(blockchain[-1], strTxData, timestamp, proof)
        if newBlockAttempt[Block.currenthash.value][0:difficulty] == '0' * difficulty:
            stopTime = time.time()
            timer = stopTime - timestamp
            print('New block found with proof', proof, 'in', round(timer, 2), 'seconds.')
            newBlockFound = True
        else:
            proof += 1
    blockchain.append(newBlockAttempt)
    writeBlockchain(blockchain)


def mine():  # 코드 길이 조정
    mineNewBlock()


def isSameBlock(block1, block2):
    if str(block1[Block.index.value]) != str(block2[Block.index.value]):
        return False
    elif str(block1[Block.previoushash.value]) != str(block2[Block.previoushash.value]):
        return False
    elif str(block1[Block.timestamp.value]) != str(block2[Block.timestamp.value]):
        return False
    elif str(block1[Block.data.value]) != str(block2[Block.data.value]):
        return False
    elif str(block1[Block.currenthash.value]) != str(block2[Block.currenthash.value]):
        return False
    elif str(block1[Block.proof.value]) != str(block2[Block.proof.value]):
        return False
    return True


def isValidNewBlock(newBlock, previousBlock):
    if int(previousBlock[Block.index.value]) + 1 != int(newBlock[Block.index.value]):
        print('Indices Do Not Match Up')
        return False
    elif previousBlock[Block.currenthash.value] != newBlock[Block.previoushash.value]:
        print("Previous hash does not match")
        return False
    elif calculateHashForBlock(newBlock) != newBlock[Block.currenthash.value]:
        print("Hash is invalid")
        return False
    elif newBlock[Block.currenthash.value][0:g_difficulty] != '0' * g_difficulty:
        print("Hash difficulty is invalid")
        return False
    return True


def newtx(txToMining):
    newtxData = []  # tx동시성 처리 , 새로운 블록에서 예외처리
    # transform given data to txData object
    print(len(txToMining))

    # if len(txToMining) == 1:
    try:
        for line in txToMining:
            # print(line[0],line[1],line[2])
            tx = txDataList(0, line['sender'], line['amount'], line['receiver'], str(uuid.uuid4()))
            newtxData.append(tx)
    # else:
    #     return -2
    except Exception as e:
        print(e)

    # limitation check : max 5 tx
    if len(newtxData) > 5:
        print('number of requested tx exceeds limitation')
        return -1
    # txWrite = writeTx(newtxData)

    if writeTx(newtxData) == 0:
        print("file write error on txData")
        return -2
    return 1


def isValidChain(bcToValidate):
    bcToValidateForBlock = []

    # Read GenesisBlock
    try:
        get_df_blockchain = pd.read_sql("select * from {}".format(g_bcDatabaseName), con=engine1)

        importedBlockchain = get_df_blockchain.values.tolist()


    except:
        print("DB open error in isValidChain")
        return False

    # transform given data to Block object
    for line in bcToValidate:
        # print(type(line))
        # index, previousHash, timestamp, data, currentHash, proof
        block = blockList(line[Block.index.value], line[Block.previoushash.value], line[Block.timestamp.value], line[Block.data.value], line[Block.currenthash.value], line[Block.proof.value])
        bcToValidateForBlock.append(block)

    # if it fails to read block data  from db(csv)
    if not importedBlockchain:
        print("fail to read genesisBlock")
        return False

    # compare the given data with genesisBlock
    if not isSameBlock(bcToValidateForBlock[0], importedBlockchain[0]):
        print('Genesis Block Incorrect')
        return False

    for i in range(0, len(bcToValidateForBlock)):
        if isSameBlock(importedBlockchain[i], bcToValidateForBlock[i]) == False:
            return False

    return True


def addNode(queryStr):
    # save
    previousList = []
    nodeList = []
    nodeList.append([queryStr[Node.ip.value], queryStr[Node.port.value], 0])  # ip, port, # of connection fail

    try:
        get_df_nodeData = pd.read_sql("select * from {}".format(g_nodeDatabaseName), con=engine1)
        get_nodeDataList = get_df_nodeData.values.tolist()
        if len(get_nodeDataList) == 0:
            #  1st create db_node
            try:
                columnTitle = list(get_df_nodeData)
                df_nodeList = pd.DataFrame(nodeList, columns=columnTitle)
                df_nodeList.to_sql(name=g_nodeDatabaseName, con=engine1, index=False, if_exists="append")
                print('new node written to nodelist.csv.')
                return 1
            except Exception as ex:
                print(ex)
                return 0

        for row in get_nodeDataList:
            if row:
                if row[0] == queryStr[Node.ip.value] and row[1] == queryStr[Node.ip.value]:
                    print("requested node is already exists")
                    nodeList.clear()
                    return -1
                else:
                    nodeList.append(row)

                columnTitle = list(get_df_nodeData)
                df_nodeList = pd.DataFrame(nodeList, columns=columnTitle)
                df_nodeList.to_sql(name=g_nodeDatabaseName, con=engine1, index=False, if_exists="replace")
                print('new node written to nodelist.csv.')

    except Exception as e:
        print(e)


def readNodes(filePath):
    print("read Nodes")

    df_node = pd.read_sql("select * from {}".format(filePath), con=engine1)
    df_node_list = df_node.values.tolist()

    print("Pulling txData from DB...")

    return df_node_list


def broadcastNewBlock(blockchain):
    # newBlock  = getLatestBlock(blockchain) # get the latest block
    importedNodes = readNodes(g_nodeDatabaseName)  # get server node ip and port
    get_df_nodeData = pd.read_sql("select * from {}".format(g_nodeDatabaseName), con=engine1)
    columnTitle = list(get_df_nodeData)
    reqHeader = {'Content-Type': 'application/json; charset=utf-8'}
    nodeDataList = []

    if len(importedNodes) > 0:
        for node in importedNodes:
            try:
                URL = "http://" + node[0] + ":" + node[1] + g_receiveNewBlock  # http://ip:port/node/receiveNewBlock
                res = requests.post(URL, headers=reqHeader, data=json.dumps(blockchain))
                if res.status_code == 200:
                    print(URL + " sent ok.")
                    print("Response Message " + res.text)
                else:
                    print(URL + " responding error " + res.status_code)

            except:
                print(URL + " is not responding.")
                if int(node[2]) > g_maximumTry:
                    print(node[0] + ":" + node[1] + " deleted from node list because of exceeding the request limit")
                else:
                    node[2] = int(node[2]) + 1

            nodeDataList.append(node)
        df_nodeDataList = pd.DataFrame(data=nodeDataList, columns=columnTitle)
        df_nodeDataList.to_sql(name=g_nodeDatabaseName, con=engine1, index=False, if_exists="replace")


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
        get_df_blockchain = pd.read_sql("select * from {}".format(g_bcDatabaseName), con=engine1)

        importedBlockchain = get_df_blockchain.values.tolist()

    except:
        print("file open error in compareMerge or No database exists")
        print("call initSvr if this server has just installed")
        return -2

    # if it fails to read block data  from db(csv)
    if len(importedBlockchain) == 0:
        print("fail to read")
        return -2

    # transform given data to Block object
    for line in bcDict:
        block1 = [line[Block.index.value], line[Block.previoushash.value], line[Block.timestamp.value], line[Block.data.value], line[Block.currenthash.value], line[Block.proof.value]]
        bcToValidateForBlock.append(block1)

    # compare the given data with genesisBlock
    if not isSameBlock(bcToValidateForBlock[0], importedBlockchain[0]):
        print('Genesis Block Incorrect')
        return -1

    # check if broadcasted new block,1 ahead than > last held block

    if isValidNewBlock(bcToValidateForBlock[-1], importedBlockchain[-1]) == False:

        # latest block == broadcasted last block
        if isSameBlock(importedBlockchain[-1], bcToValidateForBlock[-1]) == True:
            print('latest block == broadcasted last block, already updated')
            return 2
        # select longest chain
        elif len(bcToValidateForBlock) > len(importedBlockchain):
            # validation
            if isSameBlock(importedBlockchain[0], bcToValidateForBlock[0]) == False:
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
                blockList = [block[Block.index.value], block[Block.previoushash.value], str(block[Block.timestamp.value]), block[Block.data.value],
                             block[Block.currenthash.value], block[Block.proof.value]]
                blockchainList.append(blockList)

            columnTitle = list(get_df_blockchain)

            df_blockchainList = pd.DataFrame(blockchainList, columns=columnTitle)
            df_blockchainList.to_sql(name=g_bcDatabaseName, con=engine1, index=False, if_exists="replace")
            # [END] save it to csv
            return 1
        elif len(bcToValidateForBlock) < len(importedBlockchain):
            # validation
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
                print("Block Information Incorrect #2 " + tempBlocks)
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
            blockList = [block[Block.index.value], block[Block.previoushash.value], str(block[Block.timestamp.value]), block[Block.data.value],
                         block[Block.currenthash.value], block[Block.proof.value]]
            blockchainList.append(blockList)

        columnTitle = list(get_df_blockchain)

        df_blockchainList = pd.DataFrame(blockchainList, columns=columnTitle)
        df_blockchainList.to_sql(name=g_bcDatabaseName, con=engine1, index=False, if_exists="replace")
        # [END] save it to csv
        return 1


def initSvr():
    print("init Server")
    # 1. check if we have a node list file
    last_line_number = row_count(g_nodeDatabaseName)
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
    last_line_number = row_count(g_bcDatabaseName)
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
                    # print(type(line))
                    # index, previousHash, timestamp, data, currentHash, proof
                    block = [line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'],
                             line['proof']]
                    blockchainList.append(block)
                try:
                    with open(g_bcDatabaseName, "w", newline='') as file:
                        writer = csv.writer(file)
                        writer.writerows(blockchainList)
                except Exception as e:
                    print("file write error in initSvr() " + e)

    return 1


# This class will handle any incoming request from
# a browser
class myHandler(BaseHTTPRequestHandler):

    # Handler for the GET requests
    def do_GET(self):
        data = []  # response json data

        # 테이블 생성
        if None != re.search('/create/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data.append(createtable(engine1))
            self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))
        # print(re.search('/block/*', self.path))

        elif None != re.search('/block/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/block/getBlockData', self.path):
                # TODO: range return (~/block/getBlockData?from=1&to=300) -> 개선과제
                # queryString = urlparse(self.path).query.split('&')

                block = readBlockchain(g_bcDatabaseName, mode='external')

                if block == None:
                    print("No Block Exists")
                    data.append("no data exists")
                else:
                    for i in block:
                        data.append(i)

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            elif None != re.search('/block/generateBlock', self.path):  # 일단 여기 generateBlock입력
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
                print("client ip : " + self.client_address[0] + " query ip : " + queryStr[Node.ip.value])
                if self.client_address[0] != queryStr[Node.ip.value]:
                    data.append("your ip address doesn't match with the requested parameter")
                else:
                    res = addNode(queryStr)
                    if res == 1:
                        importedNodes = readNodes(g_nodeDatabaseName)
                        data = importedNodes
                        print("node added okay")
                    elif res == 0:
                        data.append("caught exception while saving")
                    elif res == -1:
                        importedNodes = readNodes(g_nodeDatabaseName)
                        data = importedNodes
                        data.append("requested node is already exists")
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))
            elif None != re.search('/node/getNode', self.path):
                importedNodes = readNodes(g_nodeDatabaseName)
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
            self.send_header('Content-Type', 'application/json')

            self.end_headers()

            if None != re.search('/block/validateBlock/*', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])  # 튜플 형식으로 content-type이 key

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
                try:
                    ctype, pdict = cgi.parse_header(self.headers['content-type'])

                    print(ctype)
                    print(pdict)
                    if ctype == 'application/json':
                        content_length = int(self.headers['Content-Length'])
                        post_data = self.rfile.read(content_length)
                        receivedData = post_data.decode('utf-8')
                        tempDict = json.loads(receivedData)  # tempDict에 key:value 그리고 리스트 저장

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
                except:
                    print("ctype None")
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
                    tempDict.append("internal server error")
                elif res == -1:  # block chain info incorrect
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

