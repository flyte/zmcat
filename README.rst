.. image:: https://travis-ci.org/flyte/zmcat.svg?branch=develop
    :target: https://travis-ci.org/flyte/zmcat

ZMCat
=====

A simple command line tool to test ZMQ push/pull/pub/sub sockets. Based on https://github.com/lucasdicioccio/zmcat

Installation
============
::

    pip install zmcat

Examples
========
::

    zmcat pub tcp://*:5555
    zmcat sub tcp://localhost:5555

    zmcat pub tcp://*:5555 --key=mykey
    zmcat sub tcp://localhost:5555 --key=mykey

    zmcat push tcp://localhost:5555
    zmcat pull tcp://*:5555

