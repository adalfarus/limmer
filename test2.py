import random
import socket
import errno
import subprocess
import threading
import time
from limmer._security import ControlCodeProtocol, ClientMessageEncoder


# {comm_code::NEWLINE}  # Seperator for messages
class _CmdWindow:
    def __init__(self, forced_host: str = None, forced_port: int = None):
        self.protocol = ControlCodeProtocol()
        self.host = forced_host or "127.0.0.1"

        self.port = None
        port = forced_port or self.find_available_port()
        while not self.port:
            self.port = self.test_port(port)
            port = self.find_available_port()

        self.process = subprocess.Popen(['py', './limmer/client.py', str(self.host), str(self.port),
                                         self.protocol.serialize()], creationflags=subprocess.CREATE_NEW_CONSOLE)
        self.connection = None
        self.connection_established = False
        threading.Thread(target=self.connect_to_server).start()

    @staticmethod
    def find_available_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # Bind to an available port provided by the OS
            return s.getsockname()[1]  # Return the allocated port

    @staticmethod
    def find_available_port_range(start_port, end_port):
        for port in range(start_port, end_port + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port  # Port is available
            except OSError as e:
                if e.errno == errno.EADDRINUSE:  # Port is already in use
                    continue
                raise  # Reraise unexpected errors
        raise RuntimeError("No available ports in the specified range")

    @staticmethod
    def test_port(port, retries=5, delay=1):
        while retries > 0:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    retries -= 1
                    time.sleep(delay)
                else:
                    raise
        raise RuntimeError("Port is still in use after several retries")

    def connect_to_server(self):
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")

            # Receive initial message from the server
            buffer_size = 1024
            initial_message = self.connection.recv(buffer_size)#.decode('utf-8')
            self.encoder = ClientMessageEncoder(initial_message, self.protocol)
            print(f"Received from server: {initial_message}")

        except ConnectionError as e:
            print(f"Connection error: {e}")
            return  # Add a return statement to prevent setting connection_established in case of error

        self.connection_established = True

    def write(self, command):
        if not command:
            return

        # Wait until the connection is established
        while not self.connection_established:
            time.sleep(0.1)  # Wait briefly and check again

        if hasattr(self, 'connection'):
            self.encoder.add_message(command)
            chunks = self.encoder.flush()
            for chunk in chunks:
                self.connection.send(chunk)

    def shutdown(self):
        if hasattr(self, 'connection') and self.connection:
            # Send a shutdown signal to the server
            self.encoder.send_control_message("shutdown")
            chunks = self.encoder.flush()
            for chunk in chunks:
                self.connection.send(chunk)
            # Close the connection
            self.connection.close()
            self.connection = None
        self.connection_established = False

    #def __del__(self):
    #    self.shutdown()


if __name__ == "__main__":
    window = _CmdWindow()
    window.write("HELL"*200)
    window.write("YEAH")
    window.encoder.send_control_message("input")
    window.shutdown()
    time.sleep(10)
