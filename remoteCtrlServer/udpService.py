import socket
import json
import threading

"""
Usage example:
self.udpClient = UdpAsyncClient(self)
self.udpClient.startListener(5005, self.serverUdpIncomingData)

def serverUdpIncomingData(self, data):
        print("UDP data-", data)
        pass
"""

class UdpAsyncClient:
    def __init__(self, mainLoopInstance, cbFn=None, port=5005, bufferSize=1024):
        self.mainLoop = mainLoopInstance
        self.parrentCb = cbFn 
        self.port = port
        self.bufferSize = bufferSize
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.listener_thread = None
        self.listening = False

    def startListener(self, port, cbFunction):
        """
        Запускає прослуховування UDP-портів в окремому потоці.
        
        Parameters:
        port (int): Порт для прослуховування.
        cbFunction (function): Функція зворотного виклику для обробки отриманих даних.
        """
        self.port = port
        self.parrentCb = cbFunction
        self.listening = True
        self.listener_thread = threading.Thread(target=self.run)
        self.listener_thread.daemon = True
        self.listener_thread.start()

    def run(self):
        self.sock.bind(('', self.port))
        while self.listening:
            try:
                data, _ = self.sock.recvfrom(self.bufferSize)
                message = data.decode('utf-8')
                
                try:
                    #json_data = json.loads(message)
                    self.parrentCb(message)
                except json.JSONDecodeError:
                    self.parrentCb("err") 
                
            except Exception:
                pass

    def stopListener(self):
        self.listening = False
        if self.listener_thread:
            self.listener_thread.join()

    def send_data(self, data, ip, port):
        """
        Відправляє дані через UDP сокет. Автоматично визначає тип даних (рядок або байти).

        Parameters:
        data (str or bytes): Дані для відправки.
        ip (str): IP-адреса отримувача.
        port (int): Порт отримувача.
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            self.sock.sendto(data, (ip, port))
        except Exception as e:
            print(f"Error sending data: {e}")