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

PORT_NUMBER = 8081
DATABASE_NAME = "serverlist"
DATABASE_IP = '127.0.0.1'
DATABASE_PORT = 3306
DATABASE_USER = "root"
DATABASE_PW = "root"
DATABASE_TABLE = "SERVERLIST"

class serverData :
    def __init__(self, ip, port, onOff):
        self.ip = ip
        self.port = port
        self.onOff = onOff

#Insert the ip address and port number of requested URL on the table. If already present, do not insert.
def addServer(ip, port) :
    result = 1

    conn = pymysql.connect(host=DATABASE_IP, port=DATABASE_PORT, user=DATABASE_USER, passwd=DATABASE_PW, \
                           database=DATABASE_NAME, charset='utf8')
    try:
        print("Trying to find server on database...........")
        with conn.cursor() as cursor:
            sql = "Select ip, port FROM " + DATABASE_TABLE + " WHERE ip = %s AND port = %s"
            cursor.execute(sql, (ip, port))
            rows = cursor.fetchall()

        if len(rows) != 0:
            print("new server is already existed.")
            result = 0
        else :
            print("No exist new server.")

    except:
        print("Failed to access serverlist database.")
        result = -1
    finally:
        conn.close()


    conn = pymysql.connect(host=DATABASE_IP, port=DATABASE_PORT, user=DATABASE_USER, passwd=DATABASE_PW, \
                           database=DATABASE_NAME, charset='utf8')

    if result == 1 :
        try:
            print("Trying to add new server on database...........")
            with conn.cursor() as curs:
                sql = "INSERT INTO " + DATABASE_TABLE + " VALUES (%s,%s,%s)"
                curs.execute(sql, (ip, port, 'on'))
                conn.commit()
            print("Success to write new server on " + DATABASE_TABLE + ".")
        except:
            print("Failed to access serverlist database.")
            result = -1
        finally:
            conn.close()

    return result

# Returns all data in the table.
def getServerList() :
    serverList = []
    isSuccess = True

    conn = pymysql.connect(host=DATABASE_IP, port=DATABASE_PORT, user=DATABASE_USER, password=DATABASE_PW,
                           db=DATABASE_NAME,
                           charset='utf8')

    try:

        print("Trying to find new server on database...........")
        with conn.cursor() as cursor:
            sql = "Select * FROM " + DATABASE_TABLE
            cursor.execute(sql)
            rows = cursor.fetchall()

            for line in rows :
                server = serverData(line[0], line[1], line[2])
                serverList.append(server)
    except:
        print("Failed to access serverlist database.")
        isSuccess = False
    finally:
        conn.close()

    return serverList, isSuccess

#If a table does not exist in the #database, create a table, if present, do not create a table.
def initSvr() :
    print("database : serverlist")
    conn = pymysql.connect(host=DATABASE_IP, port=DATABASE_PORT, user=DATABASE_USER, password=DATABASE_PW, db=DATABASE_NAME,
                           charset='utf8')

    try:
        sql = "CREATE TABLE " + DATABASE_TABLE + "(" \
                "ip varchar(255)," \
                "port varchar(255)," \
                "onOff varchar(255)" \
                ")"

        with conn.cursor() as curs :
            curs.execute(sql)

        print("Success to create table " + DATABASE_TABLE + " on " + DATABASE_NAME)
    except :
        print("Failed to create table " + DATABASE_TABLE + " on " + DATABASE_NAME)
    finally:
        conn.close()
        print("initSvr setting Done...")

class myHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        data = []
        if None != re.search('/serverList/*', self.path):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            if None != re.search('/serverList/add', self.path):

                result = addServer(self.client_address[0], self.path.split('?')[1].split('=')[1])

                if result == 1 :
                    print("Succeed to add server")
                    data.append("success")

                elif result == 0 :
                    print("your ip and port already exist.")
                    data.append("exist")
                else :
                    print("Failed to access to database.")
                    data.append("fail")

                self.wfile.write(bytes(json.dumps(data, sort_keys=True, indent=4), "utf-8"))

            elif None != re.search('/serverList/get', self.path):

                serverDataList, readSucces = getServerList()

                if serverDataList == []:
                    if readSucces:
                        print("No serverData Exists.")
                        data.append("No serverData Exists.")
                    else:
                        print("Failed to access to database.")
                        data.append("Failed to access to database.")
                else:
                    for i in serverDataList:
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
