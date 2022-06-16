# KopoBlockchain
Python Blockchain Implementation for educational purposes (Dept. of Smart Finance of Korea Polytechnics)
..

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
http://localhost:8666/block/newtx
..
