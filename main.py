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


#import io , re, smbus # , i2c , psutil

from kivy.core.window import Window
from kivy.factory import Factory

globalMasterImage = "/home/vanya/master.img"
targetdDevices = ["SDC", "SDx","SDx","SDx"]
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
startYPos = 700             #Functional block

class UpperStatusbar(Screen):
    timeLbl = StringProperty("System idle")
    runStatus = StringProperty("")


class DiscOperation(Screen):
    label_text = StringProperty("System idle")
    statusIcon = StringProperty("images/green_tick.png")
    progresBarVal = NumericProperty(0)
    slotStatusCounter = StringProperty("Passed: 0; Failed: 0; Yield: 100%")
    targetDev = StringProperty("none")
    btnText = StringProperty("targetDev")
    btnText = targetDev
    masterImage = StringProperty("none")
    failed = NumericProperty(0)
    passed = NumericProperty(0)


    def runProc(self, targetDev, masterImage):
        self.label_text = "Wait to finish process"
        self.statusIcon = "images/led_on_y.png"
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
        cmd = f'dd if=/home/vanya/master.img of=/dev/{self.devName.lower()} bs=4M count=125 status=progress'
        master_fd, slave_fd = pty.openpty()
        process = subprocess.Popen(shlex.split(cmd), stdout=slave_fd, stderr=subprocess.STDOUT, close_fds=True)
        os.close(slave_fd)
        while True:
            try:
                output = os.read(master_fd, 1024).decode()
                if output:
                    print(output, end='')
                    self.main_loop.label_text = f"[color={statusColor['pending']}]{output}[/color]"
            except OSError:
                break
        os.close(master_fd)
        process.wait()
        
        if process.returncode == 0:
            self.main_loop.statusIcon = "images/green_tick.png"   
            self.main_loop.label_text = f"Process: [color={statusColor['pass']}]PASSED[/color]"
            self.main_loop.passed += 1 
        else:
            self.main_loop.statusIcon = "images/led_on_r.png"   
            self.main_loop.label_text = f"Process: [color={statusColor['fail']}]FAILED[/color]"
            self.main_loop.failed += 1
        if ((self.main_loop.failed + self.main_loop.passed) != 0):
            
            yieldVal = (self.main_loop.passed / (self.main_loop.failed + self.main_loop.passed))*100
        
        self.main_loop.ids.startBtn.disabled = False
        self.main_loop.slotStatusCounter = f"[color={statusColor['pass']}]Passed: {self.main_loop.passed}[/color]; [color={statusColor['fail']}]Failed: {self.main_loop.failed}[/color]; Yield: {yieldVal:.1f}%"
        #return True    
            



class MainScreen(FloatLayout):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.background_image = Image(source='images/bg.jpg', size=self.size)
        self.clock = Label(text='[color=0066ff]--:--:--[/color]', markup = True, font_size=100, pos=(-710, 450) , font_name='fonts/hemi_head_bd_it.ttf')
        
         
        self.discOp1 = DiscOperation(pos=(300 , startYPos), size=(1300, 200), size_hint=(None, None))
        self.discOp2 = DiscOperation(pos=(300 , startYPos - 230 * 1 ), size=(1300, 200), size_hint=(None, None))
        self.discOp3 = DiscOperation(pos=(300 , startYPos - 230 * 2 ), size=(1300, 200), size_hint=(None, None))
        self.discOp4 = DiscOperation(pos=(300 , startYPos - 230 * 3 ), size=(1300, 200), size_hint=(None, None))
        
        self.discOp1.targetDev = targetdDevices[0]
        self.discOp2.targetDev = targetdDevices[1]
        self.discOp3.targetDev = targetdDevices[2]
        self.discOp4.targetDev = targetdDevices[3]

        self.discOp1.masterImage = globalMasterImage
        self.discOp2.masterImage = globalMasterImage
        self.discOp3.masterImage = globalMasterImage
        self.discOp4.masterImage = globalMasterImage

        
        self.statusBar = UpperStatusbar(pos=(20, 450), size=(1920-80, 160), size_hint=(None, None))
        
        self.add_widget(self.background_image)
        self.add_widget(self.discOp1)
        self.add_widget(self.discOp2)
        self.add_widget(self.discOp3)
        self.add_widget(self.discOp4)
        
        #self.add_widget(self.clock)
        self.add_widget(self.statusBar)


        Clock.schedule_interval(lambda dt: self.update_time(), 1)
    
    def update_time(self):
        dateTime = datetime.now().strftime('%H:%M:%S')
        #self.clock.text='[color=0066ff]'+datetime.now().strftime('%H:%M:%S')+'[/color]'
        passedTotal = self.discOp1.passed+self.discOp2.passed+self.discOp3.passed+self.discOp4.passed
        failedTotal = self.discOp1.failed+self.discOp2.failed+self.discOp3.failed+self.discOp4.failed
        yieldTotal = 100
        if ((passedTotal + failedTotal) != 0):
            yieldTotal = (passedTotal / (passedTotal + failedTotal))*100
        

       
        self.statusBar.timeLbl = f'[color=0066ff]{dateTime}[/color]'
        self.statusBar.runStatus = f"[color={statusColor['pass']}]Passed: {passedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={statusColor['fail']}]Failed: {failedTotal};[/color]"
        self.statusBar.runStatus += f"\n[color={statusColor['yield']}]Yield: {yieldTotal:.1f};[/color]"



class BoxApp(App):
    def build(self):
        screen = MainScreen()
        return screen

if __name__ == '__main__':
    BoxApp().run()
