import json
import threading
import socket
import queue
import sys
import signal
import time

from _security import ControlCodeProtocol, UndefinedSocket, SecureSocketServer
from ANSIUtils import enable_ansi
enable_ansi()


shutdown_signal = queue.Queue()  # Used to signal the server to shutdown between threads


def handle_shutdown(signum, frame):
    """Handle the shutdown signal by putting a shutdown request in the queue."""
    print("Received shutdown signal")
    shutdown_signal.put(True)


def client_handler(server: SecureSocketServer):
    try:
        server.rate_limit = 1000
        server.startup()

        while shutdown_signal.empty() and not server.is_shutdown():
            time.sleep(0.1)
        server.shutdown_client()
    finally:
        shutdown_signal.put(True)
        server.cleanup()


def run_server(host, port, protocol):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen()
        print(f"Listening on {host}:{port}")

        while True:
            try:
                if not shutdown_signal.empty():
                    print("Shutting down server...")
                    break
                server_socket.settimeout(1)  # Set timeout to check for shutdown signal
                try:
                    connection, address = server_socket.accept()
                    handler = SecureSocketServer(UndefinedSocket(connection), protocol)
                except socket.timeout:
                    continue  # Continue checking for shutdown signal
                print(f"Connected to {address}")

                thread = threading.Thread(target=client_handler, args=(handler,))
                thread.start()
                thread.join()
            except Exception as e:
                print(e)
                input()


if __name__ == "__main__":
    # Register the signal handler for SIGINT and SIGTERM
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    HOST, PORT, PROTOCOL = sys.argv[1:]
    run_server(HOST, int(PORT), ControlCodeProtocol.deserialize(PROTOCOL))
