from ssh_tunnel.proxy.filters import Filter
from threading import Thread, Lock
from time import sleep
from copy import deepcopy
from math import sqrt
import logging
import time
from urllib.parse import urlparse
from lib.colors import bcolors
import socket

black_domains = {}
white_domains = {}
access_log = {}
lock = Lock()

# 0 low
# 1 medium
# 2 high
warnings = {"low": {}, "medium": {}, "high": {}}

allowed_paranoia = ["paranoiac", "medium", "candid"]
current_paranoia = "paranoiac"


class CheckRecurenceRequestFilter(Filter):
    """
    Starts a new thread that will check all the connections
    Logs each connection with a timestamp

    """
    def __init__(self):
        LogsChecker(5).start()
        LogsCleaning().start()
        Console().start()

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


def add_to_list(lock, _list, domain, dev="Manual"):
    """
    Adds one domain to a list
    Takes a lock, the list, the name of the domain, the
    ip of the domain and the standard deviation
    """
    lock.acquire()
    _list[domain] = dev
    lock.release()


def remove_from_list(lock, _list, domain):
    """
    Remove one domain from a list
    Takes a lock, the list, the name of the domain
    """
    try:
        lock.acquire()
        del _list[domain]
        if domain in access_log:
            del access_log[domain]
        lock.release()
        return True
    except:
        return False


def get_ips_for_host(host):
    """ thanks i
        http://stackoverflow.com/
        questions/4815065/
        how-do-i-get-a-websites-ip-address-using-python-3-x
    """
    try:
        ips = socket.gethostbyname(host)
    except socket.gaierror:
        ips = "ip unknown"
    return ips


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


class Console(Thread):
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
        """h: prints this help message """
        if arg:
            logging.critical(
                bcolors.RED +
                "this command does not take arguments" +
                bcolors.ENDC)
        logging.critical("The list of valid commands are :")
        arguments = getUserMethodsFromClass(Console)
        for i in arguments:
            if i.startswith("c_"):
                print("\t" + getattr(Console, i).__doc__)

    def __parse_arguments__(self, arg):
        """
        Parses the commands
        """
        # list of valid commands
        command_one_arg = {
            "h": self.c_display_help,
            "lw": self.c_display_white_list,
            "lb": self.c_display_black_list,
            "lwa": self.c_display_warnings,
            "lal": self.c_display_access_log,
            "laal": self.c_display_standard_deviation_access_log,
            }
        command_multiple_arguments = {
            "ab": self.c_add_to_black_list,
            "aw": self.c_add_to_while_list,
            "rb": self.c_remove_from_black_list,
            "rw": self.c_remove_from_white_list,
            "lwa": self.c_display_warnings,
            "p": self.c_change_current_paranoia,
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

    def c_change_current_paranoia(self, level):
        """p [high|medium|low]: changes the level of paranoia """
        global current_paranoia
        global allowed_paranoia
        if level[0] in allowed_paranoia:
            lock.acquire()
            current_paranoia = level[0]
            lock.release()
            logging.critical("Paranoia level is {}".format(level))
        else:
            logging.critical(
                "{} is not a level allowed.".format(level) +
                "It sould be {}".format(allowed_paranoia))

    def c_display_white_list(self):
        """lw: prints the white listed domains """
        self.__log_warnings(white_domains)

    def c_display_black_list(self):
        """lb: prints the black listed domains """
        self.__log_warnings(black_domains)

    def c_display_access_log(self):
        """lal: prints the access log """
        self.__log_warnings(access_log)

    def c_display_standard_deviation_access_log(self):
        """laal: prints the average sd of each domain """
        for l in access_log:
            dev = standard_deviation(access_log[l], 0)
            ip = get_ips_for_host(l[7:-1])
            logging.critical("{} ({}) -- {}".format(l, ip, dev))

    def __log_warnings(self, warnings):
        """
        Displays the warning contained in w
        """
        for l in warnings:
            ip = get_ips_for_host(l[7:-1])
            logging.critical(
                "{} ({}) -- {}".format(l, ip, warnings[l]))

    def c_display_warnings(self, level="all"):
        """lwa [high|medium|low]: prints the warnings (default : all)"""
        if level == "all":
            for w in warnings:
                logging.critical("level {}".format(w))
                self.__log_warnings(warnings[w])

        else:
            lev = level[0]
            if lev == "high":
                self.__log_warnings(warnings[lev])
            if lev == "medium":
                self.__log_warnings(warnings[lev])
            if lev == "low":
                self.__log_warnings(warnings[lev])

    def c_add_to_while_list(self, domains):
        """aw [domains]: adds domains to the white list"""
        for i in domains:
            add_to_list(lock, white_domains, i)
            ip = get_ips_for_host(i)
            logging.critical("Added {} ({}) to the white list".format(i, ip))

    def c_add_to_black_list(self, domains):
        """ab [domains]: adds domains to the black list"""
        for i in domains:
            add_to_list(lock, black_domains, i)
            ip = get_ips_for_host(i)
            logging.critical("Added {} ({}) to the black list".format(i, ip))

    def c_remove_from_black_list(self, domains):
        """rb [domains]: remove domains from the black list
        and deletes all the data from this domain"""
        for i in domains:
            if remove_from_list(lock, black_domains, i):
                logging.critical(
                    "Removed {} from the black list and the access log"
                    .format(i))
            else:
                logging.critical(
                    "The domain {} if not blacklisted".format(i))

    def c_remove_from_white_list(self, domains):
        """rw [domains]: remove domains from the white list"""
        for i in domains:
            if remove_from_list(lock, white_domains, i):
                logging.critical(
                    "Removed {} from the white list and the access log"
                    .format(i))
            else:
                logging.critical(
                    "The domain {} if not whitelisted".format(i))


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
        self.deviation_alert_high = 10
        self.deviation_alert_medium = 30
        self.deviation_alert_low = 50

    def is_domain_in_warnings(self, domain):
        """
        Checks wether a domain is in one of the warning lists
        Returns True if a domain is in one of the list
        """
        for w in warnings:
            if domain in warnings[w]:
                return True
        return False

    def run(self):
        """
        Every x seconds, makes a copy of all the requests we had
        and calculate the standard deviation for each one
        """
        while True:
            access_log_cp = deepcopy(access_log)
            for domain in access_log_cp:
                if domain not in black_domains \
                        and not self.is_domain_in_warnings(domain):
                    dev = standard_deviation(
                        access_log_cp[domain],
                        self.minimum_number_of_request)
                    self.deal_with_dev(domain, dev)
            sleep(self.time_interval)

    def print_info(self, level, msg):
        if level == "high":
            color = bcolors.RED
        elif level == "medium":
            color = bcolors.WARNING
        elif level == "low":
            color = bcolors.OKBLUE
        logging.critical(color + "[" + level + "] " + bcolors.ENDC + msg)

    def deal_with_dev(self, domain, dev):
        """
        Logs a domain with a high level of access
        According to the level of paranoia around, chooses what to do
        Paranoid :
            - IP based URL/non www :
                -- dev < high alert level : add in warning high, alert user
                   and ban domain
                -- dev < medium aler level : add in warning medium, alert user
                   and ban domain
                -- dev < low alert level : add in low level warning
            - www based URL :
                -- add to low level warning
        Medium
            - IP based URL/non www :
                -- dev < high alert level : add in warning high, alert user and
                   ban domain
                -- dev < medium aler level : add in warning medium, alert user
                -- dev < low alert level : add in low level warning
            - www based URL :
                -- add to low level warning
       Low
            - IP based URL/non www :
                -- dev < high alert level : add in warning high, alert user
                -- dev < medium aler level : add in warning medium, alert user
                -- dev < low alert level : add in low level warning
            - www based URL :
                -- add to low level warning
        """
        # si on a pas de données concernant la dev, on stop
        if not dev:
            return False

        # We only log info www
        if domain.startswith("http://www"):
            warnings["low"][domain] = dev
            return False

        elif current_paranoia == "paranoiac":
            # a program is probably trying to access the web
            # as any good paranoiac knows, there MUST be something going on
            if dev < self.deviation_alert_high:
                self.print_info(
                    "high",
                    "added {} to the blacklist".format(domain))
                add_to_list(lock, black_domains, domain, dev)
            elif dev < self.deviation_alert_medium:
                self.print_info(
                    "high",
                    "added {} to the blacklist".format(domain))
                add_to_list(lock, black_domains, domain, dev)
            # if the deviation is low, we only log it
            elif dev < self.deviation_alert_low:
                self.print_info(
                    "low",
                    "the domain {} is acting funny. Val = {}"
                    .format(domain, dev))
                warnings["low"][domain] = dev

        elif current_paranoia == "medium":
            # we are still a bit on the effy side...
            # we block high alerts
            if dev < self.deviation_alert_high:
                self.print_info(
                    "high ",
                    "added {} to the blacklist".format(domain))
                add_to_list(lock, black_domains, domain, dev)
            # but only logg the other ones
            elif dev < self.deviation_alert_medium:
                self.print_info(
                    "medium",
                    "the domain {} is acting funny. Val = {}"
                    .format(domain, dev))
                warnings["medium"][domain] = dev
            elif dev < self.deviation_alert_low:
                warnings["low"][domain] = dev

        elif current_paranoia == "candid":
            # hippy style... people can only be nice on the web
            # we only logg informations but tell the user
            if dev < self.deviation_alert_high:
                self.print_info(
                    "high",
                    "the domain {} is acting funny. Val = {}"
                    .format(domain, dev))
                warnings["high"][domain] = dev
            elif dev < self.deviation_alert_medium:
                self.print_info(
                    "medium",
                    "the domain {} is acting funny. Val = {}"
                    .format(domain, dev))
                warnings["medium"][domain] = dev
            elif dev < self.deviation_alert_low:
                warnings["low"][domain] = dev

        return True


def standard_deviation(array, minimum_number_of_request):
    """
    Calculates, for each timestamp, the average and the standard deviation
    If the standard deviation is under x, it means that we have to deal
    with a robot and we add it to the blacklist
    We need a minimum of request to test it as a single access to a site
    will give us a standard deviation of near 0
    """
    array_len = len(array)
    if array_len > minimum_number_of_request:
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
        return standard_deviation
    else:
        return False
