import struct
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import padding as sym_padding


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
    def __init__(self, protocol, chunk_size=1024):
        self.protocol = protocol
        self.chunk_size = chunk_size
        self.buffer = b""
        self.block_size = 128  # Block size for padding, in bits
        self.protocol = protocol
        self.chunk_size = chunk_size
        self.key_size = int(32 * 1.5)  # Estimated size of the encrypted AES key
        self.nonce_size = 12  # Size of nonce for AES-GCM
        self.timestamp_size = struct.calcsize("d")
        self.length_indicator_size = 2  # Size for the length indicator
        self.metadata_size = self.key_size + self.length_indicator_size
        self.public_key_bytes = b'''-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0ju9QF67nlJJSFnSKHK4\nDpDZajD7zMknKYDEft4euFPLVWQYa1XuIEhDBKmN4tLczl8tQac7enhw2kwvUr5t\n9EWSPa31PJ18hOXHrvVQIxCDm4vcJ+SCWuWvatjvot64TDTwyz9hoh09C2MnIwef\nmts+duCXdonqQdNCTStlqVW9ETtp4+fhNme+lNRs9mTE5lh7FAZPyFzJA/tHWjLF\nI0/t1BS8/MzFozMlFJKB0f0doZ0L8MMLnBufDnuT/08xBHqHQP+qUqPxwMdB9PNP\nUN8O6mRAV5iLWiWd6BYnrJmSazKuULuKXaqMrFWJic32iyjbuw9jFyS21z9lQLVf\nNwIDAQAB\n-----END PUBLIC KEY-----\n'''

    def _encrypt_with_aes_gcm(self, message):
        aes_key = AESGCM.generate_key(bit_length=128)
        aesgcm = AESGCM(aes_key)
        nonce = os.urandom(self.nonce_size)
        encrypted_message = aesgcm.encrypt(nonce, message, None)
        return nonce + encrypted_message, aes_key

    def _encrypt_aes_key(self, aes_key):
        public_key = serialization.load_pem_public_key(self.public_key_bytes, backend=default_backend())
        encrypted_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return encrypted_key

    def _adjust_and_encrypt_message(self, message):
        max_message_size = self.chunk_size - self.nonce_size - self.timestamp_size - self.metadata_size
        while True:
            padded_message = self._pad_message(message)
            encrypted_message, aes_key = self._encrypt_with_aes_gcm(padded_message)

            if len(encrypted_message) <= max_message_size:
                break

            # Reduce message size and retry
            message = message[:int(len(message) * 0.9)]

        return encrypted_message, aes_key, message

    def _pad_message(self, message):
        # Pad the message with the timestamp
        timestamp = struct.pack("d", time.time())

        padder = sym_padding.PKCS7(self.block_size).padder()
        padded_data = padder.update(message + b"\x00" * self.timestamp_size) + padder.finalize()

        finalized_data = padded_data[:-self.timestamp_size] + timestamp

        return finalized_data

    #def _pad_message(self, message):
    #    padder = sym_padding.PKCS7(self.block_size).padder()
    #    padded_data = padder.update(message) + padder.finalize()
    #    return padded_data

    def flush(self):
        encoded_blocks = []
        while len(self.buffer) > 0:
            # Get a chunk of the buffer up to the estimated max message size
            message_chunk_length = int((self.chunk_size - self.metadata_size - self.timestamp_size) * 0.75)
            message_chunk = self.buffer[:message_chunk_length]

            readied_chunk = message_chunk.ljust(message_chunk_length, b'\x00')

            encrypted_chunk, aes_key, message = self._adjust_and_encrypt_message(readied_chunk)
            encrypted_key = self._encrypt_aes_key(aes_key)
            self.buffer = self.buffer[len(message):]

            final_chunk = encrypted_chunk.ljust(self.chunk_size - len(encrypted_key) - self.length_indicator_size,
                                                b'\x00')
            final_chunk += encrypted_key
            final_chunk += struct.pack("H", len(encrypted_chunk))

            encoded_blocks.append(final_chunk)

        return encoded_blocks

    def add_message(self, message):
        message_bytes = message.encode() if isinstance(message, str) else message
        self.buffer += message_bytes + self.protocol.get_control_code("end").encode()

    def send_control_message(self, control_type):
        control_code = self.protocol.get_control_code(control_type).encode()
        self.buffer += control_code


# Example usage
encoder = MessageEncoder(ControlCodeProtocol())
encoder.add_message("Your message here")#()"HELLO WORLD I AM HEREEEEEEEEEEEEEEEEEEEEEEEEEE"* 100)
encoder.send_control_message("shutdown")
print(encoder.buffer, time.time())
chunks = encoder.flush()


class MessageDecoder:
    def __init__(self, private_key_pem, chunk_size=1024):
        self.chunk_size = chunk_size
        self.private_key = self._load_private_key(private_key_pem)

    def _load_private_key(self, pem_data):
        return serialization.load_pem_private_key(
            pem_data,
            password=None,  # Provide a password here if the key is encrypted
            backend=default_backend()
        )

    def decrypt_chunk(self, chunk):
        # Assuming the size of RSA encrypted data matches the RSA key size (e.g., 256 bytes for 2048-bit RSA)
        rsa_encrypted_data_size = 256  # Adjust this size based on your RSA key length

        # Extract the length of the encrypted message
        encrypted_message_length = struct.unpack("H", chunk[-2:])[0]

        # Calculate the starting position of the RSA encrypted AES key
        start_of_key = self.chunk_size - rsa_encrypted_data_size - 2

        # Extract the encrypted AES key
        encrypted_key = chunk[start_of_key:-2]
        encrypted_message = chunk[:encrypted_message_length]

        # Decrypt the AES key
        aes_key = self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Decrypt the message chunk
        aesgcm = AESGCM(aes_key)
        nonce = encrypted_message[:12]  # Assuming a 12-byte nonce for AES-GCM
        ciphertext = encrypted_message[12:]
        # Assuming the timestamp is at the end of the decrypted message
        timestamp_size = struct.calcsize("d")
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)

        # Extract the timestamp from the end of the decrypted data
        timestamp_bytes = decrypted_data[-timestamp_size:]
        decrypted_message = decrypted_data[:-timestamp_size]
        finalized_message = decrypted_message.rstrip(b"\x00")

        # Convert the timestamp back to a float
        timestamp = struct.unpack("d", timestamp_bytes)[0]

        return finalized_message, timestamp


private_key_bytes = b'-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDSO71AXrueUklI\nWdIocrgOkNlqMPvMyScpgMR+3h64U8tVZBhrVe4gSEMEqY3i0tzOXy1Bpzt6eHDa\nTC9Svm30RZI9rfU8nXyE5ceu9VAjEIObi9wn5IJa5a9q2O+i3rhMNPDLP2GiHT0L\nYycjB5+a2z524Jd2iepB00JNK2WpVb0RO2nj5+E2Z76U1Gz2ZMTmWHsUBk/IXMkD\n+0daMsUjT+3UFLz8zMWjMyUUkoHR/R2hnQvwwwucG58Oe5P/TzEEeodA/6pSo/HA\nx0H0809Q3w7qZEBXmItaJZ3oFiesmZJrMq5Qu4pdqoysVYmJzfaLKNu7D2MXJLbX\nP2VAtV83AgMBAAECggEAZXgm8lwm4xXlP/H2YMZp9sHL5hipV+CYscvwSymLGz16\nbQcIUDoj2ln2Wtg5XsqWf1bpwX/lUcmy8nIF/0JhUJ6JpJKDRJPgh0ZeeB/340yz\nsM4y3uBIWHX2kjQNiYdE3adJt1eqmHPTRF1BhQNHchcy0W66PCD5u3arUBLLmQwk\nUOq5GFS0Y/50lFQtSYyoS9Z8dHbv4U7PejGWuCuTDqU2XNcYwUyVQPF7/tlzFekm\nVp3IK0R+yvpJ59lfmcC3afiWZ1teiqMOeyzr95ac1VjJQ6C7Tw858ugz7b+ud8tg\nIj+wsq6oQ6fBPrqrIMUxz4EzXHzBfHNiKakALhIBNQKBgQDuyKHeEjEnRvZFyrq7\nUFWNOl2Nz3i9t4hPWN2HMEj7U8rA5HfHDwGn80YweF1S7dnrEMD0o4+8a4xjcZPA\nQzkxzbtMbcAzRNbg+EV6MP1Ts2bQasseQGZmrONTVWj5h+sSzOAN1U3dkmCcinaY\nIjKDY3qUjRcAAQAkEolwPYHm8wKBgQDhZCL264t6f82JEQ4vOZY1jzwiqb4+i8a4\n/VSXQjPdEARLmtAb4PRyj3QqPsKUeFN6wlMK4+cM+bQBWEXi+zTNZhFihdSI1KA3\nVVNJrWqnsWoXn5pOpCzQVy2v9fy7B6YHkSYBZjN9RsIs6Ib3j2H3nFgZRPZLkOS5\no8ILqi+/rQKBgG/uirovquzvfcgvhSMDQGdIgcxVAhNksjgHvyh9AOkXWUbcki00\noqEZD8Du20hhiLKBEwJanalEfPWsqwcIPApVl0P3eo5N6bBhkSf7SPTwdvSh6v8O\nTzI4PwO0WNYH2bDhavHxGGQSFsmquncMKMOgYTi7fpmY3nkKW3TK0FbzAoGBAM48\nMV4cs1iYnro/l+oQWGiTsqPJC+HxRhm4+/EXy5sIb9W6R5hq42H774BEQwlVfJVE\nQHYjiSQvS807N191GqCjN18eNBYr8JoRAg/VlVTyGrCZArnYsYTFcHGktOdyHTKp\nVsxK9uw3la8/6VeWpD7MmTQuDOuiHhfbRtAjnmNVAoGBAN5By5qm96LWwxfTAJWL\n7QYQ2jcB+lVDayTUqDU+Qk0CR1BhYXY5ICXCX5QhokwbjUwYzK7pE9nG7Si1ev1W\nDw+vfvSN2p1CwE+pgoAJy7/oc3LMUNU5nTgxua4PCOLhXVwDj/eEidKYdQZ4IX4R\nl20E9aXSkjlPd19n+/ZZoRuy\n-----END PRIVATE KEY-----\n'
decoder = MessageDecoder(private_key_bytes)
for chunk in chunks:
    print(chunk)
    decrypted_message, timestamp = decoder.decrypt_chunk(chunk)
    print(decrypted_message, timestamp)
