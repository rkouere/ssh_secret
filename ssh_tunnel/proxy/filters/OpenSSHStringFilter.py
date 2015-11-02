import binascii
import logging
from ssh_tunnel.proxy.filters import blacklist, Filter
import re


prog = re.compile(b'^SSH-[0-9]+(\.)?[0-9]?-(.*)')


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
        bodies = []
        # Construct a list of decoded bodies
        bodies.append(body)
        try:
            bodies.append(binascii.a2b_base64(body))
        except binascii.Error:
            logging.debug("not a base64")

        for target in bodies:
            if prog.match(target):
                logging.info("Openssh detected")
                return True
        return False
