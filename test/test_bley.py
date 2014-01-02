from postfix import PostfixPolicy, PostfixPolicyFactory
from twisted.trial import unittest
from twisted.internet.protocol import ClientFactory
from twisted.internet.defer import Deferred
import ipaddr


class PostfixPolicyClient(PostfixPolicy):

    action = ""
    reason = ""

    def connectionMade(self):
        for x in self.factory.data:
            line = "%s=%s" % (x, self.factory.data[x])
            self.sendLine(line)
        self.sendLine("")

    def lineReceived(self, line):
        line = line.strip()
        if line.startswith("action"):
            actionline = line.split(None, 1)
            self.action = actionline[0]
            if len(actionline) == 2:
                self.reason = actionline[1]
        if line == "":
            self.factory.action_received(self.action)
            self.transport.loseConnection()


class PostfixPolicyClientFactory(ClientFactory):
    protocol = PostfixPolicyClient

    def __init__(self, data):
        self.deferred = Deferred()
        self.data = data

    def action_received(self, action, text=""):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback(action)

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


class BleyTestCase(unittest.TestCase):

    ipv4net = ipaddr.IPNetwork('192.0.2.0/24')
    ipv4generator = ipv4net.iterhosts()

    def _get_next_ipv4(self):
        try:
            return self.ipv4generator.next()
        except StopIteration:
            self.ipv4generator = self.ipv4net.iterhosts()
            return self.ipv4generator.next()

    def test_incomplete_request(self):
        ip = self._get_next_ipv4()

        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
        }
        d = get_action("127.0.0.1", 1337, data)

        def got_action(action):
            self.assertEquals(action, "action=DUNNO")

        d.addCallback(got_action)

        return d

    def test_good_client(self):
        ip = self._get_next_ipv4()

        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'localhost',
        }
        d = get_action("127.0.0.1", 1337, data)

        def got_action(action):
            self.assertEquals(action, "action=DUNNO")

        d.addCallback(got_action)

        return d

    def test_ip_help_and_dyn_host(self):
        ip = self._get_next_ipv4()

        data = {
            'sender': 'nothinguseful@example.com',
            'recipient': 'nothinguseful@example.com',
            'client_address': ip,
            'client_name': 'client123.dyn.example.com',
            'helo_name': '[%s]' % ip,
        }
        d = get_action("127.0.0.1", 1337, data)

        def got_action(action):
            self.assertEquals(action, "action=DEFER_IF_PERMIT")

        d.addCallback(got_action)

        return d

    def test_same_sender_recipient_and_dyn_host(self):
        ip = self._get_next_ipv4()

        data = {
            'sender': 'nothinguseful@example.com',
            'recipient': 'nothinguseful@example.com',
            'client_address': ip,
            'client_name': 'client123.dyn.example.com',
            'helo_name': 'client123.dyn.example.com',
        }
        d = get_action("127.0.0.1", 1337, data)

        def got_action(action):
            self.assertEquals(action, "action=DEFER_IF_PERMIT")

        d.addCallback(got_action)

        return d

    def test_same_sender_recipient_and_ip_helo(self):
        ip = self._get_next_ipv4()

        data = {
            'sender': 'nothinguseful@example.com',
            'recipient': 'nothinguseful@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': '[%s]' % ip,
        }
        d = get_action("127.0.0.1", 1337, data)

        def got_action(action):
            self.assertEquals(action, "action=DEFER_IF_PERMIT")

        d.addCallback(got_action)

        return d

    def test_bad_helo(self):
        ip = self._get_next_ipv4()

        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        def got_action(action):
            self.assertEquals(action, "action=DEFER_IF_PERMIT")

        d.addCallback(got_action)

        return d

    def test_postmaster(self):
        ip = self._get_next_ipv4()

        data = {
            'sender': 'angryuser@different.example.com',
            'recipient': 'postmaster@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        def got_action(action):
            self.assertEquals(action, "action=DUNNO")

        d.addCallback(got_action)

        return d


def get_action(host, port, data):
    from twisted.internet import reactor
    factory = PostfixPolicyClientFactory(data)
    reactor.connectTCP(host, port, factory)
    return factory.deferred
