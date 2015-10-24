import random
import requests
import logging
from ssh_tunnel.proxy.filters import Filter


class ReplayerFilter(Filter):
    """Technically not a filter ; randomly replay requests to mess with the servers"""
    def drop(self, path, headers, body):
        if random.getrandbits(2) > 3:
            logging.info("replaying request for the lulz")
            try:
                requests.post(path, headers=headers, data=body)
            except requests.exceptions.ConnectionError:
                pass
        # Always return False as the request should not been dropped
        return False
