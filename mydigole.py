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
		self.spi = spidev.SpiDev() #nouvel objet SPI
		self.spi.open(0,0) # sur port SPI 0 CS 0
		self.spi.max_speed_hz = 1000000 #200000 #15000000 # vitesse = 200 KHz pour le digole (max 15000000)
		self.spi.bits_per_word = 8 #8 bits per word
		self.spi.lsbfirst = False #MSB bits
		self.spi.mode = 0 #mode SPI O
		#put screen on
		self.setScreen(1)
				

	#- Envoie une commande (string)
	def sendCmd(self,buf):
		for c in buf:
			self.spi.writebytes([ord(c)])

	def sendCmd2Flash(self,buf,decal):
		a = decal + 1
		for c in buf:
			self.spi.writebytes([c])
			if(a >= 64):
				time.sleep(0.15)
				a = 1
			else:
				a = a+1

	#- Envoie une commande (valeur)
	def sendVal(self,val):
		self.spi.writebytes([val])

	#- Envoie plusieurs valeurs
	def sendVals(self,val):
		for v in val:
			self.spi.writebytes([v])

	#- Efface l'ecran		
	def clearScreen(self):
		self.sendCmd("CL")

	#- Affiche un texte a l'ecran
	def printText(self,txt):
		self.sendCmd("TT")
		self.sendCmd(txt)
		self.sendVal(0)

	#- Affiche un texte a l'ecran (avec position)
	def printText2(self,x,y,txt):
		self.setCursor(x,y)
		self.sendCmd("TT")
		self.sendCmd(txt)
		self.sendVal(0)

	#- Affiche un texte a l'ecran (avec position)
	def printTextP(self,x,y,txt):
		self.setCursorP(x,y)
		self.sendCmd("TT")
		self.sendCmd(txt)
		self.sendVal(0)

	#- Change le curseur (position)
	def setCursor(self,x,y):
	        self.sendCmd("TP")
	        self.sendVal(x)
	        self.sendVal(y)

	#- Change le curseur (pixels)
	def setCursorP(self,x,y):
	        self.sendCmd("ETP")
	        self.sendVal(x)
	        self.sendVal(y)

	def setCursorLastPos(self):
		self.sendCmd("ETB")

	#- Dessine un pixel
	def drawPixel(self,x,y):
	        self.sendCmd("DP")	
	        self.sendVal(x)
	        self.sendVal(y)

	#- Dessine une ligne
	def drawLine(self,x,y,x2,y2):
	        self.sendCmd("LN")	
	        self.sendVal(x)
        	self.sendVal(y)
        	self.sendVal(x2)
        	self.sendVal(y2)

	#- Dessine un carre
	def drawRect(self,x,y,x2,y2):
	        self.sendCmd("DR")
	        self.sendVal(x)
	        self.sendVal(y)
	        self.sendVal(x2)
	        self.sendVal(y2)

	#- Remplit un carre
	def fillRect(self,x,y,x2,y2):
	        self.sendCmd("FR")
	        self.sendVal(x)
	        self.sendVal(y)
	        self.sendVal(x2)
	        self.sendVal(y2)

	#- Dessine ou remplit un cercle
	def drawCircle(self,x,y,r,f):
	        self.sendCmd("CC")
	        self.sendVal(x)
	        self.sendVal(y)
	        self.sendVal(r)
	        self.sendVal(f)

	#- Affiche une image noir et blanc
	def drawPic(self,x,y,w,h,data):
	        self.sendCmd("DIM")
	        self.sendVal(x)
	        self.sendVal(y)
	        self.sendVal(w)
	        self.sendVal(h)
	        self.sendVals(data)
	
	#- Affiche une image NB prise d'un fichier
	def drawPic2(self,x,y,w,h,data):
       		self.sendCmd("DIM")
        	self.sendVal(x)
        	self.sendVal(y)
        	self.sendVal(w)
        	self.sendVal(h)
        	self.sendCmd(data)
	#Affiche une image couleur prise d'un fichier
	def drawPic3(self,x,y,w,h,data):
	        self.sendCmd("EDIM1")
	        self.sendVal(x)
	        self.sendVal(y)
	        self.sendVal(w)
	        self.sendVal(h)
	        self.sendCmd(data)

	#- Change la font
	def setFont(self,f):
        	self.sendCmd("SF")
        	self.sendVal(f)

	#- allume ou eteint l'ecran
	def setScreen(self,on):
        	self.sendCmd("SOO")
        	self.sendVal(on)

	#- change la couleur de dessin
	def setFGcolor(self,c):
        	self.sendCmd("SC")
        	self.sendVal(c)
	def setFGcolorTrue(self,a,b,c):
		self.sendCmd("ESC")
		self.sendVals([a,b,c])

	#- change la couleur du background
	def setBGcolor(self):
        	self.sendCmd("BGC")

	#- change la couleur de dessin
	def setDrawMode(self,m):
	        self.sendCmd("DM")
	        self.sendCmd(m)
	
	#- change l'ecran d'accueil
	def setWelcomeScreen(self,bitm):
		self.sendCmd("SSS")
		#compute bmp length
		fl=len(bitm)+9
		print "len+9=",fl
		fl1,fl2=self.convert(fl)
		print "len conv=",hex(fl1),"-",hex(fl2)
		f2=fl+2
		f21,f22=self.convert(f2)
		print "len conv2=",hex(f21),"-",hex(f22)

		#send first size
		self.sendVals([f22,f21])
		time.sleep(0.300)
		#send second size
		self.sendVals([fl1,fl2])	
		#send commands
		self.sendCmd("CLDIM")
		self.sendVal(25)
		self.sendVal(0)
		self.sendVal(110)
		self.sendVal(120)
		#send bitmap
		self.sendCmd2Flash(bitm,11)
		time.sleep(0.300)
		self.sendVal(255)
		
		#sleep 3 seconds
		time.sleep(3)
		#verify
		self.sendCmd("DSS")	
		self.sendVal(255)	


	#convert 16bit integer to two 8bit integers
	def convert(self,int32_val):
    		bin = np.binary_repr(int32_val, width = 32) 
    		int8_arr = [int(bin[0:8],2), int(bin[8:16],2), int(bin[16:24],2), int(bin[24:32],2)]
    		return int8_arr[2],int8_arr[3] 

	#download a font
	def downloadFont(self,myfont,fontnum):
		self.clearScreen()
		#compute font lenght
		fl=len(myfont)
		print "len=",fl
		fl1,fl2=self.convert(fl)
		print "len conv=",hex(fl1),"-",hex(fl2)
		#send command
		self.sendCmd("SUF")
		#custom font number
		self.sendVal(fontnum)
		time.sleep(0.300)
		#send length
		self.sendVals([fl2,fl1])
		#send font data to flash
		self.sendCmd2Flash(myfont,0)
		#sleep at least 3 seconds after flash
		time.sleep(3)
	
	#close connection
	def close(self):
		self.spi.close()

