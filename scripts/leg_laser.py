#!/usr/bin/python

import rospy
from sensor_msgs.msg import LaserScan
#from geometry_msgs.msg import Twist
from std_msgs.msg import String
from std_msgs.msg import Float32

import math
import numpy as np
from sklearn.cluster import DBSCAN
import matplotlib.pyplot as plt
import math
import time

class LegL():
	def __init__(self):
		self.rospy = rospy
		self.rospy.init_node('LegMonitoring', anonymous = True)
		self.rospy.loginfo("Starting Lower Limbs Monitoring")
		self.initParameters()
		self.initSubscribers()
		self.initPublishers()
		self.initVariables()
		self.mainControl()

	def initParameters(self):
		self.LegMonitoringTopic = self.rospy.get_param("~LegMonitoring_topic","/scan_rplidar")
		self.controlRate = self.rospy.get_param("~control_rate", 100)
		self.angle_min_new = self.rospy.get_param("~angle_min_new",155)
		self.angle_max_new = self.rospy.get_param("~angle_min_new",215)
		return

	def initPublishers(self):
		self.pubDist = self.rospy.Publisher("/distance", Float32, queue_size=10)
		self.pubDistF = self.rospy.Publisher("/distanceF", Float32, queue_size=10)
		return

	def initSubscribers(self):
		self.subPose = self.rospy.Subscriber(self.LegMonitoringTopic, LaserScan, self.callbackLaser)
		return

	def initVariables(self):
		self.rate = self.rospy.Rate(self.controlRate)
		self.angle_min = 0
		self.angle_max = 0
		self.scan_time = 0
		self.ranges = 0
		self.angle_increment = 0
		self.time_increment = 0
		self.range_min = 0
		self.range_max = 0
		self.change = False
		self.font = {'family': 'serif',
					'color':  'darkred',
					'weight': 'normal',
					'size': 9,
					}
		self.amostras = [[0,0],[0,0]]
		self.distAnt = 0
		self.distAtual = 0
		self.veloc = [0]
		self.mediaX = 0
		self.mediaY = 0
		self.k = 0
		"""----------------------------------  """

		#vetor com os parametros da formacao.
		#posicao 1 - a distancia entre os robos
		self.qDes = np.array([0.7, 0, 0, 0])

		return

	""" ---------------------------------- """
	def callbackLaser(self, msg):

		self.angle_min = msg.angle_min
		self.angle_max = msg.angle_max
		self.angle_increment = msg.angle_increment
		self.time_increment = msg.time_increment
		self.scan_time = msg.scan_time
		self.range_min = msg.range_min
		self.range_max = msg.range_max
		self.ranges = msg.ranges
		self.change = True

	""" ---------------------------------- """

	def legCluster(self):
		#Encontra os clusters
		clustering = DBSCAN(eps=0.05, min_samples=4).fit(self.cart)
		IDX = clustering.labels_
		#plot dos dados
		k = np.max(IDX)
		#ramdom das cores
		cmap = plt.cm.get_cmap('hsv', 4)

		#gera a variavel das medias
		medias = []
		for j in range(k+1):
			Xj = self.cart[IDX==j]
			Xj[:,0]=Xj[:,0] #*(-1)
			mediaX = np.mean(Xj[:,0])
			mediaY = np.mean(Xj[:,1])
			medias.append([mediaX,mediaY])
			stilo = '.'
			color = cmap(j)
			plt.scatter(Xj[:,0],Xj[:,1], c=color, marker=stilo)
			plt.text(mediaX, mediaY, 'leg ' + str(j+1), fontdict=self.font)
			plt.xlim([0, 1])
			plt.ylim([-0.5, 0.5])

		if medias != []:
			mediasArray = np.array(medias)
			self.mediaX = np.mean(mediasArray[:,0])
			self.mediaY = np.mean(mediasArray[:,1])
			plt.text(self.mediaX, self.mediaY, '*', fontdict=self.font)
			plt.text(self.mediaX+0.02, self.mediaY, 'Person', fontdict=self.font)
			self.amostras[1]=[self.mediaX, self.mediaY]
			self.distAnt = math.sqrt(math.pow(self.amostras[0][0],2)+math.pow(self.amostras[0][1],2))
			self.distAtual = math.sqrt(math.pow(self.amostras[1][0],2)+math.pow(self.amostras[1][1],2))
			self.end = time.time()
			tempo = (self.end-self.start)
			self.veloc.append((self.distAtual-self.distAnt)/(tempo*10))

			self.amostras[0] = self.amostras[1]

			msg1 = Float32()
			msg1.data = self.mediaX
			self.pubDist.publish(msg1)
			msg2 = Float32()
			msg2.data = self.qDes[0]
			self.pubDistF.publish(msg2)
		

		return

	def mainControl(self):
		plt.ion()
		while not self.rospy.is_shutdown():
			self.msg = LaserScan()
			if self.change:
				self.start = time.time()
				self.cartesiano = []
				angulo = self.angle_min
				anguloMin = self.angle_min_new
				anguloMax = self.angle_max_new
				# Vetor Range tem 1440 posicoes. /4 = 360! Logo, para acessar a posicao referente aquele angulo, so multiplicar por 4
				vetorRangeCropped = [anguloMin*4, anguloMax*4]

				
				incr = self.angle_increment
				for i in range(len(self.ranges)):
					# capturas as amostras nas distancias especificadas
					if not math.isnan(self.ranges[i]) and not math.isinf(self.ranges[i]) and ((i> vetorRangeCropped[0] and i< vetorRangeCropped[1])) and self.ranges[i]<0.7:
						self.cartesiano.append([self.ranges[i] * math.cos(angulo), self.ranges[i] * math.sin(angulo)])
					angulo = angulo + incr
					

				self.cart = np.array(self.cartesiano)

				if self.cartesiano != []:
					self.legCluster()

				else:
					msg1 = Float32()
					msg1.data = 0
					self.pubDist.publish(msg1)

				plt.grid()
				plt.pause(0.0001)
				plt.clf()

				self.change = False

			self.rate.sleep()

if __name__ == '__main__':
	try:
		legL = LegL()
	except rospy.ROSInterruptException:
		pass
