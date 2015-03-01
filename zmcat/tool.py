import zmq
import argparse

def _get_socket(typ):
    """
    Create a ZeroMQ socket of type typ.
    """
    context = zmq.Context()
    socket = context.socket(typ)
    return socket


def _get_bound_socket(typ, uri):
    """
    Create a ZeroMQ socket of type typ and bind it to uri.
    """
    socket = _get_socket(typ)
    socket.bind(uri)
    return socket


def _get_connected_socket(typ, uri):
    """
    Create a ZeroMQ socket of type typ and connect it to uri.
    """
    socket = _get_socket(typ)
    socket.connect(uri)
    return socket


def pub(uri):
    """
    Publish stdin on a ZeroMQ socket bound to uri.
    """
    socket = _get_bound_socket(zmq.PUB, uri)
    while True:
        socket.send_unicode(unicode("%s%s" % (key, raw_input())))


def sub(uri):
    """
    Subscribe to a ZeroMQ PUB socket at uri and print its messages to stdout.
    """
    socket = _get_connected_socket(zmq.SUB, uri)
    socket.setsockopt_string(zmq.SUBSCRIBE, unicode(key))
    while True:
        print socket.recv()


def push(uri):
    """
    Push stdin to a ZeroMQ PULL socket at uri.
    """
    socket = _get_connected_socket(zmq.PUSH, uri)
    while True:
        socket.send_unicode(unicode(raw_input()))


def pull(uri):
    """
    Create a ZeroMQ PULL socket at uri and print its messages to stdout.
    """
    socket = _get_bound_socket(zmq.PULL, uri)
    while True:
        print socket.recv()


def main():
    types = {
        "pub": pub,
        "sub": sub,
        "push": push,
        "pull": pull
    }

    p = argparse.ArgumentParser()
    p.add_argument("type", choices=types.keys())
    p.add_argument("uri")
    p.add_argument("--key", default="ZMCAT")
    args = p.parse_args()

    # Set key globally
    key = args.key

    try:
        # Call the relevant function
        types[args.type](args.uri)
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    main()