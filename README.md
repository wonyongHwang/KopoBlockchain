# **[Kopo BlockChain Project 가이드 라인]**

## **개요**

Postman 혹은 Webpage에서 BlockChain, txData 조회 및 채굴

* 기존 블록체인의 채굴 자동화 및 DB 저장
* 웹페이지를 통한 데이터 조회

![blockchain project](https://i.imgur.com/CtALucG.png)

## **필수 프로그램**

* mySql(HeidiSQL)
* Pycharm
* Nodejs

**PyCharm Module**

* requests
* pandas
* threading
* time
* hashlib
* create_engine

## **mySql Database**

### **blockchain**

|    *NAME*    | *DATA TYPE* | *LENGTH* | *PRIMARY KEY* |
| -------------| ----------- | ---------| --------------|
| NO           | INT         | 11       | O             |
| PREVIOUSHASH | VARCHAR     | 1000     |               |
| TIMESTAMP    | VARCHAR     | 1000     |               |
| DATA         | VARCHAR     | 1000     |               |
| CURRENTHASH  | VARCHAR     | 1000     |               |
| PROOF        | INT         | 11       |               |
| FEE          | DOUBLE      |          |               |
| SIGNATURE    | VARCHAR     | 1000     |               |

### **txdata**

|    *NAME*    | *DATA TYPE* | *LENGTH* | *PRIMARY KEY* |
| -------------| ----------- | ---------| --------------|
| COMMITYN     | INT         | 11       |               |
| SENDER       | VARCHAR     | 1000     |               |
| AMOUNT       | VARCHAR     | 1000     |               |
| RECEIVER     | VARCHAR     | 50       |               |
| UUID         | BLOB        |          | O             |
| FEE          | DOUBLE      |          |               |
| MESSAGE      | VARCHAR     | 1000     |               |
| TXTIME       | VARCHAR     | 1000     |               |

### **nodelist**

|    *NAME*    | *DATA TYPE* | *LENGTH* | *PRIMARY KEY* |
| -------------| ----------- | ---------| --------------|
| IP           | VARCHAR     | 50       |               |
| PORT         | VARCHAR     | 50       |               |
| TRIAL        | INT         | 11       |               |

## **Post Man**

PyCharm Running!

###  **GET** getBlockData
```
http://localhost:8099/block/getBlockData
http://localhost:8099/block/getBlockData?from=1&to=5
```
###### HEADERS
```
Content-Typeapplication/json
```
###### PARAMS
```
from 1
to 5
```

### **GET** GenerateBlock
```
http://localhost:8099/block/generateBlock
```

### **GET** getTxData
```
http://localhost:8099/txdata/getTxdata
http://localhost:8099/txdata/getTxdata?count=10
```
###### HEADERS
```
Content-Typeapplication/json
```
###### PARAMS
```
count 10
```

### **POST** newTx
```
http://localhost:8099/block/generateBlock
```
###### HEARDERS
```
Content-typeapplication/json;charset=utf-8
```
###### BODY
```
[
  {
      "sender": "Hwang",
      "amount": "5000",
      "receiver": "Ji",
      "fee": "12",
      "message" : "blackchain!!!!!!"
  }
]
```

### **GET** getNode
```
http://localhost:8099/node/getNode
```

### **GET** addNode
```
http://localhost:8099/node/addNode?192.168.110.000:8800
```
###### PARAMS
```
192.168.110.000
8800
```

## **Web**

### nodejs 실행 (cmd -> 폴더이동 -> supervisor app.js)

* Main : http://localhost/
* BlockData : http://localhost/getBlockData
* TxData : http://localhost/getTxdata
* NodeList : http://localhost/getNodelist


### **조회 방식**

* 채굴된 블록 및 원하는 블록 갯수 조회
* txData는 블럭에 반영되지 않는 데이터 조회
* Fee(수수료), time(생성시간) 내림차순으로 정렬 조회

```
Error :
Access to XMLHttpRequest at 'URL' from origin 'http://localhost' has been blocked by CORS policy:No 'Access-Control-Allow-Origin' header is present on the requested resource.
```
참고 : https://chrome.google.com/webstore/detail/allow-cors-access-control/lhobafahddgcelffkeicbaginigeejlf

## **보완점**

* 로직의 간편화 및 예외처리
* Broadcast 구현
* compareMerge Trouble Shooting
