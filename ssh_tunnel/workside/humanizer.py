"""This modules contains a thread that fakes human behaviour, in
order to flood the proxy with legitimate traffic"""

import requests
import random
import time
from threading import Thread
from ssh_tunnel.workside import USER_AGENT


class HumanizerThread(Thread):
    def __init__(self, homeside_url, *args, **kwargs):
        self.homeside_url = homeside_url
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            method = random.choice(['GET', 'POST'])
            uri = "{}/{}".format(self.homeside_url, random.getrandbits(128))
            try:
                requests.request(method, uri, headers={'User-Agent': USER_AGENT})
            except requests.exceptions.RequestException as e:
                print("requests failed to {} {}".format(method, uri))
                print(e)
            duration = random.randint(800, 1200)/1000
            print("Contacted {}, sleeping {}".format(uri, duration))
            time.sleep(duration)
