import time
import subprocess
import re
import os
import shlex
import pty
from threading import Thread

imagesRootDir = "/home/pi/images/"
imagesBuilderRootDir = "./imgBuilder/"

class ProcessStatus:
    runing = "running"
    stopped = "stopped"
    paused = "paused"
    pending = "pending"
    error = "error"
    criticalError = "criticalError"
    failed = "failed"
    passed = "passed"
    canceled = "canceled"
    completed = "completed"
    

class BackgroundWorker(Thread):
    def __init__(self):
        super(BackgroundWorker, self).__init__()
        self.currentState = ProcessStatus.pending
        self.daemon = True
        self._running = True
        self._frozen = False
        self._driveName = ""
        self.imageName = ""
        self._cmd = ""
        self._progressInfo = ProcessStatus.pending
        self.resultCb = None  
        self.resultsCounter = [0,0]
        self.progressPercent = 0
        self.overwriteRestriction = True

    
    def cbRegister(self, cbFn):
        if callable(cbFn):    
            self.resultCb = cbFn
        else:
            raise TypeError("cbFn must be a callable function")

    

    def startProc(self):
        """
        Запускає потік, якщо він ще не запущений.
        Перезапускає потік, якщо він був зупинений.
        """
        if not self.is_alive():
            self._running = True
            self.__init__()  
            self.start()
    
    def stopProc(self):
        """
        Зупиняє виконання потоку.
        """
        
        self._running = False

    def pauseProc(self):
        """
        Призупиняє виконання потоку.
        """
        self._running = False
    def passIncr(self):
        self.resultsCounter[1] += 1
        #self.resultCb(f"resCnt: {self.resultsCounter}")
    
    def failIncr(self):
        self.resultsCounter[0] += 1
        #self.resultCb(f"resCnt: {self.resultsCounter}")

    def getStatus(self):
        """
        Повертає поточний статус потоку.
        """
        return self.isFree(), self.currentState, self._progressInfo, self.resultsCounter, self.progressPercent
    
    def isFree(self) -> bool:
        if (self.currentState == ProcessStatus.pending or 
            self.currentState == ProcessStatus.paused or 
            self.currentState == ProcessStatus.passed or 
            self.currentState == ProcessStatus.completed or 
            self.currentState == ProcessStatus.error or 
            self.currentState == ProcessStatus.failed):
            return True
        else:    
            return False
    def setDrive(self, driveName) -> bool:
        """
        Встановлює ім'я диска для виконання в потоці.
        
        Parameters:
        driveName (str): Ім'я диска.
        """
        if(self.isFree()):
            self._driveName = self._devNameResolve(driveName)
            return True
        else:    
            return False
    def allowOverwrite(self, allow) -> bool:
        '''
        true - allow overwrite
        false - deny overwrite
        '''
        self.overwriteRestriction = allow
        return True
    
    def writeDev(self, targetDev, imageName) -> str:
        if not imageName.endswith('.img'):
            return "err: invalid image file extension"
        resolvedDev = self._devNameResolve(targetDev)
        if resolvedDev.startswith("err:"):
            return resolvedDev
        self._driveName = resolvedDev
        if not os.path.exists(f"{imagesRootDir}{imageName}"):
            return "err: image file not found"
        
        print(f"writeDev - {targetDev}; {resolvedDev}: {imageName}")
        if self.isFree():
            self.imageName = imageName
            self._cmd = "write"
            self._running = True
            return "ok: writeDev"
        else:
            return "err: Thread is busy" 
    

    def readDev(self, targetDev, imageName) -> str:
        if not imageName.endswith('.img'):
            return "err: invalid image file extension"
        if self.overwriteRestriction and os.path.exists(f"{imagesRootDir}{imageName}"):
            subprocess.run(['rm', f"{imagesRootDir}{imageName}"])   

        resolvedDev = self._devNameResolve(targetDev)
        if resolvedDev.startswith("err:"):
            return resolvedDev
        self._driveName = resolvedDev
        print(f"readDev - {targetDev}; {resolvedDev}: {imageName}")
        if self.isFree():
            self.imageName = imageName
            self._cmd = "read"
            self._running = True
            return "ok: readDev"
        else:
            return "err: Thread is busy" 
    
    def buildDevFs(self, targetDev, rootFSzip) -> str:
        resolvedDev = self._devNameResolve(targetDev)
        if resolvedDev.startswith("err:"):
            return resolvedDev
        self._driveName = resolvedDev
        
        rootFSzipFullPath = f"{imagesBuilderRootDir}imgParts/{rootFSzip}"

        if not os.path.exists(rootFSzipFullPath):
            return f"err: {rootFSzipFullPath} not exist"
            

        print(f"img builder - {targetDev}; {resolvedDev}: {rootFSzipFullPath}")
        return f"Ready to build {targetDev}; {rootFSzipFullPath}"




    def _devNameResolve(self, devName) -> str:
        dedvPath = subprocess.check_output(['readlink', '-f', f"/dev/{devName}"], text=True).strip()
        dedvPath = re.sub(r'\d+$', '', dedvPath)
        print(f"resolved: {devName} -> {dedvPath}")
        
        if os.path.exists(dedvPath):
            return dedvPath
        else:
            return f"err: device {devName} not found"


    def setCmd(self, cmd) -> bool:
        """
        Встановлює команду для виконання в потоці.
        
        Parameters:
        cmd (str): Команда для виконання.
        """
        #if(self.isFree()):
        self._cmd = cmd
        return True
        
        #else:    
        #    return False

    def _procPause(self):
        """
        Призупиняє виконання потоку.
        """
        self.tmpState = self.currentState
        self.currentState = ProcessStatus.paused
        while self._frozen:
            time.sleep(.1)
        self.currentState = self.tmpState


    def run(self):
        """
        Основний метод потоку. Виконує команду в циклі, поки _running встановлено в True.
        """
        print("Thread is STARTED")
        self.currentState = ProcessStatus.pending
        
        while self._running:
            if self._cmd == "read":
                self.progressPercent = 100
                self.cmd = f'dd if={self._driveName} of={imagesRootDir}{self.imageName} status=progress bs=256M count=4'
                print(self.cmd)
                master_fd, slave_fd = pty.openpty()
                process = subprocess.Popen(shlex.split(self.cmd), stdout=slave_fd, stderr=subprocess.STDOUT, close_fds=True)
                os.close(slave_fd)
                self.currentState = ProcessStatus.runing
                while True:
                    try:
                        output = os.read(master_fd, 256).decode()
                        if output:
                            print(re.sub(r'[^\x20-\x7E]', ',', output))
                            self._progressInfo = output.replace(';', '').replace('\n', ',').replace('\r', ',')
                            match = re.search(r'\((\d+) MB, (\d+) MiB\) copied, (\d+ s), (\d+\.\d+ MB/s)', output)
                            if match:
                                self.currentState = f"{match.group(1)}, {match.group(2)}; {match.group(3)}, {match.group(4)}"

                        if(self._cmd == "cancel"):
                            break   
                    except OSError:
                        pass
                    #break
                    self.retcode = process.poll()
                    if self.retcode is not None:
                        break
                    time.sleep(0.1)
                os.close(master_fd)
                process.wait()
                if(self.retcode == 0):
                    self.currentState = ProcessStatus.passed
                    self._progressInfo = ProcessStatus.completed
                    self.passIncr()
                    print("Operation PASSED")
                else:
                    self.currentState = ProcessStatus.failed
                    self._progressInfo = ProcessStatus.completed
                    self.failIncr()
                    print("Operation FAILED")
                self._cmd = ""
            
            
            #Write image to device
            elif self._cmd == "write":
                self.cmd = f'dd if={imagesRootDir}{self.imageName} of={self._driveName} status=progress bs=256M'
                self.imageSize = os.path.getsize(f"{imagesRootDir}{self.imageName}")
                print(self.cmd)
                master_fd, slave_fd = pty.openpty()
                process = subprocess.Popen(shlex.split(self.cmd), stdout=slave_fd, stderr=subprocess.STDOUT, close_fds=True)
                os.close(slave_fd)
                self.currentState = ProcessStatus.runing
                while True:
                    try:
                        output = os.read(master_fd, 256).decode()
                        if output:
                            print(re.sub(r'[^\x20-\x7E]', '', output))
                            match = re.search(r'\d+', output)
                            self._progressInfo = output.replace(';', ',').replace('\n', ',').replace('\r', ',')
                            if match:
                                bytesWrite = int(match.group())
                                self.progressPercent = int((bytesWrite / self.imageSize) * 100)
                            
                            match = re.search(r'\((\d+) MB, (\d+) MiB\) copied, (\d+ s), (\d+\.\d+ MB/s)', output)
                            if match:
                                self.currentState = f"{match.group(1)}, {match.group(2)}; {match.group(3)}, {match.group(4)}"
                        
                        if(self._cmd == "cancel"):
                            break   
                    except OSError:
                        pass
                    #break
                    self.retcode = process.poll()
                    if self.retcode is not None:
                        break
                    time.sleep(0.1)
                os.close(master_fd)
                process.wait()
                if(self.retcode == 0):
                    self.currentState = ProcessStatus.passed
                    self._progressInfo = ProcessStatus.completed
                    self.passIncr()
                    print("Operation PASSED")
                else:
                    self.currentState = ProcessStatus.failed
                    self._progressInfo = ProcessStatus.completed
                    self.failIncr()
                    print("Operation FAILED")
                self._cmd = ""
            
            
            #self._progressInfo = f"Running: {self.counter}"
            #self.resultCb(f"Thread is running cmd={self._cmd}; " 
            #              f"drive={self._driveName}; " 
            #              f"counter={self.counter}; " 
            #              f"currentState={self.currentState}; "
            #              f"progressInfo={self._progressInfo} "
            #              f"image={self.imageName}"
            #              )

            #self.currentState = ProcessStatus.completed
            #self._progressInfo = "Completed"
   
            time.sleep(1)
            #self._procPause()
        print("Thread is STOPED")
        self.currentState = ProcessStatus.stopped