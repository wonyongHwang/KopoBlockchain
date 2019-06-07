'''
Our group changed all file writing and reading systems to work in conjunction with DB.
In addition, a user table was added within the DB to manage the name, key, and balance of participants in the transaction.
Up to five transactions can be stacked, and the transmission and reception of the amount was set to be valid only after the block was mined, and the miner can get mine reward.
And the elements through postman that send a request and receive a response were configured to be processed by HTML.
'''

import hashlib
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import json
import re
from urllib.parse import parse_qs
import threading
import cgi
import uuid

import pandas as pd
from sqlalchemy import create_engine, types
import cx_Oracle as oci # for connect Oracle Database

import codecs
from random import *


# 20190605 DongJoon Kim Parameters Required for Oracle Connections. Table name, Columns as global variables.
PORT_NUMBER = 8097
db_ip = '192.168.110.3'
db_port = '1522'
db_serviceName = 'xe'
db_id = 'DJ2019'
db_pw = 'DJ2019'

db_userTableName = 'BPS_USERS'
db_userTableColumns = ('USERID', 'USERKEY', 'BALANCE', 'USABLE_AMOUNT')
db_blockTableName = 'BPS_BLOCK'
db_blockTableColumns = ('BLOCKINDEX', 'PREVIOUSHASH', 'TIMESTAMP', 'DATA', 'CURRENTHASH', 'PROOF')
db_txTableName = 'BPS_TXDATA'
db_txTableColumns = ('COMMIT_YN', 'SENDER', 'AMOUNT', 'RECEIVER', 'UUID')

g_difficulty = 1

count = 0
count2 = 0
mineSuccess = False


class Block:

    def __init__(self, index, previousHash, timestamp, data, currentHash, proof):
        self.index = index
        self.previousHash = previousHash
        self.timestamp = timestamp
        self.data = data
        self.currentHash = currentHash
        self.proof = proof

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

class txData:

    def __init__(self, commitYN, sender, amount, receiver, uuid):
        self.commitYN = commitYN
        self.sender = sender
        self.amount = amount
        self.receiver = receiver
        self.uuid = uuid

# 20190605 DongJoon Kim Query making a table.
def makeCreateTableQuery(tableName, columns):
    print('\tFunction "makeCreateTableQuery" executed')

    if (tableName == 'BPS_BLOCK'):
        createTableQuery = "CREATE TABLE BPS_BLOCK(\
        %s VARCHAR2 (100) NOT NULL, \
        %s VARCHAR2 (64) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        %s VARCHAR2 (500) NOT NULL, \
        %s VARCHAR2 (64) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        CONSTRAINTS PK_BPS_BLOCK PRIMARY KEY(BLOCKINDEX) \
        )" % columns

    if (tableName == 'BPS_TXDATA'):
        createTableQuery = "CREATE TABLE BPS_TXDATA(\
        %s VARCHAR2 (1) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        CONSTRAINTS PK_BPS_TXDATA PRIMARY KEY(UUID) \
        )" % columns

    if (tableName == 'BPS_USERS'):
        createTableQuery = "CREATE TABLE BPS_USERS(\
        %s VARCHAR2 (100) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        %s VARCHAR2 (100) NOT NULL, \
        CONSTRAINTS PK_BPS_USERS PRIMARY KEY(USERKEY) \
        )" % columns

    return createTableQuery

# 20190605 DongJoon Kim Query dropping a table.
def makeDropTableQuery(tableName):
    dropTableQuery = 'DROP TABLE %s' % tableName
    return dropTableQuery

# 20190605 DongJoon Kim Updating Query as "Update {TableName} set {Value} where {Condition}".
# Also, Completing that are ‘(‘ , ‘=‘, ‘or’ and ‘and’ by Using For loop in the Query.
def makeUpdateQuery(tableName, setValue, whereCondition):
    setValueInput = ''
    for key, value in setValue.items():
        setValueInput += str(key)
        setValueInput += ' = '
        if (isNumber(value)):
            setValueInput += "%s" % str(value)
        else:
            setValueInput += "'%s'" % str(value)
        setValueInput += ', '
    setValueInput = setValueInput.rstrip(', ')

    whereConditionInput = ''
    for key, value in whereCondition.items():
        if (type(value) == list):
            whereConditionInput += '('
            for eachValue in value:
                whereConditionInput += str(key)
                whereConditionInput += ' = '
                if (isNumber(eachValue)):
                    whereConditionInput += str(eachValue)
                else:
                    whereConditionInput += "'%s'" % str(eachValue)
                whereConditionInput += ' OR '
            whereConditionInput = whereConditionInput.rstrip(' OR ')
            whereConditionInput += ')'
        else:
            whereConditionInput += str(key)
            whereConditionInput += ' = '
            if (isNumber(value)):
                whereConditionInput += str(value)
            else:
                whereConditionInput += "'%s'" % str(value)
        whereConditionInput += ' AND '
    whereConditionInput = whereConditionInput.rstrip(' AND ')
    updateQuery = 'UPDATE %s SET %s WHERE %s' % (tableName, setValueInput, whereConditionInput)
    return updateQuery

# 20190605 DongJoon Kim Inserting Data in the Oracle DB Server.
def insertData(tableName, **kwargs):
    connectComplete = False
    cursorComplete = False

    try:
        connectInfo = db_id + '/' + db_pw + '@' + db_ip + ':' + db_port + '/' + db_serviceName
        oracleConnection = oci.connect(connectInfo)
        connectComplete = True
        oracleCursor = oracleConnection.cursor()
        cursorComplete = True

        detailInsert = ''
        for (key, value) in kwargs.items():
            detailInsert += ':%s, ' % str(key)
        detailInsert = detailInsert.rstrip(', ')
        insertQuery = 'INSERT INTO %s VALUES(%s)' % (tableName, detailInsert)
        oracleCursor.execute(insertQuery, kwargs)
        oracleConnection.commit()

        oracleCursor.close()
        oracleConnection.close
        return True
    except:
        if (cursorComplete == False):
            oracleCursor.close()
        if (connectComplete == False):
            oracleConnection.close
        return False

# 20190605 DongJoon Kim Selecting Data in the Oracle DB Server.
# Also Completing that are ‘(‘ , ‘=‘, ‘or’ and ‘and’ by Using For loop in the Query.
def selectTable(tableName, columns, whereCondition=None):
    connectInfo = 'oracle+cx_oracle://%s:%s@%s:%s/%s' % (db_id, db_pw, db_ip, db_port, db_serviceName)
    engine = create_engine(connectInfo)

    if (whereCondition != None):
        whereConditionInput = ''
        for key, value in whereCondition.items():
            if (type(value) == list):
                whereConditionInput += '('
                for eachValue in value:
                    whereConditionInput += str(key)
                    whereConditionInput += ' = '
                    if (isNumber(eachValue)):
                        whereConditionInput += str(eachValue)
                    else:
                        whereConditionInput += "'%s'" % str(eachValue)
                    whereConditionInput += ' OR '
                whereConditionInput = whereConditionInput.rstrip(' OR ')
                whereConditionInput += ')'
            else:
                whereConditionInput += str(key)
                whereConditionInput += ' = '
                if (isNumber(value)):
                    whereConditionInput += str(value)
                else:
                    whereConditionInput += "'%s'" % str(value)
            whereConditionInput += ' AND '
        whereConditionInput = whereConditionInput.rstrip(' AND ')
        selectQuery = 'SELECT * FROM %s WHERE %s' % (tableName, whereConditionInput)
    else:
        selectQuery = 'SELECT * FROM %s' % tableName

    try:
        resultData = pd.read_sql_query(selectQuery, engine)
    except:
        print('Table select error, There are no table named "%s" in db. \n It will be created' % tableName)
        createTable(tableName, columns)
        resultData = pd.read_sql_query(selectQuery, engine)
    resultData.rename(columns=lambda x: x.strip().upper(), inplace=True)
    return resultData

# 20190605 DongJoon Kim After connecting with DB, making Table in the DB through createTableQuery
def createTable(tableName, columns):

    connectComplete = False
    cursorComplete = False

    try:
        connectInfo = db_id + '/' + db_pw + '@' + db_ip + ':' + db_port + '/' + db_serviceName
        oracleConnect = oci.connect(connectInfo)
        connectComplete = True
        oracleCursor = oracleConnect.cursor()
        cursorComplete = True

        createTableQuery = makeCreateTableQuery(tableName, columns)
        oracleCursor.execute(createTableQuery)
        oracleConnect.commit()
        oracleCursor.close()
        oracleConnect.close
        return True

    except:
        if (cursorComplete == True):
            oracleCursor.close()
        if (connectComplete == True):
            oracleConnect.close
        return False

# 20190605 DongJoon Kim When entering data into OralceDB, because index is not in order.
# So Every time new data comes in DB. Table is created every time through replaceTable.
# The function dropTable and createTable in this.
def replaceTable(tableName, columns):
    connectComplete = False
    cursorComplete = False

    try:
        connectInfo = db_id + '/' + db_pw + '@' + db_ip + ':' + db_port + '/' + db_serviceName
        oracleConnect = oci.connect(connectInfo)
        connectComplete = True
        oracleCursor = oracleConnect.cursor()
        cursorComplete = True

        dropTableQuery = makeDropTableQuery(tableName)
        try:
            oracleCursor.execute(dropTableQuery)
        except:
            pass
        createTableQuery = makeCreateTableQuery(tableName, columns)
        oracleCursor.execute(createTableQuery)
        oracleConnect.commit()
        oracleCursor.close()
        oracleConnect.close

    except:
        if (cursorComplete == True):
            oracleCursor.close()
        if (connectComplete == True):
            oracleConnect.close

# 20190605 DongJoon Kim When there is a change value (= transfer service), this function updates the value of each table.
# When conducting the service, the money is updated from sender and receiver's accounts.
def updateTable(tableName, setValue, whereCondition):
    connectComplete = False
    cursorComplete = False

    try:
        connectInfo = db_id + '/' + db_pw + '@' + db_ip + ':' + db_port + '/' + db_serviceName
        oracleConnect = oci.connect(connectInfo)
        connectComplete = True
        oracleCursor = oracleConnect.cursor()
        cursorComplete = True

        updateQuery = makeUpdateQuery(tableName, setValue, whereCondition)
        oracleCursor.execute(updateQuery)
        oracleConnect.commit()
        oracleCursor.close()
        oracleConnect.close

    except:
        if (cursorComplete == True):
            oracleCursor.close()
        if (connectComplete == True):
            oracleConnect.close

# 20190605 TaeYeop Jo, YeaGeun Kim Checking datatype
def isNumber(value):
    if (type(value) == int or type(value) == float):
        return True
    else:
        return False

# 20190605 TaeYeop Jo, YeaGeun Kim Converting datatype to float
def isNumberConvertable(value):
    try:
        float(value)
        return True
    except:
        return False

# 20190605 TaeYeop Jo, YeaGeun Kim Checking information(COMMIT_YN, senderUserkey, receiverUserkey) about transfer
def transferInfoCheck(senderUserkey, receiverUserkey, amount, uuid):

    whereCondition = {}
    whereCondition['UUID'] = uuid
    txData = selectTable(db_txTableName, db_txTableColumns, whereCondition)
    if txData['COMMIT_YN'][0] != '0':
        return "ALREADY_MINED"

    whereCondition = {}
    whereCondition['USERKEY'] = senderUserkey
    senderData = selectTable(db_userTableName, db_userTableColumns, whereCondition)
    if (len(senderData) == 0):
        print("No sender matched")
        return "USER_INFO_NOT_MATCH"

    whereCondition = {}
    whereCondition['USERKEY'] = receiverUserkey
    receiverData = selectTable(db_userTableName, db_userTableColumns, whereCondition)
    if (len(receiverData) == 0):
        print("No receiver matched")
        return "USER_INFO_NOT_MATCH"

    resultMessage = moneyTransferCommit(senderData, receiverData, amount, uuid)

    return resultMessage

# 20190605 TaeYeop Jo, YeaGeun Kim Committing about transfer service as checking sender's BALANCE
def moneyTransferCommit(senderData, receiverData, amount, uuid):

    if (float(senderData['BALANCE'][0]) >= amount):
        setValue = {}
        setValue['BALANCE'] = float(senderData['BALANCE'][0]) - float(amount)
        whereCondition = {}
        whereCondition['USERID'] = senderData['USERID'][0]
        whereCondition['USERKEY'] = senderData['USERKEY'][0]
        updateTable(db_userTableName, setValue, whereCondition)

        setValue = {}
        setValue['BALANCE'] = float(receiverData['BALANCE'][0]) + float(amount)
        setValue['USABLE_AMOUNT'] = float(receiverData['USABLE_AMOUNT'][0]) + float(amount)
        whereCondition = {}
        whereCondition['USERID'] = receiverData['USERID'][0]
        whereCondition['USERKEY'] = receiverData['USERKEY'][0]
        updateTable(db_userTableName, setValue, whereCondition)

        return "SUCCESS"

    else:
        return "LACK_OF_BALANCE"

def generateGenesisBlock():
    print('\tFunction "generateGenesisBlock" executed')
    timestamp = time.time()
    print("time.time() => %f \n" % timestamp)
    tempHash = calculateHash(0, '0', timestamp, "Genesis Block", 0)
    print(tempHash)
    return Block(0, '0', timestamp, "Genesis Block",  tempHash, 0)

def calculateHash(index, previousHash, timestamp, data, proof):
    print('\tFunction "calculateHash" executed')
    value = str(index) + str(previousHash) + str(timestamp) + str(data) + str(proof)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())

def calculateHashForBlock(block):
    print('\tFunction "calculateHashForBlock" executed')
    return calculateHash(block.index, block.previousHash, block.timestamp, block.data, block.proof)

def getLatestBlock(blockchain):
    print('\tFunction "getLatestBlock" executed')
    return blockchain[len(blockchain) - 1]

def generateNextBlock(blockchain, blockData, timestamp, proof):
    print('\tFunction "generateNextBlock" executed')
    previousBlock = getLatestBlock(blockchain)
    nextIndex = int(previousBlock.index) + 1
    nextTimestamp = timestamp
    nextHash = calculateHash(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, proof)
    # index, previousHash, timestamp, data, currentHash, proof
    return Block(nextIndex, previousBlock.currentHash, nextTimestamp, blockData, nextHash, proof)

# 20190605 DongJoon Kim Comparing about index between updating block and existing BPS_BLOCK table's block
def writeBlockchain(blockchain, id=None, key=None):
    print('\tFunction "writeBlockchain" executed')
    blockchainList = []
    for block in blockchain:
        blockList = [str(block.index), str(block.previousHash), str(block.timestamp), str(block.data),
                     str(block.currentHash), str(block.proof)]
        blockchainList.append(blockList)

    connectInfo = 'oracle+cx_oracle://%s:%s@%s:%s/%s' % (db_id, db_pw, db_ip, db_port, db_serviceName)
    engine = create_engine(connectInfo)

    blockReader = selectTable(db_blockTableName, db_blockTableColumns)

    lastLineNumber = len(blockReader)
    for i in range(lastLineNumber):
        lineNumber = i + 1
        if (lineNumber == lastLineNumber):
            line = blockReader.loc[i]
            lastBlock = Block(line[0], line[1], line[2], line[3], line[4], line[5])
    try:
        if (int(lastBlock.index) + 1 != int(blockchainList[-1][0]) or lastLineNumber + 1 != len(blockchainList)):
            print("Index sequence mismatch")
            if (lastBlock.index == str(blockchainList[-1][0])):
                print("DB has already been updated")
            return False

    except:
        print(
            'Index search error, There are no data or Existing table have problems. \n It will be replaced by full data.')
        pass

    blockWriter = pd.DataFrame(blockchainList, columns=db_blockTableColumns)
    # convert type to varchar if the types of the columns of a dataframe is object
    replaceTable(db_blockTableName, db_blockTableColumns)
    try:
        to_varchar = {c: types.VARCHAR(blockWriter[c].str.len().max()) for c in
                      blockWriter.columns[blockWriter.dtypes == 'object'].tolist()}
        blockWriter.to_sql(db_blockTableName, engine, if_exists='append', index=False, dtype=to_varchar)
        print('Blockchain written to db')

    except Exception as e:
        print(e)
        print('Data save error, It seems to have an integrity or type problem.')
        to_varchar = {c: types.VARCHAR(blockReader[c].str.len().max()) for c in
                      blockReader.columns[blockReader.dtypes == 'object'].tolist()}
        blockReader.to_sql(db_blockTableName, engine, if_exists='append', index=False, dtype=to_varchar)
        return False

    # update txData cause it has been mined.
    updateResult = updateTx(blockchain[-1])

    if (updateResult == True):
        whereCondition = {}
        whereCondition["USERID"] = id
        whereCondition["USERKEY"] = key
        matchedUser = selectTable(db_userTableName, db_userTableColumns, whereCondition)
        if len(matchedUser) == 0:
            return False

        userBalance = float(matchedUser["BALANCE"])
        userUsableAmount = float(matchedUser["USABLE_AMOUNT"])

        setValue = {}
        setValue["BALANCE"] = userBalance + 1000
        setValue["USABLE_AMOUNT"] = userUsableAmount + 1000
        updateTable(db_userTableName, setValue, whereCondition)
        print('Block successfully mined, Mining compensation will be given to user %s(%s)' % (id, key))

    return True

## 20190605 HyungSeok Jeong It is a function of reading blocks. (except, if there is no block, make the first block and mine compensation +1000 )
def readBlockchain(tableName=db_blockTableName, columns=db_blockTableColumns, id=None, key=None,  mode='internal'):
    print('\tFunction "readBlockchain" executed')

    importedBlockchain = []

    blockReader = selectTable(tableName, columns)
    try:
        if len(blockReader) == 0:
            raise Exception
        for i in range(len(blockReader)):
            line = blockReader.loc[i]
            block = Block(line[0], line[1], line[2], line[3], str(line[4]), str(line[5]))
            importedBlockchain.append(block)
        print("success pulling blockchain from DB")
        return importedBlockchain
    except:
        if mode == 'internal':
            blockchain = generateGenesisBlock()
            importedBlockchain.append(blockchain)
            if (writeBlockchain(importedBlockchain, id, key)):
                whereCondition = {}
                whereCondition["USERID"] = id
                whereCondition["USERKEY"] = key
                matchedUser = selectTable(db_userTableName, db_userTableColumns, whereCondition)
                if len(matchedUser) == 0:
                    return

                userBalance = float(matchedUser["BALANCE"])
                userUsableAmount = float(matchedUser["USABLE_AMOUNT"])

                setValue = {}
                setValue["BALANCE"] = userBalance + 1000
                setValue["USABLE_AMOUNT"] = userUsableAmount + 1000
                updateTable(db_userTableName, setValue, whereCondition)
                print('Genesis block mined, Mining compensation will be given to user %s(%s)' % (id, key))
            return importedBlockchain
        else:
            return None

## 20190605 DongJoon Kim Function that updates the TxData table and execute function named transferInfoCheck
def updateTx(blockData):
    print('\tFunction "updateTx" executed')
    phrase = re.compile(
        r"\w+[-]\w+[-]\w+[-]\w+[-]\w+")  # [6b3b3c1e-858d-4e3b-b012-8faac98b49a8]UserID hwanTNS:no appropriate service handler foundg sent 333 bitTokens to UserID kim.
    matchList = phrase.findall(blockData.data)
    if len(matchList) == 0:
        print("No Match Found! " + str(blockData.data) + "block idx: " + str(blockData.index))
        return False

    for eachuuid in matchList:
        whereCondition = {}
        whereCondition['UUID'] = eachuuid
        userData = selectTable(db_txTableName, db_txTableColumns, whereCondition)
        transferCheck = transferInfoCheck(userData['SENDER'][0], userData['RECEIVER'][0], float(userData['AMOUNT'][0]), eachuuid)

        if transferCheck == 'SUCCESS':
            setValue = {db_txTableColumns[0]: 1}
            whereCondition = {db_txTableColumns[4]: eachuuid}
            updateTable(db_txTableName, setValue, whereCondition)

    print('TxData updated')
    return True

## 20190605 DongJoon Kim It is a function of recording new transactions. return if five commitYNs are exceeded in txData. (If there are more than five transactions, do not allow transactions.)
def writeTx(txRawData, senderData, inputMoney):
    print('\tFunction "writeTx" executed')
    txDataList = []
    for txDatum in txRawData:
        txList = [txDatum.commitYN, txDatum.sender, txDatum.amount, txDatum.receiver, txDatum.uuid]
        for i in range(len(txList)):
            txList[i] = str(txList[i])
        txDataList.append(txList)

    connectInfo = 'oracle+cx_oracle://%s:%s@%s:%s/%s' % (db_id, db_pw, db_ip, db_port, db_serviceName)
    engine = create_engine(connectInfo)

    txData = selectTable(db_txTableName, db_txTableColumns)
    if (len(txData[txData['COMMIT_YN'] == '0']) >= 5):
        print('Too many non-mined transaction data exsist')
        return -1

    newTxData = pd.DataFrame(txDataList, columns = db_txTableColumns)
    mergedTxData = pd.concat([txData, newTxData], axis=0, sort=False).reset_index(drop=True)
    replaceTable(db_txTableName, db_txTableColumns)
    try:
        to_varchar = {c: types.VARCHAR(mergedTxData[c].str.len().max()) for c in
                      mergedTxData.columns[mergedTxData.dtypes == 'object'].tolist()}
        mergedTxData.to_sql(db_txTableName, engine, if_exists='append', index=False, dtype=to_varchar)
    except Exception as e:
        print('Data save error, It seems to have an integrity or type problem.')

        uuidChange = False
        print("Verifying UUID duplication")
        for i in range(100):
            newTxData['UUID'] = str(uuid.uuid4())
            mergedTxData = pd.concat([txData, newTxData], axis=0, sort=False).reset_index(drop=True)
            try:
                mergedTxData.to_sql(db_txTableName, engine, if_exists='append', index=False, dtype=to_varchar)
                uuidChange = True
                print("Duplicated UUID is successfully changed")
                break
            except:
                pass

        if (uuidChange == False):
            print("UUID duplication check Failed")
            to_varchar = {c: types.VARCHAR(txData[c].str.len().max()) for c in
                          txData.columns[txData.dtypes == 'object'].tolist()}
            txData.to_sql(db_txTableName, engine, if_exists='append', index=False, dtype=to_varchar)
        return 0

    setValue = {}
    setValue['USABLE_AMOUNT'] = float(senderData['USABLE_AMOUNT'][0]) - inputMoney
    whereCondition = {}
    whereCondition['USERID'] = senderData['USERID'][0]
    whereCondition['USERKEY'] = senderData['USERKEY'][0]
    updateTable(db_userTableName, setValue, whereCondition)

    print('txData written to DB')
    return 1


def readTx(tableName, columns):
    print('\tFunction "readTx" executed')

    importedTx = []

    txReader = selectTable(tableName, columns)
    for i in range(len(txReader)):
        row = txReader.loc[i]
        if row[0] == '0':  # find unmined txData
            line = txData(row[0], row[1], row[2], row[3], row[4])
            importedTx.append(line)
    return importedTx

def getTxData():
    print('\tFunction "getTxData" executed')
    strTxData = ''
    importedTx = readTx(db_txTableName, db_txTableColumns)
    if len(importedTx) > 0:
        for i in importedTx:
            transaction = "["+ i.uuid + "]" "UserKey " + i.sender + " sent " + i.amount + " bitTokens to UserKey " + i.receiver + ". "
            print(transaction)
            strTxData += transaction
    return strTxData

## 20190605 HyungSeok Jeong This function is used to input the job certificate into the block table if the miner succeeds in mining by receiving the miner's id, unique key, difficulty, blockTable, and column as parameters.
def mineNewBlock(id, key, difficulty=g_difficulty, tableName=db_blockTableName, columns=db_blockTableColumns):
    print('\tFunction "mineNewBlock" executed')

    global mineSuccess

    blockchain = readBlockchain(tableName, columns, id, key)
    strTxData = getTxData()
    if strTxData == '':

        if (blockchain[-1].data == 'Genesis Block'):
            mineSuccess = True
            return

        print('txdata not found, so mining aborted')
        mineSuccess = False
        return

    timestamp = time.time()
    proof = 0
    newBlockFound = False

    print("Mining  blocks")
    while not newBlockFound:
        newBlockAttempt = generateNextBlock(blockchain, strTxData, timestamp, proof)
        if newBlockAttempt.currentHash[
           0:difficulty] == '0' * difficulty:
            newBlockFound = True
        else:
            proof += 1

    blockchain = readBlockchain(tableName, columns, id, key)
    blockchain.append(newBlockAttempt)
    blockIndexList = []
    for eachBlock in blockchain:
        blockIndexList.append(eachBlock.index)
    if (len(blockIndexList) == len(set(blockIndexList))):
        writeBlockchain(blockchain, id=id, key=key)
        mineSuccess = True
    else:
        print('Duplicated block index found. It seems that the block data has already been written.')
        mineSuccess = False

def mine(id, key):
    print('\tFunction "mine" executed')
    mineNewBlock(id, key)

def newtx(txToMining, senderData, inputMoney):
    print('\tFunction "newtx" executed')
    newtxData = []
    # transform given data to txData object
    tx = txData('0', txToMining['inputMyKey'][0], txToMining['inputMoney'][0], txToMining['inputOpponentKey'][0], uuid.uuid4())
    newtxData.append(tx)
    result = writeTx(newtxData, senderData, inputMoney)
    if result == 0:
        return 0
    elif result == -1:
        return -1
    return 1


class myHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        data = []
        userKey = 0

        # 20190605 JiIn Ko, SunYoung Lim Split url to obtain recordID and userID.
        if None != re.search('/id', self.path):
            recordID = self.path.split('?')[-1]
            userId = recordID.split('=')[-1]
            checkError = selectTable(db_userTableName, db_userTableColumns) ## Check userTable
            del checkError

            isSuccess = False
            for i in range(100):
                keyTemp = str(randint(0, 10000000))  # Generate a random key value
                userKey = keyTemp.zfill(10)  # Set the number of keys to ten.
                if insertData(db_userTableName, USERID=userId, USERKEY=userKey, BALANCE='0', USABLE_AMMONT='0'):
                    isSuccess = True
                    break

            if isSuccess == False:
                print("USERKEY INSERT ERROR")
                return

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(userKey, 'utf-8'))
            return

        # 20190605 JiIn Ko, SunYoung Lim When you enter login, you send it to the written path below.
        elif None != re.search('/login', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            path = './html_files/login.html'
            f = codecs.open(path, 'r', encoding='utf-8').read()
            self.wfile.write(bytes(f, 'utf-8'))

        # 20190605 JiIn Ko, SunYoung Lim When you enter tx, you send it to the written path below.
        elif None != re.search('/tx', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            path = './html_files/tx.html'
            f = codecs.open(path, 'r', encoding='utf-8').read()
            self.wfile.write(bytes(f, 'utf-8'))

        # 20190605 JiIn Ko, SunYoung Lim When you enter mine, you send it to the written path below.
        elif None != re.search('/mine', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            path = './html_files/mine.html'
            f = codecs.open(path, 'r', encoding='utf-8').read()
            self.wfile.write(bytes(f, 'utf-8'))

        # 20190605 JiIn Ko, SunYoung Lim Weakness : The size is big, so if you give it at once, the server can die. So you have to give it away.(Paging processing / scope of posting)
        elif None != re.search('/block/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            # 20190605 JiIn Ko, SunYoung Lim When url enters block getblockdata, read blockchain and check whether the data is present
            if None != re.search('/block/getBlockData', self.path):

                block = readBlockchain(db_blockTableName, db_blockTableColumns, mode='external')
                try:
                    if len(block) == 0 :
                        data.append("no data exists")
                    else :
                        for i in block:
                            print(i.__dict__)
                            data.append(i.__dict__)
                except:
                    data.append("no data exists")

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            # 20190605 JiIn Ko, SunYoung Lim When url enters the generator block, check the number of requests first.
            elif None != re.search('/block/generateBlock', self.path):
                global count2
                if (count2 > 0):
                    self.wfile.write(bytes(json.dumps({'SUCCESS': 'MANY_REQUEST'}), "utf-8"))
                    return
                count2 += 1

                ## Parsing the ID and key part, and then select the table containing the ID and key.
                if None != re.search('/block/generateBlock\?id=[\w]+&key=[\d]{10}', self.path):
                    parameter = self.path.split('?')[-1]
                    id = parameter.split('&')[0]
                    if (id.split('=')[0] == 'id'):
                        id = id.split('=')[1]
                    else:
                        self.wfile.write(bytes(json.dumps({'SUCCESS': 'URL_PROBLEM'}, sort_keys = True, indent = 4), "utf-8"))
                        count2 = 0
                        return
                    key = parameter.split('&')[1]
                    if (key.split('=')[0] == 'key'):
                        key = key.split('=')[1]
                    else:
                        self.wfile.write(bytes(json.dumps({'SUCCESS': 'URL_PROBLEM'}, sort_keys = True, indent = 4), "utf-8"))
                        count2 = 0
                        return
                else:
                    self.wfile.write(bytes(json.dumps({'SUCCESS': 'URL_PROBLEM'}, sort_keys=True, indent=4), "utf-8"))
                    count2 = 0
                    return

                whereCondition = {}
                whereCondition["USERID"] = id
                whereCondition["USERKEY"] = key
                matchedUser = selectTable(db_userTableName, db_userTableColumns, whereCondition)

                ## Check the table inquired and tell if it is mined.
                if len(matchedUser) == 0:
                    self.wfile.write(bytes(json.dumps({'SUCCESS': 'NO_MATCH'}, sort_keys=True, indent=4), "utf-8"))
                    count2 = 0
                    return

                t = threading.Thread(target=mine(id, key))
                result = t.start()

                resultResponse = {}
                resultResponse['SUCCESS'] = 'MATCH'

                global mineSuccess

                if (mineSuccess == True):
                    resultResponse['isMine'] = 'SUCCESS'
                else:
                    resultResponse['isMine'] = 'FAIL'

                mineSuccess = False
                count2 = 0
                self.wfile.write(bytes(json.dumps(resultResponse, sort_keys=True, indent=4), "utf-8"))

            else:
                data.append("{info:no such api}")
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

        # 20190605 JiIn Ko, SunYoung Lim When you enter "/", you send it to the written path below.
        elif None != re.search('/', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            path = './html_files/blockchainHome.html'
            f = codecs.open(path, 'r', encoding='utf-8').read()
            self.wfile.write(bytes(f, 'utf-8'))

        else:
            ## Change the message favicon.ico to 200.
            if None != re.search('favicon.ico', self.path):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                return
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

    def do_POST(self):
        # 20190605 JiIn Ko, SunYoung Lim When url enters tx_data, check the number of requests first.
        if None != re.search('/tx_data', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            global count
            if (count > 0):
                self.wfile.write(bytes(json.dumps({'SUCCESS': 'MANY_REQUEST'}), "utf-8"))
                return

            count += 1
            ctype, pdict = cgi.parse_header(self.headers['content-type'])

            if ctype == 'application/x-www-form-urlencoded':
                content_length = int(self.headers['Content-Length'])
                postvars = parse_qs((self.rfile.read(content_length)).decode('utf-8'), keep_blank_values=True)

                ## Verify that the values entered are blank
                if postvars['inputMyID'][0] == '':
                    postvars['SUCCESS'] = "FAILED"
                    self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                    count = 0
                    return
                elif postvars['inputMyKey'][0] == '':
                    postvars['SUCCESS'] = "FAILED"
                    self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                    count = 0
                    return
                elif postvars['inputOpponentID'][0] == '':
                    postvars['SUCCESS'] = "FAILED"
                    self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                    count = 0
                    return
                elif postvars['inputOpponentKey'][0] == '':
                    postvars['SUCCESS'] = "FAILED"
                    self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                    count = 0
                    return
                elif postvars['inputMoney'][0] == '':
                    postvars['SUCCESS'] = "FAILED"
                    self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                    count = 0
                    return

                try:
                    ## A code to confirm that the amount to be remitted is numeric.
                    inputMoney = float(postvars['inputMoney'][0])
                except:
                    postvars['SUCCESS'] = "NUMBER"
                    self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                    count = 0
                    return

                ## Code for verifying that sender ID and sender key are in the DB.
                whereCondition = {}
                whereCondition['USERID'] = postvars['inputMyID'][0]
                whereCondition['USERKEY'] = postvars['inputMyKey'][0]
                senderData = selectTable(db_userTableName, db_userTableColumns, whereCondition)
                if (len(senderData) == 0):
                    postvars['SUCCESS'] = "NO_MATCH_SENDER"
                    self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                    count = 0
                    return

                ## Code for verifying that receiver ID and receiver key are in the DB.
                whereCondition = {}
                whereCondition['USERID'] = postvars['inputOpponentID'][0]
                whereCondition['USERKEY'] = postvars['inputOpponentKey'][0]
                receiverData = selectTable(db_userTableName, db_userTableColumns, whereCondition)
                if (len(receiverData) == 0):
                    postvars['SUCCESS'] = "NO_MATCH_RECEIVER"
                    self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                    count = 0
                    return

                ## A code to check if the sender's USABLE_AMOUNT is equal to or greater than the amount it sends.
                if (float(senderData['USABLE_AMOUNT'][0]) >= inputMoney) and inputMoney > 0:
                    pass

                else:
                    if (inputMoney <= 0): ## A code to confirm whether the amount sent is zero or negative number.
                        postvars['SUCCESS'] = "ZERO_ENTERED"
                        self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                        count = 0
                        return
                    else:
                        postvars['SUCCESS'] = "LACK_OF_USABLE_AMOUNT"
                        postvars['USABLE'] = senderData['USABLE_AMOUNT'][0]
                        self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                        count = 0
                        return

                res = newtx(postvars, senderData, inputMoney)
                if res == 1:
                    postvars["SUCCESS"] = "ACCEPTED"
                elif res == -1:
                    postvars["SUCCESS"] = "MINE_BLOCK"
                else:
                    postvars["SUCCESS"] = "ERROR"

                self.wfile.write(bytes(json.dumps(postvars), "utf-8"))
                count = 0
                return

            else:
                self.send_response(403)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()

        ## 20190605 JiIn Ko, SunYoung Lim If this receives request client's checking amount, conducting below's part.
        if None != re.search('/check_amount', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            ctype, pdict = cgi.parse_header(self.headers['content-type'])
            print(ctype)
            print(pdict)

            if ctype == 'application/x-www-form-urlencoded':
                content_length = int(self.headers['Content-Length'])
                checkAmount = parse_qs((self.rfile.read(content_length)).decode('utf-8'), keep_blank_values=True)

                if checkAmount['key'][0] == '': ## If there isn't key from request, this sends response as "FAILED".
                    checkAmount['SUCCESS'] = "FAILED"
                    self.wfile.write(bytes(json.dumps(checkAmount), "utf-8"))
                    return

                if (isNumberConvertable(checkAmount['key'][0]) == False): ## If Key's value in request can't convert float type, this sends response as "NUMBER".
                    checkAmount['SUCCESS'] = "NUMBER"
                    self.wfile.write(bytes(json.dumps(checkAmount), "utf-8"))
                    return

                whereCondition = {}

                whereCondition['USERKEY'] = checkAmount['key'][0]
                senderData = selectTable(db_userTableName, db_userTableColumns, whereCondition)
                if (len(senderData) == 0): ## If senderData isn't exist, this sends response as "NO_MATCH_KEY".
                    checkAmount['SUCCESS'] = "NO_MATCH_KEY"
                    self.wfile.write(bytes(json.dumps(checkAmount), "utf-8"))
                    return

                checkAmount['SUCCESS'] = "AMOUNT_CHECK"
                checkAmount['USABLE_AMOUNT'] = senderData['USABLE_AMOUNT'][0]
                checkAmount['BALANCE'] = senderData['BALANCE'][0]
                self.wfile.write(bytes(json.dumps(checkAmount), "utf-8"))
                return

            else:
                self.send_response(403)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()

        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

try:
    server = ThreadedHTTPServer(('', PORT_NUMBER), myHandler)
    print('Started httpserver on port ', PORT_NUMBER)

    # Wait forever for incoming http requests
    server.serve_forever()

except KeyboardInterrupt as e:
    print('^C received, shutting down the web server')
    server.socket.close()

except Exception as e:
    print(e)
    server.socket.close()