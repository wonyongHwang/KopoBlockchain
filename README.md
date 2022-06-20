
# KopoBlockchain
Python Blockchain Implementation for educational purposes (Dept. of Smart Finance of Korea Polytechnics)
..

### YOU MUST RUN BLOCKCHIAN SERVER BEFORE FOLLOW THESE INSTRUCTIONS BELOW !!!

## 📖 Contents

- [getBlockData](#-getBlockData)

- [generateBlock](#-generateBlock)

- [newBlock](#-newBlock)

- [newTx](#-newTx-post)

- [validateBlock](#-validateBlock)

- [Diagrams](#-Diagrams)






## 🧱 getBlockData

You can get Block data by link down below. (GET Method)

You MUST run myBlockChain.py on pyCharm before click this link.

http://localhost:8666/block/getBlockData

#### *This is Example Request for getBlockData (curl)
```
curl --location --request GET 'http://localhost:8666/block/getBlockData'
```

## 💡 generateBlock
You should write tx before generate a new block. if you don't write new tx, mining will be aborted.

You can write new tx here -> [newTx](#-newTx-post)

You can generate a new block by link down below.

it use GET method to run this function.

http://localhost:8666/block/generateBlock

#### *This is Example Request for generateBlock (curl)
```
curl --location --request GET 'http://localhost:8666/block/generateBlock'
```

## ⛏ newBlock

You can mine a new block by link down below.

it also use GET method to run this function.

http://localhost:8666/block/mineNewBlock

#### *This is Example Request for newBlock (curl)
```
curl --location --request GET 'http://localhost:8666/block/mineNewBlock'
```


## 💵 newtx (POST)
Please use Post Method for this Example request.

You have to fill out Headers and Body before when you send requests.

(Content-Type(KEY) : application/json(VALUE), Body = raw, json)

#### *This is Example Request for newTx (curl, POST Method)
```
curl --location --request POST 'http://localhost:8666/block/newtx' \
--header 'Content-Type: application/json' \
--data-raw '[{
    "sender" : "sender_name",
    "amount" : "number_of_amounts",
    "receiver" : "receiver_name"
}]'
```


## 🔎 validateBlock
You can check that new block is valid or not.

You have to figure out "currentHash", "data", "index", "previousHash", "proof", "timestamp" before validate new block.

Use POST Method same as newTx before.

#### *This is Example Request for validateBlock (curl, POST Method)

```
curl --location --request POST 'http://localhost:8666/block/validateBlock' \
--data-raw '[
    {
        "currentHash": "aad22d5f3bb41eaacda9883106e8770cf9818a710cba5309e11bfd4721dfee6f",
        "data": "Genesis Block",
        "index": "0",
        "previousHash": "0",
        "proof": "0",
        "timestamp": "1654828634.695756"
    }
]'
```
# 💎 Diagrams
## 🌊 Flow chart Image for generateBlock
![initial](https://github.com/SunghwanNam/KopoBlockchain/blob/283eac7a1299875d4ff556ae97afd2aae0e8186b/generateBlock.png)

## 🌊 Flow chart Image for getBlockData
![initial](https://github.com/SunghwanNam/KopoBlockchain/blob/283eac7a1299875d4ff556ae97afd2aae0e8186b/getBlockData.png)

## 🌊 Flow chart Image for addNodeData
![Untitled Diagram-Page-8 drawio](https://user-images.githubusercontent.com/103026653/174598167-26169227-3869-4c40-9fb2-385ac397b23a.png)
