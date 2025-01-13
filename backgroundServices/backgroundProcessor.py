from threading import Thread
import time

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
        self._cmd = ""
        self._progressInfo = ""
        self.resultCb = None  

    
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
    def getStatus(self):
        """
        Повертає поточний статус потоку.
        """
        return self.isFree(), self.currentState, self._progressInfo
    
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
            self._driveName = driveName
            return True
        else:    
            return False

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
        self.counter = 0
        while self._running:
            if self._cmd == "start":
                self.currentState = ProcessStatus.runing
                self.counter = 10
                self._cmd = ""
            elif self._cmd == "stop":
                self.currentState = ProcessStatus.stopped   
                self.counter = 0
                self._cmd = ""

            
            
            self._progressInfo = f"Running: {self.counter}"
            self.resultCb(f"Thread is running cmd={self._cmd}; drive={self._progressInfo}; counter={self.counter}; currentState={self.currentState}")

            if self.counter != 0:
                self.counter -=1
            else:
                self.currentState = ProcessStatus.completed
                self._progressInfo = "Completed"
   
            time.sleep(1)
            #self._procPause()
        print("Thread is STOPED")
        self.currentState = ProcessStatus.stopped