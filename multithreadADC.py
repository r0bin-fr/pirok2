import os
import glob
import time
import threading
import readHSR
import Adafruit_ADS1x15


class TaskPrintBar(threading.Thread): 

    def __init__(self, taskid = 0, mData = readHSR.HSRData()): 
        threading.Thread.__init__(self) 
        self.taskid = taskid
        self._stopevent = threading.Event( ) 
	self.mData = mData
	self.buffer = 0.0

    def run(self):
    	print "thread capteur no", self.taskid, "is readry!"
	
	#configure ADC to read values until 6V
	GAIN = 2/3
	#init ADC chipset
	adc = Adafruit_ADS1x15.ADS1015()

	while not self._stopevent.isSet(): 
    		#read ADC channel 0 three times in order to get an average value
    		val1 = adc.read_adc(0, gain=GAIN)
    		val2 = adc.read_adc(0, gain=GAIN)
    		val3 = adc.read_adc(0, gain=GAIN)
		valADC = (val1+val2+val3)/3 
		#convert in volts
		valADCvolt = (valADC * 6.144) / 2047
		#convert in bar
		#0 psi outputs 0,52v 150 psi outputs 2,5v 300 psi outputs 4,5v
		#print("valeur pression en volt",valADCvolt)
		valueCapteurPression = (20.6843*(valADCvolt-0.52))/4
		#print("valeur presion en bar=",valueCapteurPression)
		#stockage de valeur		
		self.mData.setRange(valueCapteurPression)
		self._stopevent.wait(0.5) 


    def stop(self): 
	print "stopping thread no", self.taskid
        self._stopevent.set( ) 

