import binascii
import logging
from ssh_tunnel.proxy.filters import addToLog, Filter


class CheckRecurenceRequestFilter(Filter):
    """
    Starts a new thread that will check all the connections
    Logs each connection with a timestamp

    """
    def drop(self, path, headers, body):
        addToLog(path)
        return False

def checkLogs():
    """
    Every n seconds copy the current log of connections and checks the standard deviation of each connection.
    If it is below a certain number and that the average is also below a certain number, adds the domain to the blacklist
    """
