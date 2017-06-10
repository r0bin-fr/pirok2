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
import multithreadHum
import multithreadRange
import multithreadADC

#Temperature file backup
TEMPBACKUP = '/home/pi/pirock/settings.txt'
DEFAULT_BOILER_TEMP = 115
BOOST_BOILER_TEMP   = 124
SCREEN_UPDATE_TIME  = 0.5  #500ms
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
cBlanc = 254 #254 #4
cB1=cB2=cB3=63
cBleu = 0x32 #2
cRouge = 0xC4 #224
cVert = 28
fBig=200
fSmall=201

#global values
dhtData = readMaxim.MaximData(0)
hsrData = readHSR.HSRData(0)
barData = readHSR.HSRData(0)

#tasks
task4 = multithreadHum.TaskPrintHum(3,dhtData)
task5 = multithreadRange.TaskPrintRange(4,hsrData)
task9 = multithreadADC.TaskPrintBar(8,barData)

#how to quit application nicely
def quitApplicationNicely():
	done = True
	saveSettings()
	digole.setScreen(0)
	task4.stop()
	task5.stop()
	task9.stop()
	time.sleep(0.1)
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


#update the screen
def digole_update(temp,hum,range,bar):
    	#display the current time
    	if(int(time.time())%2 == 0):    
		stime=time.strftime('%H:%M')
	else:
		stime=time.strftime('%H %M')

	#temp chaudiere	
	digole.setFont(fSmall)
	digole.setFGcolor(cRouge)
	digole.printTextP(5,20,"c")
	if( consigneBoost == 0 ):
		digole.setFGcolor(cBlanc)
	st=temptarget
	digole.printText(str(st)+"+   ")

	#pression extraction
	digole.setFGcolor(cVert)
	digole.printTextP(89,20,"d")	
	digole.setFGcolor(cBlanc)
	digole.printTextP(116,20,"     ")
	digole.printText2(0,1," ")
	#st="{0:.1f}".format(random.uniform(5, 10))
	st="{0:.1f}".format(bar)
	digole.printTextP(118,20,str(st)+"b")
	
	#niveau eau
	digole.setFont(fBig)
	digole.setFGcolor(cBleu)
	digole.printTextP(30,80,chr(ord('A')+getWLvalue(range)))

	#temperature
	digole.setFGcolor(cBlanc)
	st="{0:.1f}".format(random.uniform(92, 95))
	digole.printTextP(50,80,str(st)+"+ ")

	#temperature ambiante et hygrometrie
	digole.setFGcolor(cBlanc)
	digole.setFont(fSmall)
#	digole.printText2(4,6,"23+ / 40a")
#	digole.printText2(4,6,st)
	st="{0:.1f}+/{1:.1f}a".format(temp,hum)
	digole.printText2(3,6,st)

	
			
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
task4.start()
task5.start()
task9.start()

flagTouch=1
#infinite loop
while not done:
	#try to respect as much as possible the time slot
    	timestamp = time.time()
	
	#get touch update
        if encoder.get_bTouched():
        	print "Touche!"
		if flagTouch:
			digole.setScreen(0)
			flagTouch=0
		else:
			digole.setScreen(1)
                        flagTouch=1		

	#get switch update
    	if encoder.get_bPushed():
        	print "switch on!"
		#were we already in boost mode?
		if(consigneBoost == 0):
			lastTargetTemp = temptarget
			temptarget = BOOST_BOILER_TEMP
			consigneBoost = 1
		else:
			temptarget = lastTargetTemp
			consigneBoost = 0
			
	#get encoder updates
	delta = encoder.get_cycles()
	#did we turn the encoder?
    	if delta!=0:	
		print "encoder triggered, delta=", delta
		if(consigneBoost == 0):
			temptarget += delta
			print "new temp target=", temptarget
		

	#get values update
	t4,h4 = dhtData.getTempHum()
	r5 = hsrData.getRange()
	b9 = barData.getRange()
#	print "Temp=",t4," Humidity=",h4," Range=",r5
	#update the screen
	digole_update(t4,h4,r5,b9)
    
    	#only sleep the time we need to respect the clock
    	remainingTimeToSleep = time.time() - timestamp
    	remainingTimeToSleep = SCREEN_UPDATE_TIME - remainingTimeToSleep
    	if(remainingTimeToSleep > 0):
#		print "time to sleep=",remainingTimeToSleep
       		time.sleep(remainingTimeToSleep)

	   
#end the tasks nicely
quitApplicationNicely()

