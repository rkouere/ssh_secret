import time
from threading import Thread
from ssh_tunnel.workside.workside import run as work_run
from ssh_tunnel.homeside.homeside import run as home_run


class AbstractProgram(Thread):
    def __init__(self, passphrase, runner, *args, **kwargs):
        self.passphrase = passphrase
        self.runner = runner
        super(*args, **kwargs)
        Thread.__init__(self)

    def run(self):
        self.runner(self.passphrase)


passphrase = "plop"
work_thread = AbstractProgram(passphrase, work_run)
home_thread = AbstractProgram(passphrase, home_run)

work_thread.start()
time.sleep(2)
home_thread.start()
