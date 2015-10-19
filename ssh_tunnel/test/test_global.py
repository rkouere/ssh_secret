import unittest
from ssh_tunnel.workside.workside import run as work_run
from ssh_tunnel.homeside.homeside import run as home_run

passphrase = "plop"
work_run(passphrase)
home_run(passphrase)
