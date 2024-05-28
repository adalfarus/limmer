import json
import threading
import socket
import queue
import sys
import re
import time

from _security import ControlCodeProtocol, UndefinedSocket, SecureSocketServer
from ANSIUtils import enable_ansi
enable_ansi()


shutdown_signal = queue.Queue()  # Used to signal the server to shutdown between threads


def client_handler(connection, server: SecureSocketServer):
    try:
        server.rate_limit = 1000
        server.start_and_exchange_keys(False)
    finally:
        shutdown_signal.put(True)
        connection.close()


def run_client(host, port, protocol):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((host, port))
        server.listen()
        print(f"Listening on {host}:{port}")

        while True:
            try:
                if not shutdown_signal.empty():
                    print("Shutting down server...")
                    break
                server.settimeout(1)  # Set timeout to check for shutdown signal
                try:
                    connection, address = server.accept()
                    handler = SecureSocketServer(UndefinedSocket(connection), protocol)
                except socket.timeout:
                    continue  # Continue checking for shutdown signal
                print(f"Connected to {address}")

                thread = threading.Thread(target=client_handler, args=(connection, handler,))
                thread.start()
                thread.join()
            except Exception as e:
                print(e)
                input()


if __name__ == "__main__":
    HOST, PORT, PROTOCOL = sys.argv[1:]
    run_client(HOST, int(PORT), ControlCodeProtocol.deserialize(PROTOCOL))
