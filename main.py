#!/usr/bin/python

# -*- coding: latin-1 -*-
import math
import time
import calendar
import signal
import sys
from subprocess import call
from time import gmtime, strftime
from datetime import datetime as dt
import mydigole
import myencoder
#import myplotly
import random
import readMaxim
import readHSR
import readFlow
import multithreadHum
import multithreadRange
import multithreadADC
import multithreadTemp
import multithreadPID
import multithreadPIDPump
import multithreadHX711
import multithreadBTPoids

#Temperature file backup
TEMPBACKUP = '/home/pi/pirok2/settings.txt'
DEFAULT_BOILER_TEMP = 115
BOOST_BOILER_TEMP   = 124
SCREEN_UPDATE_TIME  = 0.5  #500ms
OLED_TIMEOUT 	    = 120   #in seconds
OLED_FADE_TIMEOUT   = 10    #in seconds
OLED_WHITE_STD	    = 254
OLED_WHITE_FADE	    = 98 #76
BL_STD = 100 #40
EXTRACTION_TIMEOUT  = 7   #in seconds
DEFAULTPUMPVAL		= 9 #11    #in bar
BOOST_TIMEOUT = 5 * 60 # 5 minutes in seconds
boostTimestamp = 0.0

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
cBleu = 159 #82 #70 #0x32 #2
cBleuF = 18 #82 #0x0B
cRouge = 0xE4 #0xC4 #224
cVert = 28
cGris = 213 #cBleu #76
cOrange = 0xF0
fBig=200
fSmall=201

#global values
maximT1 = readMaxim.MaximData(0)
maximT2 = readMaxim.MaximData(0)
dhtData = readMaxim.MaximData(0)
hsrData = readHSR.HSRData(0)
barData = readHSR.HSRData(0)
flowData = readFlow.FlowData()
pumpPTarget = DEFAULTPUMPVAL
poidsData = readHSR.HSRData(0)
poidsBTData = readHSR.HSRData(0)
poids = 0.0
lastpoids = 0.0

#plotly data
#myplot = myplotly.MyPlotly(0)

#tasks
task1 = multithreadTemp.TaskPrintTemp(0,maximT1)
task2 = multithreadTemp.TaskPrintTemp(1,maximT2)
task3 = multithreadHX711.TaskPrintWeight(2,poidsData)
task4 = multithreadHum.TaskPrintHum(3,dhtData)
task5 = multithreadRange.TaskPrintRange(4,hsrData)
task8 = multithreadBTPoids.TaskPrintWeight2(7,poidsBTData)
task9 = multithreadADC.TaskPrintBar(8,barData)
#**** PID setup: *****
#maximT2 is the group temperature (for boost algorithm), maximT1 is the boiler temp sensor, default target value = 115C
temptarget=115
task6PID = multithreadPID.TaskControlPID(6,maximT2,maximT1,temptarget)
#Pump PID setup
task7PID = multithreadPIDPump.TaskControlPID(7,barData,DEFAULTPUMPVAL)

#how to quit application nicely
def quitApplicationNicely():
	done = True
	saveSettings()
	digole.setScreen(0)
	task6PID.stop()
	task7PID.stop()
	task1.stop()
	task2.stop()
	task3.stop()
	task4.stop()
	task5.stop()
	task8.stop()
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

#---------------------------
#-- Graph for extraction ---
#---------------------------
ext_rang = 0
graphTX = 0
graphTY = 0
graphRX=0
graphRY=0
COL_X = 1
#COL_Y = 110
BOTTOM_TEXT_Y = 128
BOTTOM_TEXT_HEIGHT = 16
COL_Y = BOTTOM_TEXT_Y - BOTTOM_TEXT_HEIGHT - 3


#Pressure graph protection
PRESSURE_GRAPH_MAX_BAR = 12.0       # top of graph = 12 bar
PRESSURE_MAX_DISPLAY_JUMP = 3.5     # max displayed jump between two refreshes
lastDisplayedBar = 0.0

#Total weight blue bars during extraction
#Each refresh draws only one new bar at the current graph X position.
#Pressure is drawn immediately after, over the blue bar.
WEIGHT_TOTAL_TARGET = 40.0      # grams corresponding to full graph height
WEIGHT_BAR_Y_TOP = 0
WEIGHT_BAR_Y_BASE = COL_Y - 1
WEIGHT_BAR_WIDTH = 2
#HX711 tare protection at extraction start
#After task3.met_a_zero(), the HX711 thread may need a few cycles
#before publishing the new zeroed value.
WEIGHT_TARE_SETTLE_TIME = 0.8
#If the first value after tare is still high, use it as visual baseline
#so the graph starts at zero instead of starting at cup weight.
WEIGHT_TARE_BASELINE_THRESHOLD = 5.0
#If HX711 later drops well below the temporary baseline,
#follow it down because the tare probably finally caught up.
WEIGHT_TARE_BASELINE_DROP = 3.0
weightTareTimestamp = 0.0
weightGraphBaseline = 0.0
weightGraphBaselineSet = 0

def init_graph_extraction(currentBar=0.0):
	global ext_rang 
	global graphTX
	global graphTY
	global graphRX
	global graphRY
	global lastDisplayedBar

	ext_rang = COL_X + 1
	graphTX = -1
	graphTY = 0
	graphRX = -1
	graphRY = 0

	# Start displayed pressure from the real current pressure,
	# not from zero.
	lastDisplayedBar = clamp_pressure_value(currentBar)

	digole.clearScreen()
	digole.setFGcolor(cGris) #cBlanc)

	#AXES
	digole.drawLine(COL_X,0,COL_X,COL_Y+1)
	digole.drawLine(COL_X,COL_Y,160,COL_Y)
	#digole.drawLine(COL_X,COL_Y+1,160,COL_Y+1)

	#DOTS
	i=0
	while(i<COL_Y):
		digole.drawLine(COL_X-1,i,COL_X,i)
		i=i+10
	j=COL_X+10
	while(j<160):
		digole.drawLine(j,COL_Y+1,j,COL_Y+2)
		j=j+10


def get_weight_for_graph(poids):
	global weightGraphBaseline
	global weightGraphBaselineSet

	#During tare pending, force graph weight to zero.
	#This avoids drawing the first blue bars with the pre-tare cup weight.
	if weightTareTimestamp > 0:
		if (time.time() - weightTareTimestamp) < WEIGHT_TARE_SETTLE_TIME:
			return 0.0

	#Safety against negative HX711 values.
	if poids < 0:
		poids = 0.0

	#First value after tare delay:
	#if it is still high, it is probably a pre-tare or delayed value.
	#Use it as a temporary visual baseline.
	if weightGraphBaselineSet == 0:
		if poids > WEIGHT_TARE_BASELINE_THRESHOLD:
			weightGraphBaseline = poids
		else:
			weightGraphBaseline = 0.0

		weightGraphBaselineSet = 1

	#If baseline was high and HX711 tare finally catches up,
	#reset baseline down to the new lower value.
	if weightGraphBaseline > 0:
		if poids < (weightGraphBaseline - WEIGHT_TARE_BASELINE_DROP):
			weightGraphBaseline = poids

	poidsGraph = poids - weightGraphBaseline

	if poidsGraph < 0:
		poidsGraph = 0.0

	return poidsGraph


def draw_weight_total_bar(x, currentWeight):
    #Draw one blue background bar representing total extracted weight.
    #It is drawn only at the current graph X position.
    #The pressure curve must be drawn after this function, so it appears on top.

    if currentWeight < 0:
        currentWeight = 0.0

    if currentWeight > WEIGHT_TOTAL_TARGET:
        currentWeight = WEIGHT_TOTAL_TARGET

    ratio = currentWeight / WEIGHT_TOTAL_TARGET

    if ratio < 0:
        ratio = 0
    if ratio > 1:
        ratio = 1

    barHeight = int(ratio * (WEIGHT_BAR_Y_BASE - WEIGHT_BAR_Y_TOP))

    if barHeight <= 0:
        return

    x1 = x
    x2 = x #+ WEIGHT_BAR_WIDTH

    if x1 > 159:
        return
    if x2 > 159:
        x2 = 159

    y1 = WEIGHT_BAR_Y_BASE - barHeight
    y2 = WEIGHT_BAR_Y_BASE

    digole.setFGcolor(cBleuF)
    digole.fillRect(x1, y1, x2, y2)

def clamp_pressure_value(bar):
	#Keep pressure inside display range.
	if bar < 0:
		bar = 0.0

	if bar > PRESSURE_GRAPH_MAX_BAR:
		bar = PRESSURE_GRAPH_MAX_BAR

	return bar


def pressure_to_y(bar):
	#Convert pressure in bar to graph Y coordinate.
	#0 bar is at COL_Y, PRESSURE_GRAPH_MAX_BAR is at the top.
	bar = clamp_pressure_value(bar)

	ratio = bar / PRESSURE_GRAPH_MAX_BAR

	if ratio < 0:
		ratio = 0
	if ratio > 1:
		ratio = 1

	return int(COL_Y - (ratio * COL_Y))


def get_filtered_display_bar(bar):
	global lastDisplayedBar

	#Clamp first, so the display never tries to draw outside the graph.
	bar = clamp_pressure_value(bar)

	#Avoid crazy visual spikes.
	#This protects only the displayed curve, not the real PID value.
	if abs(bar - lastDisplayedBar) > PRESSURE_MAX_DISPLAY_JUMP:
		if bar > lastDisplayedBar:
			bar = lastDisplayedBar + PRESSURE_MAX_DISPLAY_JUMP
		else:
			bar = lastDisplayedBar - PRESSURE_MAX_DISPLAY_JUMP

	lastDisplayedBar = bar
	return bar


def draw_pressure_graph_segment(bar, pumpPTarget):
	global ext_rang
	global graphTX, graphTY
	global graphRX, graphRY

	#Use protected values for display.
	displayBar = get_filtered_display_bar(bar)
	displayTarget = clamp_pressure_value(pumpPTarget)

	targetY = pressure_to_y(displayTarget)
	barY = pressure_to_y(displayBar)

	#Init first point.
	if(graphTX == -1):
		graphTX = ext_rang
		graphTY = targetY
		graphRX = ext_rang
		graphRY = barY
		return

	#Draw target pressure.
	digole.setFGcolor(cRouge)
	digole.drawLine(graphTX, graphTY, ext_rang, targetY)

	#Draw current pressure over the blue weight bar.
	digole.setFGcolor(cVert)
	digole.drawLine(graphRX, graphRY, ext_rang, barY)

	#Backup coords for next refresh.
	graphTX = ext_rang
	graphTY = targetY
	graphRX = ext_rang
	graphRY = barY

#---- Fonction principale pour affichage extraction
def ihm_extraction(tboil,tnez,temp,hum,range,bar,isPumpRunning,pumpRate,pumpPTarget,poids):
	global ext_rang
	global graphTX,graphTY,graphRX,graphRY

	#Draw only the new blue weight bar at current X position.
    	#Pressure graph will be drawn just after, so it remains visible over the bar.
	poidsForGraph = get_weight_for_graph(poids)
	draw_weight_total_bar(ext_rang, poidsForGraph)
	
	#affichage pression 
	digole.setFont(fSmall)
	digole.setFGcolor(cVert)
	st=" {0:.1f} ".format(bar)
	digole.printTextP(5,BOTTOM_TEXT_Y,st)
	digole.setFGcolor(cBlanc)
	st="/{0:.0f}b ".format(pumpPTarget)	
	digole.printTextP(45,BOTTOM_TEXT_Y,st)
#	st=" {0:.1f}/{1:.0f}b {2:.1f}+ ".format(bar,pumpPTarget,poids)	
#	st=" {0:.1f}b {1:.1f} {2:.1f}+ ".format(bar,poids,tnez)	

	#affichage temperature	
	digole.setFGcolor(cOrange)
	st=" {0:.1f}+ ".format(tnez)
	digole.printTextP(90,BOTTOM_TEXT_Y,st)

	#affichage poids
	digole.setFGcolor(cBlanc)
	digole.setFont(fSmall)
	st="{0:.1f} ".format(poidsForGraph)
	digole.printTextP(16,25,st)
	digole.setFont(0)
	digole.setCursorMove(-7,-3)
	digole.printText("g ")


	#Draw protected pressure graph over the blue weight bar.
	draw_pressure_graph_segment(bar, pumpPTarget)

	#increment x
	ext_rang = ext_rang + 2
	if(ext_rang > 160):
		init_graph_extraction(bar)


	
#---- Fonction principale pour ecran idle
def digole_update(tboil,tnez,temp,hum,range,bar,isPumpRunning,pumpRate,pumpPTarget,poids):
	global cGris
	#display a specific GUI when extracting
	if(isPumpRunning):
		return ihm_extraction(tboil,tnez,temp,hum,range,bar,isPumpRunning,pumpRate,pumpPTarget,poids)
		
	#temp chaudiere	
	digole.setFont(fSmall)
	digole.setFGcolor(cRouge)
	digole.printTextP(5,30,"c")
	if( consigneBoost == 0 ):
		digole.setFGcolor(cBlanc)
	if tboil > 200:
		tboil = 199.0
	if tboil < 0:
		tboil = 0.0
	st="{0:.0f}/{1:.0f}+   ".format(tboil, temptarget)
	digole.printText(st)
	
	#pression extraction
	tshiftx=5
	digole.setFGcolor(cVert)
	digole.printTextP(89+tshiftx,30,"d")	
	digole.setFGcolor(cBlanc)
#	digole.printTextP(116+tshiftx,20,"     ")
	digole.printText2(0,1," ")
	#st="{0:.1f}".format(random.uniform(5, 10))
	st="{0:.1f}  ".format(bar)
#	digole.printTextP(118+tshiftx,20,str(st)+"b")
	digole.printTextP(118+tshiftx,30,str(st))
	
	#niveau eau
	digole.setFont(fBig)
	digole.setFGcolor(cGris)#cBleu)
	digole.printTextP(30,90,chr(ord('A')+getWLvalue(range)))

	#temperature
	digole.setFGcolor(cBlanc)
	st="{0:.1f}".format(tnez)
#	st="{0:.1f}".format(poids)
	digole.printTextP(50,90,str(st)+"+ ")

#bymatt
	digole.setFGcolor(cBlanc)
        digole.setFont(0)
	st="{0:.0f}   ".format(cGris)
        digole.printTextP(25,100,st)


	#get the current time
#	if(int(time.time())%2 == 0):   
#		stime=time.strftime('%H.%M')
#	else:
#		stime=time.strftime('%H\'%M')
	if(int(time.time())%2 == 0):   
		stime=time.strftime('%H %M')
	else:
		stime=time.strftime('%H:%M')
	digole.setFGcolor(cGris)
	digole.setFont(0)
	digole.printTextP(25,118,"tulipes / "+stime)
	#digole.setFont(fSmall)
	#digole.printTextP(50,118,stime+" ")

	#temperature ambiante et hygrometrie
#	st="{0:.1f}+/{1:.0f}a".format(temp,hum)
#	st="{0:.1f}+/{1:.0f}a  ".format(temp,poids)
	#st="{0:.1f}g/{1:.0f}a  ".format(poids,hum)

#remove this ? 
#	st="{0:.0f}g  ".format(cBlanc)
#	digole.setFGcolor(cGris)
#	digole.printTextP(66,118,st)

	


# screen on with timeout
def screenOnWithTimeout():
	global digole,flagTouch,touchTstamp,cBlanc
	digole.setScreen(1)
#	digole.setDrawDir(2)
	flagTouch=1
	touchTstamp = time.time()
	cBlanc = OLED_WHITE_STD
	digole.setBL(BL_STD)

#screen off, timeout disabled
def screenOffNow():
	global digole,flagTouch,cBlanc
	digole.setScreen(0)
	digole.clearScreen()
	#digole.setDrawDir(2)
	digole.setOLEDOFF()
	flagTouch=0
	cBlanc = OLED_WHITE_STD
	digole.setBL(BL_STD)

#start extraction mode
def startExtractionMode():
	global pumpTimestamp, task3, task9,task7PID
	print "startExtractionMode"
	pumpTimestamp = time.time()
	
	#accelere le rythme de pesee / pression / PID
	task3.rythmeHaut()
	task3.met_a_zero()
	#After HX711 tare, protect the graph from old/pre-tare values.
	weightTareTimestamp = time.time()
	weightGraphBaseline = 0.0
	weightGraphBaselineSet = 0
	
	task8.rythmeHaut()
	task9.rythmeHaut()
	task7PID.rythmeHaut()
	#affiche les courbes de pression
   	init_graph_extraction(barData.getRange())
	print "startExtractionMode2"

#stop extraction mode
def stopExtractionMode():
	global digole, task3, task9,task7PID
	print "stopExtractionMode"
	digole.clearScreen()
	#reduit le rythme de pesee / pression / PID
	task3.rythmeBas()
	task8.rythmeBas()
	task9.rythmeBas()
	task7PID.rythmeBas()

#surveille que le boost ne dure pas trop longtemps
def check_boost_timeout(): 
	global temptarget
	global lastTargetTemp
	global consigneBoost
	global boostTimestamp

	if consigneBoost == 1:
		if boostTimestamp > 0:
			if (time.time() - boostTimestamp) > BOOST_TIMEOUT:
				print "Boost timeout - back to previous target temp"
				temptarget = lastTargetTemp
 				consigneBoost = 0
 				boostTimestamp = 0.0
				#apply settings immediately
				task6PID.setTargetTemp(temptarget)

# -------------------------------------------------------
# ------------------- Main Program Loop -----------------
# -------------------------------------------------------
#intercept control c for nice quit
signal.signal(signal.SIGINT, signal_handler)
done = False
#init vars
loadSettings()
lastTargetTemp = temptarget
consigneBoost = 0

#digole screen init
digole = mydigole.DigoleMaster()
digole.setDrawDir(2)
digole.setBL(BL_STD)
digole.setFGcolor(cNoir)
digole.setBGcolor(cNoir)
digole.clearScreen()

#encoder init
encoder_val = temptarget
encoder = myencoder.RotaryEncoder(A_PIN, B_PIN, SW_PIN, TOUCH_PIN)
encoder.start()

#start multitasking
task1.start()
task2.start()
task3.start()
task4.start()
task5.start()
#task8.start()
task9.start()
task6PID.start()
task7PID.start()

#pump data
isPumpRunning = 0
timeLastFlowRecorded = 0
pumpTimestamp = 0
pumpOfficialChrono = 0

flagTouch=1
touchTstamp = time.time()
#init data before loop
fl = flowData.getFlow()
plyrefresh = 1

#infinite loop
while not done:
	#try to respect as much as possible the time slot
	timestamp = time.time()

	#get flow update	
	fl = flowData.getFlow()
	#print "flow=",fl
	if(fl > 0.0):
		print "flow detected:", fl
		#avoid false positives
		if( fl < 10.0 ) and (isPumpRunning == 0):
			print "fake extraction?"
		else:
			screenOnWithTimeout()
			#if a new extraction is starting...
			if(isPumpRunning == 0):
				#start it
				startExtractionMode()
			isPumpRunning = 1
			timeLastFlowRecorded = time.time()
			pumpOfficialChrono = time.time() - pumpTimestamp
	else:
		#allow some time (15s) to play with pump pressure (case when not enough power to trigger flowmeter)
		if((time.time() - timeLastFlowRecorded) > EXTRACTION_TIMEOUT):
			#if extraction is finishing...
			if(isPumpRunning):
				stopExtractionMode()
			isPumpRunning = 0
			#make sure we put back the full power after use
			#if(pumpRate < 100):
			#	pumpRate = 100
			#	SSRControl.setPumpPWM( pumpRate )
			pumpPTarget = DEFAULTPUMPVAL
			task7PID.setTargetPressure(pumpPTarget)

	#get touch update
		if encoder.get_bTouched():
			print "Touche!"
		#if flagTouch:
			#prevent multi touch: wait 2 seconds before screen off
		#	if(timestamp - touchTstamp > 2):
		#		screenOffNow()
			#if touched during fadeoff, power on again
		#	if (timestamp - touchTstamp) >= (OLED_TIMEOUT - OLED_FADE_TIMEOUT):
		#		screenOnWithTimeout()
		#else:
			screenOnWithTimeout()

	#timeout on screen ON
	if flagTouch:
		if (timestamp - touchTstamp) >= OLED_TIMEOUT:
			screenOffNow()
		else:
			if (timestamp - touchTstamp) >= (OLED_TIMEOUT - OLED_FADE_TIMEOUT):
				#fade whites
				#cBlanc = OLED_WHITE_FADE
				digole.setBL(10)
	
	#check si on a pas un timeout sur le boostmode
	check_boost_timeout()

	#get switch update
	if encoder.get_bPushed():
		if flagTouch == 0:
			screenOnWithTimeout()
		else:
				#if screen is on, apply boost mode
			screenOnWithTimeout()
			#were we already in boost mode?
			if(consigneBoost == 0):
				lastTargetTemp = temptarget
				temptarget = BOOST_BOILER_TEMP
				consigneBoost = 1
				boostTimestamp = time.time()
			else:
				temptarget = lastTargetTemp
				consigneBoost = 0
				boostTimestamp = 0.0
			#apply settings immediately
			task6PID.setTargetTemp(temptarget)

	#check for weight
	poids = poidsData.getRange()
	if poids < 0:
		poids = 0
	if(isPumpRunning == 0):
		#avoid erronous values
		#if(abs(poids-lastpoids)<25):
			#did we exeed the maximum shot weigth = 18gr ?
			#if poids > 18:
			#	print "suspend pump!!"
			#	task7PID.suspendPump()
			#	poids = poidsData.getRange()
			#else:
			#	task7PID.setTargetPressure(pumpPTarget)
			#remember last correct val
			#lastpoids = poids

	#else:
		#did we press on the bassinelle?
		if poids > 300: #( poids > 10) and ( poids < 100 ):
			#print strftime("%Y-%m-%d %H:%M:%S", gmtime())," weight on:",poids,"g."
			#if yes, turn on screen
			screenOnWithTimeout()
			#reset balance
			task3.met_a_zero()			
	
	#is BT weight sensor connected? if yes the screen is ON
	if (task8.isNotConnected() == 0):
#				print strftime("%Y-%m-%d %H:%M:%S", gmtime())," screen on with BT!"
		screenOnWithTimeout()	

	#get encoder updates
	delta = encoder.get_cycles()
	#did we turn the encoder?
	if delta!=0:
		if flagTouch==0:
 			#turn on screen only
			screenOnWithTimeout()
		else:
			#turn on screen and proceed to treatment
			screenOnWithTimeout()	
			#only update pump when extracting, and temp when idle
			if(isPumpRunning):
				#update pump rate
				pumpPTarget += delta
				if(pumpPTarget > 12):
					pumpPTarget = 12
				if(pumpPTarget < 0):
					pumpPTarget = 0
				task7PID.setTargetPressure(pumpPTarget)
			
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

				#test color
				cGris += delta
				if(cGris > 255):
					cGris = 0
				if(cGris < 0):
					cGris = 255


	#get values update
	tboil=maximT1.getTemp()
	tnez=maximT2.getTemp()
	t4,h4 = dhtData.getTempHum()
	r5 = hsrData.getRange()
	b9 = barData.getRange()
	pumpRate = task7PID.getCurrentDrive()
	poids2 = poidsBTData.getRange()
	
	#update the screen
	digole_update(tboil,tnez,t4,h4,r5,b9,isPumpRunning,pumpRate,pumpPTarget,poids)
	#- stream data online
	#-- no extration: refresh only each 5 minutes
	#if((dt.now().minute % 2) == 0): 
		#if(plyrefresh):
			#myplot.update(tboil,tnez,t4,h4)
			#plyrefresh=0
	#else:
	#	plyrefresh = 1
	#-- extraction: refresh rate 0.5s with full data
	#if (isPumpRunning):
	#	myplot.updateFull(tboil,tnez,t4,h4,b9,pumpPTarget,poids2,fl)

	#only sleep the time we need to respect the clock
	remainingTimeToSleep = time.time() - timestamp
	remainingTimeToSleep = SCREEN_UPDATE_TIME - remainingTimeToSleep
	if(remainingTimeToSleep > 0):
#		print "time to sleep=",remainingTimeToSleep
		time.sleep(remainingTimeToSleep)

	   
#end the tasks nicely
quitApplicationNicely()
