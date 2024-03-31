import json
import threading
import socket
import queue
import sys
import re
from _security import ControlCodeProtocol, ServerMessageDecoder


shutdown_signal = queue.Queue()  # Used to signal the server to shutdown between threads


def parse_message_with_brackets(message):
    # Define a regular expression pattern to match text inside and outside brackets
    pattern = r'(\[[^\]]+\])|([^\[\]]+)'

    # Find all matches of the pattern in the message
    matches = re.findall(pattern, message)

    # Flatten the tuple results and filter out empty matches
    parsed_parts = [part for match in matches for part in match if part]

    return parsed_parts


def client_handler(connection, protocol: ControlCodeProtocol, decoder: ServerMessageDecoder):
    try:
        buffer = ""
        complete_buffer = ""  # Buffer to accumulate complete messages
        decoder.rate_limit = 1000

        while True:
            msgs = connection.recv(1024)
            if not msgs:
                break

            # Decrypt and validate the chunk
            decrypted_chunk = decoder.decrypt_and_validate_chunk(msgs).decode('utf-8')
            buffer += decrypted_chunk

            # Process complete and partial messages in buffer
            # Check for bracketed expressions using regular expression
            pattern = r'(\[[^\]]+\])|([^\[\]]+)'
            matches = re.findall(pattern, buffer)

            # Flatten the tuple results and filter out empty matches
            parsed_parts = [part for match in matches for part in match if part]
            completed_parts = []

            print(f"Buffer: {buffer}")
            if parsed_parts:
                last_end = 0
                for i, expression in enumerate(parsed_parts):
                    try:
                        validation_result = protocol.validate_control_code(expression)
                    except ValueError:
                        continue
                    if validation_result == "end":
                        # Consider message as complete
                        completed_parts.append(parsed_parts[last_end:i+1])
                        last_end = i
                    elif validation_result is "None":
                        # Malformed or invalid expression, add to buffer
                        complete_buffer += expression
                    elif validation_result == "shutdown":
                        shutdown_signal.put(True)
                        return
                    elif validation_result == "input":
                        inp = input()
                    else:
                        # There are no other expressions at the moment
                        pass

                len_to_remove = 0
                for completed_part in completed_parts:
                    message = ''.join(completed_part[:-1])
                    len_to_remove += len(message) + len(completed_part[-1])
                    complete_buffer += message
                buffer = buffer[len_to_remove:]

                print(f"Complete Message: {complete_buffer}")
            print(f"Remaining Buffer: {buffer}")
    finally:
        connection.close()


def run_client(host, port, protocol):
    decoder = ServerMessageDecoder()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((host, port))
        server.listen()
        print(f"Listening on {host}:{port}")

        while True:
            if not shutdown_signal.empty():
                print("Shutting down server...")
                break
            server.settimeout(1)  # Set timeout to check for shutdown signal
            try:
                connection, address = server.accept()
            except socket.timeout:
                continue  # Continue checking for shutdown signal
            print(f"Connected to {address}")

            # Send the public key bytes
            connection.sendall(decoder.public_key_bytes)#.encode('utf-8'))

            thread = threading.Thread(target=client_handler, args=(connection, protocol, decoder,)).start()


if __name__ == "__main__":
    HOST, PORT, PROTOCOL = sys.argv[1:]
    run_client(HOST, int(PORT), ControlCodeProtocol.deserialize(PROTOCOL))
