from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

class HTTPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, client_instance=None, **kwargs):
        self.client_instance = client_instance
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        if self.client_instance:
            if self.path != '/favicon.ico':
                result = self.client_instance.remCtrlCB(self.path)
                self.wfile.write(result.encode('utf-8'))
            else:
                self.wfile.write("icon".encode('utf-8'))


    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        boundary = self.headers['Content-Type'].split("=")[1].encode()
        line = self.rfile.readline()
        content_length -= len(line)
        
        if boundary in line:
            line = self.rfile.readline()
            content_length -= len(line)
            filename = line.split(b'filename=')[1].split(b'"')[1].decode()

            # Skip headers
            while line.strip():
                line = self.rfile.readline()
                content_length -= len(line)

            # Save file
            with open(os.path.join('./uploads', filename), 'wb') as f:
                preline = self.rfile.readline()
                content_length -= len(preline)
                while content_length > 0:
                    line = self.rfile.readline()
                    content_length -= len(line)
                    if boundary in line:
                        preline = preline[:-1]  # Remove trailing \r\n
                        f.write(preline)
                        break
                    else:
                        f.write(preline)
                        preline = line
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'File uploaded successfully')

class RemoteController:
    def __init__(self, port, main_screen_instance):
        self.port = port
        self.handler = HTTPRequestHandler
        self.server_instance = None
        self.main_screen_instance = main_screen_instance 

    def start(self):
        server_address = ('', self.port)
        self.handler_instance = lambda *args, **kwargs: self.handler(*args, client_instance=self.main_screen_instance, **kwargs)
        httpd = HTTPServer(server_address, self.handler_instance)
        print(f"Serving on port {self.port}")
        self.server_instance = httpd 
        httpd.serve_forever()
    
    def shutdown(self):
        if self.server_instance:
            self.server_instance.shutdown()

def start_server_in_thread(port, main_screen_instance):
    server = RemoteController(port, main_screen_instance)
    thread = threading.Thread(target=server.start)
    thread.start()
    return server, thread