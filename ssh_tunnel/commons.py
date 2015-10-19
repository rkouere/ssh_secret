"""
Commons function used both by workside and homeside
"""

import hashlib, binascii
try:
    from Crypto.Cipher import AES
    from Crypto import Random
except ImportError:
    print("Please run ``pip3 install pycrypto``")
    import os
    os.exit(1)

SALT = b'31415916'
ITERATIONS = 30


class Cipherer():
    """Class to abstract symetric encryption between home and work
    """
    def __init__(self, passphrase):
        self.key = hashlib.pbkdf2_hmac('sha256', passphrase.encode(), SALT, ITERATIONS)

    def encrypt(self, data):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        msg = iv + cipher.encrypt(data)
        return msg

    def decrypt(self, data):
        iv = data[:16]
        msg = data[16:]
        cipher = AES.new(self.key, AES.MODE_CFB, iv)
        return cipher.decrypt(msg)
