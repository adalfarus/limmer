from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from aplustools.io.environment import strict
import json
import os
import base64
import time
import struct
import datetime


@strict
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


# @strict  # Strict decorator makes any private attributes truly private
class ServerMessageDecoder:
    def __init__(self, chunk_size=1024, private_key_bytes_overwrite=None):
        # Generate RSA key pair
        self._private_key = self._load_private_key(private_key_bytes_overwrite) if private_key_bytes_overwrite else (
            rsa.generate_private_key(public_exponent=65537, key_size=2048))
        self._public_key = self._private_key.public_key()

        # Serialize public key to send to clients
        self.public_key_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)
        self._last_timestamp = datetime.datetime.now()
        self.rate_limit = 1  # Allow 1 message per second

        self._last_sequence_number = -1
        self.time_window = datetime.timedelta(minutes=5)  # Time window for valid timestamps
        self._chunk_size = chunk_size

    def _load_private_key(self, pem_data):
        return serialization.load_pem_private_key(
            pem_data,
            password=None,  # Provide a password here if the key is encrypted
            backend=default_backend()
        )

    def _decrypt_aes_key(self, encrypted_key):
        return self._private_key.decrypt(
            encrypted_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))

    @staticmethod
    def _decrypt_message_aes_gcm(encrypted_message, key):
        iv, ciphertext, tag = encrypted_message[:12], encrypted_message[12:-16], encrypted_message[-16:]
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()

    def _check_rate_limit(self):
        current_time = datetime.datetime.now()
        if (current_time - self._last_timestamp).total_seconds() > self.rate_limit:
            return False
        self._last_timestamp = current_time
        return True

    def _decrypt_message(self, encrypted_message, encrypted_aes_key):
        # Check rate limiting
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded")

        aes_key = self._decrypt_aes_key(encrypted_aes_key)
        return self._decrypt_message_aes_gcm(encrypted_message, aes_key)

    def _parse_message(self, plainbytes):
        # Assuming the timestamp is at the end of the decrypted message
        timestamp_size = struct.calcsize("d")

        # Extract the timestamp from the end of the decrypted data
        timestamp_bytes = plainbytes[-timestamp_size:]
        decrypted_message = plainbytes[:-timestamp_size]
        finalized_message = decrypted_message.rstrip(b"\x00")

        # Convert the timestamp back to a float
        timestamp = struct.unpack("d", timestamp_bytes)[0]
        return timestamp, self._last_sequence_number+1, finalized_message,

    def _validate_timestamp(self, timestamp):
        current_time = datetime.datetime.now(datetime.timezone.utc)
        timestamp_datetime = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

        if current_time - timestamp_datetime > self.time_window or timestamp_datetime > current_time:
            return False
        return True

    def _validate_sequence_number(self, sequence_number):
        if sequence_number <= self._last_sequence_number:
            return False
        self.last_sequence_number = sequence_number
        return True

    def _unpack_chunk(self, chunk):
        # Decrypt message
        rsa_encrypted_data_size = 256

        # Extract the length of the encrypted message
        encrypted_message_length = struct.unpack("H", chunk[-2:])[0]

        # Calculate the starting position of the RSA encrypted AES key
        start_of_key = self._chunk_size - rsa_encrypted_data_size - 2

        # Extract the encrypted AES key
        encrypted_key = chunk[start_of_key:-2]
        encrypted_message = chunk[:encrypted_message_length]
        return encrypted_key, encrypted_message

    def decrypt_and_validate_chunk(self, chunk):
        encrypted_key, encrypted_message = self._unpack_chunk(chunk)

        plainbytes = self._decrypt_message(encrypted_message, encrypted_key)

        # Extract timestamp and sequence number from the plaintext
        timestamp, sequence_number, actual_message = self._parse_message(plainbytes)

        # Validate timestamp and sequence number
        if not self._validate_timestamp(timestamp) or not self._validate_sequence_number(sequence_number):
            raise Exception("Invalid message: timestamp or sequence number is not valid.")

        return actual_message


@strict
class ClientMessageEncoder:
    def __init__(self, public_key_bytes, protocol, chunk_size=1024):
        self.public_key = serialization.load_pem_public_key(public_key_bytes, backend=default_backend())
        self._protocol = protocol
        self._chunk_size = chunk_size
        self._buffer = b""
        self._block_size = 128  # Block size for padding, in bits
        self._key_size = int(32 * 1.5)  # Estimated size of the encrypted AES key
        self._nonce_size = 12  # Size of nonce for AES-GCM
        self._timestamp_size = struct.calcsize("d")
        self._length_indicator_size = 2  # Size for the length indicator
        self._metadata_size = self._key_size + self._length_indicator_size

    def _encrypt_aes_key(self, aes_key):
        # Encrypt AES Key with server's public RSA key
        return self.public_key.encrypt(
            aes_key, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))

    def _encrypt_with_aes_gcm(self, message):
        aes_key = AESGCM.generate_key(bit_length=128)
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(self._nonce_size)
        encrypted_message = aesgcm.encrypt(nonce, message, None)
        return nonce + encrypted_message, aes_key

    def _pad_message(self, message):
        # Pad the message with the timestamp
        timestamp = struct.pack("d", time.time())

        padder = sym_padding.PKCS7(self._block_size).padder()
        padded_data = padder.update(message + b"\x00" * self._timestamp_size) + padder.finalize()

        finalized_data = padded_data[:-self._timestamp_size] + timestamp

        return finalized_data

    def _adjust_and_encrypt_message(self, message):
        max_message_size = self._chunk_size - self._nonce_size - self._timestamp_size - self._metadata_size
        while True:
            padded_message = self._pad_message(message)
            encrypted_message, aes_key = self._encrypt_with_aes_gcm(padded_message)

            if len(encrypted_message) <= max_message_size:
                break

            # Reduce message size and retry
            message = message[:int(len(message) * 0.9)]

        return encrypted_message, aes_key, message

    def flush(self):
        encoded_blocks = []
        while len(self._buffer) > 0:
            # Get a chunk of the buffer up to the estimated max message size
            message_chunk_length = int((self._chunk_size - self._metadata_size - self._timestamp_size) * 0.75)
            message_chunk = self._buffer[:message_chunk_length]

            readied_chunk = message_chunk.ljust(message_chunk_length, b'\x00')

            encrypted_chunk, aes_key, message = self._adjust_and_encrypt_message(readied_chunk)
            encrypted_key = self._encrypt_aes_key(aes_key)
            self._buffer = self._buffer[len(message):]

            final_chunk = encrypted_chunk.ljust(self._chunk_size - len(encrypted_key) - self._length_indicator_size,
                                                b'\x00')
            final_chunk += encrypted_key
            final_chunk += struct.pack("H", len(encrypted_chunk))

            encoded_blocks.append(final_chunk)

        return encoded_blocks

    def add_message(self, message):
        message_bytes = message.encode() if isinstance(message, str) else message
        self._buffer += message_bytes + self._protocol.get_control_code("end").encode()

    def send_control_message(self, control_type):
        control_code = self._protocol.get_control_code(control_type).encode()
        self._buffer += control_code


if __name__ == "__main__":
    decoder = ServerMessageDecoder()
    encoder = ClientMessageEncoder(decoder.public_key_bytes, ControlCodeProtocol())
    encoder.add_message("Hello World")
    encoder.send_control_message("shutdown")
    chunks = encoder.flush()
    for chunk in chunks:
        print(decoder.decrypt_and_validate_chunk(chunk))


class ServerStream:
    pass


class ClientStream:
    pass
