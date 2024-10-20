from email.mime import image
import subprocess
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
from remoteCtrl import start_server_in_thread
from kivy.uix.popup import Popup
from kivy.config import Config

from kivy.core.window import Window
from kivy.factory import Factory





class MainScreen(FloatLayout):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.background_image = Image(source='images/bg_d.jpg', size=self.size)
        self.add_widget(self.background_image)

    





class BoxApp(App):
    def build(self):
        self.screen = MainScreen()
        return self.screen
    
    def on_stop(self):
        self.screen.stop_server()


if __name__ == '__main__':
    BoxApp().run()
