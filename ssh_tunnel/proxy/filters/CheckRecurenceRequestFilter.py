from ssh_tunnel.proxy.filters import Filter
from threading import Thread, Lock
from time import sleep
from copy import deepcopy
from math import sqrt
import logging
import time
from urllib.parse import urlparse
from lib.colors import bcolors

black_domains = {}
white_domains = {}
access_log = {}
lock = Lock()


class CheckRecurenceRequestFilter(Filter):
    """
    Starts a new thread that will check all the connections
    Logs each connection with a timestamp

    """
    def __init__(self):
        LogsChecker(5).start()
        LogsCleaning().start()
        console().start()

    def drop(self, path, headers, body):
        """
        Checks that the path is not blacklisted
        If not, adds it to the logs
        """
        parsed_uri = urlparse(path)
        domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
        logging.info(black_domains)
        if domain not in black_domains:
            self.addToLog(domain)
            return (False, "")
        return (True, "Standard deviation too low : {} < 10".format(
            black_domains[domain]))

    def addToLog(self, domain):
        """
        We are only going to look at the domain url
        """
        lock.acquire()
        if domain in access_log:
            access_log[domain].append(time.time())
        else:
            access_log[domain] = [time.time()]
        lock.release()


def getUserMethodsFromClass(c):
    """
    Lists user's defined methods
    """
    methods = dir(c)
    user_methods = []
    for i in methods:
        if not i.startswith("__"):
            user_methods.append(i)
    return user_methods


class console(Thread):
    """
    Let's us interact with the system
    """
    def __init__(self):
        ''' Constructor. '''
        Thread.__init__(self)

    def run(self):
        while True:
            command = input('> ')
            self.__parse_arguments__(command)

    def c_display_help(self, arg=None):
        """[h] Prints this help message """
        if arg:
            logging.critical(
                bcolors.RED +
                "this command does not take arguments" +
                bcolors.ENDC)
        logging.critical(
            bcolors.BOLD +
            "The list of valid commands are :" + bcolors.ENDC)
        arguments = getUserMethodsFromClass(console)
        for i in arguments:
            if i.startswith("c_"):
                print(getattr(console, i).__doc__)

    def __parse_arguments__(self, arg):
        """
        Parses the commands
        """
        # list of valid commands
        command_one_arg = {
            "h": self.c_display_help,
            "lw": self.c_display_white_list,
            "lb": self.c_display_black_list,
            }
        command_multiple_arguments = {
            "ab": self.c_add_to_black_list,
            "aw": self.c_add_to_while_list,
            "rb": self.c_remove_from_black_list,
            "rw": self.c_remove_from_white_list,
        }
        # check if the command also has arguments
        arguments = arg.split(" ")
        if len(arguments) > 1:
            method = command_multiple_arguments.get(
                arguments[0], self.c_display_help)
            method(arguments[1:])
        else:
            method = command_one_arg.get(
                arguments[0], self.c_display_help)
            method()

    def c_display_white_list(self):
        """lw: Prints the white listed domains """
        logging.critical("{}".format(white_domains))

    def c_display_black_list(self):
        """lb: Prints the black listed domains """
        logging.critical("{}".format(black_domains))

    def c_add_to_while_list(self, domains):
        """aw [domains]: Adds domains to the white list"""
        lock.acquire()
        for i in domains:
            white_domains[i] = "Manual"
        lock.release()

    def c_add_to_black_list(self, domains):
        """ab [domains]: Adds domains to the black list"""
        lock.acquire()
        for i in domains:
            black_domains[i] = "Manual"
        lock.release()

    def c_remove_from_black_list(self, domains):
        """ab [domains]: remove domains from the black list"""
        lock.acquire()
        for i in domains:
            del black_domains[i]
        lock.release()

    def c_remove_from_white_list(self, domains):
        """rb [domains]: Remove domains from the white list"""
        lock.acquire()
        for i in domains:
            del white_domains[i]
        lock.release()


class LogsCleaning(Thread):
    """
    Will look at all the logs and remove the domains which have not been
    accessed for more than x minutes.
    """
    def __init__(self):
        Thread.__init__(self)
        # minimum time of inactivity between now and the latest access
        self.latest_access = 10*1000
        self.time_interval = 5*60  # time interval between checksminutes
        logging.debug("Thread LogsCleaning started")

    def run(self):
        """
        Checks that the latest access to the domain is under xxx
        If not, removes it from the list of logs
        """
        global access_log
        while 1:
            now = time.time()
            lock.acquire()
            access_log_copy = deepcopy(access_log)
            lock.release()
            for domain in access_log_copy:
                latest_tmp = 0  # stock the latest access to the domain
                for access in access_log_copy[domain]:
                    if access > latest_tmp:
                        latest_tmp = access
                    if latest_tmp < now - self.latest_access:
                        logging.info(
                            "domain {} has not been accessed for a long " +
                            "time. Removed from the logs".format(domain))
                        del access_log[domain]
            sleep(self.time_interval)


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
        self.minimum_number_of_request = 50
        self.deviation_minimum = 10

    def run(self):
        """
        Every x seconds, makes a copy of all the requests we had
        and calculate the standard deviation for each one
        """
        while True:
            access_log_cp = deepcopy(access_log)
            for domain in access_log_cp:
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
                black_domains[domain] = standard_deviation
