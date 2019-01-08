#!/usr/bin/python
from plotly import tools
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.tools as tls
import sys
import repr
from plotly.graph_objs import Scatter, Layout, Figure, Data, Stream, YAxis
from datetime import datetime


#
# Class to handle Plotly data for Pirok2!
#
class MyPlotly:
	def __init__(self,doinit):
		#get my streams from config file
		self.pystream_ids = tls.get_credentials_file()['stream_ids']
		#print self.pystream_ids
		stream_token_tboil = self.pystream_ids[0]
		stream_token_tnez = self.pystream_ids[1]
		stream_token_t4 = self.pystream_ids[2]
		stream_token_h4 = self.pystream_ids[3]
		stream_token_b9 = self.pystream_ids[4]
		stream_token_btarg = self.pystream_ids[5]
		stream_token_poids2 = self.pystream_ids[6]
		stream_token_fl = self.pystream_ids[7]
		#test date 
		pyi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		#layout
		trace1 = go.Scatter(
    			x=[],
    			y=[],
    			name='T chaudiere',
    			stream=dict(
        			token=stream_token_tboil,
        			maxpoints=10000
    			)
		)
		trace2 = go.Scatter(
                        x=[],
                        y=[],
                        name='T extraction',
                        stream=dict(
                                token=stream_token_tnez,
                                maxpoints=10000
                        )
                )
		trace3 = go.Scatter(
                        x=[],
                        y=[],
                        name='T cuisine',
                        stream=dict(
                                token=stream_token_t4,
                                maxpoints=10000
                        ),
                        yaxis='y4'
                )
		trace4 = go.Scatter(
                        x=[],
                        y=[],
                        name='Hygro cuisine',
                        stream=dict(
                                token=stream_token_h4,
                                maxpoints=10000
                        ),
			#opacity=0.4,
                        yaxis='y5'
                )
		trace5 = go.Scatter(
		    	x=[],
		    	y=[],
		    	name='Pression extraction',
	    		stream=dict(
        			token=stream_token_b9,
        			maxpoints=10000
    	    		),
    			yaxis='y2'
		)
		trace6 = go.Scatter(
                        x=[],
                        y=[],
                        name='Pression consigne',
                        stream=dict(
                                token=stream_token_btarg,
                                maxpoints=10000
                        ),
                        yaxis='y2'
                )
		trace7 = go.Bar(
                        x=[],
                        y=[],
                        name='Poids shot',
                        stream=dict(
                                token=stream_token_poids2,
                                maxpoints=10000
                        ),
			opacity=0.4,
                        yaxis='y3'
                )
		trace8 = go.Scatter(
                        x=[],
                        y=[],
                        name='Flow',
                        stream=dict(
                                token=stream_token_fl,
                                maxpoints=10000
                        ),
                        yaxis='y6'
                )
	

		layout = go.Layout(
			title='My coffee shots',
    			yaxis=dict(
        			title='*C',
				domain=[0.55, 1]
    			),
    			yaxis2=dict(
        			title='bar',
        			titlefont=dict(
            				color='rgb(148, 103, 189)'
        			),
        			tickfont=dict(
            				color='rgb(148, 103, 189)'
        			),
        			overlaying='y',
        			side='right',
				domain=[0.55, 1]
    			),
			yaxis3=dict(
                                title='grams',
				domain=[0.2,0.5]
                        ),
			yaxis4=dict(
                                title='*C',
				domain=[0,0.2]
                        ),
                        yaxis5=dict(
                                title='%hygro',
                                side='right',
                                overlaying='y4',
				layer="below traces",
                                domain=[0,0.2]
                        ),
			yaxis6=dict(
                                title='flow',
                                side='right',
                                overlaying='y3',
#                                layer="below traces",
#                                domain=[0,0.2]
                        ),

		)

		#create figure object
		fig = Figure(data=[trace1, trace2, trace3, trace4, trace5, trace6, trace7,trace8], layout=layout)

		#opening streams
		try:
			if(doinit):
				print "Init Plotly figure and layout..."
	        		print(py.plot(fig, filename='Mes shots plotly'))
			print "Opening Plotly streams..."
        		self.stream_tboil = py.Stream(stream_token_tboil)
        		self.stream_tboil.open()
        		self.stream_tnez = py.Stream(stream_token_tnez)
        		self.stream_tnez.open()
        		self.stream_t4 = py.Stream(stream_token_t4)
        		self.stream_t4.open()
        		self.stream_h4 = py.Stream(stream_token_h4)
        		self.stream_h4.open()
        		self.stream_b9 = py.Stream(stream_token_b9)
        		self.stream_b9.open()
        		self.stream_btarg = py.Stream(stream_token_btarg)
        		self.stream_btarg.open()
        		self.stream_poids2 = py.Stream(stream_token_poids2)
        		self.stream_poids2.open()
        		self.stream_fl = py.Stream(stream_token_fl)
        		self.stream_fl.open()
			print "Plotly streams openned with success!"
		except Exception as e:
        		print "Plotly STREAMS unexpected error:", sys.exc_info()[0], " e=",repr(e)

	#helper to update plotly streams with try catch 
	def updateStream(self,st,data):
		#heartbeat to keep stream openned if closed
		try:
			st.heartbeat()
		except:
			print ""		
		#send data through stream
		try:
			st.write(data)
		except Exception as e:
                	print "Plotly updateHELPER unexpected error:", sys.exc_info()[0], " e=",repr(e)

	#- met a jour le graphe (simple, hors extraction)
	def update(self,tboil,tnez,t4,h4):
		#if(connected
		try:
                        pyi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			print "tboil"
			self.updateStream(self.stream_tboil,{'x': pyi, 'y': round(tboil,1) })
			print "tnez"
                        self.updateStream(self.stream_tnez,{'x': pyi, 'y': round(tnez,1) })
			print "h4"
                        self.updateStream(self.stream_h4,{'x': pyi, 'y': round(h4,1) })
			print "t4"
                        self.updateStream(self.stream_t4,{'x': pyi, 'y':  round(t4,1) })
			print "update success"
                except Exception as e:
                        print "Plotly updateSMALL unexpected error:", sys.exc_info()[0], " e=",repr(e)

	#- met a jour le graphe lors de l'extraction
	def updateFull(self,tboil,tnez,t4,h4,b9,pumpPTarget,poids2,fl):
		try:
                        pyi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			self.updateStream(self.stream_tboil,{'x': pyi, 'y': round(tboil,1) })
			self.updateStream(self.stream_tnez,{'x': pyi, 'y': round(tnez,1) })
			self.updateStream(self.stream_h4,{'x': pyi, 'y': round(h4,1) })
			self.updateStream(self.stream_t4,{'x': pyi, 'y': round(t4,1) })
			self.updateStream(self.stream_b9,{'x': pyi, 'y': round(b9, 1) })
                        self.updateStream(self.stream_btarg,{'x': pyi, 'y': pumpPTarget })
			if(poids2 > 100):
				poids2 = 100
			if(poids2 < 0):
				poids2 = 0
                        self.updateStream(self.stream_poids2,{'x': pyi, 'y': round(poids2,1) })
			if(fl > 30):
				fl = 30
                        self.updateStream(self.stream_fl,{'x': pyi, 'y': round(fl,1) })
                except Exception as e:
                        print "Plotly UpdateFULL unexpected error:", sys.exc_info()[0], " e=",repr(e)

