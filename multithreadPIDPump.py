import os
import glob
import time
import threading
import readMaxim
import readHSR 
import SSRControl
from RPi import GPIO
#for data input
import sys
from select import select


class TaskControlPID(threading.Thread): 

    #default target temp is 118C
    def __init__(self, taskid = 0, dataPump = None, pTarget = 11.0): 
        threading.Thread.__init__(self) 
	self.lok = threading.Lock()
        self.taskid = taskid
        self._stopevent = threading.Event( ) 
        self.dataPump = dataPump
	
	self.currentDrive = 0
	#init regulator values
#	self.m_timeStep = 0.05
	self.m_timeStep = 1
	self.m_targetPressure = pTarget
	self.m_latestPressure = 9.0
	self.m_latestPower = 0.0
	self.m_latestPower2 = 0.0
	#init PID values
	self.m_PIDBASE = 25
	self.m_pGain = 0.5 #20.0 #100.0 #0.6
	self.m_iGain = 0.0 #1.0 
	self.m_iState = 0.0 
	self.m_iMin  = -self.m_PIDBASE
	self.m_iMax  = self.m_PIDBASE
	self.m_dGain = 0.0#30.0 #1.0
	self.m_dState = 0.0

    #rythmes hauts et bas
    def rythmeHaut(self):
        self.m_timeStep = 0.1

    def rythmeBas(self):
        self.m_timeStep = 1
 
	
    #based on James Ward's PID algorithm
    def pid_update(self,error = 0.0, position = 0.0, pt= 0):
	if( pt == 0):
		# calculate proportional term
		pTerm = self.m_pGain * error
	else:
		#Add Proportional on Measurement, for P_ON_M algorithm
      		pTerm = -(self.m_pGain * (position - self.m_latestPressure));
		if(pTerm > self.m_iMax ):
			pTerm = self.m_iMax
		if(pTerm < self.m_iMin ):
			pTerm = self.m_iMin

	# calculate integral state with appropriate limiting
	self.m_iState += error
	if ( self.m_iState > self.m_iMax ):
		self.m_iState = self.m_iMax
	if ( self.m_iState < self.m_iMin ):
		self.m_iState = self.m_iMin

	#calculate integral term
	iTerm = self.m_iGain * self.m_iState

	#calculate derivative term
	dTerm = self.m_dGain * (self.m_dState - position)
	self.m_dState = position

	return pTerm + dTerm + iTerm


    def run(self):
    	print "Thread PID no", self.taskid, "is readry!\n > PID pump power!"
	
	drive = 0.0
	lastdrive = 0.0

	#based on James Ward's PID algorithm	
	while not self._stopevent.isSet(): 
		#get user entry
#        	rlist, _, _ = select([sys.stdin], [], [], 0.005)
		rlist = 0
        	if rlist:
                	cP=cI=cD=0.0
			s = sys.stdin.readline()
                	try:
                       		sP,sI,sD = s.split(" ")
                       		cP=float(sP)
                       		cI=float(sI)
                       		cD=float(sD)
                	except ValueError:
                        	print "Error conversion, NaN"
#                	print "Entered:",s," cP=",cP," cI=",cI," cD=",cD
			print "***********************************************************"
			print "oldP=",self.m_pGain,"oldI=",self.m_iGain,"oldD=",self.m_dGain
                	print "newcP=",cP," cI=",cI," cD=",cD
			print "***********************************************************"
			self.m_pGain = cP
			self.m_iGain = cI
			self.m_dGain = cD
						

		#PID computation
		#timestamp
		next = time.time()
		#get current pressure
		latestPressure = self.dataPump.getRange()
		#controle de la pompe
		lastdrive = drive	
		
		#calculate next time step
		next += self.m_timeStep
		#get current target pressure
		cTargetPressure = self.getTargetPressure()

		#calculate PID update
		drive = self.pid_update( cTargetPressure - latestPressure, latestPressure, 0)
						
		#clamp the output power to sensible range
		if ( drive > self.m_PIDBASE ):
			drive = self.m_PIDBASE
		if ( drive < -self.m_PIDBASE ):
			drive = -self.m_PIDBASE

		#update the pump power (with PWM) if last state changed
		if ( 1 ):#drive != lastdrive ):
			drv = self.m_latestPower + drive
#			drv = 50 + drive
			if(drv < 50):
				drv = 50
			if(drv > 100):
				drv = 100
#			print "Bar/",latestPressure,"/Target/",cTargetPressure,"/Drv/",drv,"/raw drive/",drive
			#SSRControl.setPumpPWM( 50 + (drv/2) )
			#moyenne
			#drv = (drv + self.m_latestPower + self.m_latestPower2)/3
			self.setCurrentDrive( drv )
			if(self.m_latestPower != drv):
				SSRControl.setPumpPWM( drv )
			self.m_latestPower2 = self.m_latestPower
			self.m_latestPower = drv


		#wait the remaining time (typically, slot = 1 second)
		remain = next - time.time()
		if ( remain > 0.0 ):
#			print "sleeping ", remain
			self._stopevent.wait(remain)

    def stop(self): 
	print "stopping thread no", self.taskid
        self._stopevent.set( ) 

    def getTargetPressure(self):
        #protect concurrent access with mutex
	self.lok.acquire()
        tt = self.m_targetPressure 
        self.lok.release()
	return tt

    def setTargetPressure(self,press=9):
        #protect concurrent access with mutex
	self.lok.acquire()
        self.m_targetPressure = press
        self.lok.release()

    def getCurrentDrive(self):
        #protect concurrent access with mutex
        self.lok.acquire()
        tt = self.currentDrive
        self.lok.release()
        return tt

    def setCurrentDrive(self,drive=0):
        #protect concurrent access with mutex
        self.lok.acquire()
        self.currentDrive = drive
        self.lok.release()

