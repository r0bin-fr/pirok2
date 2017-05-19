#!/usr/bin/python

import spidev #bibliotheque SPI
import time # pour tempo 1s
import numpy as np #bit and hex management
import random #for demo

#for data input
import sys
from select import select


#
# Class to handle the Digole OLED screen
#
class DigoleMaster:

	# Parametres font / couleur
	cNoir = 0#4 #254
	cBlanc = 222 #254 #4
	cB1=cB2=cB3=63
	cBleu = 0x32 #2
	cRouge = 0xC4 #224
	cVert = 28
	fBig=200
	fSmall=201

	def __init__(self):
		# Activation du bus SPI
		spi = spidev.SpiDev() #nouvel objet SPI
		spi.open(0,0) # sur port SPI 0 CS 0
		spi.max_speed_hz = 1000000 #200000 #15000000 # vitesse = 200 KHz pour le digole (max 15000000)
		spi.bits_per_word = 8 #8 bits per word
		spi.lsbfirst = False #MSB bits
		spi.mode = 0 #mode SPI O

	#- Envoie une commande (string)
	def sendCmd(buf):
		for c in buf:
			spi.writebytes([ord(c)])

	def sendCmd2Flash(buf,decal):
		a = decal + 1
		for c in buf:
			spi.writebytes([c])
			if(a >= 64):
				time.sleep(0.15)
				a = 1
			else:
				a = a+1

	#- Envoie une commande (valeur)
	def sendVal(val):
		spi.writebytes([val])

	#- Envoie plusieurs valeurs
	def sendVals(val):
		for v in val:
			spi.writebytes([v])

	#- Efface l'ecran		
	def clearScreen():
		sendCmd("CL")

	#- Affiche un texte a l'ecran
	def printText(txt):
		sendCmd("TT")
		sendCmd(txt)
		sendVal(0)

	#- Affiche un texte a l'ecran (avec position)
	def printText2(x,y,txt):
		setCursor(x,y)
		sendCmd("TT")
		sendCmd(txt)
		sendVal(0)

	#- Affiche un texte a l'ecran (avec position)
	def printTextP(x,y,txt):
		setCursorP(x,y)
		sendCmd("TT")
		sendCmd(txt)
		sendVal(0)

	#- Change le curseur (position)
	def setCursor(x,y):
	        sendCmd("TP")
	        sendVal(x)
	        sendVal(y)

	#- Change le curseur (pixels)
	def setCursorP(x,y):
	        sendCmd("ETP")
	        sendVal(x)
	        sendVal(y)

	def setCursorLastPos():
		sendCmd("ETB")

	#- Dessine un pixel
	def drawPixel(x,y):
	        sendCmd("DP")	
	        sendVal(x)
	        sendVal(y)

	#- Dessine une ligne
	def drawLine(x,y,x2,y2):
	        sendCmd("LN")	
	        sendVal(x)
        	sendVal(y)
        	sendVal(x2)
        	sendVal(y2)

	#- Dessine un carre
	def drawRect(x,y,x2,y2):
	        sendCmd("DR")
	        sendVal(x)
	        sendVal(y)
	        sendVal(x2)
	        sendVal(y2)

	#- Remplit un carre
	def fillRect(x,y,x2,y2):
	        sendCmd("FR")
	        sendVal(x)
	        sendVal(y)
	        sendVal(x2)
	        sendVal(y2)

	#- Dessine ou remplit un cercle
	def drawCircle(x,y,r,f):
	        sendCmd("CC")
	        sendVal(x)
	        sendVal(y)
	        sendVal(r)
	        sendVal(f)

	#- Affiche une image noir et blanc
	def drawPic(x,y,w,h,data):
	        sendCmd("DIM")
	        sendVal(x)
	        sendVal(y)
	        sendVal(w)
	        sendVal(h)
	        sendVals(data)
	
	#- Affiche une image NB prise d'un fichier
	def drawPic2(x,y,w,h,data):
       		sendCmd("DIM")
        	sendVal(x)
        	sendVal(y)
        	sendVal(w)
        	sendVal(h)
        	sendCmd(data)
	#Affiche une image couleur prise d'un fichier
	def drawPic3(x,y,w,h,data):
	        sendCmd("EDIM1")
	        sendVal(x)
	        sendVal(y)
	        sendVal(w)
	        sendVal(h)
	        sendCmd(data)

	#- Change la font
	def setFont(f):
        	sendCmd("SF")
        	sendVal(f)

	#- allume ou eteint l'ecran
	def setScreen(on):
        	sendCmd("SOO")
        	sendVal(on)

	#- change la couleur de dessin
	def setFGcolor(c):
        	sendCmd("SC")
        	sendVal(c)
	def setFGcolorTrue(a,b,c):
		sendCmd("ESC")
		sendVals([a,b,c])

	#- change la couleur du background
	def setBGcolor():
        	sendCmd("BGC")

	#- change la couleur de dessin
	def setDrawMode(m):
	        sendCmd("DM")
	        sendCmd(m)
	
	#- change l'ecran d'accueil
	def setWelcomeScreen1():
		sendCmd("SSS")
		bitm = fp.read()
		print "len=",len(bitm)
		sendVals([0x9C, 0x06])
		time.sleep(0.300)
		sendVals([0x06, 0x9A])
		#commandes sup:
		
		#avant:
		sendCmd("CLDIM")
		sendVal(25)
		sendVal(0)
		sendVal(110)
		sendVal(120)
		sendCmd2Flash(bitm,11)
		time.sleep(0.300)
		sendVal(255)

	#convert 16bit integer to two 8bit integers
	def convert(int32_val):
    		bin = np.binary_repr(int32_val, width = 32) 
    		int8_arr = [int(bin[0:8],2), int(bin[8:16],2), int(bin[16:24],2), int(bin[24:32],2)]
    		return int8_arr[2],int8_arr[3] 

	def downloadFont(myfont,fontnum):
		clearScreen()
		#compute font lenght
		fl=len(myfont)
		print "len=",fl
		fl1,fl2=convert(fl)
		print "len conv=",hex(fl1),"-",hex(fl2)
		#send command
		sendCmd("SUF")
		#custom font number
		sendVal(fontnum)
		time.sleep(0.300)
		#send length
		sendVals([fl2,fl1])
		#send font data to flash
		sendCmd2Flash(myfont,0)
		#sleep at least 3 seconds after flash
		time.sleep(3)


