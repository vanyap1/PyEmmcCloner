import subprocess
import subprocess
import time
import shlex
import pty
import os, socket, re
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
from obsolete.remoteCtrl import start_server_in_thread
from kivy.uix.popup import Popup




#import io , re, smbus # , i2c , psutil

from kivy.core.window import Window
from kivy.factory import Factory

remCtrlPort = 8080
targetdDevices = ["SDF", "SDG","SDC","SDx","SDx", "SDW"]
Result = namedtuple('Result', ['passed', 'failed'])
masterImagePath = "../"


Window.size = (1024, 600)
startYPos = 188             #Functional block



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

    def setColor(self, text, color):
        return f"[color={color}]{text}[/color]"




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
        popup = ImageCreator(NewimageName = "master.img", sourceDevise="sdk")
        popup.open()
        
    
    


class DiskWriter(Screen):
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

    def setMasterImage(self, image):
        self.masterImage = image
        #self.statusBar.setLabel(image)


    def runProc(self):
        self.slotCurrentStatus = "awaiting"
        self.label_text = "Wait to finish process"
        #self.statusIcon = "images/led_on_y.png"
        self.ids.startBtn.disabled = True
        ImageWriter(self, self.targetDev, self.masterImage)
        


class ImageWriter(Thread):
    def __init__(self, main_loop_instance, devName, masterImage):
        self.main_loop = main_loop_instance
        self.devName = devName
        self.masterImage = masterImage
        #self.main_loop.progresBarVal
        
        Thread.__init__(self)
        self.daemon = True
        self.start()
    
    def run(self):
        imageSize = os.path.getsize(f"{masterImagePath}{self.masterImage}")
        cmd = f'dd if={masterImagePath}{self.masterImage} of=/dev/{self.devName.lower()} bs=4M status=progress' #count=125 
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(shlex.split(cmd), stdout=slave_fd, stderr=subprocess.STDOUT, close_fds=True)
        os.close(slave_fd)
        while True:
            try:
                output = os.read(master_fd, 1024).decode()
                if output:
                    print(output)
                    match = re.search(r'\d+', output)
                    if match:
                        bytesWrite = int(match.group())
                        self.main_loop.progresBarVal = int((bytesWrite / imageSize) * 100)                     
                    self.main_loop.label_text = f"[color={Color.pending}]{output}[/color]"
                    self.main_loop.slotCurrentStatus = f"progress:{output}"
            except OSError:
                break
        os.close(master_fd)
        process.wait()
        
        if process.returncode == 0:
            self.main_loop.label_text = f"Process: [color={Color.green}]PASSED[/color]"
            self.main_loop.passed += 1
            self.main_loop.slotCurrentStatus = "pass" 
        else:
            self.main_loop.label_text = f"Process: [color={Color.red}]FAILED[/color]"
            self.main_loop.failed += 1
            self.main_loop.slotCurrentStatus = "fail"

        if ((self.main_loop.failed + self.main_loop.passed) != 0):
            
            yieldVal = (self.main_loop.passed / (self.main_loop.failed + self.main_loop.passed))*100
        
        self.main_loop.ids.startBtn.disabled = False
        self.main_loop.slotStatusCounter = f"[color={Color.green}]Passed: {self.main_loop.passed}[/color]; [color={Color.red}]Failed: {self.main_loop.failed}[/color]; Yield: {yieldVal:.1f}%"
        
        return True    
            
class ImageReader(Thread):
    def __init__(self, parrentProcInstance, devName=None, newImageName=None):
        self.parrentProc = parrentProcInstance
        self.devName = devName
        self.newImageName = newImageName
        #self.main_loop.progresBarVal
        
        Thread.__init__(self)
        self.daemon = True
        self.start()
    
    def run(self):
        if(self.devName==None or self.newImageName==None):
            return False
        pass





class MainScreen(FloatLayout):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.masterImage = "master.img"
        self.background_image = Image(source='images/bg_d.jpg', size=self.size)
        self.add_widget(self.background_image)


        self.operations = []
        for index, device in enumerate(targetdDevices):
            yPos = startYPos
            xPoz = 3
            if(index!=0 and index << 4):
                yPos = startYPos - 60 * index
    
            if(index >= 4):
                yPos = startYPos - 60 * (index - 4)
                xPoz = 3 + 3 + 250


            discOp = DiskWriter(pos=(xPoz , yPos), size=(500, 100), size_hint=(None, None))
            discOp.targetDev = device
            discOp.masterImage = self.masterImage
            self.operations.append(discOp)
            self.add_widget(self.operations[index])

            print(f"Index: {index}, Device: {device}")


        self.statusBar = UpperStatusbar(pos=(3, 245), size=(1024-10, 100), size_hint=(None, None))
        self.statusBar.ctrlType = self.setColor("LOCAL" , Color.green)
        self.statusBar.masterImage = self.setColor(self.masterImage , Color.yellow)
        
        self.statusBar.ipAddr = self.setColor(f"{self.get_ip_addresses()}:{remCtrlPort}", Color.yellow)
       

        self.add_widget(self.statusBar)

        Clock.schedule_interval(lambda dt: self.update_time(), 1)

        self.server, self.server_thread = start_server_in_thread(remCtrlPort, self)

    
    def remCtrlCB(self, arg):
        #['', 'slot', '0', 'status']
        reguest = arg.lower().split("/")
        print("CB arg-", reguest )
        #return self.statusBar.runStatus
        if(reguest[1] == "slot"):
            if(reguest[3] == "status"):
                slotNum = int(reguest[2])
                if(slotNum > len(self.operations)-1):
                    return "slot not exist"
                return self.operations[slotNum].slotCurrentStatus
            elif(reguest[3] == "run"):
                slotNum = int(reguest[2])
                if(slotNum > len(self.operations)-1):
                    return "slot not exist"
                self.operations[slotNum].runProc()
                return "ok"  
            elif(reguest[3] == "name"):
                slotNum = int(reguest[2])
                if(reguest[4] == "clr"):
                    self.operations[slotNum].slotName = ""
                else:    
                    self.operations[slotNum].slotName = self.setColor(reguest[4].upper() , Color.green)
                return "ok" 
            else:
                return "wrong slot command"
        elif(reguest[1] == "config"):
            if(reguest[2] == "image"):
                if(os.path.isfile(f"{masterImagePath}{reguest[3]}")):
                    self.masterImage = reguest[3]
                    self.statusBar.masterImage = self.setColor(self.masterImage , Color.green)
                    for op in self.operations:
                        op.masterImage = self.masterImage
                    return "ok"    
                else:
                    return "err; this image does not exist"
            elif(reguest[2] == "image?"):      
                return self.masterImage
            
            elif(reguest[2] == "rem"): 
                if(reguest[3] == "true"):
                    self.statusBar.ctrlType = self.setColor("REMOTE" , Color.red)
                    for op in self.operations:
                        op.ids.startBtn.disabled = True
                elif(reguest[3] == "false"):
                    self.statusBar.ctrlType = self.setColor("LOCAL" , Color.green)
                    for op in self.operations:
                        op.ids.startBtn.disabled = False
                else:
                    return "wrong ctrl command"    
            return "ok"

        else:
            return "incorrect request"


    
    
    
    def setColor(self, text, color):
        return f"[color={color}]{text}[/color]"
        

    def get_ip_addresses(self):
        result = subprocess.run(['ip', 'addr'], stdout=subprocess.PIPE, text=True)
        ip_addresses = []
        for line in result.stdout.split('\n'):
            if 'inet ' in line and '127.0.0.1' not in line:
                ip_address = line.split()[1].split('/')[0]
                ip_addresses.append(ip_address)
        res = ', '.join(ip_addresses)
        return res


    def update_time(self):
        dateTime = datetime.now().strftime('%H:%M:%S')
        passedTotal = 0
        failedTotal = 0
        
        for operation in self.operations:
            passedTotal += operation.passed
            failedTotal += operation.failed

        yieldTotal = 100
        if ((passedTotal + failedTotal) != 0):
            yieldTotal = (passedTotal / (passedTotal + failedTotal))*100

        self.statusBar.timeLbl = f'[color=0066ff]{dateTime}[/color]'
        self.statusBar.runStatus = f"[color={Color.green}]Passed: {passedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={Color.red}]Failed: {failedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={Color.yellow}]Yield: {yieldTotal:.1f};[/color]"

    def stop_server(self):
        if self.server:
            self.server.shutdown()
            self.server_thread.join()


class BoxApp(App):
    def build(self):
        self.screen = MainScreen()
        return self.screen
    
    def on_stop(self):
        self.screen.stop_server()


if __name__ == '__main__':
    BoxApp().run()
