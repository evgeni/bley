from postfix import PostfixPolicyFactory
from twisted.trial import unittest
from twisted.test import proto_helpers


class PostfixPolicyTestCase(unittest.TestCase):
    def setUp(self):
        factory = PostfixPolicyFactory()
        self.proto = factory.buildProtocol(('127.0.0.1', 0))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)

    def test_DUNNO(self):
        self.proto.lineReceived("sender=root@example.com")
        self.proto.lineReceived("recipient=user@example.com")
        self.proto.lineReceived("")
        self.assertEqual(self.tr.value(), "action=DUNNO\n\n")
