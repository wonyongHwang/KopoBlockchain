#-*- coding: utf-8 -*-
import hashlib
import time
from http.server import BaseHTTPRequestHandler, HTTPServer  # 이거 파이썬 3.0버전에서만 사용가능함
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

PORT_NUMBER = 8099
MAX_GET_DATA_LISTS = 10
MAX_NUMBER_OF_TX = 50
DATABASE_TP_NAME = "transaction_pool"
DATABASE_TP_IP = "localhost"
DATABASE_TP_PORT = 3300
DATABASE_TP_USER = "root"
DATABASE_TP_PW = "root"
DATABASE_TP_TABLE = "TRANSACTION_POOL"

class txData:
    def __init__(self, commitYN, sender, amount, receiver, fee, uuid, transactionTime):
        self.commitYN = commitYN
        self.sender = sender
        self.amount = amount
        self.receiver = receiver
        self.fee = fee
        self.uuid = uuid
        self.transactionTime = transactionTime

#블록생성에 성공한 거래내역들의 commitYN을 1로 바꿔줄 때
def updateTx(txToMining):
    uuidList = []
    conn = pymysql.connect(host=DATABASE_TP_IP, port=DATABASE_TP_PORT, user=DATABASE_TP_USER,
                           password=DATABASE_TP_PW, db=DATABASE_TP_NAME,
                           charset='utf8')

    phrase = re.compile(
        r"\w+[-]\w+[-]\w+[-]\w+[-]\w+")
    matchList = phrase.findall(txToMining[0]['data'])

    for line in matchList :
        print(line)
        uuidList.append(line)

    try:
        with conn.cursor() as curs:
            for uuidNum in uuidList:
                print("Updating table data to compare...")
                sql = "UPDATE " + DATABASE_TP_TABLE + " SET commitYN=1 WHERE uuid='" + uuidNum + "'"  # 실행 할 쿼리문 입력
                curs.execute(sql)  # 쿼리문 실행
        print("Succecss to update database......")
        conn.commit()
    except:
        print("Cannot access to database to update")
        conn.close()
        return False
    finally:
        conn.close()
        return True

#node(postman)에서 새로운 거래내역(newTx) 입력을 요청했을 때
def newTx(txToMining, mode='new'):
    newTxData = []

    conn = pymysql.connect(host=DATABASE_TP_IP, port=DATABASE_TP_PORT, user=DATABASE_TP_USER, password=DATABASE_TP_PW, db=DATABASE_TP_NAME,
                           charset='utf8')
    curs = conn.cursor()
    uuidNum = str(uuid.uuid4())
    transactionTime = time.time()

    for line in txToMining :
        tx = txData(0, line['sender'], line['amount'], line['receiver'], line['fee'], uuidNum, transactionTime)
        newTxData.append(tx)


    if len(newTxData) > MAX_GET_DATA_LISTS :
        print("number of requested txData exceeds limitation")
        return -2

    conn = pymysql.connect(host=DATABASE_TP_IP, port=DATABASE_TP_PORT, user=DATABASE_TP_USER, password=DATABASE_TP_PW,
                           db=DATABASE_TP_NAME, charset='utf8')
    try :
        with conn.cursor() as curs:
            for txRow in newTxData:
                print(txRow.__dict__)
                print("start insert into table....")
                sql = "INSERT INTO " + DATABASE_TP_TABLE + " VALUES (%s, %s, %s, %s, %s, %s, %s)"  # 실행 할 쿼리문 입력
                curs.execute(sql, (0, txRow.sender, txRow.amount, txRow.receiver, txRow.fee, txRow.uuid, txRow.transactionTime))# 쿼리문 실행
                # curs.execute(sql)  # 쿼리문 실행
            conn.commit()
    except :
        print("cannot access to database to insert")
        return -1
    finally:
        conn.close()

    return 1

#transation_pool의 데이터를 가져와 반환
def getTxData(mode='zero') :
    txDataList = []
    isSuccess = True
    zeroCount = 0;
    conn = pymysql.connect(host=DATABASE_TP_IP, port=DATABASE_TP_PORT, user=DATABASE_TP_USER, password=DATABASE_TP_PW,
                           db=DATABASE_TP_NAME,
                           charset='utf8')

    if mode == "zero" :
        sql = "SELECT * FROM " + DATABASE_TP_TABLE + " WHERE commitYN = 0"
    else :
        sql = "SELECT * FROM " + DATABASE_TP_TABLE

    try :
        with conn.cursor() as curs:
            curs.execute(sql)
            rows = curs.fetchall()

            for row in rows :
                if mode == "zero" and zeroCount > MAX_NUMBER_OF_TX :
                    break
                else :
                    line = txData(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
                    txDataList.append(line)
                    zeroCount = zeroCount + 1
        conn.commit()
    except :
        print("Failed to access to database..........")
        isSuccess = False
    finally:
        conn.close()

    return txDataList, isSuccess

#create table 한다
def initSvr() :
    conn = pymysql.connect(host=DATABASE_TP_IP, port=DATABASE_TP_PORT, user=DATABASE_TP_USER, password=DATABASE_TP_PW, db=DATABASE_TP_NAME,
                           charset='utf8')

    try:
        sql = "CREATE TABLE " + DATABASE_TP_TABLE + "(" \
                "commitYN int," \
                "sender varchar(255)," \
                "amount varchar(255)," \
                "receiver varchar(255)," \
                "fee varchar(255)," \
                "uuid varchar(255)," \
                "transactionTime float" \
                ")"

        with conn.cursor() as curs :
            curs.execute(sql)

        print("Success to create table " + DATABASE_TP_TABLE + " on " + DATABASE_TP_NAME)
    except :
        print("Failed to create table " + DATABASE_TP_TABLE + " on " + DATABASE_TP_NAME)
    finally:
        conn.close()



class myHandler(BaseHTTPRequestHandler):

    # def __init__(self, request, client_address, server):
    #    BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    # Handler for the GET requests
    # get방식으로 보내는 요청의 종류로는 블록체인의 데이터 요청, 블록 생성, 노드데이터 요청, 노드생성이 존재한다.
    def do_GET(self):
        data = []  # response json data
        if None != re.search('/getTxData/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/getTxData/zero', self.path):

                txDataList, isSucces = getTxData()

                if txDataList == '':
                    if isSucces:
                        print("No txData Exists commitYn is 0")
                        data.append("No txData Exists commitYn is 0")
                    else:
                        print("Failed to access to database")
                        data.append("Failed to access to database")
                else:
                    for i in txDataList:
                        print(i.__dict__)
                        data.append(i.__dict__)

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            # 블럭을 생성하는 경우 (최초, 그 이후 전부)
            elif None != re.search('/getTxData/all', self.path):

                txDataList, isSucces = getTxData(mode='all')

                if txDataList == '':
                    if isSucces :
                        print("No txData Exists")
                        data.append("No txData Exists")
                    else :
                        print("Failed to access to database")
                        data.append("Failed to access to database")
                else:
                    for i in txDataList:
                        print(i.__dict__)
                        data.append(i.__dict__)

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))
            else:
                data.append("{info:no such api}")
                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

        else:
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
        # ref : https://mafayyaz.wordpress.com/2013/02/08/writing-simple-http-server-in-python-with-rest-and-json/

    def do_POST(self):

        if None != re.search('/txData/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/txData/update', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                # print(ctype) #print(pdict)

                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)  # load your str into a list #print(type(tempDict))
                    if updateTx(tempDict) == True:
                        tempDict.append("success")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else:
                        tempDict.append("failed")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

            elif None != re.search('/txData/new', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)
                    res = newTx(tempDict)
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
    print('Started transactionPool server on port ', PORT_NUMBER)

    initSvr()
    # Wait forever for incoming http requests
    server.serve_forever()

except (KeyboardInterrupt, Exception) as e:
    print('^C received, shutting down the web server')
    print(e)
    server.socket.close()