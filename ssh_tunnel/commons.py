import hashlib, binascii


SALT = b'31415916'
ITERATIONS = 30


class Cipherer():
    def __init__(self, passphrase):
        self.derived_key = hashlib.pbkdf2_hmac('sha256', passphrase.encode(), SALT, ITERATIONS)

    def encrypt(self, data):
        return binascii.b2a_base64(data)

    def decrypt(self, data):
        return binascii.a2b_base64(data)
