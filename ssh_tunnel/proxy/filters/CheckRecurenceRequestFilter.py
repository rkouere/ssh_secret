from ssh_tunnel.proxy.filters import addToLog, Filter, access_log
from threading import Thread
from time import sleep
from copy import deepcopy
from math import sqrt
import logging

class CheckRecurenceRequestFilter(Filter):
    """
    Starts a new thread that will check all the connections
    Logs each connection with a timestamp

    """
    def __init__(self):
        LogsChecker(5).start()

    def drop(self, path, headers, body):
        addToLog(path)
        return False


class LogsChecker(Thread):
    """
    Takes a time interval in seconds
    Every n seconds copy the current log of connections and checks the
    standard deviation of each connection.
    If it is below a certain number and that the average is also below
    a certain number, adds the domain to the blacklist
    """
    def __init__(self, time_interval):
        ''' Constructor. '''
        Thread.__init__(self)
        self.time_interval = time_interval
        self.minimum_number_of_request = 0
        logging.debug("Thread started started")
        

    def run(self):
        """
        """
        while True:
            access_log_cp = deepcopy(access_log)
            for domain in access_log_cp:
                logging.debug("============== \nvalues for domain {}".format(domain))
                self.standard_deviation(access_log_cp[domain])
            sleep(self.time_interval)

    def standard_deviation(self, array):
        """
        Calculates, for each timestamp, the average and the standard deviation
        If the standard deviation is under x, it means that we have to deal
        with a robot
        and we blacklist it
        We need a minimum of request to test it as a single access to a site
        will give us a standard deviation of near 0


        Method to calculate the standard deviation
        To calculate the Variance, take each difference, square it, and
        then average the result:
        And the Standard Deviation is just the square root of Variance
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
