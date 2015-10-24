import binascii
import logging
from ssh_tunnel.proxy.filters import blacklist, Filter


class OpenSSHStringFilter(Filter):
    """Finds the OpenSSH version exchange at the begining of the protocol"""
    def drop(self, path, headers, body):
        bodies = []
        # Construct a list of decoded bodies
        bodies.append(body)
        try:
            bodies.append(binascii.a2b_base64(body))
        except binascii.Error:
            logging.debug("not a base64")

        for target in bodies:
            if len(target) < 32 and b"OpenSSH" in target:
                logging.info("Openssh detected")
                blacklist(path)
                return True
        return False
