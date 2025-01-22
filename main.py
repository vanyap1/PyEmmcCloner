
import re
import configparser
import json
import os
import shutil
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen 
from threading import Thread
from kivy.clock import Clock
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.image import Image
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ObjectProperty
from datetime import datetime
from collections import namedtuple

#from remoteCtrl import start_server_in_thread
from remoteCtrlServer.udpService import UdpAsyncClient
from remoteCtrlServer.httpserver import start_server_in_thread
from backgroundServices.backgroundProcessor import BackgroundWorker

#from kivy.uix.popup import Popup
from kivy.config import Config

from kivy.core.window import Window
#from kivy.factory import Factory

from supportFunctions import *


config = configparser.ConfigParser()

if not os.path.exists("config.ini"):
    print("Config file not found")
    shutil.copy("config_init.ini", "config.ini")
    print("Config file copied from config_init.ini to config.ini")
    
config.read("config.ini")


# result array position index
passed = 1
failed = 0

#default config values
masterImageDev = config.get('DEFAULT', 'masterImageDev')
masterImageDir = config.get('DEFAULT', 'masterImageDir')
screenBgImage = config.get('DEFAULT', 'bgImage')


#network config values
remCtrlPort = int(config.get('Network', 'remCtrlPort'))
remCtrlHost = config.get('Network', 'remCtrlHost')


#slot config values
targetdDevices = config.get('SlotWidgets', 'targetdDevices').split(', ')

#GPIO expander config values

slotUdpHandlerPort = int(config.get('udpClient', 'udpPort')) 

doorOpenSensorModuleNum = int(config.get('jig', 'doorOpenSensorModuleNum')) 


Window.size = (800, 480)
Window.fullscreen = False





Result = namedtuple('Result', ['passed', 'failed'])

class Color():
    passed = "00ff00"
    failed = "ff0000"
    #yield = "ffbf00"
    terminated= "ffff00"
    error = "0000ff"
    pending ="00ffff"
    green = "00ff00"
    red = "ff0000"
    yellow = "ffbf00"

Builder.load_file('kv/commandsWidget.kv')
Builder.load_file('kv/statusbar.kv')
Builder.load_file('kv/masterImageCreator.kv')
startYPos = (200)/2             #Functional block


class UpperStatusbar(Screen):
    timeLbl = StringProperty("System idle")
    runStatus = StringProperty("run state")
    jigState = StringProperty("")
    ctrlType = StringProperty("--")
    ipAddr = StringProperty(f"none /:{remCtrlPort} ")

    def setLabel(self, param):
        self.masterImage = param

    def setColor(self, text, color):
        return f"[color={color}]{text}[/color]"
    
    def imageCreateWindow(self):
        pass



class SlotWidget(Screen):
    label_text = StringProperty("System idle")
    slotCurrentStatus = StringProperty("pending")
    
    slotStatusCounter = StringProperty("Passed: 0\n Failed: 0\n Yield: 100%")
    targetDev = StringProperty("none")
    jigStatus = BooleanProperty(False)
    emmcInserted = BooleanProperty(False)
    emmcConnectionDir = StringProperty("none")
    emmcCurrentState = StringProperty("EMMC Connected")
    slotStateusLabel = StringProperty("EMMC not detect")

    masterImage = StringProperty("none")
    failed = NumericProperty(0)
    passed = NumericProperty(0)
    slotName = StringProperty("")
    workerInstance = ObjectProperty(None)
    progresBarVal = NumericProperty(0) 
    

    
    def workerCbReg(self):                                                      #Background worker result handler callback registration
        #Starting background worker
        self.workerInstance.startProc()                                         #Start background worker
        self.workerInstance.setDrive(self.targetDev)                            #Set target device
        self.workerInstance.cbRegister(self.resultHandlerCb)                    #Register callback for background worker
        
    

    def resultHandlerCb(self, arg):                                             #Background worker callback handler
        print("resultHandlerCb-", arg)
        pass

    def getSlotStatus(self):                                                    #Slot status getter
        slotStatusBool, slotStatus, progress_info, resultPassFail, progress = self.workerInstance.getStatus() 
        
        self.yieldVal = 100
        if resultPassFail[failed] != 0 and resultPassFail[passed] != 0:
            try:
                self.yieldVal = (resultPassFail[passed] / (resultPassFail[passed] + resultPassFail[failed]))*100
            except ZeroDivisionError:
                self.yieldVal = 100
            except:
                print("Unexpected error:", sys.exc_info()[0])    
        self.slotStatusCounter = f"[color={Color.green}]Passed: {resultPassFail[passed]}[/color]\n [color={Color.red}]Failed: {resultPassFail[failed]}[/color]\n Yield: {self.yieldVal:.1f}%"
    
        return slotStatusBool, slotStatus, progress_info, resultPassFail, progress
    
    def runProc(self):                                                          #Slot process start

        pass

    def backgroundWorkerCmd(self, cmd):                                         #Background worker command setter
        self.workerInstance.setCmd(cmd)
        pass
    def writeImg(self, imagePath):                                              #Write image to device, 
        res = self.workerInstance.writeDev(self.targetDev, imagePath)
        return res

    def readImg(self, imagePath):                                               #Read image from device
        res = self.workerInstance.readDev(self.targetDev, imagePath)    
        return res
    def buildImg(self, rootFSzip):                                              #Build image on device
        res = self.workerInstance.buildDevFs(self.targetDev, rootFSzip)
        return res
    def getStatus(self):                                                        #Get slot status
        return self.slotCurrentStatus

    ''' GPIO Based part
    OPI - Orange PI single board mini pc 
    OPI Shield GPIO baset communication part
    '''
    def getJigStatus(self):                                                     #Check JIG status input pin
        return True    
    def isEmmcDetected(self):                                                   #Check eMMC card detection line
        return True
    
    
    
    

    
        
        
        
class MainScreen(FloatLayout):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        

        self.supportFns = supportFNs                            #Support functions object creation
        self.jigState = False                                   #JIG state variable
        self.background_image = Image(source=screenBgImage, size=self.size)
        self.add_widget(self.background_image)                  #Add background image to screen
        self.statusBar = UpperStatusbar(pos=(10, 190), size=(800-44, 80), size_hint=(None, None))
        self.statusBar.ctrlType = self.setColor("LOCAL" , Color.green)
        
        self.statusBar.ipAddr = self.setColor(f"{self.supportFns.get_ip_addresses(self)}:{remCtrlPort}", Color.yellow)
        self.add_widget(self.statusBar)                         #Add status bar to screen

        self.emmcSlots = []                                     #Slots array creation
        for index, device in enumerate(targetdDevices):         #Iterate through target devices and create slots widgets grid
            yPos = startYPos
            xPoz = 0
            if(index <= 4):
                xPoz = ((175+20) * index) + 20
            
            if(index >= 4):
                yPos = startYPos - 90
                xPoz = ((175+20) * (index - 4)) + 20
            
            emmcWidget = SlotWidget(pos=(xPoz/2 , yPos), size=(175, 160), size_hint=(None, None))
            emmcWidget.targetDev = device
            emmcWidget.slotName = f"{index}"
            
            slotWorker = BackgroundWorker()                     #Background worker creation for slot long time process
            emmcWidget.workerInstance = slotWorker              #Send worker instance to slotInstance
            emmcWidget.workerCbReg()                            #Register callback for worker


            #Add slots to slots array
            self.emmcSlots.append(emmcWidget)                   #Add slot to slots array
            self.add_widget(self.emmcSlots[index])              #Add slot widget to screen

        
       
        self.server, self.server_thread = start_server_in_thread(remCtrlPort, self.remCtrlCB, self) #Start remote control server
        Clock.schedule_interval(lambda dt: self.update_time(), 1)                                   #Start screen update timer
        self.udpClient = UdpAsyncClient(self)
        self.udpClient.startListener(slotUdpHandlerPort, self.udbCbWorker)

    def isSlotReady(self, slotNum):
        if self.emmcSlots[slotNum].emmcInserted == False:
            return "err: emmc not inserted"
        if self.emmcSlots[slotNum].emmcConnectionDir != "crpi":
            return "err: Slot is not in crpi mode" 
        if self.jigState == False:
            return "err: JIG is not closed"       

    def remCtrlCB(self, arg):                                   #Remote control callback
        #['', 'slot', '0', 'status']
        reguest = arg.split("/")                        #Split request to array
        print("CB arg-", reguest )
        result, number = self.checkIfSlotCmd(reguest[0])        #Check if request is slot command and slot number extraction
        if result:
            #slot command handler
            #number -=1                                          #Slot number correction
            print("slot number-", number)
            if number >= len(self.emmcSlots):
                return f"err: slot {number} does not exist"
            if reguest[1]:
                if(reguest[1] == "status_obsolete"):
                    resultBool, resultStr, progress = self.emmcSlots[number].getSlotStatus()
                    print(f"status: {resultBool}; {resultStr}; {progress}")
                    return f"{resultBool}; {resultStr}; {progress}"
                
                elif(reguest[1] == "status"):
                    statusRes = self.emmcSlots[number].getSlotStatus()
                    slotFree = False
                    if statusRes[0] == True:
                        slotFree = True
                    statusResStr = statusRes[1].replace(";", ",")     
                    return F"info: {slotFree}; {statusResStr}; {statusRes[2]}; {statusRes[3][1]}; {statusRes[3][0]}; {statusRes[4]}"
                
                elif(reguest[1] == "buildimg"):
                    return  self.emmcSlots[number].buildImg(reguest[2])
                
                elif(reguest[1] == "readimg"): 
                    res = self.isSlotReady(number)
                    if res:
                        return res
                    else:
                        return  self.emmcSlots[number].readImg(reguest[2])
                    
                elif(reguest[1] == "writeimg"):
                    res = self.isSlotReady(number)
                    if res:
                        return res
                    else:
                        return   self.emmcSlots[number].writeImg(reguest[2])    
                return "ok" 

        else:
            #common command handler
            print(reguest)
            return "ok"
        
        return "incorrect request"
    
    def checkIfSlotCmd(self, text):
        match = re.match(r'^slot(\d+)', text)
        if match:
            slot_number = int(match.group(1))
            return True, slot_number
        return False, None

    def stop_server(self):
        if self.server:
            self.server.shutdown()
            self.server_thread.join()

    def setColor(self, text, color):                                #Text color setter   
        return f"[color={color}]{text}[/color]"

    def update_time(self):
        dateTime = datetime.now().strftime('%H:%M:%S')
        passedTotal = 0
        failedTotal = 0
        
        for emmcSlot in self.emmcSlots:
            passedTotal += emmcSlot.passed
            failedTotal += emmcSlot.failed
            emmcSlot.label_text = emmcSlot.getSlotStatus()[1]
            emmcSlot.passed = emmcSlot.getSlotStatus()[3][1]
            emmcSlot.failed = emmcSlot.getSlotStatus()[3][0]
            emmcSlot.progresBarVal = emmcSlot.getSlotStatus()[4] 

        yieldTotal = 100
        if ((passedTotal + failedTotal) != 0):
            yieldTotal = (passedTotal / (passedTotal + failedTotal))*100
        self.statusBar.timeLbl = f'[color=0066ff]{dateTime}[/color]'
        self.statusBar.runStatus = f"[color={Color.green}]Passed: {passedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={Color.red}]Failed: {failedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={Color.yellow}]Yield: {yieldTotal:.1f};[/color]"

    def udbCbWorker(self, arg):
        try:
            data = json.loads(arg)
            #print(data)
            slotNum = data.get("slotNum")
            cardConnStatus = data.get("slotStatus")
            cardDetect = data.get("emmcDetect")
            jigStatus = data.get("jigSwitch")
            try:
                if slotNum < len(self.emmcSlots):
                    self.emmcSlots[slotNum].emmcInserted = cardDetect
                    self.emmcSlots[slotNum].jigStatus = jigStatus
                    self.emmcSlots[slotNum].emmcConnectionDir = cardConnStatus
                    if cardDetect == False:
                        self.emmcSlots[slotNum].slotStateusLabel = "EMMC not detect"
                        self.emmcSlots[slotNum].emmcCurrentState = "EMMC Connected"    
                    else:
                        self.emmcSlots[slotNum].slotStateusLabel = self.emmcSlots[slotNum].emmcCurrentState    

                if slotNum == 0:
                    self.statusBar.jigState = f"JIG: {jigStatus}"
                    self.jigState = jigStatus
            except:
                print("Slot number out of range error")      

            #print(f"slotNum: {slotNum}; cardDetect: {cardDetect}; cardConnStatus: {cardConnStatus}; jigStatus: {jigStatus}")


        except json.JSONDecodeError as e:
            print("Failed to deserialize JSON:", e)
        pass
        

class BoxApp(App):
    def build(self):
        self.screen = MainScreen()
        return self.screen
    
    def on_stop(self):
        self.screen.stop_server()

if __name__ == '__main__':
    BoxApp().run()
