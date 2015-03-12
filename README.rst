.. image:: https://travis-ci.org/flyte/zmcat.svg?branch=develop
    :target: https://travis-ci.org/flyte/zmcat

ZMCat
=====

A simple command line tool to test ZMQ push/pull/pub/sub sockets. Based on https://github.com/lucasdicioccio/zmcat

Installation
============
::

    pip install zmcat

Usage
=====
::

    zmcat <socket_type> <uri> [--bind] [--key]

socket_type
***********
The type of ZMQ socket you require (pub, sub, push, pull).

uri
***
The URI to bind/connect to. For example, tcp://127.0.0.1:5555 or ipc:///tmp/mysocket

--bind
******
Bind to an interface instead of connecting to an existing socket. Relevant only for socket_type push and pull.

--key
*****
The key to use for a pub/sub socket.


Examples
========
::

    zmcat pub tcp://*:5555
    zmcat sub tcp://localhost:5555

    zmcat pub tcp://*:5555 --key=mykey
    zmcat sub tcp://localhost:5555 --key=mykey

    zmcat push tcp://localhost:5555
    zmcat pull tcp://*:5555 --bind

    zmcat push tcp://*:5555 --bind
    zmcat pull tcp://localhost:5555