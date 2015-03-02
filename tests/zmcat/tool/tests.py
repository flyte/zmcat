import logging
import os
import socket
import zmq
import mock
from time import sleep
from unittest import TestCase
from zmcat import ZMCat

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class GetOutOfLoopException(Exception):
    pass


def port_open(port):
    """
    Check to see if a port is open by connecting a vanilla socket to it.
    """
    log.debug("Creating vanilla socket")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    log.debug("Connecting vanilla socket to port %d" % port)
    result = sock.connect_ex(("127.0.0.1", port))

    log.debug("Result (0 connected, >0 did not): %d" % result)
    sock.close()
    return result == 0


def get_random_bound_zmq_socket(typ):
    """
    Find a high port not in use and bind to it.
    """
    zmcat = ZMCat()
    zmq_sock = None
    port = 49152
    while not zmq_sock and port <= 65536:
        try:
            zmq_sock = zmcat._get_bound_socket(
                typ, "tcp://127.0.0.1:%d" % port)
            log.debug("Socket bound to port %d" % port)
        except zmq.ZMQError as e:
            if e.errno == zmq.EADDRINUSE:
                port += 1
            else:
                zmq_sock.close()
                raise
    return zmq_sock, port


class ZMCatToolTestCase(TestCase):

    def test_get_socket(self):
        """
        _get_socket() should provide a ZeroMQ socket of the desired type.
        """
        zmcat = ZMCat()
        for typ in (zmq.PUSH, zmq.PULL, zmq.PUB, zmq.SUB):
            socket = zmcat._get_socket(typ)
            self.assertEqual(
                socket.TYPE, typ, "Socket type should be what we asked for")

    def test_get_bound_socket(self):
        """
        _get_bound_socket() should provide a ZeroMQ socket bound to interface.
        """
        zmq_sock, port = get_random_bound_zmq_socket(zmq.PUB)
        self.assertTrue(zmq_sock, "Socket must be able to bind to a port")

        try:
            self.assertTrue(
                port_open(port),
                "Port should be open and accepting conections")
        finally:
            zmq_sock.close()

    def test_get_connected_socket(self):
        """
        _get_connected_socket() should provide a connected ZeroMQ socket.
        """
        zmcat = ZMCat()
        uri = "ipc:///tmp/test-get-connected-socket"
        bound_sock = zmcat._get_bound_socket(zmq.PUB, uri)
        connected_sock = zmcat._get_connected_socket(zmq.SUB, uri)

        msg = u"Remember, Sully, when I promised to kill you last? I lied."
        prefix = u"ARNIE"
        msg = u"%s%s" % (prefix, msg)
        try:
            connected_sock.setsockopt_string(zmq.SUBSCRIBE, prefix)
            sleep(0.1)
            bound_sock.send_unicode(msg)
            sleep(0.1)
            self.assertEqual(
                connected_sock.recv(zmq.NOBLOCK),
                msg)
        finally:
            bound_sock.close()
            connected_sock.close()

    def test_pub(self):
        """
        pub() should set up a PUB socket and send stdin through it.
        """
        prefix = u"ARNIE"
        zmcat = ZMCat(key=prefix)
        uri = "ipc:///tmp/test-pub"
        sub_sock = zmcat._get_connected_socket(zmq.SUB, uri)
        sub_sock.setsockopt_string(zmq.SUBSCRIBE, prefix)
        msg = u"Who is your daddy and what does he do?"

        # Mock raw_input to return without standard input
        with mock.patch("__builtin__.raw_input", side_effect=[msg]):
            zmcat.input = raw_input
            try:
                zmcat.pub(uri)
            except StopIteration:
                pass

        sleep(0.1)
        self.assertEqual(sub_sock.recv(zmq.NOBLOCK), u"%s%s" % (prefix, msg))

    def test_sub(self):
        """
        sub() should set up a SUB socket and send its messages to output.
        """
        output_file = "/tmp/test-sub.output"

        def save_and_raise(msg):
            """
            Save the msg to a file and raise an exception to get out of the
            while True loop in sub().
            """
            print msg
            with open(output_file, "w") as f:
                f.write(msg)
            raise GetOutOfLoopException()

        zmcat = ZMCat(output=save_and_raise)
        uri = "ipc:///tmp/test-sub"
        msg = u"Stop whining!"

        try:
            # Mock the reception of a packet from ZMQ
            with mock.patch("zmq.sugar.socket.Socket.recv", return_value=msg):
                try:
                    zmcat.sub(uri)
                except GetOutOfLoopException:
                    pass
            with open(output_file) as f:
                self.assertEqual(f.read(), msg)
        finally:
            try:
                os.unlink(output_file)
            except OSError:
                pass  # Oh well
