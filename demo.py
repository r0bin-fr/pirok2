#!/usr/bin/python

import time # pour tempo 1s
import mydigole #for digole screen 
import random # for demo

#for data input
import sys
from select import select


# Parametres font / couleur
cNoir = 0#4 #254
cBlanc = 222 #254 #4
cB1=cB2=cB3=63
cBleu = 0x32 #2
cRouge = 0xC4 #224
cVert = 28
fBig=200
fSmall=201

#---------------------
#------ MAIN ---------
#---------------------
digole = mydigole.DigoleMaster()

digole.setFGcolor(cNoir)
digole.setBGcolor()
digole.clearScreen()

whiteVals=[77,81,113,117,141,149,181,213,245,249,250,1]
colc=0
cold=0

wval=0
while 1:
	#temp chaudiere	
	digole.setFont(fSmall)
	digole.setFGcolor(cRouge)
	digole.printTextP(5,20,"c")
	digole.setFGcolor(cBlanc)
#	digole.setFGcolorTrue(cB1,cB2,cB3)
	st=random.randint(115, 124)
	digole.printText(str(st)+"+   ")

	#pression extraction
	digole.setFGcolor(cVert)
	digole.printTextP(89,20,"d")	
	digole.setFGcolor(cBlanc)
#	digole.setFGcolorTrue(cB1,cB2,cB3)
	digole.printTextP(116,20,"     ")
	digole.printText2(0,1," ")
	st="{0:.1f}".format(random.uniform(5, 10))
	digole.printTextP(118,20,str(st)+"b")
	
	#niveau eau
	digole.setFont(fBig)
	digole.setFGcolor(cBleu)
#	digole.printTextP(30,80,random.choice('ABCDEF'))
	digole.printTextP(30,80,chr(ord('A')+wval))
	wval = wval + 1
	if(wval >= 6):
		wval = 0

	#temperature
	digole.setFGcolor(cBlanc)
#	digole.setFGcolorTrue(cB1,cB2,cB3)
	st="{0:.1f}".format(random.uniform(92, 95))
	digole.printTextP(50,80,str(st)+"+ ")

	#temperature ambiante et hygrometrie
	digole.setFGcolor(254)
	digole.setFont(fSmall)
	digole.printText2(4,6,"23+ / 40a")
	
	#time.sleep(0.7)
	
	#get user entry	
	rlist, _, _ = select([sys.stdin], [], [], 1)
	if rlist:
    		s = sys.stdin.readline()
		try:
#			cB1,cB2,cB3 = s.split(",")
#			cB1=int(cB1)
#			cB2=int(cB2)
#			cB3=int(cB3)
			cBlanc=int(s)
		except ValueError:
			print "NaN"
			cBlanc =cBlanc+2
    		print "Entered:",s,"cBlanc=",cBlanc
#    		print "Entered:",s,"cB1=",cB1,"cB2=",cB2,"cB3=",cB3
		digole.clearScreen()
	#white color swap
	#if(colc %2):
	#	digole.clearScreen()
	#	cBlanc = whiteVals[cold]
	#	if(cBlanc%2):
	#		cBlanc = cBlanc-1
	#	print "color=", cBlanc
	#	cold=cold+1
	#	if(cold >= len(whiteVals)):
	#		cold=0
	#colc=colc+1	
	#cBlanc = 76
