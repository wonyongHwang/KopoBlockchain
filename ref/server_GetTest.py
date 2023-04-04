#!/usr/bin/python
# from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from http.server import BaseHTTPRequestHandler,HTTPServer
from socketserver import ThreadingMixIn
import json
import re
from urllib.parse import parse_qs
import cgi

PORT_NUMBER = 8099

# This class will handle any incoming request from
# a browser
class myHandler(BaseHTTPRequestHandler):


    # Handler for the GET requests
    def do_GET(self):

        print('Get request received')
        if None != re.search('/api/*', self.path):
            print('Get '+self.client_address[0])
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            # Send the html message
            self.wfile.write(bytes("<html><head><title>Title goes here.</title></head>", "utf-8")) #"euc-kr"
            self.wfile.write(bytes("<body><p>This is a test.</p>", "utf-8"))
            self.wfile.write(bytes("<p>You accessed path: %s</p>" % self.path, "utf-8"))
            self.wfile.write(bytes("<p>Your IP: %s</p>" % self.client_address[0], "utf-8"))
            self.wfile.write(bytes("</body></html>", "utf-8"))

        else:
            self.send_response(400, 'Bad Request: record does not exist')
            self.send_header('Content-Type', 'application/json')
            self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

try:

    # Create a web server and define the handler to manage the
    # incoming request
    #server = HTTPServer(('', PORT_NUMBER), myHandler)
    server = ThreadedHTTPServer(('', PORT_NUMBER), myHandler)

    print ('Started httpserver on port ' , PORT_NUMBER)

    # Wait forever for incoming http requests
    server.serve_forever()

except:
    print ('^C received, shutting down the web server')
    print("서버 종료1!!")
    server.socket.close()
