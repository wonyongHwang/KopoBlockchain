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

PORT_NUMBER = 8089
MAX_GET_DATA_LISTS = 10
MAX_NUMBER_OF_TX = 50
DATABASE_TP_NAME = "transaction_pool"
DATABASE_TP_IP = 'localhost'
DATABASE_TP_PORT = 3400
DATABASE_TP_USER = "root"
DATABASE_TP_PW = "root"
DATABASE_TP_TABLE = "TRANSACTION_POOL"

#Transaction data
class txData:
    def __init__(self, commitYN, sender, amount, receiver, fee, uuid, transactionTime):
        self.commitYN = commitYN
        self.sender = sender
        self.amount = amount
        self.receiver = receiver
        self.fee = fee
        self.uuid = uuid
        self.transactionTime = transactionTime

#In accordance with the requested URL,
# the 'commitYN' of the received transaction is changed from 0 to 1 for 'update' or from 1 to 0.
def updateTx(txToMining, mode = 'update'):
    if mode == 'update' :
        commit = "1"
        print("update mode : 0 -> 1")
    else :
        commit = "0"
        print("rollback mode : 1 -> 0")

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
                sql = "UPDATE " + DATABASE_TP_TABLE + " SET commitYN=" + commit + " WHERE uuid='" + uuidNum + "'"
                curs.execute(sql)
        print("Succecss to update database.")
        conn.commit()
    except:
        print("Cannot access to database to update.")
        conn.close()
        return False
    finally:
        conn.close()
        return True

# Store the transaction details in the table.
def newTx(txToMining):
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
        print("number of requested txData exceeds limitation.")
        return -2

    conn = pymysql.connect(host=DATABASE_TP_IP, port=DATABASE_TP_PORT, user=DATABASE_TP_USER, password=DATABASE_TP_PW,
                           db=DATABASE_TP_NAME, charset='utf8')
    try :
        with conn.cursor() as curs:
            for txRow in newTxData:
                print(txRow.__dict__)
                print("Start inserting into table....")
                sql = "INSERT INTO " + DATABASE_TP_TABLE + " VALUES (%s, %s, %s, %s, %s, %s, %s)"
                curs.execute(sql, (0, txRow.sender, txRow.amount, txRow.receiver, txRow.fee, txRow.uuid, txRow.transactionTime))

            conn.commit()
        print("Succeed to insert txData on database.")
    except :
        print("Failed to access database for insert.")
        return -1
    finally:
        conn.close()

    return 1

#If the requested URL is 'zero' then 'commitYN' returns up to 50 transaction details data,
#and if the request is 'all' then the entire data.
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
        print("Failed to access to database.")
        isSuccess = False
    finally:
        conn.close()

    return txDataList, isSuccess

#If a table does not exist in the #database, create a table, if present, do not create a table.
def initSvr() :
    print("server : TRANSACTION mode")
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
        print("initSvr setting Done...")

# Processes various kinds of requests
class myHandler(BaseHTTPRequestHandler):

     def do_GET(self):
        data = []
        if None != re.search('/getTxData/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            #Returns up to 50 data sequentially with a value of 0 'commitYN'
            if None != re.search('/getTxData/zero', self.path):

                txDataList, isSuccess = getTxData()

                if txDataList == '':
                    if isSuccess:
                        print("No txData Exists commitYn is 0.")
                        data.append("No txData Exists commitYn is 0.")
                    else:
                        print("Failed to access to database.")
                        data.append("Failed to access to database.")
                else:
                    for i in txDataList:
                        print(i.__dict__)
                        data.append(i.__dict__)

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            #Returns the entire transaction data of the table.
            elif None != re.search('/getTxData/all', self.path):

                txDataList, isSucces = getTxData(mode='all')

                if txDataList == '':
                    if isSucces :
                        print("No txData Exists.")
                        data.append("No txData Exists.")
                    else :
                        print("Failed to access to database.")
                        data.append("Failed to access to database.")
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

     def do_POST(self):

        if None != re.search('/txData/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            #Change the value of 'commitYN' in the data of the table to '0' and '1'
            # based on the data contained in response.
            if None != re.search('/txData/update', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])

                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)
                    if updateTx(tempDict, mode = 'update') == True:
                        tempDict.append("success")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else:
                        tempDict.append("failed")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
            # Change the value of 'commitYN' in the data of the table to '1' and '0'
            # based on the data contained in response.
            if None != re.search('/txData/rollBack', self.path):
                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                # print(ctype) #print(pdict)

                if ctype == 'application/json':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    receivedData = post_data.decode('utf-8')
                    print(type(receivedData))
                    tempDict = json.loads(receivedData)
                    if updateTx(tempDict, mode = "rollback") == True:
                        tempDict.append("success")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else:
                        tempDict.append("failed")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

            #Insert data contained in #response into the table.
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
                        tempDict.append("accepted : it will be mined later.")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    elif res == -1:
                        tempDict.append("declined : number of request txData exceeds limitation.")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    elif res == -2:
                        tempDict.append("declined : error on data read or write.")
                        self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
                    else:
                        tempDict.append("error : requested data is abnormal.")
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