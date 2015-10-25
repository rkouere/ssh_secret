import binascii
import logging
from ssh_tunnel.proxy.filters import blacklist, Filter
import re


class OpenSSHStringFilter(Filter):
    """
    Finds the OpenSSH version exchange at the begining of the protocol
    Info : according to the ssh rfc4253:
    "When the connection has been established, both sides MUST send an
    identification string.  This identification string MUST be
             SSH-protoversion-softwareversion
    Let's regex this...
    """
    def drop(self, path, headers, body):
        prog = re.compile('^SSH-[0-9]+(\.)?[0-9]?-(.*?) ')
        bodies = []
        # Construct a list of decoded bodies
        bodies.append(body)
        try:
            bodies.append(binascii.a2b_base64(body))
        except binascii.Error:
            logging.debug("not a base64")

        for target in bodies:
            print("length targer = " + str(len(target)))
            if prog.match(target.decode()):
                logging.info("Openssh detected")
                blacklist(path)
                return True
        return False
