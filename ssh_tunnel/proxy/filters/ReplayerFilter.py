import random
import requests
import logging
import time
from threading import Thread
from ssh_tunnel.proxy.filters import Filter


class ReplayerDelayer(Thread):
    def __init__(self, path, headers, data, *args, **kwargs):
        self.path = path
        self.headers = headers
        self.data = data
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        time.sleep(1)
        logging.info("Replaying {} for the lulz ({})".format(self.path, self))
        try:
            requests.post(self.path, headers=self.headers, data=self.data)
        except requests.exceptions.ConnectionError:
            pass
        return


class ReplayerFilter(Filter):
    """Technically not a filter ; randomly replay requests to mess with the servers"""
    def drop(self, path, headers, body):
        if random.randint(0, 100) > 70:
            # Delay the request in a new thread while we immediately return
            ReplayerDelayer(path, headers, body).start()
        # Always return False as the request should not been dropped
        return (False, None)
