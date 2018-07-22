import os
import glob
import time
import threading
import readHSR
import sys
import subprocess

#from hx711_python_2 import HX711                # import the class HX711
#import RPi.GPIO as GPIO         # import GPIO

PIROK_RATIO = 640.0 #ratio estime
PIROK_POIDS0 = 8728214 #poids a vide

class TaskPrintWeight(threading.Thread): 

    def __init__(self, taskid = 0, mData = readHSR.HSRData()): 
        threading.Thread.__init__(self) 
        self.taskid = taskid
        self._stopevent = threading.Event( ) 
	self.mData = mData
	self.tempo = 0.5
	#mutex to protect concurrent access to chipset 
	self.lok = threading.Lock()
	self.pbassinelle = 0.0
	self.ratio = PIROK_RATIO
	# Create an object hx which represents hx711 chip
#      	hx = HX711(dout_pin=19, pd_sck_pin=20, gain_channel_A=128, select_channel='A')
	# Before we start, reset the hx711 
 #       result = hx.reset()
 #       if result:                      
 #              	print('Hx711 Ready to use')
 #       else:
 #              	print('Hx711 not ready')
	# measure tare and save the value as offset for current channel
 #       result = hx.zero(times=10)

	#set ratio to known value
	#hx.set_scale_ratio(scale_ratio=318.0)
 #       hx.set_scale_ratio(scale_ratio=738.34)#640.65)
	
	#attribute object to use it later
	#self.hx = hx

    def pese_raw(self):
	#protect access to hx711 with mutex
	self.lok.acquire()
	#pese brut
	task = subprocess.Popen(['sudo','cat','/sys/kernel/hx711/scale'],stdout=subprocess.PIPE)
        val = int(task.stdout.readline())
	#release mutex
	self.lok.release()
	return val

    def pese_raw2(self):
	t = self.pese_raw() - PIROK_POIDS0
        return (float(t)/ self.ratio)

    def met_a_zero(self):
	self.pbassinelle = self.pese_raw2() 

    def pese(self):
	#t = self.pese_raw() - PIROK_POIDS0
	return self.pese_raw2() - self.pbassinelle 

    def pese_puis_raz(self):
        t = self.pese_raw2()
	t2 = t - self.pbassinelle
	self.pbassinelle = t
	return t2
    
    #def rythmeHaut(self):
	#set fast tempo 100ms
	#self.tempo = 0.1
	#reset scale
	#self.met_a_zero()

    #def rythmeBas(self):
	#set slow tempo 1sec
	#self.tempo = 1

    def run(self):
    	print "thread capteur no", self.taskid, " HX711 is readry!"
	#RAZ
	self.met_a_zero()
	#pesee
	while not self._stopevent.isSet():
		#6 lectures pour faire une moyenne
		#val = self.hx.get_weight_mean(times=6)
		val = self.pese_puis_raz() #self.pese()
		#si la valeur est correcte, on la stocke
		#print "weight=",val
		self.mData.setRange(val)
		#attende de x ms entre chaque lecture
		self._stopevent.wait(self.tempo)


    def stop(self): 
	print "stopping thread no", self.taskid
        self._stopevent.set( ) 

