from ssh_tunnel.proxy.filters import Filter
from threading import Thread, Lock
from time import sleep
from copy import deepcopy
from math import sqrt
import logging
import time
from urllib.parse import urlparse

black_domains = []
access_log = {}


class CheckRecurenceRequestFilter(Filter):
    """
    Starts a new thread that will check all the connections
    Logs each connection with a timestamp

    """
    def __init__(self):
        self.lock = Lock()
        LogsChecker(5, self.lock).start()

    def drop(self, path, headers, body):
        """
        Checks that the path is not blacklisted
        If not, adds it to the logs
        """
        parsed_uri = urlparse(path)
        domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        if domain not in black_domains:
            self.addToLog(domain)
            return False
        return True

    def addToLog(self, domain):
        """
        We are only going to look at the domain url
        """
        logging.info("list of sites accessed = \n{}".format(access_log))
        self.lock.acquire()
        if domain in access_log:
            access_log[domain].append(time.time())
        else:
            access_log[domain] = [time.time()]
        self.lock.release()


class LogsCleaning(Thread):
    """
    Will look at all the logs and remove the domains which have not been
    accessed for more than x minutes
    """
    def _init_(self):
        Thread.__init__(self)
        self.occurence = 10*60

    def clean(self):
        print("toto")


class LogsChecker(Thread):
    """
    Takes a time interval in seconds
    Every n seconds copy the current log of connections and checks the
    standard deviation of each connection.
    If it is below a certain number and that the average is also below
    a certain number, adds the domain to the blacklist
    """
    def __init__(self, time_interval, lock):
        ''' Constructor. '''
        Thread.__init__(self)
        self.time_interval = time_interval
        self.minimum_number_of_request = 50
        self.deviation_minimum = 10
        self.lock = lock
        logging.debug("Thread started started")

    def run(self):
        """
        Every x seconds, makes a copy of all the requests we had
        and calculate the standard deviation for each one
        """
        while True:
            access_log_cp = deepcopy(access_log)
            for domain in access_log_cp:
                logging.debug(
                    "============== \nvalues for domain {}".format(domain))
                self.standard_deviation(access_log_cp[domain], domain)
            sleep(self.time_interval)

    def standard_deviation(self, array, domain):
        """
        Calculates, for each timestamp, the average and the standard deviation
        If the standard deviation is under x, it means that we have to deal
        with a robot and we add it to the blacklist
        We need a minimum of request to test it as a single access to a site
        will give us a standard deviation of near 0
        """
        array_len = len(array)
        if array_len > self.minimum_number_of_request:
            average = 0
            square_values = 0
            # get the average
            for i in array:
                average += i

            average = average/array_len

            for i in array:
                tmp = i - average
                square_values += pow(tmp, 2)

            variance = square_values/array_len
            standard_deviation = sqrt(variance)
            logging.debug("average = {}".format(average))
            logging.debug("standard deviation = {}".format(standard_deviation))
            if standard_deviation < self.deviation_minimum:
                black_domains.append(domain)
