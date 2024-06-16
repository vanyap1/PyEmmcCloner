import subprocess
import subprocess
import time
import shlex
import pty
import os
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
from remoteCtrl import start_server_in_thread



#import io , re, smbus # , i2c , psutil

from kivy.core.window import Window
from kivy.factory import Factory

globalMasterImage = "/home/vanya/master.img"
targetdDevices = ["SDC", "SDx","SDx","SDx","SDx", "SDW"]
Result = namedtuple('Result', ['passed', 'failed'])


statusColor = {
    "pass": "00ff00",
    "fail": "ff0000",
    "yield": "ffbf00",
    "terminated": "ffff00",
    "error": "0000ff",
    "pending": "00ffff"
}

Builder.load_file('kv/commandsWidget.kv')
Builder.load_file('kv/statusbar.kv')



Window.size = (1024, 600)
startYPos = 188             #Functional block

class UpperStatusbar(Screen):
    timeLbl = StringProperty("System idle")
    runStatus = StringProperty("")


class DiscOperation(Screen):
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

        Thread.__init__(self)
        self.daemon = True
        self.start()
    
    def run(self):
        cmd = f'dd if=/home/vanya/master.img of=/dev/{self.devName.lower()} bs=4M status=progress' #count=125 
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(shlex.split(cmd), stdout=slave_fd, stderr=subprocess.STDOUT, close_fds=True)
        os.close(slave_fd)
        while True:
            try:
                output = os.read(master_fd, 1024).decode()
                if output:
                    print(output, end='')
                    self.main_loop.label_text = f"[color={statusColor['pending']}]{output}[/color]"
                    self.main_loop.slotCurrentStatus = f"progress:{output}"
            except OSError:
                break
        os.close(master_fd)
        process.wait()
        
        if process.returncode == 0:
            self.main_loop.label_text = f"Process: [color={statusColor['pass']}]PASSED[/color]"
            self.main_loop.passed += 1
            self.main_loop.slotCurrentStatus = "pass" 
        else:
            self.main_loop.label_text = f"Process: [color={statusColor['fail']}]FAILED[/color]"
            self.main_loop.failed += 1
            self.main_loop.slotCurrentStatus = "fail"

        if ((self.main_loop.failed + self.main_loop.passed) != 0):
            
            yieldVal = (self.main_loop.passed / (self.main_loop.failed + self.main_loop.passed))*100
        
        self.main_loop.ids.startBtn.disabled = False
        self.main_loop.slotStatusCounter = f"[color={statusColor['pass']}]Passed: {self.main_loop.passed}[/color]; [color={statusColor['fail']}]Failed: {self.main_loop.failed}[/color]; Yield: {yieldVal:.1f}%"
        
        return True    
            



class MainScreen(FloatLayout):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
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


            discOp = DiscOperation(pos=(xPoz , yPos), size=(500, 100), size_hint=(None, None))
            discOp.targetDev = device
            discOp.masterImage = globalMasterImage
            self.operations.append(discOp)
            self.add_widget(self.operations[index])

            print(f"Index: {index}, Device: {device}")


        self.statusBar = UpperStatusbar(pos=(3, 245), size=(1024-10, 100), size_hint=(None, None))
        
        self.add_widget(self.statusBar)

        Clock.schedule_interval(lambda dt: self.update_time(), 1)

        self.server, self.server_thread = start_server_in_thread(8080, self)

    
    def remCtrlCB(self, arg):
        #['', 'slot', '0', 'status']
        reguest = arg.split("/")
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

            else:
                return "incorrect slot command"
        elif(reguest[1] == "config"):
            return "ok"

        else:
            return "incorrect request"


        




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
        self.statusBar.runStatus = f"[color={statusColor['pass']}]Passed: {passedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={statusColor['fail']}]Failed: {failedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={statusColor['yield']}]Yield: {yieldTotal:.1f};[/color]"

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
