# SSH tunnel #

The aim of this project is to provide programs to allow two hosts,
with one behind a restricted internet access and a proxy, to
communicate together using SSH.

In other words, we build an SSH-over-HTTP tunnel.

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

## Specification ##

With a first implementation, we
