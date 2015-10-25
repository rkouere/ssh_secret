from threading import Thread
import logging


class SSLThread(Thread):
    def __init__(self, in_socket, out_socket, *args, **kwargs):
        self.in_socket = in_socket
        self.out_socket = out_socket
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        while True:
            try:
                self.in_socket.send(self.out_socket.recv(512))
            except (OSError, ConnectionResetError, BrokenPipeError):
                logging.info("Connection terminated")
                return
