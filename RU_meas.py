"""
This is the python code contains driver for all measurement devices.
@author: Wenyuan Zhang @ Rutgers GershLab
"""

import sys, os, time, datetime
import visa
import win32com.client  # Python ActiveX Client
import numpy as np
import ctypes
import matplotlib.pyplot as plt
# to use labview program, open all relevant labview before running python
LabVIEW = win32com.client.Dispatch('LabVIEW.Application') 
rm = visa.ResourceManager()
dir_ = "C:\\Google Drive\\Rutgers Qubit Main Share Folder\\_People__Wenyuan\\Python\\" #measurement code directory

def setPlotting(PLOT=True):
    """
    Close all opening plots and turn on/off interaction mode
    """
    plt.close("all")
    if PLOT:
        plt.ion()# turn off plot interactive mode       
        print("Plot interactive on")
    else:
        plt.ioff()
        print("Plot interactive off")

def timestamp():
    return '{:%Y%m%d%H%M%S}'.format(datetime.datetime.now())
#############################################################################
        #Instuments 
    
class labView(object):
    
    def __init__(self):
        self.VI =None
        
    def initialize(self,VIpath):
        print("initialization %s" % VIpath)
        self.VI= LabVIEW.getvireference(VIpath)  # Path to LabVIEW VI
        self.VI._FlagAsMethod("Call")  # Flag "Call" as Method       
        
class VisaInstrument(object):    
    def __init__(self):
        self._name =None
        self._visaAddress = None
        self.handle = None
        
    def initialize(self):
        try:
            self.handle = rm.open_resource(self._visaAddress)
        except:
            print("ERROR: Cannot initialize instrument!")
            
    def getHandle(self):
        return self.handle
    def write(self,string):
        return self.handle.write(string)
    def ask(self,string):
        return self.handle.ask(string)
        
class K2602(labView):
    # if it is local folder please refer to e.g.
    # 'C:\\users\\josh\\desktop\\python.vi')
    
    def __init__(self):
        VIpath = dir_+"K2602A_SetCurrent.vi"
        super(K2602,self).initialize(VIpath)
        #self.setCurrent(1,0,0.001)        
        #self.setCurrent(2,0,0.001)
        
    def setCurrent(self,Chan,value,output_range):
        """
        output_range: 0.1
        """
        paras = ["Channel (1or2)",'Set Current (A)','Range (A)']
        values = [Chan,value,output_range]
        self.VI.Call(paras,values)
        time.sleep(0.2)
        return True
        
    def setB(self,value):
        if abs(value)>2e-3:
            print("current out of limit")
            return False
        else:
            if abs(value) <= 1e-3:
                self.setCurrent(2,0,0.001)
                self.setCurrent(1,value,0.001)
            else:
                if value > 0:
                    self.setCurrent(1,1e-3,0.001)
                    self.setCurrent(2,value-1e-3,0.001)
                else:
                    self.setCurrent(2,-1e-3,0.001)
                    self.setCurrent(1,value+1e-3,0.001)
            return True
                
    def setB_uA(self,value):
        self.setB(value*1e-6)

class Gigatronics(labView):
    def __init__(self,address):
        self.address = address
        VIpath = '\\\\192.168.13.2\\Gersh_Labview\\Python\\Gigatronics910_SetFreqLevel.vi'    
        super(Gigatronics,self).initialize(VIpath)
#        self.VI.Call()

    def setFreqPow(self,freq,power):
        paras = ["GPIB Address","Frequency (GHz)","Power (dBm)"]
        values = [self.address,freq,power]
        self.VI.Call(paras,values)

class LakeShore(VisaInstrument):
    def __init__(self,visaAddress = "GPIB::12::INSTR",name = "LakeShore"):

        self._name = name
        self._visaAddress = visaAddress
        
        print("Initializing with resource %s" % visaAddress)
        print("Initializing LakeShore")
        
        try:
            super(LakeShore, self).initialize()
        except:
          print("ERROR: Cannot initialize instrument!")

    def readTemp(self,Chan):
        """
        return Temperature(K) and Resistance(Ohm)
        """
        Temp = self.ask("RDGK? %d \n\r" % Chan)
        Temp = float(Temp.split()[0])
        time.sleep(0.1)
        Resistance = self.ask("RDGR? %d \n\r" % Chan)
        Resistance = float(Resistance.split()[0])
        time.sleep(0.1)
        return Temp,Resistance

        
class Anristu_sgen(VisaInstrument):
    
    def __init__(self,visaAddress = "GPIB::18::INSTR",name = "Anristu_sgen"):
        self._name = name
        self._visaAddress = visaAddress
        
        print("Initializing with resource %s" % visaAddress)
        print("Initializing Anristu_sgen")
        
        try:
          super(Anristu_sgen, self).initialize()
        except:
          print("ERROR: Cannot initialize instrument!")
    
    def setFreqPow(self,freq,power):
        self.write("CF1 %.8f GH; XL1 %4f DM; PO;XP" % (freq,power))
        time.sleep(0.2)
    def RFswitch(self,option):
        if option=='ON':
            self.write('RF1')
        else:
            self.write('RF0')

class Aeroflex(labView):
    def __init__(self):
        VIpath = dir_+"Aeroflex8311_SetAttenuation.vi"
        super(Aeroflex,self).initialize(VIpath)
        self.setAtten(1,0) # zero attenuator on the output line through Aeroflex
    def setAtten(self,CHAN,attenuation):
        paras = ["Channel","Attenuation (dB)"]
        values = [CHAN,int(np.abs(attenuation))]
        self.VI.Call(paras,values)
        time.sleep(0.2)
        return True
    def atten_DRinput(self,attenuation):
        self.setAtten(1,attenuation)
        
    def BalAtten(self,attenuation):
        self.setAtten(1,attenuation)
        if attenuation<30:
            at2=np.ceil((15*np.exp(-attenuation/15)))-1
#            at2=30-attenuation
        else:
            at2=2
        print(at2)
        self.setAtten(2,at2)
        return at2
        
class spectroscopy_File_Header():
    """
    Initialize header to spectroscopy file
    """
    def __init__(self,TChan1,TChan2,PUMPON,Misc,Device,set_spara):
        self.labels = "#T%d(K)\tT%d(K)\tSignalFreq(Hz)\tMag(dB)\tPhase(rad)\tSignalPow(dBm)\tNumOfAvg\tVNA_Port1_atten" %(TChan1,TChan2)
        if PUMPON:
            self.labels = self.labels + '\tPumpFreq(GHz)\tPumpPower(dBm)'
        
        note = []
        note.append("Device: %s" % Device)
        note.append("Spara: %s" % set_spara)
        note.append("Misc: %s" % Misc)
        note.append("Signal Source : Anristu37369A")
        note.append('Data starts from here :\n')    
        self.note = note
    def addtolabels(self,string):
        self.labels = self.labels + string
    def header(self):
        header = [self.labels]
        header.extend(self.note)
        header = "\n#".join(header)
        return header
    def num_row(self):
        return np.size(self.labels.split('\t'))

class ATS_spec(labView):
    def __init__(self,num_pts=8192,num_avg=4000,num_buff=1):
        VIpath = "Z:\\IQ Mixer\\"+"ATS9870_Spect_v1.vi"
        
        super(ATS_spec,self).initialize(VIpath)
        self.num_pts=num_pts
        self.num_avg=num_avg
        self.num_buff=num_buff
        self.measure([4])
        self.readvalue()
        time.sleep(0.1)
       
    def measure(self,frequency_GHz_List):
        """
        frequency_GHz_List is numpy array
        """
        paras = ['Number of Points','#ofAvgs','# of Buffers to Avg','Frequency(GHz)']
        if type(frequency_GHz_List) != list:
            frequency_GHz_List = frequency_GHz_List.tolist()
        values = [self.num_pts,self.num_avg,self.num_buff,frequency_GHz_List]
        self.VI.Call(paras,values)
        #time.sleep(0.2)
        return self.readvalue()
    def readvalue(self):
        result = self.VI.getcontrolvalue('appended array')    
        return np.array(result)

class AgilentPSG(VisaInstrument):
    def __init__(self,visaAddress = "GPIB::19::INSTR",name = "AgilentPSG"):
        self._name = name
        self._visaAddress = visaAddress
        
        print("Initializing with resource %s" % visaAddress)
        print("Initializing AgilentPSG")
        
        try:
            super(AgilentPSG, self).initialize()
        except:
          print("ERROR: Cannot initialize instrument!")
          self.RFswitch('OFF')
    def setFreq(self,freq_GHz):
         self.write("FREQ %d MHz\n" % (freq_GHz*1e3))
         time.sleep(0.2)
         return self.ask("FREQ:CW?")
    def setPower(self,pow_dBm):
        if pow_dBm >=-140:
            self.write("OUTP:STAT ON\n")
            self.write("POW:AMPL %f dBm\n" % pow_dBm)
            time.sleep(0.2)
            return self.ask("POW:AMPL?")
        else:
            #print('Off')
            self.RFswitch('OFF')
            
    def RFswitch(self,state):
        if state == 'ON' or state =='OFF':
            self.write("OUTP:STAT %s\n"%state)
        else:
            print('state is not ON nor OFF')
        return self.ask("OUTP?")

class HP436A(labView):
    def __init__(self):
        VIpath = dir_+'HP 436A Read Single Measurement.vi'    
        super(HP436A,self).initialize(VIpath)
#        self.VI.Call()

    def readPower(self):
        self.VI.Call()
        result = self.VI.getcontrolvalue('Measurement')
        return result

def popupWin(msg):
    ctypes.windll.user32.MessageBoxW(0, msg, "Warning:", 1)
        
         
#%%
        
if __name__ =="__main__":
    import time
    Dir = "C:\\Users\\meas\\Dropbox\\_People__Wenyuan\\MW_Calibration\\02172017\\"
    SGEN1=Anristu_sgen()
    SGEN2=Gigatronics(6)
    attBank=Aeroflex()
    powerMeter=HP436A()
    SGEN1.setFreqPow(4,15)
    SGEN2.setFreqPow(3.97,10)
    ATS=ATS_spec(8192,4000,1)
    
#    AeroflexP1_input_dBm=-20
#    AeroflexP1_att_dB=np.arange(0,50,3)
#    AeroflexP2_att_dB=30
#    attBank.setAtten(2,AeroflexP2_att_dB)
#    result=[]
#    powerMeter.readPower()
#    for atten in AeroflexP1_att_dB:
#        attBank.setAtten(1,atten)
#        result.append(powerMeter.readPower())
#        print(atten)
#        time.sleep(4)
#    
#    result=np.array(result)
##    data = np.vstack((AeroflexP1_att_dB,result)).transpose()
#    
#    
#    x = AeroflexP1_input_dBm-AeroflexP1_att_dB
#    y = result+AeroflexP2_att_dB
#    
#    data= np.vstack((x,y)).transpose()
#    setup=['VNA','ATS'][1]
#    fname=Dir+'%s_S21RTinputpowervsPortPpower_noBPF_%s.dat'%(setup,timestamp())
#    with open(fname,'w') as fh :
#        fh.write('#\n')
#    with open(fname,'ab') as fh:
#        np.savetxt(fh,data)
#%%
    plt.close('all')    
    attBank.BalAtten(10)
    ATS.measure(np.arange(2.5,10,0.1).tolist())    