from __future__ import print_function

import argparse
from time import sleep

import sys
import zmq


if sys.version_info.major == 2:
    inputf = raw_input  # noqa: F821
else:
    inputf = input
    unicode = str


# Allow sockets to connect together before sending data
COURTESY_DELAY = 0.1


class ZMCat:

    def __init__(self, key="ZMCAT", input=None, output=print):
        input = input or inputf
        self.key = key
        self.input = input
        self.output = output

    def _get_socket(self, typ):
        """
        Create a ZeroMQ socket of type typ.
        """
        context = zmq.Context()
        socket = context.socket(typ)
        return socket

    def _get_bound_socket(self, typ, uri):
        """
        Create a ZeroMQ socket of type typ and bind it to uri.
        """
        socket = self._get_socket(typ)
        socket.bind(uri)
        sleep(COURTESY_DELAY)
        return socket

    def _get_connected_socket(self, typ, uri):
        """
        Create a ZeroMQ socket of type typ and connect it to uri.
        """
        socket = self._get_socket(typ)
        socket.connect(uri)
        sleep(COURTESY_DELAY)
        return socket

    def pub(self, uri):
        """
        Publish input on a ZeroMQ socket bound to uri.
        """
        socket = self._get_bound_socket(zmq.PUB, uri)
        while True:
            socket.send_unicode(unicode("%s%s" % (self.key, self.input())))

    def sub(self, uri):
        """
        Subscribe to ZeroMQ PUB socket at uri and print its msgs to output.
        """
        socket = self._get_connected_socket(zmq.SUB, uri)
        socket.setsockopt_string(zmq.SUBSCRIBE, unicode(self.key))
        while True:
            self.output(socket.recv())

    def push(self, uri, bind):
        """
        Push input to a ZeroMQ PULL socket at uri.
        """
        if bind:
            socket = self._get_bound_socket(zmq.PUSH, uri)
        else:
            socket = self._get_connected_socket(zmq.PUSH, uri)
        while True:
            socket.send_unicode(unicode(self.input()))

    def pull(self, uri, bind):
        """
        Create a ZeroMQ PULL socket at uri and print its messages to output.
        """
        if bind:
            socket = self._get_bound_socket(zmq.PULL, uri)
        else:
            socket = self._get_connected_socket(zmq.PULL, uri)
        while True:
            self.output(socket.recv())

    def req(self, uri):
        """
        Create a ZeroMQ REQuest on the uri. Wait for a reply and output it.
        """
        socket = self._get_connected_socket(zmq.REQ, uri)
        socket.connect(uri)
        socket.send_unicode(self.input())
        self.output(socket.recv())

    def rep(self, uri):
        """
        Create a ZeroMQ REPly socket and bind to the uri. Response is echo
        of REQuest.
        """
        socket = self._get_bound_socket(zmq.REP, uri)
        while True:
            req = socket.recv()
            socket.send(req)
            self.output(req)


def main():
    zmcat = ZMCat()

    types = {
        "pub": zmcat.pub,
        "sub": zmcat.sub,
        "push": zmcat.push,
        "pull": zmcat.pull,
        "req": zmcat.req,
        "rep": zmcat.rep
    }

    p = argparse.ArgumentParser()
    p.add_argument("type", choices=types.keys())
    p.add_argument("uri")
    p.add_argument("--key", default="ZMCAT")
    p.add_argument("--bind", default=False, action="store_true")
    args = p.parse_args()

    zmcat.key = args.key
    kwargs = {}
    if args.type in ("push", "pull"):
        kwargs["bind"] = args.bind

    try:
        # Call the relevant function
        types[args.type](args.uri, **kwargs)
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
