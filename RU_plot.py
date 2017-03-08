# -*- coding: utf-8 -*-
"""
Created on Sat Dec 10 13:18:00 2016
This is module contains functions that read and plot TWPA data
@author: Wenyuan Zhang
"""

import numpy as np
import os
import fnmatch
import re
import matplotlib.pyplot as plt
import scipy.optimize as spopt
from scipy.stats import linregress
import time, datetime
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
from config import *

def getxarray(A):
    """
    unwrapping stacked x array to get a singal valued x axis
    """
    min_ = A.min()
    max_ = A.max()
    step = np.abs(A[1]-A[2])
    length = int(np.round((max_-min_)/step))+1
    x = A[0:length]     
    x = np.array(x)        
    return x

def magPhase2ReIm(mag,phase):
    mag = 10**(mag/20)
    Re = mag*np.cos(phase)
    Im = mag*np.sin(phase)
    return Re,Im
def ReIm2magPhase(Re,Im):
    Spara = Re+1j*Im
    mag = 20*np.log10(absolute(Spara))
    phase = np.angle(Spara)
    return mag, phase    

class dfile(object):
    def __init__(self,fname) :
        """
        get header and data
        """
        self.fname = fname
        self.header=[]
        fh = open(self.fname,'r')
        line = fh.readline()     
#        print('1: ',line[0])
        while line[0] == '#':
            self.header.append(line)
            line = fh.readline()

        self.labels = self.header[0][1:].split()
        
        data = np.loadtxt(fname)
        self.num_cols = data.shape[1]

        if "Data starts from here" not in self.header[-1]:            
            print(self.header[-1])
        if "VNA Port 1 to Aeroflex CHAN2 to Coupler" in self.header[-1]:
#            print()
            temp_row = self.header[-1].split()[-self.num_cols::]        
            temp_row = [float(s) for s in temp_row]
            temp_row = np.array(temp_row)
#            print(temp_row)
            self.data = temp_row
            for row in data:
                self.data=np.vstack((self.data,row))
        else:
            self.data = data
        
        self.num_rows = self.data.shape[0]
        self.index = np.arange(self.num_rows)
        
class TWPAdata(dfile):
    """
    read TWPAdata and change to 2D spreadsheet XYZ
    X must be continously stored as rows and stacked. 
    Y is constant for each X period.
    """
    def __init__(self,fname,xlabel='SignalFreq(Hz)',ylabel='SignalPow(dBm)'):
        print("Processing %s" % fname)

        super(TWPAdata,self).__init__(fname)
                
        #self.mag = self.data[:,self.labels.index("Mag(dB)")] #+ self.data[:,self.labels.index('VNA_Port1_atten')]
        #self.phase = self.data[:,self.labels.index("Phase(rad)")]
        #self.Re,self.Im = magPhase2ReIm(self.mag,self.phase)
        try :
            self.data[:,self.labels.index("Mag(dB)")] = self.data[:,self.labels.index("Mag(dB)")] + self.data[:,self.labels.index('VNA_Port1_atten')]
            print("Apply S21 Mag correction.")
        except:
            pass
        self.X = self.getX(xlabel)
        self.Y = self.getY(ylabel)
        #print("Done")
        
    def getParaArray(self,index):
        """
        get a list of values of certain parameters varied in the measurement
        This function is valid for one variable varied, e.g. signal power.
        It is not valid if two are varied, e.g. both signal power and magneitc fied. 
        """
        x = self.data[:,index]
        rows = int((self.num_rows/self.X.size))
        x = np.reshape(x,(rows,self.X.size))
        y =[]
        for i in x:
            y.append(np.average(i))
        return np.array(y)
        
    def remove_electricDelay(self,freq,phase):
        """
        return slope, intercept
        """
        result= linregress(freq,phase)
        slope,intercept = result[0:2]
        return slope, intercept
    def getIndex(self,label):
        """
        return index corresponds to column
        """
        return self.labels.index(label)
        
    def getY(self,ylabel):
        return self.getParaArray(self.getIndex(ylabel))
    def getX(self,xlabel):
        return getxarray(self.data[:,self.getIndex(xlabel)])
        
    def to2DZ(self,zlabel):
        """
        return X,Y as 1D array, Z as 2D array.
        """
        i = self.labels.index(zlabel)
        t = self.data[:,i]
        Z=[]
        index = np.reshape(self.index,(self.Y.size,self.X.size))
        for row in index:
            Z.append(t[row])
        Z = np.array(Z)
        return Z.transpose()
        
def getFileList(matchKey,timestamp,fdir):
    """
    input the file name, and time stamp
    timestamp shoud be a 2-d tuple
    output file list
    """
    entries = []
    time_i = timestamp[0]
    time_f = timestamp[-1]
    for dfile in os.listdir(fdir):
        if fnmatch.fnmatch(dfile,matchKey) :    
            if "PumpON" not in dfile:
                creationTime = int(dfile.split('.')[0].split('_')[-1])                
                
            if (creationTime <=time_f ) and (creationTime>=time_i):
                print(dfile, "added to list")
                B_field = float(re.findall('[+-]?\d+',dfile)[-2])                
                entries.append([B_field,fdir+dfile])
    entries.sort()       # order data in terms of magnetic field
    return entries

class dataXYZ(object):
    """
    X,Y are 1D arrays
    Z is 2D 
    """
    def __init__(self):
        self.X = None
        self.Y = None
        self.Z = None
        self.timestamp = None
        self.figname = None
        self.fname = None
    
    def initialize(self,X,Y,Z):
        self.X = X
        self.Y = Y
        self.Z = Z
        
    def readfromfile(self,fname):
        """
        read data into X,Y,Z
        the data file should have X and Y as first row and column.
        Z fills the rest of the 2-D array.
        """
        data = np.loadtxt(fname)
        self.X = data[0,1:]
        self.Y = data[1:,0]
        self.Z = data[1:,1:]
        self.fname = fname
    def savetofile(self,fname,**kwargs):
        """
        **kwargs: Misc to save header from original measurement file
        """
        header = []
        header.append("# X :%s"%kwargs['x'])
        header.append("# Y :%s"%kwargs['y'])
        header.append("# Z :%s"%kwargs['z'])
        header = '\n'.join(header)
        fname = outputDir+fname
        with open(fname,'w') as fh:
            fh.write(header)
            if 'Misc' in kwargs:
                fh.write(kwargs['Misc'])
            else :
                print("Misc not in keyword." )
                return False
        
        a,b = self.Z.shape    
        Xdim, Ydim = [self.X.size,self.Y.size]
        if a == Ydim and b ==Xdim:
            print('X,Y dimensions',Xdim,Ydim)
            matrix = np.zeros((Ydim+1,Xdim+1))
            matrix[0,1:] = self.X
            matrix[1:,0] = self.Y
            matrix[1:,1:] = self.Z
            with open(fname,'ab') as fh:
                np.savetxt(fh,matrix,delimiter='\t')
        else:
            print("X,Y,Z dimensions don't match. Fail to save file.")
            return False
            
    def pcolor(self):
        plt.close()
        plt.figure(figsize =(6,6))
        self.fig = plt.gcf()
        plt.pcolormesh(self.X,self.Y,self.Z)
        plt.autoscale(tight=True)
        plt.subplots_adjust(bottom = 0.3,top=0.9)
        plt.show()
        self.ax = plt.gca()
        self.timestamp = get_timestamp_from_fname(self.fname)
        plt.xlabel(self.labels[0])
        plt.ylabel(self.labels[1])
        plt.title(self.labels[3])
        cbar =plt.colorbar()
        cbar.set_label(self.labels[2])
        
    def savefig(self,Dir_,figname,**kwargs):
        """
        **kwargs : timestamp
        """
        if 'timestamp' in kwargs:
            self.fig.savefig(Dir_+figname+'_%s.png'% timestamp)
        else:
            self.fig.savefig(Dir_+figname+'.png')
        
    def set_labels(self,xlabel,ylabel,zlabel,title):
        self.labels = [xlabel,ylabel,zlabel,title]

    def texttoPlot(self,stringList):
        text = []
        text.extend(stringList)
        text.append('Time stamp: *%s.dat' % self.timestamp)
        self.ax.text(0,-0.3,'\n'.join(text), horizontalalignment='left',verticalalignment='center',transform=self.ax.transAxes)
        
def get_timestamp_from_fname(fname_):
    return fname_.split('.')[0].split('_')[-1]
    
        #%%
#if __name__ =="__main__":
#    
#    Dir_ =  inputDir+"GAINMEAS\\"
#    fname =Dir_+"TWPA_S21GAIN_sigFreq=4000-7000MHz_AeroflexCH2=40dB_pumpFreq=5200MHz_B=240uA_20161229230459.dat"
#    data = dataXYZ()
#    data.readfromfile(fname)
#    title = 'Gain at pump frequency = 5.2GHz, B = 240uA,'
#    zlabel = 'Gain(dB)'
#    data.labels('Pump Power(dBm)','Signal Freq(GHz)',zlabel,title)
#    data.pcolor()
##    data.savefig("Gain_AeroflexCH2=40dB_pFreq=5200MHz_B=240uA")
##    X = np.arange(10)
##    Y = X
##    Z = np.ones((9,9))
##    contour = contourXYZ()            
##    contour.initialize(X,Y,Z)
##    contour.pcolor()
##    fname = dataDir + 'TWPA__PhasevsPowervsB_sigf=4150MHz_20161228183003.dat'
##    entry = TWPAdata(fname,xlabel='SignalPow(dBm)',ylabel='B(uA)')
##    print(entry.getX('SignalPow(dBm)'))
##    Y = entry.X
##    X = np.hstack((np.arange(290,220,-1),np.arange(200,50,-30),np.arange(50,-10,-2)))
##    Z = entry.to2DZ('Phase(rad)').transpose()
##    contour = contourXYZ()            
##    contour.initialize(X,Y,Z)
##    contour.pcolor()
