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
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from datetime import datetime, date, timedelta


import io , os, re, smbus # , i2c , psutil

from kivy.core.window import Window
from kivy.factory import Factory

globalMasterImage = "/home/vanya/master.img"
targetdDevices = ["SDC", "SDx","SDx","SDx"]
statusColor = {
    "pass": "00ff00",
    "fail": "ff0000",
    "terminated": "ffff00",
    "error": "0000ff",
    "pending": "00ffff"
}

Builder.load_file('kv/commansWidget.kv')

Window.size = (1920, 1080)
startYPos = 700             #Functional block


class DiscOperation(Screen):
    label_text = StringProperty("System idle")
    statusIcon = StringProperty("images/green_tick.png")
    progresBarVal = NumericProperty(0)
    targetDev = StringProperty("none")
    btnText = StringProperty("targetDev")
    btnText = targetDev
    masterImage = StringProperty("none")

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
        else:
            self.main_loop.statusIcon = "images/led_on_r.png"   
            self.main_loop.label_text = f"Process: [color={statusColor['fail']}]]FAILED[/color]"
        self.main_loop.ids.startBtn.disabled = False
        return True    
            



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


        self.add_widget(self.background_image)
        self.add_widget(self.discOp1)
        self.add_widget(self.discOp2)
        self.add_widget(self.discOp3)
        self.add_widget(self.discOp4)
        
        self.add_widget(self.clock)

        Clock.schedule_interval(lambda dt: self.update_time(), 1)
    
    def update_time(self):
        self.clock.text='[color=0066ff]'+datetime.now().strftime('%H:%M:%S')+'[/color]'



class BoxApp(App):
    def build(self):
        screen = MainScreen()
        return screen

if __name__ == '__main__':
    BoxApp().run()
