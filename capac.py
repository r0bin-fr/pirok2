#!/usr/bin/python

from smbus import SMBus
import RPi.GPIO as GPIO
import time
#for data input
import sys
from select import select


#i2c CAP1188 address
address = 0x29
CAP1188_SENINPUTSTATUS = 0x3
CAP1188_SENLEDSTATUS = 0x4
CAP1188_SENSNOISE = 0xA
CAP1188_NOISETHR = 0x38
CAP1188_MTBLK = 0x2A
CAP1188_PRODID = 0xFD
CAP1188_MANUID = 0xFE
CAP1188_STANDBYCFG = 0x41
CAP1188_REV = 0xFF
CAP1188_MAIN = 0x00
CAP1188_MAIN_INT = 0x01
CAP1188_LEDPOL = 0x73
CAP1188_INTENABLE = 0x27
CAP1188_REPRATE = 0x28
CAP1188_LEDLINK = 0x72

CAP1188_SENSITIVITY = 0x1f
CAP1188_CALIBRATE = 0x26
#reset pin BCM#27 on RPi
CAP1188_RESETPIN = 27

#init i2c
b = SMBus(1)
#reset cap1188
GPIO.setmode(GPIO.BCM)
GPIO.setup(CAP1188_RESETPIN, GPIO.OUT)
GPIO.output(CAP1188_RESETPIN, False)
time.sleep(0.1)
GPIO.output(CAP1188_RESETPIN, True)
time.sleep(0.1)
GPIO.output(CAP1188_RESETPIN, False)
time.sleep(1)

#init cap118
b.write_byte_data(address, CAP1188_MTBLK, 0)#allow multiple touches
#b.write_byte_data(address, CAP1188_STANDBYCFG, 0x30)#speed up a bit
b.write_byte_data(address, CAP1188_STANDBYCFG, 0xB9) #mode proximity sensor

#b.write_byte_data(address, CAP1188_INTENABLE, 0x05)
b.write_byte_data(address, CAP1188_LEDLINK, 0xff) #Have LEDs follow touches
#b.write_byte_data(address, CAP1188_SENSITIVITY, 0x6f) #reduce sensitivity
#b.write_byte_data(address, CAP1188_SENSITIVITY, 0x2f) #standard sensitivity
b.write_byte_data(address, CAP1188_SENSITIVITY, 0x1f) #maax sensitivity
b.write_byte_data(address, CAP1188_CALIBRATE, 0xff) #force recalibration
b.write_byte_data(address, CAP1188_NOISETHR,0x1) #noise thresold level 62.5

time.sleep(1)

#read register
b.write_byte(address, CAP1188_PRODID)
print "prodid=",hex(b.read_byte(address))
b.write_byte(address, CAP1188_MANUID)
print "manuid=",hex(b.read_byte(address))
b.write_byte(address, CAP1188_REV)
print "rev=",hex(b.read_byte(address))

#read loop 
try:
	while True:
		#input detection
		t1 = b.read_byte_data(address, CAP1188_SENINPUTSTATUS)
 		if(t1):
			print("detexed:"+str(t1)+","+'{0:08b}'.format(t1))

#		if (t1 & 4):
#			print "toto"

		#error checking
		t2 = b.read_byte_data(address, CAP1188_SENSNOISE)
		if(t2):
			print "Error: ",t2,'{0:08b}'.format(t2)

		#data entry
#		rlist, _, _ = select([sys.stdin], [], [], 0.1)
#        	if rlist:
		if 0:
                	s = sys.stdin.readline()
                	try:
                	        val=int(s)
				b.write_byte_data(address, CAP1188_SENSITIVITY, val)
				time.sleep(0.05)
                	except ValueError:
                	        print "Entry error: NaN"
                	print "Entered:",s,"decoded=",hex(val)


		#reinit sensor
 		time.sleep(0.05)
 		b.write_byte_data(address, CAP1188_MAIN, 0x00)

finally: 
	GPIO.cleanup()
