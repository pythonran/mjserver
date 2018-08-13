import KBEngine
from KBEDebug import *
import random

class Room(KBEngine.Entity):
	def __init__(self):
		KBEngine.Entity.__init__(self)
		KBEngine.addSpaceGeometryMapping(self.spaceID,None,"spaces/mjRoom")
		KBEngine.globalData["Room_%i" % self.spaceID] = self
		self.roomInfo = roomInfo(self.roomKey,self.playerMaxCount)
		self.game = None
		self.clearPublicRoomInfo()
		

	def enterRoom(self, EntityCall):
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			if seat.userId == 0:
				seat.userId = EntityCall.id
				seat.entity = EntityCall
				seat.score = 1000   #带入分数
				print("玩家进来了---"+str(seat.userId)+" 座位号为 "+str(i))
				EntityCall.changeRoomSeatIndex(i)
				self.base.CanEnterRoom(EntityCall)
				EntityCall.enterRoomSuccess(self.roomKey)
				return

	def changeRoomSuccess(self,entityID):
		self.roomInfo.clearDataByEntityID(entityID)

	def ReqLeaveRoom(self,EntityCall):
		#通知玩家base销毁cell
		EntityCall.base.onLeaveRoom()
		#让base向大厅要人
		self.base.leaveRoom(EntityCall.id)
		#清除该玩家坐过的椅子数据
		self.roomInfo.clearDataByEntityID(EntityCall.id)

	def setPublicRoomInfo(self):
		playerList = []
		for i in range(self.playerMaxCount):
			seatData =self.game.gameSeats[i]
			d={
				"userId":seatData.userId,
				"holdsCount":len(seatData.holds)
				}
			playerList.append(d)
		data = {
			"state" :self.game.state,
			"playerInfo":playerList,
			"button":self.game.button,
			"turn": self.game.turn,
			}
		self.public_roomInfo = data

	##清空游戏共享数据
	def clearPublicRoomInfo(self):
		playerList = []
		for i in range(self.playerMaxCount):
			d={
				"userId":0,
				"holdsCount":0,
				}
			playerList.append(d)
		data = {
			"state" :"idel",
			"playerInfo":playerList,
			"button":-1,
			"turn": -1,
			}
		self.public_roomInfo = data

	def reqGetRoomInfo(self,callerEntityID):
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			if seat.userId ==callerEntityID:
				if(seat.entity.client):
					seat.entity.client.onGetRoomInfo(self.public_roomInfo)

	def reqChangeReadyState(self, callerEntityID, STATE):
		print("callerEntityID reqChangeReadyState", callerEntityID)
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			if seat.userId ==callerEntityID:
				seat.ready = not STATE
				seat.entity.cell.playerReadyStateChange(seat.ready)
				print(seat.ready)
				break
		for i in range(len(self.roomInfo.seats)):
			seat = self.roomInfo.seats[i]
			if seat.ready  == False:
				return

		self.begin()

	def begin(self):
		print("全部就位---开始处理！")
		self.clearPublicRoomInfo()
		self.game = MJData(self.roomInfo,self.playerMaxCount)
		self.shuffle(self.game)
		self.deal(self.game)
		self.numOfMJ = len(self.game.mahjongs) - self.game.currentIndex
		self.cur_turn = self.game.button
		self.game.state = "playing"
		self.setPublicRoomInfo()
		seats = self.roomInfo.seats
		for i in range(len(seats)):
			if seats[i].entity.client:
				seats[i].entity.cell.game_holds_push(self.game.gameSeats[i].holds)
				#seats[i].entity.client.upDataClientRoomInfo(self.public_roomInfo)
				seats[i].entity.client.game_begin_push()

		print("游戏开始！")


		
	#洗牌
	def shuffle(self,game):
		mahjongs = game.mahjongs
		# 筒 (0 ~ 8 表示筒子)
		# 条 9 ~ 17表示条子
		# 万 18 ~ 26表示万
		# 27~33 表示东南西北，中发板
		for c in range(4):
			for i in range(34):
				mahjongs.append(i)
		random.shuffle(mahjongs)		#随机打乱牌  洗牌

	#发牌
	def deal(self,game):
		game.currentIndex = 0	#强制清0
		#每人13张 一共 13*人数  庄家多一张 
		seatIndex = game.button
		allFPCount = 13*self.playerMaxCount
		for i in range(allFPCount):
			self.mopai(game,seatIndex)
			seatIndex +=1
			seatIndex = seatIndex%self.playerMaxCount

		#庄家多摸最后一张
		self.mopai(game,game.button)
		#当前轮设置为庄家
		game.turn = game.button


	#摸牌
	def mopai(self,game,seatIndex):
		pai = game.mahjongs[game.currentIndex]
		game.gameSeats[seatIndex].holds.append(pai)
		game.currentIndex += 1

#----------------------------------------------------------------------------
#麻将信息类
class MJData:
	def __init__(self,roomInfo,maxPlayerCount):
		self.state = "idle"
		self.seatList = roomInfo.seats
		self.mahjongs = []
		self.currentIndex = 0  #当前发的牌在所有牌中的索引
		self.button = 1 #庄家位置
		self.turn = 0  #记录该谁出牌
		self.chuPai = -1
		self.gameSeats = []
		for i in range(maxPlayerCount):	
			seat = seatData(self,i,self.seatList[i].userId)
			self.gameSeats.append(seat)


#所有玩家的牌类信息
class seatData:
	def __init__(self,game,index,userId):
		self.game = game   #游戏对象
		self.seatIndex = index   #玩家座位索引
		self.userId = userId		#玩家id
		self.holds = []  #持有的牌
		self.folds = []  #打出的牌


#房间信息
class roomInfo:
	def __init__(self,roomKey,maxPlayerCount):
		self.id = roomKey
		self.seats = []
		for i in range(maxPlayerCount):
			seat = seat_roomInfo(i)
			self.seats.append(seat)

	def clearData(self):
		for i in range(len(self.seats)):
			self.clearDataBySeat(i,False)

	def clearDataBySeat(self,index,isOut = True):
		s = self.seats[index]
		if isOut:
			s.userId = 0
			s.entity = None
		s.ready = False
		s.score = 0
		s.seatIndex = index

	def clearDataByEntityID(self,entityID,isOut = True):
		for i in range(len(self.seats)):
			if self.seats[i].userId == entityID:
				self.clearDataBySeat(i,isOut)
				break



#椅子信息
class seat_roomInfo:
	def __init__(self,seatIndex):
		self.userId = 0
		self.entity = None
		self.score = 0
		self.ready = False
		self.seatIndex = seatIndex