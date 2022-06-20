
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


#### Experiment of block Size
title : Experiment to find out the size of the block applied to the block chain

What is Blockchain?
  A data structure that binds multiple transaction details into one block and continuously connects them to existing blocks like a chain. 
  -> Blockchain = Block + Chain(like Linked List)
 Blockchain size limits are small by modern data storage standards, but crypto transactions are very lightweight, when it comes to data storage.  Bitcoin’s block size is limited to 1 MB, but this small amount of data is enough to store over 2000 transactions. There is no defined of block size in this code. just have limit to send 4 number of txData in the block.       
Since txdata is limited to 4, it stores a very small amount of data, so we will check the size of the block we made through
an experiment.

 #When one txdata is sent, the size stored in the block is less than 1kb.
 #amount of 5000 txdata is required up to 1mb by simple calculation.
 #There are various exceptions in the experiment, but we will ignore them.
 #Expectation: When more than 2000 txdata are sent, or when the size exceeds 1mb, observe whether more than 2 blocks are generated.
 #Observe whether the time is directly proportional to the size of the data when the mining difficulty is the same.
 
  the way of an experiment:
	$sending 1 txData: You can see how much size one txdata has.
    ![1txData](https://user-images.githubusercontent.com/103026653/174604175-c81854bf-54bd-4d29-a75f-a9115c7de4d0.png)

    $sending 4 txData: A block with 4 txdata also has a size of 1kb.
    ![4txdata](https://user-images.githubusercontent.com/103026653/174604381-13b6f9e7-6e58-4e95-8234-c52f70944e0b.png)

    $sending 100 txData:
    ![100txdata](https://user-images.githubusercontent.com/103026653/174604555-f512e641-9d4a-4878-a234-760477157a3b.png)
    
    $sending 2000 txData: 
    ![2000개txdata](https://user-images.githubusercontent.com/103026653/174604696-3d6a3252-2faa-44d4-971c-deb394e1681c.png)
  
    $sending 5000 txData: 
    ![5000txdata](https://user-images.githubusercontent.com/103026653/174604761-f246b2ae-0ca4-442d-80b5-99045c26fa0e.png)

    $sending 10000 txdata: 
    ![commit](https://user-images.githubusercontent.com/103026653/174604916-cca744e0-6151-438a-a82a-9f8b2ec330f7.png)
    ![10000](https://user-images.githubusercontent.com/103026653/174605054-76831d33-5540-4482-8499-ecb7e9d388a4.png)

	$sending 80000 txdata : in this case, the txData.csv file is 4.5mb so i expect created 4 number of block 
    ![4 5mb](https://user-images.githubusercontent.com/103026653/174604815-9dfe0f40-ca5f-407f-ba9e-256215d3d085.png)
    ![10만개의txdata](https://user-images.githubusercontent.com/103026653/174604850-80799e16-ed01-4f2f-afc7-dfa7e7d56584.png)

 CONCULUTION : When looking at txdata in the method of calculating the size limit of the block of our code, up to 2000 were stored based on about 10 minutes. When an amount larger than 2000 txdata was sent in the post method, it took 20 minutes for 5000 txdata. From 10000, when you see whether the commit is in the txdata.csv file, 1 (stored in a block) is displayed.
 I saw that, but in block.csv, it was not saved in the block and the data was corrupted, so I could see that a new first block was created. In the process of mining after sending more than 80000 txdata, it was not possible to confirm whether the mining time exceeded 3 days and whether it was working. 
 Based on these experimental results, we found that the code can be modified to send up to 5000 txdata instead of the 5 limit. Also, It was found that the amount of txData does not indicate the time it takes to mine.
	         
Limitation: When more than 2000 TXDATA is sent, or when data exceeding 1MB in size is sent, The code must be changed so that blocks are continuously generated according to the size of the data being stored.	   
 
