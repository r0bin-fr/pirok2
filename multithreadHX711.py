import os
import glob
import time
import threading
import readHSR
import sys
import subprocess

from hx711_python_2 import HX711                # import the class HX711
import RPi.GPIO as GPIO         # import GPIO

PIROK_RATIO = 657.0 #ratio estime
PIROK_POIDS0 = 8728214 #poids a vide
PIROK_NBPES = 9
MAX_JUMP = 80.0  # variation max plausible en grammes entre deux lectures
PIROK_RYTHM_BAS = 0.5
PIROK_RYTHM_HAUT = 0.25
MAX_BIG_JUMP_REPEAT = 3 

class TaskPrintWeight(threading.Thread):

    def __init__(self, taskid = 0, mData = readHSR.HSRData()):
        threading.Thread.__init__(self)
        self.taskid = taskid
        self._stopevent = threading.Event( )
        self.mData = mData
	self.tempo = PIROK_RYTHM_BAS 
	self.bigJumpCount = 0 
	self.bigJumpCandidate = None
	#mutex to protect concurrent access to chipset
        self.lok = threading.Lock()
        self.pbassinelle = 0.0
        self.ratio = PIROK_RATIO
        self.last_valid = None
        # Create an object hx which represents hx711 chip
        hx = HX711(dout_pin=19, pd_sck_pin=20, gain_channel_A=128, select_channel='A')
        # Before we start, reset the hx711
        result = hx.reset()
        if result:
                print('Hx711 Ready to use')
        else:
                print('Hx711 not ready')
        # measure tare and save the value as offset for current channel
        result = hx.zero(times=20)

        #set ratio to known value
        hx.set_scale_ratio(scale_ratio=self.ratio)

        #attribute object to use it later
        self.hx = hx


    def pese_raw(self):
        with self.lok:
            values = []
            for i in range(PIROK_NBPES):
                val = self.hx.get_weight_mean(times=1)
                values.append(val)
                time.sleep(0.02)
                
        values.sort()
        return values[len(values) // 2]


    def filtre_valeur(self, val):
#"""
#    Filtre les valeurs HX711.
#    Rejette les gros sauts isolés, mais accepte un gros changement
#    s'il persiste plusieurs lectures.
#    """

	if not hasattr(self, 'bigJumpCandidate'):
		self.bigJumpCandidate = None
		self.bigJumpCount = 0

	delta = abs(val - self.pbassinelle)

	# Variation normale : on accepte.
	if delta <= MAX_JUMP:
		self.pbassinelle = val
		self.bigJumpCandidate = None
		self.bigJumpCount = 0
		return val

	# Gros saut : on vérifie s'il ressemble au précédent candidat.
	if self.bigJumpCandidate is not None:
		candidateDelta = abs(val - self.bigJumpCandidate)
	else:
		candidateDelta = MAX_JUMP + 1

	if self.bigJumpCandidate is not None and candidateDelta <= MAX_JUMP:
		self.bigJumpCount = self.bigJumpCount + 1
	else:
 		self.bigJumpCandidate = val
		self.bigJumpCount = 1

	# Le gros saut persiste : on accepte la nouvelle zone de poids.
	if self.bigJumpCount >= MAX_BIG_JUMP_REPEAT:
		print "gros changement HX711 accepte apres repetition:", val, "ancienne:", self.pbassinelle

		self.pbassinelle = val
		self.bigJumpCandidate = None
		self.bigJumpCount = 0
		return val

	# Gros saut isolé ou pas encore confirmé : on garde l'ancienne valeur.
	print "valeur HX711 aberrante rejetee:", val, "ancienne:", self.pbassinelle, "count:", self.bigJumpCount
	return self.pbassinelle

        
    def met_a_zero(self):
        with self.lok:
            self.hx.zero(times=20)
	# Après une tare, on repart explicitement de zéro.
        # Sinon le filtre peut comparer la nouvelle valeur zéro
        # avec une ancienne valeur résiduelle.
            self.pbassinelle = 0.0
            self.bigJumpCandidate = None
            self.bigJumpCount = 0
            self.last_valid = None
            self._stopevent.wait(0.01)


    def rythmeHaut(self):
        #set fast tempo 100ms
        self.tempo = PIROK_RYTHM_HAUT
        #reset scale
        #self.met_a_zero()

    def rythmeBas(self):
        #set slow tempo 1sec
        self.tempo = PIROK_RYTHM_BAS

    def run(self):
        print "thread capteur no", self.taskid, " HX711 is readry!"
 
        while not self._stopevent.isSet():
                #6 lectures pour faire une moyenne
                #val = self.hx.get_weight_mean(times=6)
                val = self.pese_raw() #self.pese_puis_raz() #self.pese()
                val = self.filtre_valeur(val)
                self.mData.setRange(val)
                #attende de x ms entre chaque lecture
                self._stopevent.wait(self.tempo)


    def stop(self):
        print "stopping thread no", self.taskid
        self._stopevent.set( )

