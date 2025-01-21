from threading import Thread
import time



class SlotHandler(Thread):
    OPERATION_OK = 0
    OPERATION_ERR = 1
    OPERATION_PROC = 2
    
    CMD_EMPTY = 0
    IMAGE_WRITE = 101
    IMAGE_READ = 201

    def __init__(self, device=None, masterImgDir="/"):
        super().__init__()
        self._targetDevice = device
        self._imagePath = None
        self._cmd = None
        self._currentStatus = "idle"
        self._currentStatusBool = self.OPERATION_OK
        self._running = True
        self.daemon = True
        self.resultCb = None

    def startSlot(self):
        self._running = True
        self.start()
    
    def cbRegister(self, cbFn):
        self.resultCb = cbFn

    def targetSet(self, device):
        self._targetDevice = device

    def stopSLot(self):
        self._running = False

    def getSlotStatus(self):
        return self._currentStatusBool, self._currentStatus 

    def resultCbReturn(self, arg):
        if(self.resultCb != None):
            try:
                self.resultCb("OK")
            except:
                print("retunr CB error")

    def imageWrite(self, imagePath=None):
        self._imagePath = imagePath
        self._cmd = self.IMAGE_WRITE
       

    def _imageWriter(self):
        counter = 10
        while (counter!=0):
            print(f"Dummy write: {self._imagePath}; {counter};")
            self._currentStatus = f"data writting {self._targetDevice}, image: {self._imagePath}, {counter}"
            counter -=1
            time.sleep(1)
        return self.OPERATION_OK       
    
    def imageRead(self, imagePath=None):
        self._imagePath = imagePath
        self._cmd = self.IMAGE_READ
       

    def _imageReader(self):
        counter = 10
        while (counter!=0):
            print(f"Dummy write: {self._imagePath}; {counter};")
            self._currentStatus = f"data Reading {self._targetDevice}, image: {self._imagePath}, {counter}"
            counter -=1
            time.sleep(1)
        return self.OPERATION_OK     



    def run(self):
        while self._running:
            if(self._cmd == self.IMAGE_WRITE):
                self._currentStatus = f"data writting {self._targetDevice}, image: {self._imagePath}"
                self._currentStatusBool = self.OPERATION_PROC
                print(self._currentStatus)
                if(self._imageWriter() == self.OPERATION_OK):
                    self._currentStatus = "pass"
                    print(f"Comleted: {self._targetDevice}")
                    self.resultCbReturn("OK")
                else:
                    self._currentStatus = "fail"
                    print(f"Comleted: {self._targetDevice} wit ERROR")
                    self.resultCbReturn("OK")
                self._cmd = self.CMD_EMPTY
                self._currentStatusBool = self.OPERATION_OK

            time.sleep(0.1)

        self._running = False
        self._currentStatusBool = self.OPERATION_ERR    
