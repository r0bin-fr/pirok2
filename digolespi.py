#!/usr/bin/python

import time # pour tempo 1s
import mydigole #for digole screen 

#---------------------
#------ MAIN ---------
#---------------------
digole = mydigole.DigoleMaster()

#Print 8x8 color tiles
digole.clearScreen()
digole.setFGcolor(0)
digole.setBGcolor()
digole.clearScreen()

col = 0
for j in range (128/8):
        for i in range(160/8):
                digole.setFGcolor(col)
                digole.fillRect(i*8,j*8,((i*8)+8)-1,((j*8)+8)-1)
                col = col +1
                if(col >= 256):
                        col=0

digole.close()
exit()

#Print color tiles
if 0:
	digole.clearScreen()
	digole.setFGcolor(0)
	digole.setBGcolor()
	
	for i in range(256):
		digole.clearScreen()
		digole.setFGcolor(i)	
		digole.fillRect(32,32,128,128)
		digole.setFGcolor(1)
		digole.printTextP(32,20,str(i))
		time.sleep(1)

