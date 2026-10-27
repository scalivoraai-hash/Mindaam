"""Owner-provided GCP describe shape, plus restrictive-policy regressions."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import Cloud, Blocked, SETTINGS
from deploy import validate_firewall, ensure, DESCRIPTION

MEDIA = 'tcp:80,tcp:443,tcp:7881,udp:3478,udp:50000-50200'


class FirewallValidation(unittest.TestCase):
    def fixture(self, private=False):
        return {
            'name': 'mindaam-redis-private' if private else 'mindaam-media-public',
            'description': DESCRIPTION, 'direction': 'INGRESS', 'disabled': False,
            'network': 'https://www.googleapis.com/compute/v1/projects/mindaam/global/networks/mindaam',
            'priority': 1000,
            'sourceRanges': [SETTINGS['subnet_cidr'] if private else '0.0.0.0/0'],
            'targetServiceAccounts': ['mindaam-media@mindaam.iam.gserviceaccount.com'],
            'allowed': [{'IPProtocol': p, 'ports': [port]} for p, port in
                        ([('tcp', '6379')] if private else
                         [('tcp', '80'), ('tcp', '443'), ('tcp', '7881'),
                          ('udp', '3478'), ('udp', '50000-50200')])],
        }

    def check(self, rule, private=False):
        validate_firewall(Cloud('mindaam'), rule, rule['name'],
                          'tcp:6379' if private else MEDIA,
                          SETTINGS['subnet_cidr'] if private else '0.0.0.0/0')

    def test_actual_split_entries_and_order_independent_equivalents(self):
        for private in [False, True]:
            rule = self.fixture(private)
            self.check(rule, private)
            rule['allowed'].reverse()
            rule['allowed'] += copy.deepcopy(rule['allowed'])
            self.check(rule, private)
            del rule['disabled']
            self.check(rule, private)
        rule = self.fixture()
        rule['allowed'] = [{'IPProtocol': '6', 'ports': ['7881', '80', '443']},
                           {'IPProtocol': '17', 'ports': ['50000-50100', '50101-50200', '3478']}]
        self.check(rule)

    def test_required_ports_and_protocols_are_exact(self):
        for private in [False, True]:
            original = self.fixture(private)
            variants = [original['allowed'][1:],
                        original['allowed'] + [{'IPProtocol': 'tcp', 'ports': ['22']}],
                        original['allowed'] + [{'IPProtocol': 'udp', 'ports': ['6379']}],
                        original['allowed'] + [{'IPProtocol': 'tcp'}],
                        original['allowed'] + [{'IPProtocol': 'all'}]]
            wrong = copy.deepcopy(original['allowed']); wrong[0]['IPProtocol'] = 'icmp'
            variants.append(wrong)
            for allowed in variants:
                with self.subTest(private=private, allowed=allowed), self.assertRaises(Blocked):
                    self.check({**original, 'allowed': allowed}, private)

    def test_security_fields_and_ownership_remain_required(self):
        for private in [False, True]:
            rule = self.fixture(private)
            for key, value in [
                ('sourceRanges', ['0.0.0.0/0'] if private else ['10.0.0.0/8']),
                ('targetServiceAccounts', ['other@mindaam.iam.gserviceaccount.com']),
                ('targetServiceAccounts', []), ('network', rule['network'].replace('/projects/mindaam/', '/projects/other/')),
                ('network', rule['network'] + '-other'), ('disabled', True),
                ('direction', 'EGRESS'), ('description', 'unrelated'), ('description', ''),
                ('sourceTags', ['extra-source']), ('sourceServiceAccounts', ['other@example.com']),
                ('targetTags', ['extra-target']),
            ]:
                with self.subTest(private=private, field=key), self.assertRaises(Blocked):
                    self.check({**rule, key: value}, private)

    def test_unrelated_rule_is_rejected_without_mutation(self):
        cloud = Cloud('mindaam')
        for private in [False, True]:
            rule = self.fixture(private); rule['description'] = 'unrelated'
            with patch.object(cloud, 'gc', return_value=rule) as gc:
                with self.assertRaises(Blocked):
                    ensure(cloud, ['compute', 'firewall-rules', 'describe', rule['name']],
                           ['compute', 'firewall-rules', 'create', rule['name']],
                           name=rule['name'], labels=False)
                gc.assert_called_once()
