#!/usr/bin/python

# -*- coding: latin-1 -*-
import math
import time
import calendar
import signal
import sys
from subprocess import call
import mydigole
import myencoder
import random
import readMaxim
import readHSR
import readFlow
import multithreadHum
import multithreadRange
import multithreadADC
import multithreadTemp
import SSRControl
import multithreadPID

#Temperature file backup
TEMPBACKUP = '/home/pi/pirok2/settings.txt'
DEFAULT_BOILER_TEMP = 115
BOOST_BOILER_TEMP   = 126
SCREEN_UPDATE_TIME  = 0.5  #500ms
OLED_TIMEOUT 	    = 40   #in seconds
OLED_FADE_TIMEOUT   = 5    #in seconds
OLED_WHITE_STD	    = 254
OLED_WHITE_FADE	    = 98 #76
EXTRACTION_TIMEOUT   = 12   #in seconds

#Encoder
A_PIN = 5
B_PIN = 6
SW_PIN= 26
TOUCH_PIN= 12
#water gauge value
WG_RANGE_MIN = 224.0
WG_RANGE_MAX = 50.0

#Parametres font / couleur
cNoir = 0#4 #254
cBlanc = OLED_WHITE_STD #254 #4
cB1=cB2=cB3=63
cBleu = 82 #70 #0x32 #2
cRouge = 0xC4 #224
cVert = 28
cGris = cBleu #76
fBig=200
fSmall=201

#global values
maximT1 = readMaxim.MaximData(0)
maximT2 = readMaxim.MaximData(0)
dhtData = readMaxim.MaximData(0)
hsrData = readHSR.HSRData(0)
barData = readHSR.HSRData(0)
flowData = readFlow.FlowData()
pumpRate = 100

#tasks
task1 = multithreadTemp.TaskPrintTemp(0,maximT1)
task2 = multithreadTemp.TaskPrintTemp(1,maximT2)
task4 = multithreadHum.TaskPrintHum(3,dhtData)
task5 = multithreadRange.TaskPrintRange(4,hsrData)
task9 = multithreadADC.TaskPrintBar(8,barData)
#**** PID setup: *****
#maximT2 is the group temperature (for boost algorithm), maximT1 is the boiler temp sensor, default target value = 115C
temptarget=115
task6PID = multithreadPID.TaskControlPID(6,maximT2,maximT1,temptarget)

#how to quit application nicely
def quitApplicationNicely():
	done = True
	saveSettings()
	digole.setScreen(0)
	task6PID.stop()
	task1.stop()
	task2.stop()
	task4.stop()
	task5.stop()
	task9.stop()
	time.sleep(0.1)
#	print "now join task 1"
#	task1.join()
	print "now exit"
    	sys.exit(0)

#signal handler
def signal_handler(signal, frame):
	print('You pressed Ctrl+C!')
	quitApplicationNicely()

def getTempTarget(): 
	print "getTemp"
	try:
                tfile = open(TEMPBACKUP, "r")
                line = tfile.readline()
                tfile.close()
		#conversion en entier
		ttarget = int(line)
 	except IOError as e:
		print "Erreur fichier ", TEMPBACKUP," (ouverture, lecture ou fermeture)"
                print "I/O error({0}): {1}".format(e.errno, e.strerror)
		ttarget = 0
        except:
                print "Erreur fichier ", TEMPBACKUP," (ouverture, lecture ou fermeture)", sys.exc_info()[0]
		ttarget = 0
	return ttarget

def loadSettings():
	global temptarget
	print "loadsettings"
	val = getTempTarget()
	#default: 115C
	if(val == 0):
		temptarget = DEFAULT_BOILER_TEMP
		print "Load settings: using default temptarget value of ", DEFAULT_BOILER_TEMP
	else:
		temptarget = val	
		print "Load settings: temptarget value is now ",temptarget,"C"
	#apply settings immediately
	task6PID.setTargetTemp(temptarget)

def saveSettings():
	#recuperation de la consigne reelle
	if(consigneBoost == 1):
        	temptosave = lastTargetTemp	
	else:
		temptosave = temptarget
	#a-t-on vraiment besoin d'ecrire dans la flash? (abime)
	val = getTempTarget()
	if ((val > 0) and (val == temptosave)):
		print "pas besoin d'ecrire dans la flash"
		return
	#nouvelle valeur: ecriture dans un fichier  
	buf = "%d" % temptosave
	buf = buf + "\n"
	print "Saving temptarget", buf, "ok?"
	try:
                tfile = open(TEMPBACKUP, "w")
                tfile.write(buf)
                tfile.close()
 	except IOError as e:
		print "Erreur fichier ", TEMPBACKUP," (ouverture, lecture ou fermeture)"
                print "I/O error({0}): {1}".format(e.errno, e.strerror)
        except:
                print "Erreur fichier ", TEMPBACKUP," (ouverture, lecture ou fermeture)", sys.exc_info()[0]

#translate water range into value to display
def getWLvalue(range):
	if(range > WG_RANGE_MIN):
		range = WG_RANGE_MIN
	if(range < WG_RANGE_MAX):
		range = WG_RANGE_MAX
	
	rpercent = 1.0 - ((range - WG_RANGE_MAX) / (WG_RANGE_MIN-WG_RANGE_MAX))
#	print "Range = ",rpercent * 100,"% -val=",int(rpercent * 6)
	return int(rpercent * 6)


def ihm_extraction(tboil,tnez,temp,hum,range,bar,isPumpRunning,pumpRate):
	txadj = 5
	#temp nez	
	digole.setFont(fSmall)
	digole.setFGcolor(cRouge)
	digole.printTextP(5+txadj,20,"c")
	if( consigneBoost == 0 ):
		digole.setFGcolor(cBlanc)
	if tboil > 200:
		tboil = 199.0
	if tboil < 0:
		tboil = 0.0
	st=" {0:.1f}+   ".format(tnez)
	#st=" {0:.0f}/{1:.0f}+   ".format(tboil, temptarget)
	digole.printText(st)

	#timer
	txadj=5
	digole.setFGcolor(cVert)
	digole.printTextP(5,40,"d")	
	digole.setFGcolor(cBlanc)
	st="{0:.1f}".format(pumpOfficialChrono)#(time.time() - pumpTimestamp))
	digole.printTextP(39,40,str(st)+"\'    ")

	#puissance pompe
	digole.setFGcolor(cBleu)
	digole.printTextP(12,57,"b")	
	digole.setFGcolor(cBlanc)
	st="{0:.0f}a  ".format(pumpRate)
	digole.printTextP(39,60,st)

	#pression extraction
	digole.setFGcolor(cBleu)#242)
	digole.setFont(fSmall)	
	digole.printTextP(40,110,"b")
	digole.setFont(fBig)
	st="{0:2.1f}".format(bar)
	digole.printText(str(st)+" ")

	
#update the screen
def digole_update(tboil,tnez,temp,hum,range,bar,isPumpRunning,pumpRate):
	#display a specific GUI when extracting
	if(isPumpRunning):
		return ihm_extraction(tboil,tnez,temp,hum,range,bar,isPumpRunning,pumpRate)
		
	#temp chaudiere	
	digole.setFont(fSmall)
	digole.setFGcolor(cRouge)
	digole.printTextP(5,20,"c")
	if( consigneBoost == 0 ):
		digole.setFGcolor(cBlanc)
	if tboil > 200:
		tboil = 199.0
	if tboil < 0:
		tboil = 0.0
	st="{0:.0f}/{1:.0f}+   ".format(tboil, temptarget)
	digole.printText(st)
	
	#pression extraction
#matbf	tshiftx=15
	tshiftx=5
	digole.setFGcolor(cVert)
	digole.printTextP(89+tshiftx,20,"d")	
	digole.setFGcolor(cBlanc)
#	digole.printTextP(116+tshiftx,20,"     ")
	digole.printText2(0,1," ")
	#st="{0:.1f}".format(random.uniform(5, 10))
	st="{0:.1f}  ".format(bar)
#	digole.printTextP(118+tshiftx,20,str(st)+"b")
	digole.printTextP(118+tshiftx,20,str(st))
	
	#niveau eau
	digole.setFont(fBig)
	digole.setFGcolor(cBleu)
	digole.printTextP(30,80,chr(ord('A')+getWLvalue(range)))

	#temperature
	digole.setFGcolor(cBlanc)
	st="{0:.1f}".format(tnez)
	digole.printTextP(50,80,str(st)+"+ ")

    	#get the current time
    	if(int(time.time())%2 == 0):    
		stime=time.strftime('%H.%M')
	else:
		stime=time.strftime('%H\'%M')

	#temperature ambiante et hygrometrie
	digole.setFGcolor(cBlanc)
	digole.setFont(fSmall)
#	st="{0:.1f}+ / {1:.0f}a".format(temp,hum)
#	digole.printText2(3,6,st)
#	digole.printText2(1,6,stime+" ")
	digole.printTextP(5,118,stime+" ")

	st="{0:.1f}+/{1:.0f}a".format(temp,hum)
	digole.setFGcolor(cGris)
	digole.printTextP(66,118,st)
#	digole.printText2(1,6,stime+st)



# screen on with timeout
def screenOnWithTimeout():
	global digole,flagTouch,touchTstamp,cBlanc
	digole.setScreen(1)
        flagTouch=1
        touchTstamp = time.time()
	cBlanc = OLED_WHITE_STD

#screen off, timeout disabled
def screenOffNow():
	global digole,flagTouch,cBlanc
        digole.setScreen(0)
        digole.clearScreen()
	#digole.setDrawDir(2)
	digole.setOLEDOFF()
        flagTouch=0
	cBlanc = OLED_WHITE_STD



# -------- Main Program Loop -----------
#intercept control c for nice quit
signal.signal(signal.SIGINT, signal_handler)
done = False
#init vars
loadSettings()
lastTargetTemp = temptarget
consigneBoost = 0

#digole screen init
digole = mydigole.DigoleMaster()
digole.setFGcolor(cNoir)
digole.setBGcolor()
digole.clearScreen()

#encoder init
encoder_val = temptarget
encoder = myencoder.RotaryEncoder(A_PIN, B_PIN, SW_PIN, TOUCH_PIN)
encoder.start()

#start multitasking
task1.start()
task2.start()
task4.start()
task5.start()
task9.start()
task6PID.start()

#default pump rate
SSRControl.setPumpPWM( pumpRate, 1 )
isPumpRunning = 0
timeLastFlowRecorded = 0
pumpTimestamp = 0
pumpOfficialChrono = 0

flagTouch=1
touchTstamp = time.time()
#init data before loop
fl = flowData.getFlow()

#infinite loop
while not done:
	#try to respect as much as possible the time slot
    	timestamp = time.time()

	#get flow update
	fl = flowData.getFlow()
	#print "flow=",fl
	if(fl > 0.0):
		print "flow detected:", fl
		screenOnWithTimeout()
		#if a new extraction is starting...
		if(isPumpRunning == 0):
			pumpTimestamp = time.time()
			digole.clearScreen()
		isPumpRunning = 1
		timeLastFlowRecorded = time.time()
		pumpOfficialChrono = time.time() - pumpTimestamp
	else:
		#allow some time (15s) to play with pump pressure (case when not enough power to trigger flowmeter)
		if((time.time() - timeLastFlowRecorded) > EXTRACTION_TIMEOUT):
			#if extraction is finishing...
			if(isPumpRunning):
				digole.clearScreen()
			isPumpRunning = 0
			#make sure we put back the full power after use
			if(pumpRate < 100):
				pumpRate = 100
				SSRControl.setPumpPWM( pumpRate )

	#get touch update
        if encoder.get_bTouched():
        	print "Touche!"
		if flagTouch:
			#prevent multi touch: wait 2 seconds before screen off
			if(timestamp - touchTstamp > 2):
				screenOffNow()
			#if touched during fadeoff, power on again
			if (timestamp - touchTstamp) >= (OLED_TIMEOUT - OLED_FADE_TIMEOUT):
				screenOnWithTimeout()
		else:
			screenOnWithTimeout()

	#timeout on screen ON
	if flagTouch:
		if (timestamp - touchTstamp) >= OLED_TIMEOUT:
			screenOffNow()
		else:
			if (timestamp - touchTstamp) >= (OLED_TIMEOUT - OLED_FADE_TIMEOUT):
				#fade whites
				cBlanc = OLED_WHITE_FADE
					
	#get switch update
    	if encoder.get_bPushed():
        	print "switch on!"
		screenOnWithTimeout()
		#were we already in boost mode?
		if(consigneBoost == 0):
			lastTargetTemp = temptarget
			temptarget = BOOST_BOILER_TEMP
			consigneBoost = 1
		else:
			temptarget = lastTargetTemp
			consigneBoost = 0
		#apply settings immediately
		task6PID.setTargetTemp(temptarget)
	
	#get encoder updates
	delta = encoder.get_cycles()
	#did we turn the encoder?
    	if delta!=0:	
		#turn on screen
		screenOnWithTimeout()

		#only update pump when extracting, and temp when idle
		if(isPumpRunning):
			#update pump rate
			pumpRate += (2*delta)
			if(pumpRate > 100):
				pumpRate = 100
			if(pumpRate < 1):
				pumpRate = 1
			SSRControl.setPumpPWM( pumpRate )
		else:
			#update temp target
			if(consigneBoost == 0):
				temptarget += delta
				#dont go too far
				if(temptarget > BOOST_BOILER_TEMP):
					temptarget=BOOST_BOILER_TEMP
				#dont go too low
				if(temptarget < 100):
					temptarget=100
				print "new temp target=", temptarget
				#apply settings immediately
				task6PID.setTargetTemp(temptarget)

	#get values update
	tboil=maximT1.getTemp()
	tnez=maximT2.getTemp()
	t4,h4 = dhtData.getTempHum()
	r5 = hsrData.getRange()
	b9 = barData.getRange()
	#update the screen
#	digole_update(tboil,tnez,t4,h4,r5,b9)
	digole_update(tboil,tnez,t4,h4,r5,b9,isPumpRunning,pumpRate)
    
    	#only sleep the time we need to respect the clock
    	remainingTimeToSleep = time.time() - timestamp
    	remainingTimeToSleep = SCREEN_UPDATE_TIME - remainingTimeToSleep
    	if(remainingTimeToSleep > 0):
#		print "time to sleep=",remainingTimeToSleep
       		time.sleep(remainingTimeToSleep)

	   
#end the tasks nicely
quitApplicationNicely()

