import json
import time
import base64
import os
import struct


class ControlCodeProtocol:
    def __init__(self, comm_code: str = None, exec_code_delimiter: str = "::", exec_code_start: str = "[",
                 exec_code_end: str = "]", control_codes: dict = None):
        self._comm_code = comm_code
        if not self._comm_code:
            self._comm_code = self._generate_random_string(50)
        self._exec_code_delimiter = exec_code_delimiter
        self._exec_code_start = exec_code_start
        self._exec_code_end = exec_code_end
        self._control_codes = control_codes if control_codes is not None else {
            "end": "NEWLINE", "shutdown": "SHUTDOWN 0xC000013A", "input": "IN"
        }

    @staticmethod
    def _generate_random_string(length):
        # Calculate how many bytes are needed to get the desired string length after Base64 encoding
        bytes_length = (length * 3) // 4
        random_bytes = os.urandom(bytes_length)

        # Encode these bytes into a Base64 string
        random_string_base64 = base64.urlsafe_b64encode(random_bytes).decode('utf-8')

        # Return the required length
        return random_string_base64[:length]

    def get_control_code(self, control_code):
        return (f"{self._exec_code_start}"
                f"{self._comm_code}{self._exec_code_delimiter}{self._control_codes.get(control_code.lower())}"
                f"{self._exec_code_end}")

    def validate_control_code(self, exec_code: str) -> str:
        if exec_code.startswith(self._exec_code_start) and exec_code.endswith(self._exec_code_end):
            # Remove the start and end markers
            plain_code = exec_code[len(self._exec_code_start):-len(self._exec_code_end)]

            shipped_code = plain_code[:len(self._comm_code)]
            if shipped_code == self._comm_code:
                control_code = plain_code[len(self._comm_code)+2:]
                for key, value in self._control_codes.items():
                    if control_code == value:
                        return key
                return "Invalid control code"
            return "Invalid key"
        else:
            # Raise an error if the string does not have the required start and end markers
            raise ValueError("String does not start and end with required markers")

    def serialize(self):
        return json.dumps({
            "comm_code": self._comm_code,
            "exec_delimiter": self._exec_code_delimiter,
            "exc_code_start": self._exec_code_start,
            "exc_code_end": self._exec_code_end,
            "status_codes": self._control_codes
        })

    @staticmethod
    def deserialize(serialized_data):
        data = json.loads(serialized_data)
        return ControlCodeProtocol(data["comm_code"], data["exec_delimiter"], data["exc_code_start"], data["exc_code_end"], data["status_codes"])


class MessageEncoder:
    def __init__(self, protocol: ControlCodeProtocol, chunk_size=1024):
        self.protocol = protocol
        self.chunk_size = chunk_size
        self.buffer = b""  # Byte string for the buffer
        self.timestamp_size = struct.calcsize("d")  # Timestamp size

    def add_message(self, message):
        # Convert message to bytes and add to buffer
        message_bytes = message.encode() if isinstance(message, str) else message
        self.buffer += message_bytes + self.protocol.get_control_code("end").encode()

    def send_control_message(self, control_type):
        # Add the control message to the buffer
        control_code = self.protocol.get_control_code(control_type).encode()
        self.buffer += control_code

    def flush(self):
        encoded_blocks = []
        while len(self.buffer) > 0:
            available_size = self.chunk_size - self.timestamp_size
            chunk = self.buffer[:available_size]
            self.buffer = self.buffer[len(chunk):]

            # Pad the chunk if necessary
            padded_chunk = chunk.ljust(available_size, b'\x00')

            # Add timestamp at the end of the chunk
            timestamp = struct.pack("d", time.time())
            encoded_blocks.append(padded_chunk + timestamp)

        return encoded_blocks


class MessageDecoder:
    def __init__(self, protocol, chunk_size=1024):
        self.protocol = protocol
        self.chunk_size = 1024
        self.buffer = b""
        self.messages = []

    def add_chunk(self, chunk):
        # Append chunk to the buffer
        self.buffer += chunk

        # Process buffer if it has enough data
        while len(self.buffer) >= self.chunk_size:
            self._process_chunk()

    def _process_chunk(self):
        # Extract a single chunk
        chunk, self.buffer = self.buffer[:self.chunk_size], self.buffer[self.chunk_size:]

        # Extract timestamp from the end of the chunk
        timestamp_bytes = chunk[-struct.calcsize("d"):]
        timestamp = struct.unpack("d", timestamp_bytes)[0]

        # Remove timestamp and padding
        message_part = chunk[:-struct.calcsize("d")].rstrip(b'\x00')

        # Check for control messages
        for code, signal in self.protocol._control_codes.items():
            control_code = self.protocol.get_control_code(code).encode()
            if control_code in message_part:
                message, message_part = message_part.split(control_code)
                self.messages.append((message.decode(), timestamp))
                break
        else:
            # Accumulate message parts
            self.messages.append((message_part.decode(), timestamp))

    def get_messages(self):
        return self.messages


# Example usage
protocol = ControlCodeProtocol()
encoder = MessageEncoder(protocol)

# Adding a regular message
encoder.add_message("Hello World")

# Flushing the buffer (processes and clears the buffer)
decoder = MessageDecoder(protocol)

# Sending a control message (e.g., shutdown)
encoder.send_control_message("shutdown")
encoded_blocks = encoder.flush()
for block in encoded_blocks:
    print(block)  # Binary data
    decoder.add_chunk(block)
print(decoder.get_messages())
