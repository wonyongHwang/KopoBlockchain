    # def do_POST(self):
    #
    #     if None != re.search('/block/*', self.path):
    #         self.send_response(200)
    #         self.send_header('Content-type', 'application/json')
    #         self.end_headers()
    #
    #         if None != re.search('/block/validateBlock/*', self.path):
    #             ctype, pdict = cgi.parse_header(self.headers['content-type'])
    #             #print(ctype) #print(pdict)
    #
    #             if ctype == 'application/json':
    #                 content_length = int(self.headers['Content-Length'])
    #                 post_data = self.rfile.read(content_length)
    #                 receivedData = post_data.decode('utf-8')
    #                 print(type(receivedData))
    #                 tempDict = json.loads(receivedData)  # load your str into a list #print(type(tempDict))
    #                 if isValidChain(tempDict) == True :
    #                     tempDict.append("validationResult:normal")
    #                     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
    #                 else :
    #                     tempDict.append("validationResult:abnormal")
    #                     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
    #         elif None != re.search('/block/newtx', self.path):
    #             ctype, pdict = cgi.parse_header(self.headers['content-type'])
    #             if ctype == 'application/json':
    #                 content_length = int(self.headers['Content-Length'])
    #                 post_data = self.rfile.read(content_length)
    #                 receivedData = post_data.decode('utf-8')
    #                 print(type(receivedData))
    #                 tempDict = json.loads(receivedData)
    #                 res = newtx(tempDict)
    #                 if  res == 1 :
    #                     tempDict.append("accepted : it will be mined later")
    #                     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
    #                 elif res == -1 :
    #                     tempDict.append("declined : number of request txData exceeds limitation")
    #                     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
    #                 elif res == -2 :
    #                     tempDict.append("declined : error on data read or write")
    #                     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
    #                 else :
    #                     tempDict.append("error : requested data is abnormal")
    #                     self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
    #
    #     elif None != re.search('/node/*', self.path):
    #         self.send_response(200)
    #         self.send_header('Content-type', 'application/json')
    #         self.end_headers()
    #         if None != re.search(g_receiveNewBlock, self.path): # /node/receiveNewBlock
    #             content_length = int(self.headers['Content-Length'])
    #             post_data = self.rfile.read(content_length)
    #             receivedData = post_data.decode('utf-8')
    #             tempDict = json.loads(receivedData)  # load your str into a list
    #             print(tempDict)
    #             res = compareMerge(tempDict)
    #             if res == -2: # internal error
    #                 tempDict.append("internal server error")
    #             elif res == -1 : # block chain info incorrect
    #                 tempDict.append("block chain info incorrect")
    #             elif res == 1: #normal
    #                 tempDict.append("accepted")
    #             elif res == 2: # identical
    #                 tempDict.append("already updated")
    #             elif res == 3: # we have a longer chain
    #                 tempDict.append("we have a longer chain")
    #             self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))

###해결점 1. tempDict 변수의 갱신이유?, 오류코드까지 찍으면 끝인거 같은데 반환도 따로 안하는 tempDict를 끝까지 갱신하는이유?
    #             self.wfile.write(bytes(json.dumps(tempDict), "utf-8"))
    # 해당부분에서 json.dump로 반환함. 그대로 유지 필요
    # 그렇다면 5가지 오류코드를 한개로 묶고 출력을 tempDict이 나오도록 설정 필요

###해결점 2. 수정이 간편하도록 수정, 가장 큰 눈에 보이는 카테고리는 outptut에 대한 오류 문구 출력
########### 따라서 오류 문구별로 method 구성, 이를 class로 담아 추후 해당 오류구문 수정 시 메소드만 수정하면 되도록 수정


# 위 오류 출력부분 수정방향
blockCM = UpdataAndVaildate()
blockCM.compareMerge(tempDict) #인수 삽입
blockCM.errcodefirst() # internal server error
blockCM.errcodesecond() # block chain info incorrect
blockCM.errcodethird()  # accepted
blockCM.errcodeforth()  # already updated
blockCM.errcodefifth()  # we have longer chain
###추후 시간가능하면 5가지 코드 를 다시 메소드화 시켜서 처리



class UpdataAndVaildate():
    heldBlock = []
    bcToValidataForBlock = []
    def compareMerge(bcDict): ##bcDict이 다른 노드로 부터 받은 데이터
        try:
            with open(g_bcFileName, 'r',  newline='') as file:
                blockReader = csv.reader(file)
                #last_line_number = row_count(g_bcFileName)
                for line in blockReader:
                    block = Block(line[0], line[1], line[2], line[3], line[4], line[5])
                    heldBlock.append(block) ##heldblock이 내가 가진 데이터

        except:
            print("file open error in compareMerge or No database exists")
            print("call initSvr if this server has just installed")
            return -2

        #if it fails to read block data  from db(csv)
        if len(heldBlock) == 0 :
            print("fail to read")
            return -2

        # transform given data to Block object
        for line in bcDict:
            # print(type(line))
            # index, previousHash, timestamp, data, currentHash, proof
            block = Block(line['index'], line['previousHash'], line['timestamp'], line['data'], line['currentHash'], line['proof'])
            bcToValidateForBlock.append(block)

    def shortIsvalid(bcToValidateForBlock):
        ## bcToValidateForBlock type 은 리스트,
        tempBlocks = [bcToValidateForBlock[0]]
        for i in range(1, len(bcToValidateForBlock)):
            if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                tempBlocks.append(bcToValidateForBlock[i])
            else:
                return -1
                #리턴값 확인, -1은 genesisblock관련인데 현재 오류는 그오류가 아닌거같음

    def checkGenesisBlock(bcDict):
        ####
        ####
        ####
        #982줄의 출력결과를 합쳐보기
        # compare the given data with genesisBlock
        if not isSameBlock(bcToValidateForBlock[0], heldBlock[0]):
            print('Genesis Block Incorrect')
            return -1

        # check if broadcasted new block,1 ahead than > last held block

        if isValidNewBlock(bcToValidateForBlock[-1],heldBlock[-1]) == False:

            # latest block == broadcasted last block
            if isSameBlock(heldBlock[-1], bcToValidateForBlock[-1]) == True:
                print('latest block == broadcasted last block, already updated')
                return 2
            # select longest chain
            elif len(bcToValidateForBlock) > len(heldBlock):
                ##kjy bcto 기준으로 나눠보기

                # validation
                if isSameBlock(heldBlock[0],bcToValidateForBlock[0]) == False:
                        print("Block Information Incorrect #1")
                        return -1
                # tempBlocks = [bcToValidateForBlock[0]]
                # for i in range(1, len(bcToValidateForBlock)):
                #     if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                #         tempBlocks.append(bcToValidateForBlock[i])
                #     else:
                #         return -1
                shortIsvalid(bcToValidateForBlock) ##위 주석 대체
                # [START] save it to csv
                blockchainList = []
                for block in bcToValidateForBlock:
                    blockList = [block.index, block.previousHash, str(block.timestamp), block.data,
                                 block.currentHash, block.proof]
                    blockchainList.append(blockList)
                with open(g_bcFileName, "w", newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(blockchainList)
                # [END] save it to csv
                return 1
            elif len(bcToValidateForBlock) < len(heldBlock):
                # validation
                #for i in range(0,len(bcToValidateForBlock)):
                #    if isSameBlock(heldBlock[i], bcToValidateForBlock[i]) == False:
                #        print("Block Information Incorrect #1")
                #        return -1


                # tempBlocks = [bcToValidateForBlock[0]]
                # for i in range(1, len(bcToValidateForBlock)):
                #     if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
                #         tempBlocks.append(bcToValidateForBlock[i])
                #     else:
                #         return -1
                shortIsvalid(bcToValidateForBlock) ##위 주석 대체
                print("We have a longer chain")
                return 3
            else:
                print("Block Information Incorrect #2")
                return -1
        else: # very normal case (ex> we have index 100 and receive index 101 ...)
            # tempBlocks = [bcToValidateForBlock[0]]
            # for i in range(1, len(bcToValidateForBlock)):
            #     if isValidNewBlock(bcToValidateForBlock[i], tempBlocks[i - 1]):
            #         tempBlocks.append(bcToValidateForBlock[i])
            #     else:
            #         print("Block Information Incorrect #2 "+tempBlocks.__dict__)
            #         return -1
            shortIsvalid(bcToValidateForBlock) ##위 주석 대체

            print("new block good")

            # validation
            for i in range(0, len(heldBlock)):
                if isSameBlock(heldBlock[i], bcToValidateForBlock[i]) == False:
                    print("Block Information Incorrect #1")
                    return -1
            # [START] save it to csv
            blockchainList = []
            for block in bcToValidateForBlock:
                blockList = [block.index, block.previousHash, str(block.timestamp), block.data, block.currentHash, block.proof]
                blockchainList.append(blockList)
            with open(g_bcFileName, "w", newline='') as file:
                writer = csv.writer(file)
                writer.writerows(blockchainList)
            # [END] save it to csv
            return 1
