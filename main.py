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

#Temperature file backup
TEMPBACKUP = '/home/pi/pirock/settings.txt'
DEFAULT_BOILER_TEMP = 115
BOOST_BOILER_TEMP	= 124
SCREEN_UPDATE_TIME  = 0.5  #500ms
#Encoder
A_PIN = 5
B_PIN = 6
SW_PIN= 13

#Parametres font / couleur
cNoir = 0#4 #254
cBlanc = 254 #254 #4
cB1=cB2=cB3=63
cBleu = 0x32 #2
cRouge = 0xC4 #224
cVert = 28
fBig=200
fSmall=201

#how to quit application nicely
def quitApplicationNicely():
	done = True
	saveSettings()
	digole.setScreen(0)
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

#update the screen
wval=0
def digole_update():
	global wval
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
	st="{0:.1f}".format(random.uniform(5, 10))
	digole.printTextP(118,20,str(st)+"b")
	
	#niveau eau
	digole.setFont(fBig)
	digole.setFGcolor(cBleu)
	digole.printTextP(30,80,chr(ord('A')+wval))
	wval = wval + 1
	if(wval >= 6):
		wval = 0

	#temperature
	digole.setFGcolor(cBlanc)
	st="{0:.1f}".format(random.uniform(92, 95))
	digole.printTextP(50,80,str(st)+"+ ")

	#temperature ambiante et hygrometrie
	digole.setFGcolor(cBlanc)
	digole.setFont(fSmall)
	digole.printText2(4,6,"23+ / 40a")
	
	
			
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
encoder = myencoder.RotaryEncoder(A_PIN, B_PIN, SW_PIN)
encoder.start()

while not done:
	#try to respect as much as possible the time slot
    	timestamp = time.time()
	
	#get sitch update
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
		
	#update the screen
	digole_update()
    
    	#only sleep the time we need to respect the clock
    	remainingTimeToSleep = time.time() - timestamp
    	remainingTimeToSleep = SCREEN_UPDATE_TIME - remainingTimeToSleep
    	if(remainingTimeToSleep > 0):
#		print "time to sleep=",remainingTimeToSleep
       		time.sleep(remainingTimeToSleep)

	   
#end the tasks nicely
quitApplicationNicely()

