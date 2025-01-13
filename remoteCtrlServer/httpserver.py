from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

class HTTPRequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, client_instance=None, clientCbFunction=None, **kwargs):
        self.client_instance = client_instance
        self.clientCbFunction = clientCbFunction
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
    
        file_path = os.path.join('remoteCtrlServer/html', self.path[1:])  # Remove leading '/' from path and prepend 'html/'
        print(file_path)
        if self.client_instance:
            if self.path.startswith('/cmd:'):
                command = self.path[len('/cmd:'):]
                result = self.clientCbFunction(command)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(result.encode('utf-8'))
            elif os.path.isfile(file_path):
                self.send_response(200)
                if file_path.endswith('.html'):
                    self.send_header('Content-type', 'text/html')
                elif file_path.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif file_path.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                elif file_path.endswith('.png'):
                    self.send_header('Content-type', 'image/png')
                elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                    self.send_header('Content-type', 'image/jpeg')
                else:
                    self.send_header('Content-type', 'application/octet-stream')
                self.end_headers()
                with open(file_path, 'rb') as file:
                    self.wfile.write(file.read())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write("File not found".encode('utf-8'))
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write("No client instance".encode('utf-8'))



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
    def __init__(self, port, cbFunction, main_screen_instance):
        self.port = port
        self.handler = HTTPRequestHandler
        self.server_instance = None
        self.main_screen_instance = main_screen_instance 
        self.clientCbFunction = cbFunction

    def start(self):
        server_address = ('', self.port)
        self.handler_instance = lambda *args, **kwargs: self.handler(*args, client_instance=self.main_screen_instance, clientCbFunction=self.clientCbFunction, **kwargs)
        httpd = HTTPServer(server_address, self.handler_instance)
        print(f"Serving on port {self.port}")
        self.server_instance = httpd 
        httpd.serve_forever()
    
    def shutdown(self):
        if self.server_instance:
            self.server_instance.shutdown()

def start_server_in_thread(port, cbFunction, main_screen_instance):
    server = RemoteController(port, cbFunction, main_screen_instance)
    thread = threading.Thread(target=server.start)
    thread.start()
    return server, thread