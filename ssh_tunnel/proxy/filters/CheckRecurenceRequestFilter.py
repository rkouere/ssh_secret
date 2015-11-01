import binascii
import logging
from ssh_tunnel.proxy.filters import addToLog, Filter, access_log
from threading import Thread
from time import sleep
from copy import deepcopy

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
    Every n seconds copy the current log of connections and checks the standard deviation of each connection.
    If it is below a certain number and that the average is also below a certain number, adds the domain to the blacklist
    """
    def __init__(self, time_interval):
        ''' Constructor. '''
 
        Thread.__init__(self)
        self.time_interval = time_interval
        
 
    def run(self):
        """
        
        """
        while True:
           access_log_cp = deepcopy(access_log)
           print("access_log = \n{}".format(access_log_cp))
           sleep(self.time_interval)
        
    def standard_deviation(self, array):
        """
        Pour calculer concrètement l'écart type à la main, le mieux est de prendre un exemple.
        Considérons la série {5; 7; 9; 10}
        On calcule d'abord la moyenne : m = (5 + 7 + 9 + 10)/4 = 31/4 = 7,75
        On calcule ensuite la moyenne des carrés M = (25 + 49 + 81 + 100)/4 = 255/4 = 63,75
        On calcule ensuite la variance V = M - m² = 63,75 - 7,75² = 3,6875
        Enfin l'écart type est la racine carrée de V, soit environ 1,92
        """
        moyenne = 0
        moyenne_des_carre = 0
        for i in array:
            moyenne += i
            moyenne_des_carre += i*i
