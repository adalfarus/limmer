import subprocess
from aplustools.security.protocols import ControlCodeProtocol, SecureSocketClient
from aplustools.utils import PortUtils
from limmer.styles import Color


# {comm_code::NEWLINE}  # Seperator for messages
class _CmdWindow:
    def __init__(self, forced_host: str = None, forced_port: int = None):
        self.protocol = ControlCodeProtocol()
        self.host = forced_host or "127.0.0.1"
        self.port = forced_port or PortUtils.find_available_port()

        # Starting the external process that uses SecureSocketServer
        self.process = subprocess.Popen(['py', './limmer/_server.py', str(self.host), str(self.port),
                                         self.protocol.serialize()], creationflags=subprocess.CREATE_NEW_CONSOLE)
        # Initialize the SecureSocketClient
        self.client = SecureSocketClient(self.protocol, forced_host=self.host, forced_port=self.port)
        self.client.startup()

    def write(self, *command):
        self.client.add_message(''.join(str(command_part) for command_part in command))
        self.client.sendall()
        print("CMD", *command)

    def shutdown(self):
        print("SHUTTING DOWN")
        # Tell the client to initiate a graceful shutdown
        if not self.client.is_shutdown():
            self.client.add_control_code("shutdown")
            self.client.sendall()
            self.client.close_connection()

    def input(self, string: str = ""):
        self.client.add_control_code("input", string)
        self.client.sendall()

        while True:
            input_str = self.client.get_input_buffer()

            if input_str != "" or self.client.is_shutdown():
                break

        return input_str


if __name__ == "__main__":
    window = _CmdWindow()
    window.write("HELL"*200)
    window.write("YEAH")
    inputs = window.input("Input: ")
    print("INPUTTED", inputs)

    window.write(Color.GREEN, "Grass")
    window.input()

    window.shutdown()
