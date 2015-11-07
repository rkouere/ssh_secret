# SSH tunnel #

The aim of this project is to provide programs to allow two hosts,
with one behind a restricted internet access and a proxy, to
communicate together using SSH.

In other words, we build an SSH-over-HTTP tunnel.

## Dependencies ##

requests > 2.6.1 : to install on Ubuntu : 
    + install ``python3-pip``
    + pip3 install --upgrade requests

## Definitions ##

### Server side, work side ###

We call the server side, or work side, the endpoint which internet
access is limited behind a proxy.

This is the server we want to connect to

### Client side, home side ###

We call the client side, or home side, the endpoint with no internet
restrictions.

This is the host from which we connect to the server

## Overview ##

We write one program from each host.

On the work side, the program will periodically try to connect to the
home side. We will specify an url.

On the home side, the program consist of an http server with two endpoints ;

1. ``/up``, a ``POST`` URL used by the server to send data to the client
2. ``/down``, a ``POST`` URL used by the server to read data from the client

### Client specific ###

To be able to tunnel commands from an ssh client, the http server will
listen on an incoming port, which the ssh client will use to connect
to.

As soon as the ssh client started to send data to the http server (on
the internal port), the http server will start expose those data to the ``/down`` url

## Usage ##

### Server side ###

Ensure you have a running sshd server, listening on port 22. ``ssh localhost`` should return.

Run ``python3 -m ssh_tunnel.workside.workside <passphrase>``

### Client side ###

Run ``python3 -m ssh_tunnel.homeside.homeside <passphrase>``

This command run a thread with an ssh client, using the underlaying http server ``workside``

If everything success, you should be given a shell with the ssh client.

### Proxy ###

Run ``python3 -m ssh_tunnel.proxy.proxy`` to run a proxy which block SSH-over-HTTP

### Tests ###

Run ``python3 -m ssh_tunnel.test.test_global`` to run a test with both side communicating on a local server. You will get the result of a regular ``ssh localhost`` if everything succeed.

