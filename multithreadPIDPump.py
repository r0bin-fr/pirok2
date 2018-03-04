import os
import glob
import time
import threading
import readMaxim
import readHSR 
import SSRControl
from RPi import GPIO

class TaskControlPID(threading.Thread): 

    #default target temp is 118C
    def __init__(self, taskid = 0, dataPump = None, pTarget = 9.0): 
        threading.Thread.__init__(self) 
	self.lok = threading.Lock()
        self.taskid = taskid
        self._stopevent = threading.Event( ) 
        self.dataPump = dataPump
	
	self.currentDrive = 0
	#init regulator values
	self.m_timeStep = 0.15
	self.m_targetPressure = pTarget
	self.m_latestPressure = 9.0
	self.m_latestPower = 0.0
	#init PID values
	self.m_PIDBASE = 50
	self.m_pGain = 0.6
	self.m_iGain = 0.01 
	self.m_iState = 0.0 
	self.m_iMin  = -self.m_PIDBASE
	self.m_iMax  = self.m_PIDBASE
	self.m_dGain = 0.0
	self.m_dState = 0.0
	
    #based on James Ward's PID algorithm
    def pid_update(self,error = 0.0, position = 0.0):
	# calculate proportional term
	pTerm = self.m_pGain * error

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
		drive = self.pid_update( cTargetPressure - latestPressure, latestPressure )
						
		#clamp the output power to sensible range
		if ( drive > self.m_PIDBASE ):
			drive = self.m_PIDBASE
		if ( drive < -self.m_PIDBASE ):
			drive = -self.m_PIDBASE

		#update the pump power (with PWM) if last state changed
		if ( drive != lastdrive ):
			drv = self.m_latestPower + drive
			if(drv < 50):
				drv = 50
			if(drv > 100):
				drv = 100
			print "Bar/",latestPressure,"/Target/",cTargetPressure,"/Drv/",drv
			#SSRControl.setPumpPWM( 50 + (drv/2) )
			self.setCurrentDrive( drv )
			SSRControl.setPumpPWM( drv )
			self.m_latestPower = drv

		#wait the remaining time (typically, slot = 1 second)
		remain = next - time.time()
		if ( remain > 0.0 ):
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

