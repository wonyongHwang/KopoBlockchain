# Simple blockchain Code with Mysql Database (multiple Server Environment)

Writer: JaeWon Park, KyungHyun Kim, SinWoo Lee, YeEun Jeong, SeulKi Kwon, SeongRim Kim

## Reference Material
[![KO doc](https://img.shields.io/badge/document-ppt(Korean)-blue.svg)](https://blog.naver.com/jye5943/221563523373)

## Introduction
***
### System Configuration
![ShardingSphere Scope](https://imgur.com/mFxYRWz.png)
Here is our project Keypoint.  
First, The transaction pool is separated. To implement it as similar as actual blockchain system as possible, We added a merkle hash and separate Transaction Pool code from master's blockchain code.  
Second, After running multiple servers, the list is saved in the AWS provided server's DB for freely doing synchronization. A total of three servers were operated at the same time by using Ubuntu servers.  
It would be easy to understand if you think of servers as Bitcoin miners. A list of these servers is stored in the DB of the servers provided by AWS through the serverList code.  
Last, It is off limits using csv file in the master's code. The transaction data or blockchain information that is accumulated in the csv file is saved and synchronized to the DB linked to each server.  

## Technologies
***
### This project is created with :

### Code
* Pycharm community - python 3.7
### Database
* Oracle Virtual box 6.0
* Ubuntu-16.04.3-server-amd64
* AWS(Amazon web Service) EC2 Vitual Machine
* Mysql 5.7
* putty
### For test
* Sqlyog 13.1.2
* Postman

## Launch
***
### Set test interface
### Configure the test environment as following :
* Number of running transactionPool.py = 1
* Number of running serverlist.py = 1
* Number of running blockchain.py = 3

* Number of running transaction database = 1
* Number of running serverlist database = 1
* Number of running blockchain & nodelist database = 3
### Configure database according to each code :
#### blockchain.py & transactionPool.py
  1) Create virtual machines in Oracle VM VirtualBox for the database matching each code.
  2) Install uunut-16.04.3-server-amd64 on each virtual machine.
  3) Install mysql 5.7 on each ubuntu server
  4) Modify LISTEN IP bandwidth and port number:
   ```
   ~$sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
   ```
     you can search bind-adress, and comment out for listen all ip bandwidth.  
     also, you can find port, and set port number you want.
  5) Allow MySQL ports in the Ubuntu firewall for external access.
   ```
   ~$sudo ufw 3306(default number or you set)/tcp
   ```
  6) Create database.
  7) Create a account and set permissions on the database that has been created.  
     For testing only, it is convenient to give the root full authority.
  8) Restart mysql service.   
  9) Set up port forwarding on the network of the virtual machine to connect to mysql.
#### serverlist.py
  1) Uses EC2 virtual machines in aws (Amazon Web Service).
  2) Select ubuntu Server 16.04 LTS to create an instance.
  3) Connect with putty and install mysql 5.7.
  4) Modify LISTEN IP bandwidth and port number :  
   ```
   ~$sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
   ```
     you can search bind-adress, and comment out for listen all ip bandwidth.  
     also, you can find port, and set port number you want.
  5) Allow MySQL ports in the Ubuntu firewall for external access.
   ```
   ~$sudo ufw 3306(default number or you set)/tcp
   ```
  6) Create database.
  7) Create a account and set permissions on the database that has been created.  
     For testing only, it is convenient to give the root full authority.
  8) Restart mysql service.   
  9) Create new Security Group for connecting on mysql database.

### Set ip address and port number for each code
#### transactionpool.py
```
PORT_NUMBER = 8089
MAX_GET_DATA_LISTS = 10
MAX_NUMBER_OF_TX = 50
DATABASE_TP_NAME = "transaction_pool"
DATABASE_TP_IP = 'localhost'
DATABASE_TP_PORT = 3400
DATABASE_TP_USER = "root"
DATABASE_TP_PW = "root"
DATABASE_TP_TABLE = "TRANSACTION_POOL"
```
* PORT_NUMBER = The port number where this code(transactionPool.py) exists.
* MAX_GET_DATA_LISTS = Maximum number of transactions received from a node at once
* MAX_NUMBER_OF_TX = Maximum number of transactions to be sent to blockchain code server
* DATABASE_TP_NAME = Name of database for transaction details
* DATABASE_TP_IP = Ip address of database for transaction details
* DATABASE_TP_PORT = Port Number of database for transaction details
* DATABASE_TP_USER = Mysql user name of database for transaction details
* DATABASE_TP_PW = Mysql password of database for transaction details
* DATABASE_TP_TABLE = Table name of database for transaction details
#### myBlockchain.py
```
IP_NUMBER = "127.0.0.1"
# socket.gethostbyname(socket.getfqdn())
PORT_NUMBER = 8099

DATABASE_SVR_NAME = "databasebc"
DATABASE_SVR_IP = 'localhost'
DATABASE_SVR_PORT = 3300
DATABASE_SVR_USER = "root"
DATABASE_SVR_PW = "root"
DATABASE_BC_TABLE = "blockchain"
DATABASE_ND_TABLE = "node"

DATABASE_TPSVR_IP = "http://localhost:8089"

DATABASE_MINER_LIST_IP = "http://localhost"
DATABASE_MINER_LIST_PORT = 8081

MASTER = True
SERVE = False
```
* IP_NUMBER = The ip address of this code(myBlockchain.py) stored in the table of the serverlist server.  
If all codes run locally, set to 127.0.0.1. If each codes run each other place, you can get ip address using this code.

```
socket.gethostbyname(socket.getfqdn())
```

* PORT_NUMBER = The port number where your code(myBlockchain.py) exists.

* DATABASE_SVR_NAME = Name of database for blockchain and nodelist data of this code
* DATABASE_SVR_IP = Ip address of database for blockchain and nodelist data of this code
* DATABASE_SVR_PORT = Port Number of database for blockchain and nodelist data of this code
* DATABASE_SVR_USER = Mysql user name of database for blockchain and nodelist data of this code
* DATABASE_SVR_PW = Mysql password of database for blockchain and nodelist data of this code
* DATABASE_BC_TABLE = Block chain table name of database for transaction details
* DATABASE_ND_TABLE = Nodelist table name of database for transaction details

* DATABASE_TPSVR_IP = Ip address and port number of transactionpool.py

* DATABASE_MINER_LIST_IP =  Ip address of serverlist.py
* DATABASE_MINER_LIST_PORT = port number of serverlist.py

* MASTER = True -> Determine whether this code is a master or a serve.
* SERVE = False

#### serverlist.py
```
PORT_NUMBER = 8081
DATABASE_NAME = "serverlist"
DATABASE_IP = '127.0.0.1'
DATABASE_PORT = 3306
DATABASE_USER = "root"
DATABASE_PW = "root"
DATABASE_TABLE = "SERVERLIST"
```
* PORT_NUMBER = The port number where this code(transactionPool.py) exists.
* DATABASE_NAME = Name of database for serverlist(aws)
* DATABASE_IP = Ip address of database for serverlist(aws)
* DATABASE_PORT = Port number of database for serverlist(aws)
* DATABASE_USER = mysql user name of database for serverlist(aws)
* DATABASE_PW = mysql password of database for serverlist(aws)
* DATABASE_TABLE = Table name of database for serverlist(aws)

## Test case with Postman
### For each running code, you can request the following url(Except internal url request) :
#### transactionPool.py
* Method GET :  
  http://ipAddressOfCode:portNumberOfCode/getTxData/all
* Method POST :  
  http://ipAddressOfCode:portNumberOfCode/txData/new  
  * body :  
  ```
  [
      {
          "sender": "hwang",
          "amount": "1000",
          "receiver": "kim",
          "fee" : "235"
      }
  ]
  ```
#### myBlockchain.py
* Method GET :  
  http://ipAddressOfCode:portNumberOfCode/block/getBlockData  
  http://ipAddressOfCode:portNumberOfCode/block/generateBlock  
  http://ipAddressOfCode:portNumberOfCode/node/addNode  
  http://ipAddressOfCode:portNumberOfCode/node/getNode  
