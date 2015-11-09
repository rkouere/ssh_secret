"""
Commons function used both by workside and homeside
"""

import hashlib
try:
    from Crypto.Cipher import AES
    from Crypto import Random
except ImportError:
    print("Please run ``pip3 install pycrypto``")
    import sys
    sys.exit(1)

SALT = b'31415916'
ITERATIONS = 30


class Cipherer():
    """Class to abstract symetric encryption between home and work
    """
    def __init__(self, passphrase):
        self.key = hashlib.pbkdf2_hmac('sha256', passphrase.encode(), SALT, ITERATIONS)

    def encrypt(self, data):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_EAX, iv)
        crypted = cipher.encrypt(data)
        tag = cipher.digest()
        msg = iv + crypted + tag
        print("Tag out : {}".format(str(tag)))
        return msg

    def decrypt(self, data):
        if not len(data):
            return b''
        iv = data[:16]
        msg = data[16:-16]
        tag = data[-16:]
        print("Tag in : {}".format(str(tag)))
        cipher = AES.new(self.key, AES.MODE_EAX, iv)
        cleartext = cipher.decrypt(msg)
        cipher.verify(tag)
        return cleartext
