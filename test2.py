import random
import socket
import errno
import subprocess
import threading
import time
from limmer._security import ControlCodeProtocol, SecureSocketClient


# {comm_code::NEWLINE}  # Seperator for messages
class _CmdWindow:
    def __init__(self, forced_host: str = None, forced_port: int = None):
        self.protocol = ControlCodeProtocol()
        self.host = forced_host or "127.0.0.1"
        self.port = forced_port or self.find_available_port()

        # Starting the external process that uses SecureSocketServer
        self.process = subprocess.Popen(['py', './limmer/client.py', str(self.host), str(self.port),
                                         self.protocol.serialize()], creationflags=subprocess.CREATE_NEW_CONSOLE)
        # Initialize the SecureSocketClient
        self.client = SecureSocketClient(self.protocol, forced_host=self.host, forced_port=self.port)
        self.client.start_and_exchange_keys()

    @staticmethod
    def find_available_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # Bind to an available port provided by the OS
            return s.getsockname()[1]  # Return the allocated port

    def write(self, command):
        if command:
            self.client.add_message(command)
            self.client.sendall()

    def shutdown(self):
        # Tell the client to initiate a graceful shutdown
        self.client.add_control_code("shutdown")
        self.client.sendall()
        time.sleep(1)
        self.client.close_connection()


if __name__ == "__main__":
    window = _CmdWindow()
    window.write("HELL"*200)
    window.write("YEAH")
    # window.encoder.send_control_message("input")
    # window.shutdown()
    time.sleep(10)