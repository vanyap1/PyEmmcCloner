import subprocess

import time
import shlex
import pty
import os, socket, re
from urllib import request
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen , ScreenManager
from threading import Thread
from kivy.clock import Clock
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.image import Image
from kivy.uix.scatter import Scatter
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ObjectProperty
from datetime import datetime, date, timedelta
from collections import namedtuple

#from remoteCtrl import start_server_in_thread
from remoteCtrlServer.httpserver import start_server_in_thread
from backgroundServices.backgroundProcessor import BackgroundWorker

from kivy.uix.popup import Popup
from kivy.config import Config

from kivy.core.window import Window
from kivy.factory import Factory

from supportFunctions import *
#from discOperation import SlotHandler

from i2c_gpio import  I2CGPIOController, IO, DIR, Expander



sysI2cBus = 1
Window.size = (1024, 600)
remCtrlPort = 8080

#targetdDevices = ["mmca", "mmcb","mmcd","mmce","mmc1","mmc2","mmc3","mmc4"]
targetdDevices = ["mmca", "mmcb"]
expanderAddr = [0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27]
masterImageDev = "mmca"

Result = namedtuple('Result', ['passed', 'failed'])
masterImageDir = "/home/pi/images/"



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

startYPos = 188             #Functional block


class UpperStatusbar(Screen):
    timeLbl = StringProperty("System idle")
    runStatus = StringProperty("")
    masterImage = StringProperty("image not set")
    ctrlType = StringProperty("--")
    ipAddr = StringProperty(f"none /:{remCtrlPort} ")

    def setLabel(self, param):
        self.masterImage = param

    def setColor(self, text, color):
        return f"[color={color}]{text}[/color]"
    
    def imageCreateWindow(self):
        popup = ImageCreator(NewimageName = "master.img", sourceDevise=masterImageDev)
        popup.open()


class ImageCreator(Popup):
    windowTitle = StringProperty("null")
    cliStatusLine = StringProperty("null")
    
    def __init__(self, NewimageName=None, sourceDevise=None):
        super().__init__()
        self.NewimageName = NewimageName
        self.sourceDevise = sourceDevise
        self.windowTitle = f"Image creation: {self.NewimageName}; device: {self.sourceDevise}"
        self.cliStatusLine = f"Press start to process. \nOld image '{self.NewimageName}' will be overwritwe if exist"

        if(NewimageName==None or sourceDevise==None):
            self.cliStatusLine = self.setColor("Incorrect input parameters", Color.red)


    def call_function(self):

        self.cliStatusLine = "Here will placed a progress of creation status"
        self.ids.startBtn.disabled = True
        #self.readerProperty = ImageReader(self, masterImageDev, "master.img")


    def cancelationRequesr(self):

        if hasattr(self, 'readerProperty'):
            self.readerProperty.command = "cancel"
        self.dismiss()


    def setColor(self, text, color):
        return f"[color={color}]{text}[/color]"

class SlotWidget(Screen):
    label_text = StringProperty("System idle")
    slotCurrentStatus = StringProperty("pending")
    progresBarVal = NumericProperty(0)
    slotStatusCounter = StringProperty("Passed: 0; Failed: 0; Yield: 100%")
    targetDev = StringProperty("none")
    btnText = StringProperty("targetDev")
    btnText = targetDev
    masterImage = StringProperty("none")
    failed = NumericProperty(0)
    passed = NumericProperty(0)
    slotName = StringProperty("")
    gpioController = ObjectProperty(None)
    workerInstance = ObjectProperty(None)
    
    

    def gpioInit(self):
        self.runStateShield = IO(expander = self.gpioExpander, portNum = 0, pinNum = 0, pinDir=DIR.INPUT)
        self.piShieldCmdRun = IO(expander = self.gpioExpander, portNum = 0, pinNum = 1, pinDir=DIR.OUTPUT)
        self.piShieldCmdModifier = IO(expander = self.gpioExpander, portNum = 0, pinNum = 2, pinDir=DIR.OUTPUT)

        self.jigSw = IO(expander = self.gpioExpander, portNum = 1, pinNum = 0, pinDir=DIR.INPUT)
        self.emmcDet = IO(expander = self.gpioExpander, portNum = 1, pinNum = 1, pinDir=DIR.INPUT)
        self.emmcChRel = IO(expander = self.gpioExpander, portNum = 1, pinNum = 2, pinDir=DIR.OUTPUT)
        self.okLED =IO(expander = self.gpioExpander, portNum = 1, pinNum = 3, pinDir=DIR.OUTPUT)
        self.busyLED =IO(expander = self.gpioExpander, portNum = 1, pinNum = 4, pinDir=DIR.OUTPUT)
        self.errLED =IO(expander = self.gpioExpander, portNum = 1, pinNum = 5, pinDir=DIR.OUTPUT)
        self.emmcCD = IO(expander = self.gpioExpander, portNum = 1, pinNum = 6, pinDir=DIR.OUTPUT)
        self.muxCtrl = IO(expander = self.gpioExpander, portNum = 1, pinNum = 7, pinDir=DIR.OUTPUT)
        
        
        
        
        self.gpioController.addExpandersInfo(self.gpioExpander)
        
        self.gpioController.setPinDirection(self.runStateShield, False)
        self.gpioController.setPinDirection(self.piShieldCmdRun, False)
        self.gpioController.setPinDirection(self.piShieldCmdModifier, False)
        
        self.gpioController.setPinDirection(self.emmcDet, False)
        self.gpioController.setPinDirection(self.muxCtrl, True)
        self.gpioController.setPinDirection(self.emmcCD, True)
        self.gpioController.setPinDirection(self.jigSw, False)
        self.gpioController.setPinDirection(self.busyLED, True)
        self.gpioController.setPinDirection(self.okLED, False)
        self.gpioController.setPinDirection(self.errLED, False)
        self.gpioController.setPinDirection(self.emmcChRel, True)
        
        self.workerInstance.startProc()
        self.workerInstance.setDrive(self.targetDev)
        self.workerInstance.cbRegister(self.resultHandlerCb)
        #self.backProc.startProc()
        #self.backProc.setDrive(self.targetDev)
        #self.backProc.setCmd("dfg")
        
        pass    
    
    def workerCbReg(self):
        if(self.workerInstance != None):
            #self.workerInstance.cbRegister(self.resultHandlerCb)
            pass

    def resultHandlerCb(self, arg):
        #self.gpioController.pinWrite(self.okLED, True)
        #self.gpioController.pinWrite(self.busyLED, False)

        #self.gpioController.pinWrite(self.muxCtrl, False)
        #self.gpioController.pinWrite(self.emmcCD, False)
        print(arg)

    def getJigStatus(self):
        return self.gpioController.pinRead(self.jigSw)    

    def getPiShieldStatus(self):
        return self.gpioController.pinRead(self.runStateShield)
    
    def setPiShieldcommand(self, state: bool):
        #print(state)
        self.gpioController.pinWrite(self.piShieldCmdRun, state)


    def setMasterImage(self, image):
        self.masterImage = image
        #self.statusBar.setLabel(image)
    def getSlotStatus(self):
        slotStatusBool, slotStatus, progress = self.workerInstance.getStatus() 
        return slotStatusBool, slotStatus, progress
    
    def runProc(self):
        self.gpioController.pinWrite(self.okLED, False)
        self.gpioController.pinWrite(self.errLED, False)
        self.gpioController.pinWrite(self.busyLED, True)
        
        self.gpioController.pinWrite(self.muxCtrl, False)
        self.gpioController.pinWrite(self.emmcChRel, True)
        


        self.gpioController.pinWrite(self.emmcCD, False)
        self.workerInstance.setCmd("test image.img")
        #self.workerInstance.imageWrite("")
        #print(self.workerInstance.getSlotStatus())
        pass

    def backgroundWorkerCmd(self, cmd):
        self.workerInstance.setCmd(cmd)
        pass
    def emmcConnInitConnection(self, destIf):
        print(destIf, "CONN")
        if destIf == "copi":
            self.gpioController.pinWrite(self.okLED, True)          #
            self.gpioController.pinWrite(self.errLED, False)        #
            self.gpioController.pinWrite(self.emmcCD, False) 
            time.sleep(1.5)

            self.gpioController.pinWrite(self.emmcChRel, True)      #
            self.gpioController.pinWrite(self.muxCtrl, False)       #
            

            return True
        elif destIf == "crpi":
            
            self.gpioController.pinWrite(self.okLED, False)         #
            self.gpioController.pinWrite(self.errLED, True)         #

            self.gpioController.pinWrite(self.emmcChRel, False)      #
            self.gpioController.pinWrite(self.muxCtrl, True)       #
            time.sleep(.5)
            self.gpioController.pinWrite(self.emmcCD, True)        #
            return True
        else:
            return False
        
        
        


class MainScreen(FloatLayout):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        
        self.piShielCmd :bool = False
        self.gpio = I2CGPIOController(sysI2cBus)

        self.supportFns = supportFNs
        self.masterImage = "master.img"
        self.background_image = Image(source='images/bg_d.jpg', size=self.size)
        self.add_widget(self.background_image)

        self.statusBar = UpperStatusbar(pos=(3, 245), size=(1024-10, 100), size_hint=(None, None))
        self.statusBar.ctrlType = self.setColor("LOCAL" , Color.green)
        self.statusBar.masterImage = self.setColor(self.masterImage , Color.yellow) 
        self.statusBar.ipAddr = self.setColor(f"{self.supportFns.get_ip_addresses(self)}:{remCtrlPort}", Color.yellow)
        self.add_widget(self.statusBar)

        self.emmcSlots = []
        for index, device in enumerate(targetdDevices):
            yPos = startYPos
            xPoz = 3
            if(index!=0 and index <= 4):
                yPos = startYPos - 60 * index
    
            if(index >= 4):
                yPos = startYPos - 60 * (index - 4)
                xPoz = 3 + 3 + 250

            emmcWidget = SlotWidget(pos=(xPoz , yPos), size=(500, 100), size_hint=(None, None))
            emmcWidget.targetDev = device
            print(f"Index: {index}, Device: {device}")
            emmcWidget.masterImage = self.masterImage
            
            

            slotWorker = BackgroundWorker()
            #slotWorker = SlotHandler(device=device, masterImgDir=masterImageDir)
            #slotWorker.startSlot()
            emmcWidget.workerInstance = slotWorker
            emmcWidget.workerCbReg()
            

            gpioExpander = Expander(Expander.PCA9535)
            gpioExpander.addr = expanderAddr[index]

            emmcWidget.gpioController = self.gpio
            emmcWidget.gpioExpander = gpioExpander
            emmcWidget.gpioInit()
            

            #Add slots to slots array
            self.emmcSlots.append(emmcWidget)
            self.add_widget(self.emmcSlots[index])
            print(f"Index: {index}, Device: {device}")
        
        self.gpio.startController()
        self.server, self.server_thread = start_server_in_thread(remCtrlPort, self.remCtrlCB, self)



        
        Clock.schedule_interval(lambda dt: self.update_time(), 1)

    def remCtrlCB(self, arg):
        #['', 'slot', '0', 'status']
        reguest = arg.lower().split("/")
        print("CB arg-", reguest )
        result, number = self.checkIfSlotCmd(reguest[0])
        if result:
            #slot command handler
            number -=1
            print("slot number-", number)
            if reguest[1]:
                if(reguest[1] == "status"):
                    resultBool, resultStr, progress = self.emmcSlots[number].getSlotStatus()
                    print(f"status: {resultBool}; {resultStr}; {progress}")
                    return f"{resultBool}; {resultStr}; {progress}"
                elif(reguest[1] == "run"):
                    self.emmcSlots[number].backgroundWorkerCmd("start")
                elif(reguest[1] == "stop"):
                    self.emmcSlots[number].backgroundWorkerCmd("stop")
                elif(reguest[1] == "crpi" or reguest[1] == "copi"):
                    if self.emmcSlots[number].emmcConnInitConnection(reguest[1]):
                        return "complete"
                    else:
                        return "error"
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

    def setColor(self, text, color):
        return f"[color={color}]{text}[/color]"

    def update_time(self):
        dateTime = datetime.now().strftime('%H:%M:%S')
        passedTotal = 0
        failedTotal = 0
        
        for emmcSlot in self.emmcSlots:
            passedTotal += emmcSlot.passed
            failedTotal += emmcSlot.failed
            emmcSlot.label_text = emmcSlot.getSlotStatus()[1]
            #print(emmcSlot.getJigStatus())
            #self.piShielCmd =not self.piShielCmd
            #emmcSlot.setPiShieldcommand(self.piShielCmd)
            #print(emmcSlot.getPiShieldStatus(), "; " , self.piShielCmd)
            

        yieldTotal = 100
        if ((passedTotal + failedTotal) != 0):
            yieldTotal = (passedTotal / (passedTotal + failedTotal))*100

        self.statusBar.timeLbl = f'[color=0066ff]{dateTime}[/color]'
        self.statusBar.runStatus = f"[color={Color.green}]Passed: {passedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={Color.red}]Failed: {failedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={Color.yellow}]Yield: {yieldTotal:.1f};[/color]"

        


class BoxApp(App):
    def build(self):
        self.screen = MainScreen()
        return self.screen
    
    def on_stop(self):
        self.screen.stop_server()


if __name__ == '__main__':
    BoxApp().run()
