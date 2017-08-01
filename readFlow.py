import os
import glob
import time
import threading
import sys

device_file = '/sys/kernel/flow/flow'

 
class FlowData:
	def __init__(self):
		self.flow = 0.0
		self.deltaFlow = 0.0

	def getFlow(self):
		#protect concurrent access with mutex
		try:
	                f = open(device_file, 'r')
        	        lines = f.read()#lines()
                	f.close()
			self.flow = int(lines) 

	        except IOError as e:
        	        print "Erreur fichier ", device_file," (ouverture, lecture ou fermeture)"
       	        	print "I/O error({0}): {1}".format(e.errno, e.strerror)
                	return -1
        	except:
                	print "Erreur fichier ", device_file," (ouverture, lecture ou fermeture)", sys.exc_info()[0]
			return -1

		retval = self.flow - self.deltaFlow
		self.deltaFlow = self.flow
		return retval
