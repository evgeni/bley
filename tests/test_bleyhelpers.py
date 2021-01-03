import bley.helpers
import ipaddress
import unittest


class BleyHelpersTestCase(unittest.TestCase):

    ips = [
        ("127.0.0.1", "1.0.0.127"),
        ("127.0.2.1", "1.2.0.127"),
        ("192.0.2.23", "23.2.0.192"),
        ("10.11.12.13", "13.12.11.10"),
        ("2001:DB8::1",
         "1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2"),
        ("2001:0db8:1000:0100:0010:0001:0000:0000",
         "0.0.0.0.0.0.0.0.1.0.0.0.0.1.0.0.0.0.1.0.0.0.0.1.8.b.d.0.1.0.0.2"),
    ]
    dynamic_hosts = [
        'ip-178-231-86-123.unitymediagroup.de',
        'p4FCA123E.dip0.t-ipconnect.de',
        'muedsl-82-207-123-222.citykom.de',
        'dslb-178-010-012-123.pools.arcor-ip.net',
        '108.30.123.23.dynamic.mundo-r.com',
        'AMontsouris-159-1-80-123.w92-321.abo.wanadoo.fr',
        'dyndsl-085-032-023-123.ewe-ip-backbone.de',
        'HSI-KBW-078-043-123-011.hsi4.kabel-badenwuerttemberg.de',
        'p578ABBAA.dip.t-dialin.net',
        'e179123404.adsl.alicedsl.de',
    ]
    static_hosts = [
        'mail.example.com',
        'mail.dynamicpower.example.com',
        'chi.die-welt.net',
        'v1234207132567817.yourvserver.net',
        'vps-1018888-4321.united-hoster.de',
        'static.88-198-123-123.clients.your-server.de',
        'port-83-236-123-123.static.qsc.de',
    ]

    def test_reverse_ip(self):
        for ip in self.ips:
            self.assertEqual(bley.helpers.reverse_ip(ip[0]), ip[1])

    def test_domain_from_host(self):
        if not bley.helpers.publicsuffix2:
            raise unittest.SkipTest("publicsuffix2 module not available, "
                                    "domain tests skipped")
        domains = [
            ("example.com", "example.com"),
            ("example.co.uk", "example.co.uk"),
            ("example.museum", "example.museum"),
            ("some.weird.host.example.com", "example.com"),
            ("ip-123-123-123-123.dyn.example.co.uk", "example.co.uk"),
            ("A.really.BIG.example.museum", "example.museum"),
        ]
        for domain in domains:
            self.assertEqual(bley.helpers.domain_from_host(domain[0]),
                             domain[1])

    def test_check_dyn_host_dynamic(self):
        for host in self.dynamic_hosts:
            self.assertEqual(bley.helpers.check_dyn_host(host), 1)

    def test_check_dyn_host_static(self):
        for host in self.static_hosts:
            self.assertEqual(bley.helpers.check_dyn_host(host), 0)

    def test_check_helo_good(self):
        for host in self.dynamic_hosts + self.static_hosts:
            params = {
                'client_name': host,
                'helo_name': host,
            }
            self.assertEqual(bley.helpers.check_helo(params), 0)

    def test_check_helo_domain(self):
        for host in self.dynamic_hosts + self.static_hosts:
            params = {
                'client_name': host,
                'helo_name': 'mail.%s' % host,
            }
            self.assertEqual(bley.helpers.check_helo(params), 1)

    def test_check_helo_ip(self):
        for ip in self.ips:
            params = {
                'client_name': '%s.dyn.example.com' % ip[1],
                'client_address': ipaddress.ip_address(ip[0]).exploded,
                'helo_name': '[%s]' % ip[0],
            }
            self.assertEqual(bley.helpers.check_helo(params), 1)

    def test_check_helo_bad_ip(self):
        for ip in self.ips:
            params = {
                'client_name': '%s.dyn.example.com' % ip[1],
                'client_address': ipaddress.ip_address(ip[0]).exploded,
                'helo_name': '[ip:%s]' % ip[0],
            }
            self.assertEqual(bley.helpers.check_helo(params), 2)

    def test_check_helo_bad(self):
        for ip in self.ips:
            params = {
                'client_name': '%s.dyn.example.com' % ip[1],
                'client_address': ipaddress.ip_address(ip[0]).exploded,
                'helo_name': 'windowsxp.local',
            }
            self.assertEqual(bley.helpers.check_helo(params), 2)

    def test_check_spf(self):
        raise unittest.SkipTest("SPF checks need a working network")
