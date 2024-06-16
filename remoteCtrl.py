from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

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