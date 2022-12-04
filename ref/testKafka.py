#!/usr/bin/python
# from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from http.server import BaseHTTPRequestHandler,HTTPServer
from socketserver import ThreadingMixIn
import json
import re
from urllib.parse import parse_qs
import cgi
import sys
from kafka import KafkaProducer
producer = KafkaProducer(bootstrap_servers='master:9092,slave1:9092,slave2:9092')

if len(sys.argv) != 2:
    print("Port Number is Needed")
    sys.exit()
PORT_NUMBER = int(sys.argv[1])

# This class will handle any incoming request from
# a browser
class myHandler(BaseHTTPRequestHandler):


    # Handler for the GET requests
    def do_GET(self):

        print('Get request received')
        print('self.path', self.path)
        # Handler for the GET requests
        if None != re.search('/api/*', self.path):

            recordID = "1" # (self.path.split('/')[-1]).split('?')[0]
            if recordID == "1" :
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                # Send the html message
                self.wfile.write(bytes("<html><head><title>Title goes here.</title></head>", "utf-8")) #"euc-kr"
                self.wfile.write(bytes("<body><p>This is a test. %s</p>" % PORT_NUMBER, "utf-8"))
                self.wfile.write(bytes("<p>You accessed path: %s</p>" % self.path, "utf-8"))
                self.wfile.write(bytes("</body></html>", "utf-8"))
                
                future = producer.send('kopo-topic', bytes(json.dumps(self.path),"utf-8"))
                result = future.get(timeout=60)
                print(result)

            else:
                self.send_response(400, 'Bad Request: record does not exist')
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

    def do_POST(self):
        print('POST self.path', self.path)
        print('PORT_NUMBER : ', PORT_NUMBER)
        if None != re.search('/api/*', self.path):
            ctype, pdict = cgi.parse_header(self.headers['content-type']) # application/json;encoding=utf-8;lang=ko;loc=seoul;...
            print(ctype) # application/json
            print(pdict) # {encoding:utf-8, lang:ko, loc:seoul}

            if ctype == 'application/json':
                content_length = int(self.headers['Content-Length']) # 48 bytes
                post_data = self.rfile.read(content_length)
                receivedData = post_data.decode('utf-8')
                print(type(receivedData))
                tempDict = json.loads(receivedData) #  load your str into a dict
                tempDict['PORT'] = PORT_NUMBER
                #print(type(tempDict)) #print(tempDict['this'])
                
                future = producer.send('kopo-topic', bytes(json.dumps(tempDict),"utf-8"))
                result = future.get(timeout=60)
                print(result)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

            elif ctype == 'application/x-www-form-urlencoded':
                content_length = int(self.headers['content-length'])
                # trouble shooting, below code ref : https://github.com/aws/chalice/issues/355
                postvars = parse_qs((self.rfile.read(content_length)).decode('utf-8'),keep_blank_values=True)

                #print(postvars)    #print(type(postvars)) #print(postvars.keys())

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(json.dumps(postvars) ,"utf-8"))
            else:
                self.send_response(403)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()

        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

        # ref : https://mafayyaz.wordpress.com/2013/02/08/writing-simple-http-server-in-python-with-rest-and-json/


        return


try:

    # Create a web server and define the handler to manage the
    # incoming request
    server = HTTPServer(('', PORT_NUMBER), myHandler)
    print ('Started httpserver on port ' , PORT_NUMBER)

    # Wait forever for incoming http requests
    server.serve_forever()

except:
    print ('^C received, shutting down the web server')
    print("서버 종료1!!")
    server.socket.close()
