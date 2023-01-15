from bley.postfix import PostfixPolicy
from twisted.trial import unittest
from twisted.internet.protocol import ClientFactory
from twisted.internet.defer import Deferred, DeferredList
from twisted.internet import task
from twisted.internet import reactor


class PostfixPolicyClient(PostfixPolicy):

    action = ""
    reason = ""

    def connectionMade(self):
        for x in self.factory.data:
            line = "%s=%s" % (x, self.factory.data[x])
            self.sendLine(line.encode('ascii'))
        self.sendLine(b'')

    def lineReceived(self, line):
        line = line.strip()
        if line.startswith(b"action"):
            actionline = line.split(None, 1)
            self.action = actionline[0]
            if len(actionline) == 2:
                self.reason = actionline[1]
        if line == b"":
            self.factory.action_received(self.action, self.reason)
            self.transport.loseConnection()


class PostfixPolicyClientFactory(ClientFactory):
    protocol = PostfixPolicyClient

    def __init__(self, data):
        self.deferred = Deferred()
        self.data = data

    def action_received(self, action, text=""):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.callback({'action': action, 'text': text})

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            d, self.deferred = self.deferred, None
            d.errback(reason)


class BleyTestCase(unittest.TestCase):

    ipv4 = [192, 0, 2, 0]
    ipv6 = ['2001', 'DB8', '', 0]

    def _get_next_ipv4(self):
        if self.ipv4[-1] == 255:
            self.ipv4[-1] = 0
        self.ipv4[-1] += 1
        return str(".").join([str(x) for x in self.ipv4])

    def _get_next_ipv6(self):
        if self.ipv6[-1] == 1000:
            self.ipv6[-1] = 0
        self.ipv6[-1] += 1
        return str(":").join([str(x) for x in self.ipv6])

    def _assert_dunno_action(self, data):
        self.assertEquals(data['action'], b"action=DUNNO")

    def _assert_defer_action(self, data):
        self.assertEquals(data['action'], b"action=DEFER_IF_PERMIT")
        self.assertEquals(data['text'], b"greylisted, try again later")

    def _assert_prepend_action(self, data):
        self.assertEquals(data['action'], b"action=PREPEND")
        self.assertRegexpMatches(data['text'].decode('ascii'), r"X-Greylist: delayed .* seconds by bley-.* at .*; .*")

    def test_incomplete_request(self):
        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_invalid_sender(self):
        ip = self._get_next_ipv4()
        data = {
            'sender': '{mta365@enggjournal.test|mta365@enggjournal.test|mta365@enggpublication.test|mta365@enggpublication.test|mta@enggjournal.test|mta@enggjournal.test|mta@enggpublication.test|mta@enggpublication.test|server@enggjournal.test|server@enggjournal.test|server@enggpublication.test|server@enggpublication.test',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'localhost',
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

    def test_zzz_greylisting(self):
        ip = self._get_next_ipv4()
        data = {
            'sender': 'root@example.com',
            'recipient': 'user@gl.example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        d2 = task.deferLater(reactor, 5, get_action, "127.0.0.1", 1337, data)

        d2.addCallback(self._assert_defer_action)

        d3 = task.deferLater(reactor, 65, get_action, "127.0.0.1", 1337, data)

        d3.addCallback(self._assert_prepend_action)

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
            'sender': 'someone@example.com',
            'recipient': 'user@dontgreylist.test',
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
            'sender': 'someone@example.com',
            'recipient': 'user@subdomain.dontgreylist.test',
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

    # domain name is a substring of whitelisted domain - should greylist
    def _test_whitelist_recipient_negative_test1(self, ip):
        data = {
            'sender': 'someone@example.com',
            'recipient': 'user@greylist.test',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        return d

    def test_whitelist_recipient_negative_test1_v4(self):
        ip = self._get_next_ipv4()
        return self._test_whitelist_recipient_negative_test1(ip)

    def test_whitelist_recipient_negative_test1_v6(self):
        ip = self._get_next_ipv6()
        return self._test_whitelist_recipient_negative_test1(ip)

    # domain name contains whitelisted domainname,
    # but is not a subdomain - should greylist
    def _test_whitelist_recipient_negative_test2(self, ip):
        data = {
            'sender': 'someone@example.com',
            'recipient': 'user@xxxxdontgreylist.test',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        return d

    def test_whitelist_recipient_negative_test2_v4(self):
        ip = self._get_next_ipv4()
        return self._test_whitelist_recipient_negative_test2(ip)

    def test_whitelist_recipient_negative_test2_v6(self):
        ip = self._get_next_ipv6()
        return self._test_whitelist_recipient_negative_test2(ip)

    def _test_whitelist_recipient_regex(self, ip):
        data = {
            'sender': 'someone@example.com',
            'recipient': 'user@application.test',
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
            'sender': 'someone@example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'mail.wlclient.test',
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
            'sender': 'someone@example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'important.customer.test',
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
            'sender': 'someone@example.com',
            'recipient': 'user@example.com',
            'client_address': ip,
            'client_name': 'localhost',
            'helo_name': 'invalid.local',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d

    def test_whitelist_client_ip_v4(self):
        ip = '192.0.2.202'
        return self._test_whitelist_client_ip(ip)

    def test_whitelist_client_ip_v6(self):
        ip = '2001:DB8::123:456'
        return self._test_whitelist_client_ip(ip)

    def test_dnsbl_client(self):
        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
            'client_address': '203.0.113.1',  # 1.113.0.203.testlist.bley.mx IN A 127.0.0.2
            'client_name': 'localhost',
            'helo_name': 'localhost',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_defer_action)

        return d

    def test_dnsbl_rfc_client(self):
        data = {
            'sender': 'root@example.com',
            'recipient': 'user@example.com',
            'client_address': '203.0.113.2',  # 2.113.0.203.badtestlist.bley.mx IN TXT broken
            'client_name': 'localhost',
            'helo_name': 'localhost',
        }
        d = get_action("127.0.0.1", 1337, data)

        d.addCallback(self._assert_dunno_action)

        return d


def get_action(host, port, data):
    factory = PostfixPolicyClientFactory(data)
    reactor.connectTCP(host, port, factory)
    return factory.deferred
