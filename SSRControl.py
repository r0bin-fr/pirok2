import os
import glob
import time
import threading
import sys
import subprocess

#call a C program using WiringPi to control PWM
def setBoilerPWM(drive=0, doinit=0):
	try:
        	task = subprocess.Popen(['sudo','/home/pi/pirok2/pwmlauncher',str(doinit),str(drive)])
		task_result = task.returncode
        except:
		print "Wiring pi error"


#call a C program using WiringPi to control PWM
def setPumpPWM(drive=0, doinit=0):
#	print "setPumpPWM val", drive
        try:
                task = subprocess.Popen(['sudo','/home/pi/pirok2/pwmlauncherPump',str(doinit),str(drive)])
                task_result = task.returncode
        except:
                print "Wiring pi error"




