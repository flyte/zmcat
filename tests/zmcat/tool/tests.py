import logging
import os
import socket
import mock
from time import sleep
from unittest import TestCase

import zmq

from zmcat import ZMCat, tool


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

TYPES = ("pub", "sub", "push", "pull")


class GetOutOfLoopException(Exception):
    pass


class FakeArgs:
    type = None
    key = "ZMCAT"
    uri = "ipc:///dev/null"
    bind = False


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
    while not zmq_sock:
        if port >= 65536:
            raise ValueError("No more ports left to try!")
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

    def truncated_file(self, path):
        """
        Truncates file at `path` and asserts that it is indeed empty.
        """
        with open(path, "w"):
            pass
        return path

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
                msg.encode())
        finally:
            bound_sock.close()
            connected_sock.close()

    def test_pub(self):
        """
        pub() should set up a PUB socket and send its input through it.
        """
        prefix = u"ARNIE"
        msg = u"Who is your daddy and what does he do?"
        # Mock inputf to return without standard input
        with mock.patch("zmcat.tool.inputf", side_effect=[msg]):
            zmcat = ZMCat(key=prefix)
            uri = "ipc:///tmp/test-pub"
            sub_sock = zmcat._get_connected_socket(zmq.SUB, uri)
            sub_sock.setsockopt_string(zmq.SUBSCRIBE, prefix)

            try:
                zmcat.pub(uri)
            except StopIteration:
                pass

        sleep(0.1)
        exp_msg = (u"%s%s" % (prefix, msg)).encode()
        self.assertEqual(sub_sock.recv(zmq.NOBLOCK), exp_msg)

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

    def test_push_connected(self):
        """
        push() should set up a PUSH socket and send its input through it.
        """
        msg = u"I'm a cop, you idiot!"
        with mock.patch("zmcat.tool.inputf", side_effect=[msg]):
            zmcat = ZMCat()
            uri = "ipc:///tmp/test-push"
            pull_sock = zmcat._get_bound_socket(zmq.PULL, uri)

            try:
                zmcat.push(uri, bind=False)
            except StopIteration:
                pass

        sleep(0.1)
        self.assertEqual(pull_sock.recv(zmq.NOBLOCK), msg.encode())

    def test_push_bound(self):
        """
        push() should set up a PUSH socket and send its input through it.
        """
        msg = u"I'm a cop, you idiot!"
        with mock.patch("zmcat.tool.inputf", side_effect=[msg]):
            zmcat = ZMCat()
            uri = "ipc:///tmp/test-push"
            pull_sock = zmcat._get_connected_socket(zmq.PULL, uri)

            try:
                zmcat.push(uri, bind=True)
            except StopIteration:
                pass

        sleep(0.1)
        self.assertEqual(pull_sock.recv(zmq.NOBLOCK), msg.encode())

    def test_pull_connected(self):
        """
        pull() should set up a PULL socket and print its messages to output.
        """
        output_file = "/tmp/test-sub.output"

        def save_and_raise(msg):
            """
            Save the msg to a file and raise an exception to get out of the
            while True loop in pull().
            """
            with open(output_file, "w") as f:
                f.write(msg)
            raise GetOutOfLoopException()

        zmcat = ZMCat(output=save_and_raise)
        uri = "ipc:///tmp/test-pull"
        msg = u"You son of a bitch. How are you?"

        try:
            with mock.patch("zmq.sugar.socket.Socket.recv", return_value=msg):
                try:
                    zmcat.pull(uri, bind=False)
                except GetOutOfLoopException:
                    pass
            with open(output_file) as f:
                self.assertEqual(f.read(), msg)
        finally:
            try:
                os.unlink(output_file)
            except OSError:
                pass  # Oh well

    def test_pull_bound(self):
        """
        pull() should set up a PULL socket and print its messages to output.
        """
        output_file = "/tmp/test-sub.output"

        def save_and_raise(msg):
            """
            Save the msg to a file and raise an exception to get out of the
            while True loop in pull().
            """
            with open(output_file, "w") as f:
                f.write(msg)
            raise GetOutOfLoopException()

        zmcat = ZMCat(output=save_and_raise)
        uri = "ipc:///tmp/test-pull"
        msg = u"You son of a bitch. How are you?"

        try:
            with mock.patch("zmq.sugar.socket.Socket.recv", return_value=msg):
                try:
                    zmcat.pull(uri, bind=True)
                except GetOutOfLoopException:
                    pass
            with open(output_file) as f:
                self.assertEqual(f.read(), msg)
        finally:
            try:
                os.unlink(output_file)
            except OSError:
                pass  # Oh well

    def test_req(self):
        """
        req() should set up a REQ socket and push its input through it. It
        should wait for a response and send it to output.
        """
        output_file = self.truncated_file("/tmp/test-req.output")
        req = u"Milk is for babies"
        rep = u"Real men drink beer!"
        uri = "ipc:///tmp/test-req"

        def check_input(msg):
            """
            Make sure `msg` is what we expect.
            """
            self.assertEqual(msg, req)

        zmcat = ZMCat(
            input=lambda: req,
            output=lambda msg: open(output_file, "w").write(msg)
        )
        try:
            with mock.patch("zmq.sugar.socket.Socket.recv", return_value=rep):
                with mock.patch(
                        "zmq.sugar.socket.Socket.send_unicode",
                        side_effect=check_input):
                    zmcat.req(uri)
            with open(output_file) as f:
                self.assertEqual(f.read(), rep)
        finally:
            try:
                os.unlink(output_file)
            except OSError:
                pass  # Oh well

    def test_rep(self):
        """
        rep() should echo and output whatever is REQ'd to it.
        """
        output_file = self.truncated_file("/tmp/test-rep.output")

        def save_and_raise(msg):
            """
            Save the msg to a file and raise an exception to get out of the
            while True loop in rep().
            """
            with open(output_file, "w") as f:
                f.write(msg)
            raise GetOutOfLoopException()

        zmcat = ZMCat(output=save_and_raise)
        uri = "ipc:///tmp/test-rep"
        msg = "Echo!"

        try:
            with mock.patch("zmq.sugar.socket.Socket.recv", return_value=msg):
                with mock.patch("zmq.sugar.socket.Socket.send") as mock_send:
                    try:
                        zmcat.rep(uri)
                    except GetOutOfLoopException:
                        pass
                    self.assertTrue(mock_send.called)
                    self.assertEqual(mock_send.call_args[0][0], msg)
            with open(output_file) as f:
                self.assertEqual(f.read(), msg)
        finally:
            try:
                os.unlink(output_file)
            except OSError:
                pass  # Oh well

    def test_main_calls_correct_function(self):
        """
        main() should call the correct function when given a type
        """
        fake_args = FakeArgs()
        fake_function = mock.Mock()

        for t in TYPES:
            fake_args.type = t
            with mock.patch(
                    "argparse.ArgumentParser.parse_args",
                    return_value=fake_args):
                with mock.patch("zmcat.tool.ZMCat.%s" % t, fake_function):
                    tool.main()
            self.assertTrue(fake_function.called)

    def test_main_handles_eof_error(self):
        """
        main() should handle EOFError exception from the function it calls
        """
        fake_args = FakeArgs()
        fake_args.type = "pub"

        with mock.patch(
                "argparse.ArgumentParser.parse_args", return_value=fake_args):
            with mock.patch("zmcat.tool.ZMCat.pub", side_effect=EOFError):
                try:
                    tool.main()
                except EOFError:
                    self.fail("Should catch EOFError and return")

    def test_main_handles_keyboard_interrupt(self):
        """
        main() should handle EOFError exception from the function it calls
        """
        fake_args = FakeArgs()
        fake_args.type = "pub"

        with mock.patch(
                "argparse.ArgumentParser.parse_args", return_value=fake_args):
            with mock.patch(
                    "zmcat.tool.ZMCat.pub", side_effect=KeyboardInterrupt):
                try:
                    tool.main()
                except KeyboardInterrupt:
                    self.fail("Should catch KeyboardInterrupt and return")
