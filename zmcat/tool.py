from __future__ import print_function
import zmq
import argparse
from time import sleep

# Allow sockets to connect together before sending data
COURTESY_DELAY = 0.1


class ZMCat:

    def __init__(self, key="ZMCAT", input=raw_input, output=print):
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

    def push(self, uri):
        """
        Push input to a ZeroMQ PULL socket at uri.
        """
        socket = self._get_connected_socket(zmq.PUSH, uri)
        while True:
            socket.send_unicode(unicode(self.input()))

    def pull(self, uri):
        """
        Create a ZeroMQ PULL socket at uri and print its messages to output.
        """
        socket = self._get_bound_socket(zmq.PULL, uri)
        while True:
            self.output(socket.recv())


def main():
    zmcat = ZMCat()

    types = {
        "pub": zmcat.pub,
        "sub": zmcat.sub,
        "push": zmcat.push,
        "pull": zmcat.pull
    }

    p = argparse.ArgumentParser()
    p.add_argument("type", choices=types.keys())
    p.add_argument("uri")
    p.add_argument("--key", default="ZMCAT")
    args = p.parse_args()

    zmcat.key = args.key

    try:
        # Call the relevant function
        types[args.type](args.uri)
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()
