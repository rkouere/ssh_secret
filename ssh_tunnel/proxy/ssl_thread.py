import socket
import logging
from threading import Thread
from time import sleep

RETRY_THRESHOLD = 10  # Number of retry before closing a timed-out request


class SSLThread(Thread):
    def __init__(self, in_socket, out_socket, *args, **kwargs):
        self.in_socket = in_socket
        self.out_socket = out_socket
        self.out_socket.settimeout(2)
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        retry_count = 0
        while True:
            try:
                data_in = self.out_socket.recv(512)
                retry_count = 0
            except socket.error as e:
                err = e.args[0]
                if err == 'timed out' and retry_count < RETRY_THRESHOLD:
                    sleep(1)
                    retry_count += 1
                    continue
                else:
                    logging.info("ssl timeout, closing ({})".format(self))
                    self.in_socket.close()
                    self.out_socket.close()
                    return
            except socket.error as e:
                return
            else:
                if len(data_in) == 0:
                    logging.info("Connection terminated")
                    self.in_socket.close()
                    self.out_socket.close()
                    return
                else:
                    try:
                        self.in_socket.send(data_in)
                    except OSError:
                        logging.info("Connection terminated")
                        self.in_socket.close()
                        self.out_socket.close()
                        return
