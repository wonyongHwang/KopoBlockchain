from flask import Flask, render_template, request, jsonify, make_response, send_file
import hashlib
import time
import json
import threading
import requests  # for sending new block to other nodes
import pandas as pd
import uuid
from sqlalchemy import create_engine  # for database connection
from Crypto.PublicKey import RSA  # for rsa verification
from base64 import b64encode, b64decode  # for rsa verification (string public key to public key object)

PORT_NUMBER = 8666
g_difficulty = 4
g_maximumTry = 100
g_nodeList = {'trustedServerAddress': '8666'}  # trusted server list, should be checked manually
g_databaseURL = "postgresql://postgres:postgres@localhost:5432/postgres"

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

class Blockchain:

    def __init__(self):
        self.blockColumns = ['previous_hash', 'time_stamp', 'tx_data', 'current_hash', 'proof']
        self.blockChain = pd.DataFrame([], columns=self.blockColumns)


    def addBlock(self, block):
        self.blockChain = self.blockChain.append(pd.DataFrame(block, columns=self.blockColumns))
        self.blockChain.reset_index(inplace=True, drop=True)


    def getLatestBlock(self):
        return self.blockChain.iloc[[-1]]


    def generateGenesisBlock(self):
        if not self.blockChain.values.tolist():
            print("generateGenesisBlock is called")
            timestamp = time.time()
            print("time.time() => %f \n" % timestamp)
            tempHash = calculateHash(0, '0', timestamp, "Genesis Block", 0)
            print(tempHash)
            self.blockChain = pd.DataFrame([['0', timestamp, "Genesis Block", tempHash, 0]], columns=self.blockColumns)
            return
        else:
            print("block already exists")
            raise MyException("generateGenesisBlock error, block already exists")


    def readBlockchain(self):
        print("readBlockchain")
        try:
            engine_postgre = create_engine(g_databaseURL)
            query_block = "select " + ",".join(self.blockColumns) + " from bc_blockchain order by index"
            self.blockChain = pd.read_sql_query(query_block, engine_postgre)
            engine_postgre.dispose()
        except:
            raise MyException("Database Connection Failed")

        print("Pulling blockchain from database...")
        if not self.blockChain.values.tolist():
            raise MyException("No Block Exists")
        else:
            return


    def toJSON(self, index_from=0, index_to=-1):
        data = []
        block = {}

        if index_to == -1:
            index_to = len(self.blockChain)
        elif index_to > len(self.blockChain):
            index_to = len(self.blockChain)

        for i in range(index_from, index_to):
            block['index'] = str(self.blockChain.loc[[i]].index[0])
            for j in range(0, len(self.blockColumns)):
                block[self.blockChain.columns[j]] = str(self.blockChain.loc[i][j])
            data.append(block)
            block = {}
        return data


    def writeBlockchain(self, uuidToUpdate):
        try:
            engine_postgre = create_engine(g_databaseURL)
            for i in range(0, len(self.blockChain)):
                try:
                    self.blockChain.loc[[i]].to_sql(name="bc_blockchain", con=engine_postgre, index=True,
                                                    if_exists="append")
                except:
                    pass

            for uuid in uuidToUpdate:
                update_query = "update bc_tx_pool set commityn=1 where uuid='" + str(uuid) + "'"
                engine_postgre.execute(update_query)

            engine_postgre.dispose()
            print("blockchain written to database")
        except:
            raise MyException("database connection failed.")


    def checkBalance(self, target):
        balance = 0
        for txdata in self.blockChain['tx_data'].values.tolist():
            txlist = txdata.split(" |")
            for tx in txlist:
                if tx != '' and tx != 'Genesis Block':
                    sender = tx.split(", ")[1]
                    amount = tx.split(", ")[2]
                    receiver = tx.split(", ")[3]
                    fee = tx.split(", ")[4]
                    if sender == target:
                        balance -= float(amount) + float(fee)
                    if receiver == target:
                        balance += float(amount)
        return balance


    def compareMerge(self, bcDict):

        if(isSameBlock(self.toJSON()[0], bcDict[0])):
            raise MyException("Genesis Block doesn't match")
        elif(isValidChain(self.toJSON(), bcDict)):
            raise MyException("blockchain is not valid")
        if len(self.blockChain) >= len(bcDict):
            print("maintain current block")
        elif len(self.blockChain) < len(bcDict):
            try:
                engine_postgre = create_engine(g_databaseURL)
                truncate_query = "truncate table bc_blockchain"  # SELECT * FROM TABLENAME , TRUNCATE TABLE tablename
                self.blockChain = pd.read_sql_query(truncate_query, engine_postgre)
                engine_postgre.dispose()

                for line in bcDict:
                    self.addBlock([[line['previous_hash'], line['time_stamp'], line['tx_data'], line['current_hash'], line['proof']]])

            except:
                print("database error")
                raise MyException("database connection failed")


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


class txDataList:

    def __init__(self):
        self.txColumns = ['commityn', 'sender', 'amount', 'receiver', 'fee', 'uuid', 'tx_data', 'signature']
        self.txDataFrame = pd.DataFrame([], columns=self.txColumns)


    def addTxData(self, txList):
        txdataframe = pd.DataFrame(txList, columns=self.txColumns)
        self.txDataFrame = self.txDataFrame.append(txdataframe)

    def writeTx(self):
        try:
            engine_postgre = create_engine(g_databaseURL)
        except:
            raise MyException("declined : database connection failed")

        try:
            self.txDataFrame.to_sql(name="bc_tx_pool", con=engine_postgre, index=False, if_exists="append")
            engine_postgre.dispose()
        except:
            raise MyException("database write error, maybe same uuid already exists")
        else:
            print('txData written to database')
            return


class NodeLst:
    def __init__(self):
        self.nodeColumns = ['ip', 'port', 'tmp'] # tmp: 시도 횟수
        self.nodeDataFrame = pd.DataFrame([], columns=self.nodeColumns)

    def addNode(self, ip, port):
        self.nodeDataFrame = self.nodeDataFrame.append(pd.DataFrame([[ip, port, 0]], columns=self.nodeColumns))
        self.nodeDataFrame = self.nodeDataFrame.drop_duplicates(['ip', 'port'])
        self.nodeDataFrame.reset_index(inplace=True, drop=True)

    def writeNodes(self):
        try:
            engine_postgre = create_engine(g_databaseURL)
            for i in range(0, len(self.nodeDataFrame)):
                try:
                    self.nodeDataFrame.loc[[i]].to_sql(name="bc_node_lst", con=engine_postgre, index=False,
                                                if_exists="append")
                except:
                    pass
            engine_postgre.dispose()
            print("new node written to DB")
        except:
            raise MyException("database connection failed")


    def readNodes(self):
        print("read Nodes")

        try:
            engine_postgre = create_engine(g_databaseURL)
            query_node = "select * from bc_node_lst"
            self.nodeDataFrame = pd.read_sql_query(query_node, con=engine_postgre)
            print("Pulling nodeData from DB...")
        except:
            raise MyException("database connection failed")


    def toJSON(self):
        data = []
        node = {}
        for i in range(0, len(self.nodeDataFrame)):
            for j in range(0, len(self.nodeColumns)):
                node[self.nodeDataFrame.columns[j]] = str(self.nodeDataFrame.loc[i][j])
            data.append(node)
            node = {}
        return data


class MyException(Exception):

    def __init__(self, msg):
        self.msg = msg


    def __str__(self):
        return self.msg


def isValidChain(blockchainToJson, foreignBlockChain):
    for i in range(len(blockchainToJson)):
        currentHash = calculateHash(blockchainToJson[i+1]['index'], blockchainToJson[i+1]['previous_hash'], blockchainToJson[i+1]['time_stamp'], blockchainToJson[i+1]['tx_data'], blockchainToJson[i+1]['proof'])
        if int(blockchainToJson[i]['index']) + 1 != int(blockchainToJson[i+1]['index']):
            return False
        elif blockchainToJson[i]['current_hash'] != blockchainToJson[i+1]['previous_hash']:
            return False
        elif currentHash != blockchainToJson[i+1]['current_hash']:
            return False
        elif currentHash[0:g_difficulty] != '0' * g_difficulty:
            return False

    for i in range(len(foreignBlockChain)):
        currentHash = calculateHash(foreignBlockChain[i+1]['index'], foreignBlockChain[i+1]['previous_hash'],
                                    foreignBlockChain[i+1]['time_stamp'], foreignBlockChain[i+1]['tx_data'],
                                    foreignBlockChain[i+1]['proof'])
        if int(foreignBlockChain[i]['index']) + 1 != int(foreignBlockChain[i+1]['index']):
            return False
        elif foreignBlockChain[i]['current_hash'] != foreignBlockChain[i+1]['previous_hash']:
            return False
        elif currentHash != foreignBlockChain[i+1]['current_hash']:
            return False
        elif currentHash[0:g_difficulty] != '0' * g_difficulty:
            return False

    return True


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
    return True


def signTx(sender_prvKeyString, receiver_pubKeyString, amount, fee, uuidString):
    try:
        sender_prvKey = RSA.importKey(b64decode(sender_prvKeyString))  # sender 공개키가 유효한지 검증
        RSA.importKey(b64decode(receiver_pubKeyString))   # receiver 공개키가 유효한지 검증
        msg = sender_prvKeyString + receiver_pubKeyString + amount + fee + uuidString
        msgHash = hashlib.sha256(msg.encode('utf-8')).digest()
    except:
        raise MyException("key is not valid")
    return sender_prvKey.sign(msgHash,'')[0]


def calculateHash(index, previousHash, timestamp, data, proof):
    value = str(index) + str(previousHash) + str(timestamp) + str(data) + str(proof)
    sha = hashlib.sha256(value.encode('utf-8'))
    return str(sha.hexdigest())


def getTxData(miner):
    try:
        engine_postgre = create_engine(g_databaseURL)
        tx_query = "SELECT uuid, tx_data FROM bc_tx_pool WHERE commityn = 0 order by fee desc limit 5"
        tx_df = pd.read_sql_query(tx_query, engine_postgre)
        engine_postgre.dispose()
    except:
        raise MyException("Database Connection Failed")

    totalfee = 0
    for tx in tx_df['tx_data'].values.tolist():
        totalfee += float(tx.replace(" |", "").split(", ")[4])

    strTxData = str(uuid.uuid4()) + ", MiningReward, " + str(100 + totalfee) + ", " + str(miner) + ", 0 |"
    for tx in tx_df['tx_data'].values.tolist():
        strTxData += tx

    else:
        if strTxData == '':
            raise MyException('No TxData Found, Mining aborted')
        return strTxData, tx_df['uuid'].values.tolist()


def mine(miner):
    blockchain = Blockchain()

    try:
        strTxData, uuidToUpdate = getTxData(miner)
    except:
        raise

    try:
        blockchain.readBlockchain()
    except MyException as error:
        if str(error) == "No Block Exists":
            try:
                blockchain.generateGenesisBlock()
            except:
                raise
        else:
            raise

    t = threading.Thread(target=mineNewBlock, args=[blockchain, strTxData, uuidToUpdate])
    t.start()

    return 0


def mineNewBlock(blockchain, strTxData, uuidToUpdate, difficulty=g_difficulty):

    previousBlock = blockchain.getLatestBlock()
    nextIndex = previousBlock.index[0] + 1
    prevHash = previousBlock['current_hash'].array[0]
    time.sleep(0.01)  # genesis block 이랑 2번째 block 이랑 timestamp 가 같길래 0.01초라도 다르게 하려고
    timestamp = time.time()
    proof = 0
    newBlockFound = False

    print('Mining a block...')

    while not newBlockFound:
        nextHash = calculateHash(nextIndex, prevHash, timestamp, strTxData, proof)
        if nextHash[0:difficulty] == '0' * difficulty:
            stopTime = time.time()
            timer = stopTime - timestamp
            print('New block found with proof', proof, 'in', round(timer, 2), 'seconds.')
            newBlockFound = True
        else:
            proof += 1
            if(proof % 100000 == 0):
                print(proof)

    blockchain.addBlock([[prevHash, timestamp, strTxData, nextHash, proof]])
    try:
        blockchain.writeBlockchain(uuidToUpdate)
    except Exception as error:
        print(error)


def newtx(txToMining):
    newTxData = txDataList()

    try:
        sender_prvKeyString = request.form['sender'].replace('-----BEGIN RSA PRIVATE KEY-----', '').replace(
            '-----END RSA PRIVATE KEY-----', '').replace('\n', '')
        sender_pubKey = RSA.importKey(b64decode(sender_prvKeyString)).publickey()
        sender_pubKeyString = b64encode(sender_pubKey.exportKey('DER')).decode('utf-8')
    except ValueError:
        raise MyException("declined : key is not valid")

    try:
        validateTx(txToMining)
    except Exception:
        raise
    else:
        tx = [[0, sender_pubKeyString, float(txToMining['amount']), txToMining['receiver'], float(txToMining['fee']),
               txToMining['uuid']]]
        tx[0].append(
            txToMining['uuid'] + ", " + sender_pubKeyString + ", " + str(txToMining['amount']) + ", " + txToMining[
                'receiver'] + ", " + str(txToMining['fee']) + " |")
        tx[0].append(txToMining['signature'])
        newTxData.addTxData(tx)

    try:
        newTxData.writeTx()
    except Exception:
        raise


def validateTx(txToMining):
    try:
        publicKey = RSA.importKey(b64decode(txToMining['sender']))  # sender 는 공개키(string), 문자열을 공개키 객체로 바꾸는중
        RSA.importKey(b64decode(txToMining['receiver']))  # 받는사람 주소가 유효한 공개키가 아닐시 except 로 처리
    except ValueError:
        raise MyException("declined : key is not valid")

    try:
        tx = str(txToMining['sender']) + str(txToMining['receiver']) + "%f" % float(
            txToMining['amount']) + "%f" % float(txToMining['fee']) + str(txToMining['uuid'])
        tx = tx.replace("\n", "")
        if ", " in tx or "| " in tx:  # 블록 txData split 할 때 쓸거라서 여기 있으면 안됨
            raise MyException("declined : , or | included")
        txHash = hashlib.sha256(tx.encode('utf-8')).digest()  # 보낼 때 sign 한 문자열의 해쉬값
        if not publicKey.verify(txHash, (int(txToMining['signature']),)):  # 보낸사람의 public key 로 검증
            raise MyException("declined : sign does not match") # verify 가 false 일 시 오류발생
    except ValueError:
        raise MyException("declined : not a number") # 형변환 실패시 오류발생
    except Exception:
        raise MyException("declined : validation failed")

# ----- flask routers ---- #

@app.route('/main')
def main_route():
    return render_template('main.html')


@app.route('/sign', methods=['POST'])
def sign_route():
    data = {}
    sender_prvKeyString = str(request.form['sender']).replace('-----BEGIN RSA PRIVATE KEY-----', '').replace(
        '-----END RSA PRIVATE KEY-----', '').replace('\n', '')
    receiver_pubKeyString = str(request.form['receiver']).replace('-----BEGIN PUBLIC KEY-----', '').replace(
        '-----END PUBLIC KEY-----', '').replace('\n', '')
    try:
        amount = "%f" % float(request.form['amount'])
        fee = "%f" % float(request.form['fee'])
    except ValueError:
        msg = "Failed : amount or fee is not a number"
        return {"msg": msg}

    if float(amount) < 0 or float(fee) < 0:
        msg = "Failed : amount or fee cannot be lower than 0"
        return {"msg": msg}

    if float(amount) == 0:
        msg = "Failed : amount cannot be 0"
        return {"msg": msg}

    uuidString = str(uuid.uuid4())
    try:
        signature = signTx(sender_prvKeyString, receiver_pubKeyString, amount, fee, uuidString)
    except MyException as error:
        print(error)
        data['msg'] = str(error)
    else:
        data = make_response({"sender": request.form['sender'],
                "receiver": request.form['receiver'],
                "amount": request.form['amount'],
                "fee": request.form['fee'],
                "uuid": uuidString,
                "signature": str(signature),
                "msg": "signed!"})
    finally:
        resp = make_response(data)
        return resp


@app.route('/validateSign', methods=['POST'])
def validateSign_route():
    sender_prvKeyString = str(request.form['sender']).replace('-----BEGIN RSA PRIVATE KEY-----', '').replace(
        '-----END RSA PRIVATE KEY-----', '').replace('\n', '')
    receiver_pubKeyString = str(request.form['receiver']).replace('-----BEGIN PUBLIC KEY-----', '').replace(
        '-----END PUBLIC KEY-----', '').replace('\n', '')
    try:
        amount = "%f" % float(request.form['amount'])
        fee = "%f" % float(request.form['fee'])
    except ValueError as error:
        print(error)
        return {"validity": "sign is invalid, amount or fee is not a number"}

    try:
        uuidString = str(request.form['uuid'])
        signToValidate = request.form['signature']
        signature = signTx(sender_prvKeyString, receiver_pubKeyString, amount, fee, uuidString)
    except Exception as error:
        print(error)
        return {"validity": "sign is invalid, abnormal key data"}

    if(signToValidate == str(signature)):
        validity = "sign is valid"
    elif(signToValidate == ''):
        validity = "sign is invalid, no sign data"
    else:
        validity = "sign is invalid, sign does not match"

    resp = make_response({"validity": validity})
    return resp


@app.route('/getPrivateKey')
def getPrivateKey_route():
    privateKey = RSA.generate(1024)
    resp = make_response(b64encode(privateKey.exportKey('DER')).decode('utf-8'))
    return resp


@app.route('/getPublicKey')
def getPublicKey_route():
    privateKey = RSA.generate(1024)
    resp = make_response(b64encode(privateKey.publickey().exportKey('DER')).decode('utf-8'))
    return resp


@app.route('/block/getBlockData')
def getBlockData_route():
    data = ""
    blockchain = Blockchain()

    index_from = int(request.args.get('from'))
    index_to = int(request.args.get('to'))

    try:
        blockchain.readBlockchain()
    except MyException as error:
        print(error)
        data = str(error)
    except Exception as error:
        print(str(error))
        data = "Internal Server Error"
    else:
        data = blockchain.toJSON(index_from, index_to)
    finally:
        resp = make_response(jsonify(data))
        return resp


@app.route('/block/generateBlock', methods=['POST'])
def generateBlock_route():
    data = {}  # response json data
    try:
        miner_prvKeyString = request.form['miner'].replace('-----BEGIN RSA PRIVATE KEY-----', '').replace(
            '-----END RSA PRIVATE KEY-----', '').replace('\n', '')
        miner_pubKey = RSA.importKey(b64decode(miner_prvKeyString)).publickey()
        miner_pubKeyString = b64encode(miner_pubKey.exportKey('DER')).decode('utf-8')
    except Exception as error:
        print(error)
        data['msg'] = "private key is not valid"
        resp = make_response(data)
        return resp

    try:
        mine(miner_pubKeyString)
    except MyException as error:
        print(error)
        data['msg'] = (str(error))
    else:
        data['msg'] = "mining is underway:check later by calling /block/getBlockData"
    finally:
        resp = make_response(data)
        return resp


@app.route('/block/newtx', methods=['POST'])
def newtx_route():
    data = {}
    blockchain = Blockchain()

    try:
        sender_prvKeyString = request.form['sender'].replace('-----BEGIN RSA PRIVATE KEY-----', '').replace(
            '-----END RSA PRIVATE KEY-----', '').replace('\n', '')
        sender_pubKey = RSA.importKey(b64decode(sender_prvKeyString)).publickey()
        sender_pubKeyString = b64encode(sender_pubKey.exportKey('DER')).decode('utf-8')
        payment = float(request.form['amount']) + float(request.form['fee'])
    except Exception as error:
        print(error)
        data['msg'] ="declined : abnormal data."
        resp = make_response(data)
        return resp

    tempDict = request.form
    try:
        blockchain.readBlockchain()
        if blockchain.checkBalance(sender_pubKeyString) < payment:
            raise MyException(
                "declined : There is not enough bitTokens in your wallet. Mine new blocks to make bitTokens.")
        newtx(tempDict)
    except MyException as error:
        print(error)
        data['msg'] = str(error)
    else:
        data['msg'] = "accepted : it will be mined later"
    finally:
        resp = make_response(data)
        return resp


@app.route('/checkBalance', methods=['POST'])
def checkBalance_route():
    data = {}
    blockchain = Blockchain()

    try:
        sender_prvKeyString = request.form['sender'].replace('-----BEGIN RSA PRIVATE KEY-----', '').replace(
            '-----END RSA PRIVATE KEY-----', '').replace('\n', '')
        sender_pubKey = RSA.importKey(b64decode(sender_prvKeyString)).publickey()
        sender_pubKeyString = b64encode(sender_pubKey.exportKey('DER')).decode('utf-8')
    except Exception as error:
        print(error)
        data['msg'] = "declined : abnormal data."
        resp = make_response(data)
        return resp

    try:
        blockchain.readBlockchain()
        data['msg'] = "You have " + str(blockchain.checkBalance(sender_pubKeyString)) + " bitTokens in your wallet."
    except MyException as error:
        print(error)
        data['msg'] = str(error)
    finally:
        resp = make_response(data)
        return resp


@app.route('/node/addNode')
def addNode_route():
    data = {}
    nodeLst = NodeLst()
    userip = request.args.get('ip')
    userport = request.args.get('port')
    realip=request.environ['REMOTE_ADDR']

    if request.environ['REMOTE_ADDR'] != userip:
        data['msg'] = "your ip address doesn't match with the requested parameter"
        resp = make_response(data)
        return resp
    else:
        try:
            nodeLst.readNodes()
            nodeLst.addNode(userip, userport)
            nodeLst.writeNodes()
        except MyException as error:
            data['msg'] = str(error)
        else:
            data['msg'] = "node added successfully"
        finally:
            resp = make_response(data)
            return resp


@app.route('/node/getNode')
def getNode_route():
    data = {}
    nodeLst = NodeLst()

    try:
        nodeLst.readNodes()
    except MyException as error:
        data['msg'] = str(error)
    else:
        data = nodeLst.toJSON()
    finally:
        resp = make_response(jsonify(data))
        return resp


@app.route('/info/')
def info_route():
    return render_template('info.html')


@app.route('/info/image')
def info_image_route():
    if request.args.get('i') == "b1":
        return send_file('./templates/addblock.png')
    elif request.args.get('i') == "b2":
        return send_file('./templates/getlatestblock.PNG')
    elif request.args.get('i') == "b3":
        return send_file('./templates/generategenesisblock.PNG')
    elif request.args.get('i') == "b4":
        return send_file('./templates/readblockchain.PNG')
    elif request.args.get('i') == "b5":
        return send_file('./templates/tojson.PNG')
    elif request.args.get('i') == "b6":
        return send_file('./templates/writeblockchain.PNG')
    elif request.args.get('i') == "b7":
        return send_file('./templates/checkbalance.PNG')
    elif request.args.get('i') == "t1":
        return send_file('./templates/addtxdata.PNG')
    elif request.args.get('i') == "t2":
        return send_file('./templates/writetx.PNG')
    elif request.args.get('i') == "n1":
        return send_file('./templates/addnode.PNG')
    elif request.args.get('i') == "n2":
        return send_file('./templates/writenodes.PNG')
    elif request.args.get('i') == "n3":
        return send_file('./templates/readnodes.PNG')
    elif request.args.get('i') == "n4":
        return send_file('./templates/tojson_t.PNG')
    elif request.args.get('i') == "a1":
        return send_file('./templates/signtx.PNG')
    elif request.args.get('i') == "a2":
        return send_file('./templates/calculatehash.PNG')
    elif request.args.get('i') == "a3":
        return send_file('./templates/gettxdata.PNG')
    elif request.args.get('i') == "a4":
        return send_file('./templates/mine.PNG')
    elif request.args.get('i') == "a5":
        return send_file('./templates/minenewblock.PNG')
    elif request.args.get('i') == "a6":
        return send_file('./templates/newtx.PNG')
    elif request.args.get('i') == "a7":
        return send_file('./templates/validatetx.PNG')
    elif request.args.get('i') == "c1":
        return send_file('./templates/blockchainclass.png')
    elif request.args.get('i') == "c2":
        return send_file('./templates/txclass.png')
    elif request.args.get('i') == "c3":
        return send_file('./templates/nodeclass.png')


@app.route('/info/text')
def info_text_route():
    if request.args.get('i') == "b1":
        return "Blockchain 클래스의 변수 self.blockchain 에 블록(행) 을 추가하는 함수입니다.<br>" \
               "mineNewBlock 에서 새 블록을 채굴한 후 미리 readBlockChain 해 놓은 기존 블록체인에 추가할 때 사용합니다.<br>" \
               "인자 block은 블록 하나의 데이터를 가지고 있는 이중배열입니다. block을 데이터프레임으로 만들고, self.blockchain 에 append 시켜줍니다."
    elif request.args.get('i') == "b2":
        return "Blockchain 클래스의 변수 self.blockchain 의 마지막 행을 반환하는 함수입니다.<br>" \
               "mineNewBlock 함수에서 블록을 채굴할 때 전 블록의 해쉬, 인덱스를 가져올 때 사용합니다."
    elif request.args.get('i') == "b3":
        return "제네시스 블록을 생성하고 Blockchain 클래스의 변수 self.blockchain 에 넣는 함수입니다.<br>" \
               " mine 에서 readBlockChain 을 시도했는데 블록이 하나도 없을 경우 호출됩니다.<br>" \
               "블록이 이미 존재하는 경우 에러를 raise 합니다."
    elif request.args.get('i') == "b4":
        return "데이터베이스에서 블록체인 전체를 가져와서 Blockchain 클래스의 변수 self.blockchain에 저장하는 함수입니다.<br>" \
               "블록체인 데이터가 필요한 경우마다 호출했기 때문에 많이 사용한 함수입니다.<br>" \
               "데이터베이스 엔진 생성에 실패한 경우 데이터베이스 접속 에러메시지를 raise 합니다. 데이터베이스에서 읽어왔으나 블록이 없는 경우에도 에러를 raise 합니다.<br>" \
               "블록이 없다는 에러메시지('No Block Exists')는 mine 함수의 except가 잡아서 generateGenesisBlock을 호출하는 데도 사용합니다."
    elif request.args.get('i') == "b5":
        return "Blockchain 클래스의 변수 self.blockchain 을 JSON [{...},{...},{...},{...}] 형태로 반환하는 합수입니다.<br>" \
               "인자로 index_from, index_to 를 받고, 인자의 초기값은 0, -1 입니다.<br>" \
               "index_to 가 -1 (아무것도 입력안할 시 초기값) 또는 블록체인의 길이보다 클 경우는 index_to 를 블록체인의 길이로 설정해줍니다.<br>" \
               "index_to에서 index_from 까지 for문을 돌면서 각 행을 dictionary로 만들고 그 dictionary를 배열에 담습니다. 결과는 배열 안에 딕셔너리가 담긴 JSON이 됩니다.<br>" \
               "response 를 줄 때 dataframe 자료형으로 줄 수 없으므로, JSON 으로 예쁘게 파싱하기 위한 함수입니다."
    elif request.args.get('i') == "b6":
        return "Blockchain 클래스의 변수 self.blockchain 의 데이터를 데이터베이스에 쓰기 위한 함수입니다.<br>" \
               "self.blockchain 전체를 한 번에 데이터베이스에 쓰려고 시도할 경우 한 행이라도 유효하지 않으면 전체가 실패하므로, 한 행씩 떼서 for문을 돌면서 데이터베이스 쓰기를 시도합니다.<br>" \
               "인자로는 uuidToUpdate를 받습니다. uuidToUpdate는 채굴된 블록에 포함된 트랜잭션들의 uuid값을 담고있는 배열입니다.<br>" \
               "uuidToUpdate가 가지고 있는 uuid에 해당하는 트랜잭션들은 블록에 포함된 것이므로, commityn 값을 1로 업데이트 해 줍니다.<br>" \
               "데이터베이스 엔진 생성에 실패한 경우 데이터베이스 접속 에러메시지를 raise 합니다."
    elif request.args.get('i') == "b7":
        return "지갑 주소에 잔액이 얼마나 남아있는지를 계산해서 반환하는 함수입니다.<br>" \
               "인자로 target을 받는데, 지갑 주소(공개키) 정보를 담고 있는 string 입니다.<br>" \
               "이 함수를 호출하기 전 readBlockChain을 호출했으므로 self.blockchain에는 블록체인 전체 데이터가 저장되어 있습니다.<br>" \
               "블록체인의 txData를 추출하고 파싱해서 sender, receiver, amount, fee 를 찾아냅니다. 그리고 target에 대해 계산합니다.<br>" \
               "sender == target일 경우 마이너스, receiver == target일 경우 플러스가 됩니다. 계산이 완료되면 최종 잔액을 반환합니다."
    elif request.args.get('i') == "t1":
        return "txDataList 클래스의 변수 self.txDataFrame 에 값을 넣어주는 함수입니다.<br>" \
               "인자 txList를 받아서 데이터프레임으로 만들고 self.txDataFrame에 대입해줍니다.<br>" \
               "Setter 역할을 하는 함수라고 할 수 있습니다."
    elif request.args.get('i') == "t2":
        return "txDataList 클래스의 변수 self.txDataFrame 의 값을 데이터베이스에 쓰기 위한 함수입니다.<br>" \
               "데이터베이스 엔진을 열고, self.txDataFrame 의 값을 데이터베이스로 쓰기를 시도합니다.<br>" \
               "실패할 경우 데이터베이스 쓰기 오류를 raise 합니다."
    elif request.args.get('i') == "n1":
        return "NodeLst 클래스의 변수 self.nodeDataFrame 에 노드(행) 을 추가하는 함수입니다.<br>" \
               "새 노드를 받아서 새 노드의 ip, port 를 인자로 전달하면서 addNode를 호출하게 됩니다.<br>" \
               "일단 self.nodeDataFrame에 추가한 후 drop_duplicates를 해주면 중복 노드를 제거할 수 있습니다."
    elif request.args.get('i') == "n2":
        return "NodeLst 클래스의 변수 self.nodeDataFrame 의 값을 데이터베이스에 쓰기 위한 함수입니다.<br>" \
               "데이터베이스 엔진을 열고, self.nodeDataFrame 의 값을 데이터베이스로 쓰기를 시도합니다.<br>" \
               "실패할 경우 데이터베이스 쓰기 오류를 raise 합니다."
    elif request.args.get('i') == "n3":
        return "데이터베이스에서 노드 데이터를 가져와 self.nodeDataFrame에 담기 위한 함수입니다.<br>" \
               "데이터베이스 엔진을 열고, 데이터베이스에서 데이터를 가져오려고 시도합니다.<br>" \
               "실패할 경우 데이터베이스 오류를 raise 합니다."
    elif request.args.get('i') == "n4":
        return "NodeLst 클래스의 변수 self.nodeDataFrame 을 JSON [{...},{...},{...},{...}] 형태로 반환하는 합수입니다.<br>" \
               "for문을 돌면서 각 행을 dictionary로 만들고 그 dictionary를 배열에 담습니다. 결과는 배열 안에 딕셔너리가 담긴 JSON이 됩니다.<br>" \
               "response 를 줄 때 dataframe 자료형으로 줄 수 없으므로, JSON 으로 예쁘게 파싱하기 위한 함수입니다."
    elif request.args.get('i') == "a1":
        return "트랜잭션 데이터를 sign 해서 sign데이터를 반환해주는 함수입니다.<br>" \
               "트랜잭션 데이터는 보내는사람의 개인키, 받는사람의 공개키, amount, fee, uuid 가 있습니다<br>" \
               "개인키 string은 importKey를 통해 개인키 객체로 만들고, 트랜잭션 데이터들은 하나의 string으로 합쳐줍니다.<br>" \
               "하나로 합쳐진 트랜잭션 데이터 string을 sha256으로 해쉬한 해쉬값을 개인키 객체로 sign 합니다.<br>" \
               "만약 키가 유효하지 않다면 에러를 raise 합니다."
    elif request.args.get('i') == "a2":
        return "블록의 각 요소들을 인자로 받아서 블록의 해쉬값을 계산해 반환하는 함수입니다.<br>" \
               "각 요소를 하나의 문자열로 합치고, 그 문자열을 sha256으로 해쉬한 후 그 값을 반환합니다."
    elif request.args.get('i') == "a3":
        return "블록을 채굴할 때, 새 블록에 포함될 트랜잭션을 가져오는 함수입니다.<br>" \
               "우선 데이터베이스에 접속하여 트랜잭션 데이터를 달라는 쿼리를 요청합니다.<br>" \
               "쿼리의 내용은 commityn 이 0이고, fee(수수료) 순으로 정렬된 uuid, tx_data 컬럼을 최대 5개만 달라는 것입니다.<br>" \
               "채굴자에게 줄 보상은 기본 100 + 트랜잭션에 있는 모든 fee 를 합친 값입니다. 이 보상 트랜잭션을 가장 앞에 추가합니다.<br>" \
               "그리고 블록에 포함될 나머지 트랜잭션들을 뒤에 붙여서 하나의 문자열로 만들어줍니다.<br>" \
               "하나로 된 트랜잭션 데이터 문자열과, uuid 컬럼값을 담은 배열 두 개를 반환해줍니다."
    elif request.args.get('i') == "a4":
        return "mine 함수는 블록을 채굴할 준비를 하는 함수입니다. 기존에는 mine부터 쓰레드로 돌았지만, mine 대신 mineNewBlock을 쓰레드로 돌리기로 했습니다.<br>" \
               "왜냐하면 mine이 쓰레드로 돌면 오류가 나도 응답을 줄 수 없기 때문이고, 시간이 별로 걸리지 않는 작업이므로 쓰레드로 돌릴 이유가 없습니다.<br>" \
               "mine은 getTxData, readBlockchain, generateGenesisBlock 등을 호출하고 만약 오류가 난다면 잡아서 raise 해줍니다.<br>" \
               "채굴에 필요한 정보가 모두 모였다면, 그 정보들을 mineNewBlock에 넘겨주면서 mineNewBlock을 쓰레드로 실행합니다."
    elif request.args.get('i') == "a5":
        return "mineNewBlock은 실제로 블록을 채굴하는 함수입니다. 시간이 오래 걸리므로 쓰레드로 호출됩니다.<br>" \
               "우선 인자로 넘겨받은 blockchain 객체로부터 새 블록에 들어갈 요소들을 추출하고, timestamp, proof 도 설정해줍니다.<br>" \
               "모두 준비되었다면 while문을 돌면서 difficulty에 맞는 hash가 나올때까지 proof를 늘리면서 해쉬연산을 수행합니다.<br>" \
               "만약 difficulty를 만족하는 해쉬를 찾았다면, blockchain 객체에 addBlock을 한 후 writeBlockcahin으로 데이터베이스에 기록합니다.<br>" \
               "만약 writeBlockchain 등에서 에러가 발생하면 에러메시지를 raise 해 줍니다."
    elif request.args.get('i') == "a6":
        return "새로운 트랜잭션 요청이 들어왔을 때, JSON으로 된 트랜잭션 요청을 적절하게 가공하고 검사해서 데이터베이스에 쓰는 함수입니다.<br>" \
               "우선 보내는사람, 받는사람의 키가 유효한지 검사합니다. 또 validateTx를 호출하여 sign이 유효한지 검사합니다.<br>" \
               "트랜잭션이 유효하다면 트랜잭션 데이터를 가공하여 문자열로 만들고, tx_data(블록에 들어갈 데이터와 동일)에 넣어줍니다.<br>" \
               "데이터들을 모아서 addTxData, writeTx 를 호출해서 데이터베이스에 기록합니다.<br>" \
               "실행 중 오류가 발생할 경우 오류메시지를 raise 해 줍니다."
    elif request.args.get('i') == "a7":
        return "트랜잭션 데이터가 유효한지 검사하는 함수입니다.<br>" \
               "키가 유효한지, 특수문자(, |)가 들어가있는지, sign 이 유효한지 등을 검사합니다.<br>" \
               "만약 에러가 발생한다면 그에 맞는 에러메시지를 raise 해 줍니다."
    else:
        return ""


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

    nodeLst = NodeLst()

    try:
        nodeLst.readNodes()
    except MyException as error:
        print(error)
    if not nodeLst.toJSON():
        # get nodes...
        for key, value in iter(g_nodeList.items()):
            URL = 'http://' + key + ':' + value + '/node/getNode'
            try:
                res = requests.get(URL)
            except requests.exceptions.ConnectionError:
                continue
            if res.status_code == 200:
                # json.loads는 string, bytes, bytearray -> dict 형변환
                tmpNodeLists = json.loads(res.text)
                for ip, port in iter(tmpNodeLists.items()):
                    nodeLst.addNode(ip, port, 0)

