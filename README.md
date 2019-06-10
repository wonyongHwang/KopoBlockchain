# [LOCK] - Project on Refining Blockchain Code(myBlockchain.py)

Authors: BohKuK Seo, HaeRi Kim, JinWoo Song, JongSun Park, YuRim Kim, HyeongSeob Lee

Written on 05.June.2019


## Document
[![KO doc](https://img.shields.io/badge/document-ppt(Korean)-blue.svg)](https://blog.naver.com/khr93115/221556618335)


## Overview
LOCK is the name of main technical function of this project. Under the purpose of preventing errors that occur when users try to access to the csv file(Blockchain.csv / txData.csv) related to using Blockchain code(myBlockchain.py) simultaneously, we have put a lock function at the place where the csv file needs to be open in write mode('w').
Inside the while sentence lock.acquire(), lock.release() etc had been used to implement our aim.

![ShardingSphere Scope](https://i.imgur.com/yLQtu6P.jpg)

## Default Setting
1) OS: window 64bit

## How to Build    

### Programs / Platforms and installed Modules

1) Python 3.6 - pip install requests
2) Postman 7.0.7 - https://www.getpostman.com/downloads/ (download postman from here:))
3) Node js -$npm install express
           -$npm install mysql
           -$npm install request
           -$npm install bootstrap
4) Maria db 10.x -  https://go.mariadb.com/search-download-MariaDB-server.html?utm_source=google&utm_medium=ppc&utm_campaign=MKG-Search-Google-Branded-APAC-bd&gclid=CjwKCAjw0N3nBRBvEiwAHMwvNs2zl4x2G8pfPluxvpV0YAhe1MffOkD8nNXA9bFtQKZODobJjHd-uRoCWbYQAvD_BwE (download MariaDB from here:))

5) HeidiSQL 10.x - https://www.heidisql.com/download.php (download HeidiSQL from here:))

6) OAuth 2.0
-Step1: Create Credentials - API key
you might need to put redirect_url when you try to get API key.
https://accounts.google.com/ServiceLogin/identifier?service=cloudconsole&passive=1209600&osid=1&continue=https%3A%2F%2Fconsole.developers.google.com%2F%3Fhl%3Dko%26ref%3Dhttps%3A%2F%2Fwww.google.com%2F&followup=https%3A%2F%2Fconsole.developers.google.com%2F%3Fhl%3Dko%26ref%3Dhttps%3A%2F%2Fwww.google.com%2F&hl=ko&flowName=GlifWebSignIn&flowEntry=AddSession

-Step2:
In login/login.html , login/signup.html, mypage/balance.html file
  hello.init({
  google: '<Write API client key that you got in Step1 here:)>' (put it inside the single quotation)
 }, {redirect_uri: '<Write your redirection url>'});


## How to Use
1) Run the python code (myblockchain.py)

2) send the URl
Be sure you have designated the right port number. It must be same as the number on the code(myblockchain.py).
To make blockchain.csv,  you should re-run nodes' servers after "addNodes" request.


A. on postman
urls used to test actions regarding creating, updating Blockchain, and making transactions.
https://documenter.getpostman.com/view/7384751/S1LpbY6N?version=latest#intro


B. on Website

![Website main](https://i.imgur.com/UrHs19V.jpg)

1) Set your DB connection in app.js file

var connection = mysql.createConnection({
  host: 'localhost', <- your IP
  port: 3306, <- your port number
  user: 'root', <- your DB userid
  password: 'root', <- your DB user password
  database: 'webui' <- your database name
});

2) Change your url matching with the port number that you set on myblockchain.py
var url = 'http://localhost:8097'

3) Create table: your URL + "/"
4) Create user account: your URL + "/login/signup"
5) Make transfer coin: your URL + "/send"
6) Check balance coin: your URL + "/balance"
7) Mining: your URL + "/mine"
8) See block data: your URL + "/blockdata"
