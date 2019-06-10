# [BPS - BLOCK PASS SERVICE]

## BPS Project Team Member
- Team Leader : KIM DONG JOON
- Team Member : KO JI IN
- Team Member : KIM YEA GEUN
- Team Member : LIM SUN YOUNG
- Team Member : JUNG HYOUNG SUK
- Team Member : JO TAE YEOP

## Document

[![PPT for BPS_INFO](https://img.shields.io/badge/BPS_INFO-PPT-blue.svg)](https://blog.naver.com/dlatjsdud128/221556614989)

## Overview
### Why use BPS?
- 안전한 금융거래를 위한 서비스
- 간편한 송금 서비스
- 보상을 얻을 수 있는 서비스

### What is BPS?
- 코인 거래소를 모티브로 사용자들의 거래 데이터를 블록체인에 담아 보안을 강화하고, 원활한 금융 거래를 위한 송금 서비스

### Strengh of BPS
- Web을 통해 BlockData를 사용자가 쉽게 볼 수 있습니다.
- DB와 연동으로 기존 csv에 보다 많은 양의 데이터를 처리할 수 있습니다.
- 회원들은 간편한 버튼으로 송금서비스를 이용 할 수 있습니다.
- 채굴에 성공한 사용자들에게는 보상이 주어집니다.

## How to use

### Required Program

![Required Program](https://i.imgur.com/r9PHnbV.jpg)

### How to Build

#### Install `pip` in your Pycharm and run command

```shell
import hashlib
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import json
import re
from urllib.parse import parse_qs
import threading
import cgi
import uuid
import pandas as pd
from sqlalchemy import create_engine, types
import cx_Oracle as oci
import codecs
from random import *
```

### Web
#### Pycharm에서 서버 연결(실행)
- Home : localhost:port_number/
- Join Membership : localhost:port_number/login
- Mining & Reward : localhost:port_number/mine
- Transaction & Usable Amount & Balance Search : localhost:port_number/tx

### USE Tips

![UseTips](https://i.imgur.com/ui7Kk0F.jpg)

### Toad for Oracle

- USERS TABLE  

ex) SELECT * FROM BPS_USERS;

|         *USERID*        |    *USERKEY*    |       *BALANCE*      |   *USABLE_AMOUNT*  |
| ----------------------- | --------------- | -------------------- | ------------------ |
| dongjoon                | 0000428006      | 1000                 | 1000               |
| goji                    | 0003542160      | 0                    | 0                  |
| taeyeop                 | 0003691454      | 500                  | 500                |
| hyoungseok              | 0003890083      | 0                    | 0                  |
| sunyoung                | 0000654587      | 0                    | 0                  |
| YG                      | 0001052165      | 0                    | 0                  |


- TXDATA TABLE

ex) SELECT * FROM BPS_TXDATA;

|       *COMMIT_YN*       |     *SENDER*    |       *AMOUNT*       |      *RECEIVER*    |                *UUID*               |  
| ----------------------- | --------------- | -------------------- | ------------------ | ----------------------------------- |
| 1                       | 0000428006      | 100                  | 0003542160         |d70b81fa-88fe-4839-845d-ebe8075a1384 |
| 0                       | 0003542160      | 0                    | 0000428006         |b01efe9c-0464-40bd-8b5f-642a4edfa1d2 |


- BLOCK TABLE

ex) SELECT * FROM BPS_BLOCK;

| *BLOCKINDEX* |         *PREVIOUSHASH*            |      *TIMESTAMP*     |      *DATA*        |      *CURRENTHASH*      |    *PROOF*   |  
| ------------ | --------------------------------- | -------------------- | ------------------ | ----------------------- | ------------ |
| 0            | 0                                 | 1559704155.056918    | Genesis Block      | e56ddff51bcbe44383...   | 0            |
| 1            | e56ddff51bcbe44383edf1637428c...  | 1559704199.4670026   | [d70b81fa-88fe...] | 051fbc6e0370e6eec8...   | 5            |


## Sequence diagram

- Create User
![Create User](https://i.imgur.com/INNSD5N.jpg)

- Create Tx Data
![Create Tx Data](https://i.imgur.com/cDfv1WR.jpg)

- Usable Amout, Balnace Search
![Usable Amout, Balnace Search](https://i.imgur.com/Ae7qY5u.jpg)

- Generate Block
![Generate Block](https://i.imgur.com/bMrK767.jpg)
![Generate Block](https://i.imgur.com/32Han1h.jpg)
![Generate Block](https://i.imgur.com/4s6zWwx.jpg)

- Get Block Data
![Get Block Data](https://i.imgur.com/TRoE0NG.jpg)


## Issue
- Oracle Connection

  Web에서 트랜잭션 및 블록체인 생성에 대한 사용자의 요청을 받을 때 연속적인 요청이 들어올 경우(광클) 중복되어 요청됨

  Oracle DB는 INSERT된 순서대로 SELECT가 이루어지지 않아 테이블을 지우고 다시 생성하는 방식으로 해결하였으나 동시 채굴 시 채굴 보상이 여러명에게 주어지는 문제 => 일시적 완화를 위해 global 변수 count를 사용하여 발견된 문제를 막고자 하였으나 서버에 사용자들의 동시접속이 불가능하여 순서대로 서비스를 이용해야한다는 불편함이 발생

  개선 제안 : 상기한 대로 Oracle DB 사용에 문제가되는 부분은 임시방편으로 테이블을 Replace(Drop & Create) 하는 것이 아닌 Insert & Sort로 해결해야할 것.
  또한, 함수간 간섭이 많고 연결되는 부분이 복잡하여 함수간 의존도를 줄이는 노력이 필요
