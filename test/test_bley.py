from postfix import PostfixPolicy, PostfixPolicyFactory
from twisted.trial import unittest
from twisted.internet.protocol import ClientFactory
from twisted.internet.defer import Deferred, DeferredList
from twisted.internet import task
from twisted.internet import reactor
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
    ipv6net = ipaddr.IPNetwork('2001:DB8::/32')
    ipv6generator = ipv6net.iterhosts()

    def _get_next_ipv4(self):
        try:
            return self.ipv4generator.next()
        except StopIteration:
            self.ipv4generator = self.ipv4net.iterhosts()
            return self.ipv4generator.next()

    def _get_next_ipv6(self):
        try:
            return self.ipv6generator.next()
        except StopIteration:
            self.ipv6generator = self.ipv6net.iterhosts()
            return self.ipv6generator.next()

    def _assert_dunno_action(self, action):
        self.assertEquals(action, "action=DUNNO")

    def _assert_defer_action(self, action):
        self.assertEquals(action, "action=DEFER_IF_PERMIT")

    def test_incomplete_request(self):
        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def _test_good_client(self, ip):
        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'localhost',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_good_client_v4(self):
        ip = self._get_next_ipv4()
        return self._test_good_client(ip)

    def test_good_client_v6(self):
        ip = self._get_next_ipv6()
        return self._test_good_client(ip)

    def _test_ip_help_and_dyn_host(self, ip):
        data = {
            'sender': 'nothinguseful@example.com',
            'recipient': 'nothinguseful@example.com',
            'client_address': ip,
            'client_name': 'client123.dyn.example.com',
            'helo_name': '[%s]' % ip,
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        return d

    def test_ip_help_and_dyn_host_v4(self):
        ip = self._get_next_ipv4()
        return self._test_ip_help_and_dyn_host(ip)

    def test_ip_help_and_dyn_host_v6(self):
        ip = self._get_next_ipv6()
        return self._test_ip_help_and_dyn_host(ip)

    def _test_same_sender_recipient_and_dyn_host(self, ip):
        data = {
            'sender': 'nothinguseful@example.com',
            'recipient': 'nothinguseful@example.com',
            'client_address': ip,
            'client_name': 'client123.dyn.example.com',
            'helo_name': 'client123.dyn.example.com',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        return d

    def test_same_sender_recipient_and_dyn_host_v4(self):
        ip = self._get_next_ipv4()
        return self._test_same_sender_recipient_and_dyn_host(ip)

    def test_same_sender_recipient_and_dyn_host_v6(self):
        ip = self._get_next_ipv6()
        return self._test_same_sender_recipient_and_dyn_host(ip)

    def _test_same_sender_recipient_and_ip_helo(self, ip):
        data = {
            'sender': 'nothinguseful@example.com',
            'recipient': 'nothinguseful@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': '[%s]' % ip,
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        return d

    def test_same_sender_recipient_and_ip_helo_v4(self):
        ip = self._get_next_ipv4()
        return self._test_same_sender_recipient_and_ip_helo(ip)

    def test_same_sender_recipient_and_ip_helo_v6(self):
        ip = self._get_next_ipv6()
        return self._test_same_sender_recipient_and_ip_helo(ip)

    def test_greylisting(self):
        ip = self._get_next_ipv4()
        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        d2 = task.deferLater(reactor, 5, get_action, "127.0.0.1", 1337, data)

        d2.addCallback(self._assert_defer_action)

        d3 = task.deferLater(reactor, 65, get_action, "127.0.0.1", 1337, data)

        d3.addCallback(self._assert_dunno_action)

        return DeferredList([d, d2, d3])

    def _test_bad_helo(self, ip):
        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        return d

    def test_bad_helo_v4(self):
        ip = self._get_next_ipv4()
        return self._test_bad_helo(ip)

    def test_bad_helo_v6(self):
        ip = self._get_next_ipv6()
        return self._test_bad_helo(ip)

    def _test_postmaster(self, ip):
        data = {
            'sender': 'angryuser@different.example.com',
            'recipient': 'postmaster@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_postmaster_v4(self):
        ip = self._get_next_ipv4()
        return self._test_postmaster(ip)

    def test_postmaster_v6(self):
        ip = self._get_next_ipv6()
        return self._test_postmaster(ip)

    def _test_whitelist_recipient_domain(self, ip):
        data = {
            'sender': 'someone@a1.example.com',
            'recipient': 'user@dontgreylist.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_whitelist_recipient_domain_v4(self):
        ip = self._get_next_ipv4()
        return self._test_whitelist_recipient_domain(ip)

    def test_whitelist_recipient_domain_v6(self):
        ip = self._get_next_ipv6()
        return self._test_whitelist_recipient_domain(ip)

    def _test_whitelist_recipient_subdomain(self, ip):
        data = {
            'sender': 'someone@a2.example.com',
            'recipient': 'user@sub.dontgreylist.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_whitelist_recipient_subdomain_v4(self):
        ip = self._get_next_ipv4()
        return self._test_whitelist_recipient_subdomain(ip)

    def test_whitelist_recipient_subdomain_v6(self):
        ip = self._get_next_ipv6()
        return self._test_whitelist_recipient_subdomain(ip)

    def _test_whitelist_recipient_negative_test(self, ip):
        data = {
            'sender': 'someone@a2.example.com',
            'recipient': 'user@xdontgreylist.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        return d

    def test_whitelist_recipient_negative_test_v4(self):
        ip = self._get_next_ipv4()
        return self._test_whitelist_recipient_negative_test(ip)

    def test_whitelist_recipient_negative_test_v6(self):
        ip = self._get_next_ipv6()
        return self._test_whitelist_recipient_negative_test(ip)

    def _test_whitelist_recipient_regex(self, ip):
        data = {
            'sender': 'someone@a2.example.com',
            'recipient': 'user@application.fast',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_whitelist_recipient_regex_v4(self):
        ip = self._get_next_ipv4()
        return self._test_whitelist_recipient_regex(ip)

    def test_whitelist_recipient_regex_v6(self):
        ip = self._get_next_ipv6()
        return self._test_whitelist_recipient_regex(ip)

    def _test_whitelist_clients_domain(self, ip):
        data = {
            'sender': 'someone@wcd.example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'mail.wlclient.net',
            'helo_name': 'invalid.external',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_whitelist_clients_domain_v4(self):
        ip = self._get_next_ipv4()
        return self._test_whitelist_clients_domain(ip)

    def test_whitelist_clients_domain_v6(self):
        ip = self._get_next_ipv6()
        return self._test_whitelist_clients_domain(ip)

    def _test_whitelist_clients_regex(self, ip):
        data = {
            'sender': 'someone@wcr.example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'important.customer.com',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_whitelist_clients_regex_v4(self):
        ip = self._get_next_ipv4()
        return self._test_whitelist_clients_regex(ip)

    def test_whitelist_clients_regex_v6(self):
        ip = self._get_next_ipv6()
        return self._test_whitelist_clients_regex(ip)

    def _test_whitelist_client_ip(self, ip):
        data = {
            'sender': 'someone@twci.example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_whitelist_client_ip_v4(self):
        ip = '11.22.33.44'
        return self._test_whitelist_client_ip(ip)

    def test_whitelist_client_ip_v6(self):
        ip = '5566::7788'
        return self._test_whitelist_client_ip(ip)


def get_action(host, port, data):
    factory = PostfixPolicyClientFactory(data)
    reactor.connectTCP(host, port, factory)
    return factory.deferred
