"""
Example Usage:

from i2c_gpio import I2CGPIOController, IO, DIR, Expander
import time

# Initialize the I2C bus
i2cBus = 0

# Define two expanders
expander1 = Expander(Expander.PF575)
expander2 = Expander(Expander.PCF8574)

# Define IO pins
switches = [
    IO(expander = expander1, portNum = 0, pinNum = 0, pinDir=DIR.OUTPUT),
    IO(expander = expander1, portNum = 0, pinNum = 1, pinDir=DIR.OUTPUT),
    IO(expander = expander1, portNum = 1, pinNum = 1, pinDir=DIR.OUTPUT),
    IO(expander = expander2, portNum = 0, pinNum = 2, pinDir=DIR.OUTPUT),
    IO(expander = expander2, portNum = 1, pinNum = 3, pinDir=DIR.OUTPUT)
]

if __name__ == '__main__':
    # Initialize the GPIO controller
    gpio = I2CGPIOController(i2cBus)

    # Add expanders to the controller
    gpio.addExpandersInfo(expander1)
    gpio.addExpandersInfo(expander2)

    # Set the direction for each pin
    for switch in switches:
        gpio.setPinDirection(switch, True)

    # Start the controller in a separate thread
    gpio.startController()
    
    # Toggle pins on/off in an infinite loop
    muxVal = True
    while(True):
        gpio.pinWrite(switches[0], muxVal)
        gpio.pinWrite(switches[1], muxVal)

        # Check the status of another pin
        if gpio.pinRead(switches[3]):
            print("MUX ON")
        else:
            print("MUX OFF")

        muxVal = not muxVal
        time.sleep(0.5)

        from smbus2 import SMBus, i2c_msg
        bus = SMBus(0)
        bus.write_i2c_block_data(0x12, 0x02,[1,2,3])
        bus.read_i2c_block_data(0x12, 0, 1)
"""

from threading import Thread
from smbus2 import SMBus, i2c_msg
import time

class Expander:
    """
    Class to define an I2C expander.
    Each expander can have different I2C addresses and different pin configurations.
    
    Attributes:
    PF575: Predefined configuration for PF575 expander (I2C address and type).
    PCF8574: Predefined configuration for PCF8574 expander (I2C address and type).
    """
    PF575 = [0x27, "PF575"]
    PCF8574 = [0xA0, "PCF8574"]
    PCA9535 = [0x27, "PCA9535"]

    def __init__(self, boardType):
        """
        Initialize the expander with its I2C address and type.
        
        Args:
        boardType (list): Contains the I2C address and the type of expander.
        """
        self.addr = boardType[0]
        self.type = boardType[1]
        self.outputBuff = [0, 0]  # Buffer for the output state
        self.inputBuff = [0, 0]   # Buffer for the input state
        self.ioDir = [0, 0]       # Buffer for direction configuration
class DIR:
    """
    Class representing the direction of a pin (input/output).
    """
    OUTPUT: int = 1
    INPUT: int = 0

class IO:
    """
    Class to define a specific input/output pin on an expander.
    
    Attributes:
    expander: Reference to the expander this pin belongs to.
    portNum: Port number on the expander (0 or 1).
    pinNum: Pin number within the port.
    pinDir: Pin direction, either INPUT or OUTPUT.
    """
    def __init__(self, expander: Expander, portNum: int, pinNum: int, pinDir: DIR):
        """
        Initialize the IO pin on a given expander.
        
        Args:
        expander (Expander): The expander to which the pin belongs.
        portNum (int): The port number (0 or 1).
        pinNum (int): The pin number within the port.
        pinDir (int): The direction of the pin (DIR.INPUT or DIR.OUTPUT).
        """
        self.expander = expander
        self.portNum = portNum
        self.pinNum = pinNum
        self.pinDir = pinDir



class I2CGPIOController(Thread):
    """
    Controller class to manage I2C communication with GPIO expanders.
    Inherits from threading.Thread to run asynchronously in the background.
    
    Attributes:
    expanders (list): A list of expander objects.
    bus (SMBus): I2C bus for communication.
    """
    def __init__(self, i2c_bus):
        """
        Initialize the GPIO controller for I2C communication.
        
        Args:
        i2c_bus (int): The I2C bus number.
        """
        super().__init__()
        self._running = True
        self.expanders: Expander = []
        self.bus = SMBus(i2c_bus)
        self.daemon = True  # Set thread as a daemon so it closes when the main program exits

    def startController(self):
        """
        Start the I2C GPIO controller thread.
        """
        self._running = True
        self.start()
    
    def stopController(self):
        """
        Stop the I2C GPIO controller thread.
        """
        self._running = False    

    def addExpandersInfo(self, newExpander: Expander) -> Expander:
        """
        Add a new expander to the controller.
        
        Args:
        newExpander (Expander): The expander to add.
        
        Returns:
        list: The updated list of expanders.
        """
        self.expanders.append(newExpander)
        return self.expanders

    def getExpandersInfo(self):
        """
        Retrieve the list of connected expanders.
        
        Returns:
        list: List of expander objects.
        """
        return self.expanders

    def setPinDirection(self, io: IO, pinState: bool):
        """
        Set the direction (input/output) of a pin.
        
        Args:
        io (IO): The IO object representing the pin.
        pinState (bool): The initial state of the pin.
        """
        self.pinWrite(io, not pinState)
        if io.pinDir not in (DIR.INPUT, DIR.OUTPUT):
            raise ValueError("Pin direction must be either DIR.INPUT or DIR.OUTPUT")
        if io.pinDir == DIR.INPUT:
            io.expander.ioDir[io.portNum] |= (1 << io.pinNum)
        else:
            io.expander.ioDir[io.portNum] &= ~(1 << io.pinNum)

    def pinWrite(self, io: IO, value: bool):
        """
        Write a value to a pin (either 0 or 1).
        
        Args:
        io (IO): The IO object representing the pin.
        value (bool): The value to write to the pin (True for HIGH, False for LOW).
        """
        if value not in (0, 1):
            raise ValueError("Unexpected output value must be either 0 or 1")
        if value == 1:
            io.expander.outputBuff[io.portNum] |= (1 << io.pinNum)
        else:
            io.expander.outputBuff[io.portNum] &= ~(1 << io.pinNum)

    def pinRead(self, io: IO):
        """
        Read the current state of a pin.
        
        Args:
        io (IO): The IO object representing the pin.
        
        Returns:
        int: The current logic level of the pin (1 or 0).
        """
        return not io.expander.inputBuff[io.portNum] & (1 << io.pinNum)

    def resetBoard(self):
        """
        Reset all expander registers (implementation is placeholder).
        """
        for hwExpander in self.expanders:
                if hwExpander.type == "PCA9535":
                    hwExpander.outputBuff = [255,255]

        
    def run(self):
        """
        Run the main loop for the I2C GPIO controller, managing communication with expanders.
        """
        for hwExpander in self.expanders:
            if hwExpander.type == "PCA9535":
                self.bus.write_i2c_block_data(hwExpander.addr, 0x06, hwExpander.ioDir)
                print(f"i2c DIR  {hwExpander.ioDir}")


        while self._running:
            for hwExpander in self.expanders:
                if hwExpander.type == "PF575":
                    try:
                        write = i2c_msg.write(hwExpander.addr, hwExpander.outputBuff)
                        self.bus.i2c_rdwr(write)
                    except:
                        print(f"i2c device {hwExpander.addr} error")
                elif hwExpander.type == "PCF8574":
                    # Not implemented yet
                    pass
                elif hwExpander.type == "PCA9535":
                    try:
                        hwExpander.inputBuff = self.bus.read_i2c_block_data(hwExpander.addr, 0, len(hwExpander.inputBuff))
                        self.bus.write_i2c_block_data(hwExpander.addr, 0x02, hwExpander.outputBuff)
                    except:
                        print(f"i2c device {hwExpander.addr} error")
                    #
                    # print(f"data {hwExpander.inputBuff}")
                    # Not implemented yet
                    pass
                else:
                    
                    print("Undefined board type")
            time.sleep(0.1)
