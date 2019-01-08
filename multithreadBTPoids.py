import os
import glob
import time
import threading
import binascii
import struct
import time
import sys
from bluepy.bluepy.btle import UUID, Peripheral, Characteristic, BTLEException
import readHSR

class TaskPrintWeight2(threading.Thread): 

    def __init__(self, taskid = 0, mData = readHSR.HSRData()): 
        threading.Thread.__init__(self) 
	self.taskid = taskid
        self._stopevent = threading.Event( ) 
	self.mData = mData
	self.p = 0
	self.cht = 0
	self.previousT = time.time()
	self.interval = 0.5
	self.Tlast = self.Tnow = self.Tmax = self.Tmin = 0
 	self.T_dif_now = self.T_dif_last = 0
	self.TminLoopCount = 0
	self.TmaxLoopCount = 0
	self.isBTNOK = 1
	self.tempo = 1
	
    def disconnect(self):
	self.isBTNOK = 1
	if self.p != 0:
		try:
                	self.p.disconnect()
			self.p = 0
                except:
                        print "disconnect error"

    def connect(self):
	#UUID where temp is stored
#	tempc_uuid = UUID(0x0021)
	tempc_uuid = UUID(0x2221)
	self.isBTNOK = 1

	#connection...
	while not self._stopevent.isSet() and self.isBTNOK:
		try:
			print("Connection...")
			#my bluefruit address
			self.p = Peripheral("EE:1B:17:8F:A4:5D", "random")
					    #EE:1B:17:8F:A4:5D
    			print("OK!\ngetCharacteristics")
			#for ch in self.p.getCharacteristics():
     			#	print str(ch)
    			self.cht = self.p.getCharacteristics(uuid=tempc_uuid)[0]
			print("Done!")
			self.isBTNOK = 0

		except BTLEException as e:
			print "CONNECT - BTLEException : {0}".format(e)
			self.disconnect()

		except:
			print 'CONNECT - Other error! ',sys.exc_info()[0]
			self.disconnect()

		#wait 3 second before try again
		if(not self._stopevent.isSet()):
			self._stopevent.wait(3) 

    #extract float data from BLE struct
    def extractBLEval(self,data):
	val = binascii.b2a_hex(data)
        val = binascii.unhexlify(val)
        val = struct.unpack('f', val)[0]
        return float(val)

    def read(self):
	#read loop
        while not self._stopevent.isSet():
                try:
#			print "BT READ, get value..."
			tc=self.extractBLEval(self.cht.read())
			print "poids=",tc
                        return tc

                except BTLEException as e:
                        print "BT READ - BTLEException : {0}".format(e)
			self.disconnect()

                except:
                        print 'BT READ - Other error! ',sys.exc_info()[0]
			self.disconnect()

		#disconnect
		self.disconnect()
                #wait 1 second before try again
                self._stopevent.wait(1)
		#reconnect
		self.connect()


    def rythmeHaut(self):
        #set fast tempo 100ms
        self.tempo = 0.1

    def rythmeBas(self):
        #set slow tempo 1sec
        self.tempo = 1


    #main task body
    def run(self):
    	print "thread BT is readry!"
	retBTNOK = 1
	#try to connect to BT sensor
	self.connect()

	#do a 
	while not self._stopevent.isSet(): 
			tc = self.read()
			#upgrade data in shared memory 	
			self.mData.setRange(tc)
			#wait a little
			self._stopevent.wait(self.tempo) 

    def stop(self): 
	print "stopping thread BT"
        self._stopevent.set( ) 
	#give a chance do disconnect nicely
	time.sleep(1)
	#disconnect if it was not done before
	self.disconnect()

