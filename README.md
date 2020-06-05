
# [음원 시장에서의 블록체인 적용] by 2020_2조



> ### **왜 음원시장인가?**



 - 부정적 이슈 : 불공정한 수익 분배



![image](https://user-images.githubusercontent.com/62678235/83597075-50139600-a5a1-11ea-98d2-b31460379edf.png)



![image](https://user-images.githubusercontent.com/62678235/83597255-d334ec00-a5a1-11ea-93fa-b14e327bac20.png)



 - 모델링



![image](https://user-images.githubusercontent.com/62678235/83597353-1000e300-a5a2-11ea-8f5c-f1b53899ce31.png)



 

| 현재 | 수정모델 |

|:----------:|:----------:|

| "전체" 스트리밍 횟수로 정산하기 때문에 매크로 등을 통한 순위조작 가능| "개인별" 스트리밍 횟수로 정산하여 저작권자에게 정당한 수익 분배  |                                                           



<br>

<br>



> ### **적용 모델**

>P2P & 중앙서버 하이브리드 모델



#### - 저작권자는 금융기관으로부터 정산만 받는 간접참여자이고, txData를 저장하는 중앙서버를 별도로 둔다.



![image](https://user-images.githubusercontent.com/62678235/83707873-08027b00-a656-11ea-9b5f-d30bdb03e8b2.png)



 



#### - 사용자는 음원을 재생할 때 생성되는 거래데이터를 중앙서버로 broadcastNewTx라는 기능을 통해 전달하고, 서버는 이를 저장



![image](https://user-images.githubusercontent.com/62678235/83707907-194b8780-a656-11ea-80a8-97731ea73714.png)



 



#### - 서버에 저장된 거래데이터를 채굴자가 내려받아 채굴 시도



![image](https://user-images.githubusercontent.com/62678235/83707940-27010d00-a656-11ea-8b10-d0eeb21bbb99.png)





> ### **txData 서버 전송**



- 사용 DB : POSTGRE

- DB 구현화면



![image](https://user-images.githubusercontent.com/62678235/83827634-c4714500-a719-11ea-9fd0-cafbacdbe202.png)



- **txData볼륨 이슈**

 -txData를 중앙서버에 저장하고, 블록에는 merkleRoot만 담기



![image](https://user-images.githubusercontent.com/62678235/83711050-228c2280-a65d-11ea-8ef3-179b95871667.png)



> ### **개선과제**





![image](https://user-images.githubusercontent.com/62678235/83714611-3c7e3300-a666-11ea-9afc-b85c57ef95e1.png)
