import os
import glob
import time
import threading
import readMaxim
import subprocess

#import Adafruit_DHT
#import RPi.GPIO as pigpio
#import pigpio
#import DHT22

class TaskPrintHum(threading.Thread): 

    def __init__(self, taskid = 0, mData = readMaxim.MaximData()): 
        threading.Thread.__init__(self) 
        self.taskid = taskid
        self._stopevent = threading.Event( ) 
	self.mData = mData

    def run(self):
    	print "thread capteur no", self.taskid, "is readry!"
	while not self._stopevent.isSet():
		timestamp = time.time()
		
		try:
			task = subprocess.Popen(['sudo','python','/home/pi/pirok2/AdafruitDHT.py','2302','17'],stdout=subprocess.PIPE)
			t,h = task.stdout.readline().split(' ')
			temperature = float(t)
			humidity = float(h)
		except:
			humidity = 0
			temperature = 0

		if ( humidity == 0 ) and (temperature == 0):
			print "Pas de donnees"
      		else:
			#print 'Time={0:d} Temp={1:0.1f}*C  Humidity={2:0.1f}%'.format((int(time.time())),temperature, humidity)	
			self.mData.setTempHum(temperature, humidity)

		#wait for 30 seconds before new read, we don't need so much updates on the hygrometry
		self._stopevent.wait(30)

    def stop(self): 
	print "stopping thread no", self.taskid
        self._stopevent.set( ) 
