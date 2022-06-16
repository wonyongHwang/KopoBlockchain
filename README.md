# KopoBlockchain
Python Blockchain Implementation for educational purposes (Dept. of Smart Finance of Korea Polytechnics)
..

### YOU MUST RUN BLOCKCHIAN SERVER BEFORE FOLLOW THESE INSTRUCTIONS BELOW !!!

## 🚩 Table of Contents

- [getBlockData](#-getBlockData)

- [generateBlock](#-generateBlock)

- [newBlock](#-newBlock)

- [newTx](#-newTx-post)







## 🧱 getBlockData

You can get blockdata by link down below. (GET Method)

You must run myBlockChain.py on pyCharm before click this link.

http://localhost:8666/block/getBlockData

### this is Example Request for getBlockData (curl)
```
curl --location --request GET 'http://localhost:8666/block/getBlockData'
```

## 💡 generateBlock
You should write tx before generate a new block. if you don't write new tx, mining will be aborted.

You can write new tx here -> [newTx](#-newTx-post)

You can generate a new block by link down below.

it use GET method to run this function.

http://localhost:8666/block/generateBlock

### this is Example Request for generateBlock (curl)
```
curl --location --request GET 'http://localhost:8666/block/generateBlock'
```

## ⛏ newBlock

You can mine a new block by link down below.

it also use GET method to run this function.

http://localhost:8666/block/mineNewBlock

### this is Example Request for newBlock (curl)
```
curl --location --request GET 'http://localhost:8666/block/mineNewBlock'
```


## 💵 newtx (POST)
Please use Post Method for this Example request
You have to fill out Headers and Body before when you send requests.
(Content-Type(KEY) : application/json(VALUE), Body = raw, json)

```
curl --location --request POST 'http://localhost:8666/block/newtx' \
--header 'Content-Type: application/json' \
--data-raw '[{
    "sender" : "sender_name",
    "amount" : "number_of_amounts",
    "receiver" : "receiver_name"
}]'
```
