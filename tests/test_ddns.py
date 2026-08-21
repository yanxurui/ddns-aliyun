import unittest
from unittest import mock

import aliyun
import ddns


class AliyunClientTests(unittest.TestCase):
    def test_a_update_parameters_do_not_leak_into_aaaa_lookup(self):
        client = aliyun.Aliyun('id', 'secret')
        client._get_response_data = mock.Mock(side_effect=[
            {'RecordId': 'a-record'},
            {
                'TotalCount': 1,
                'PageNumber': 1,
                'PageSize': 500,
                'DomainRecords': {'Record': [{
                    'RecordId': 'aaaa-record',
                    'RR': 'sz',
                    'Type': 'AAAA',
                    'Value': '2001:db8::1',
                }]},
            },
        ])

        client.record_ddns('a-record', 'sz', 'A', '203.0.113.10')
        records = client.get_records('example.com', 'sz', 'AAAA')

        self.assertEqual(records[0]['RecordId'], 'aaaa-record')
        lookup_params = client._get_response_data.call_args_list[1].args[0]
        self.assertEqual(lookup_params['Action'], 'DescribeDomainRecords')
        self.assertEqual(lookup_params['RRKeyWord'], 'sz')
        self.assertEqual(lookup_params['TypeKeyWord'], 'AAAA')
        for leaked_key in ('RecordId', 'RR', 'Type', 'Value'):
            self.assertNotIn(leaked_key, lookup_params)

    def test_duplicate_exact_records_raise(self):
        client = aliyun.Aliyun('id', 'secret')
        client.get_records = mock.Mock(return_value=[
            {'RecordId': '1', 'RR': 'sz', 'Type': 'AAAA', 'Value': '2001:db8::1'},
            {'RecordId': '2', 'RR': 'sz', 'Type': 'AAAA', 'Value': '2001:db8::2'},
        ])

        with self.assertRaises(aliyun.DuplicateRecordError):
            client.get_record('example.com', 'sz', 'AAAA')

    def test_record_lookup_follows_pagination(self):
        client = aliyun.Aliyun('id', 'secret')
        client._get_response_data = mock.Mock(side_effect=[
            {
                'TotalCount': 2,
                'PageSize': 1,
                'DomainRecords': {'Record': [
                    {'RecordId': '1', 'RR': 'other', 'Type': 'AAAA', 'Value': '2001:db8::1'},
                ]},
            },
            {
                'TotalCount': 2,
                'PageSize': 1,
                'DomainRecords': {'Record': [
                    {'RecordId': '2', 'RR': 'sz', 'Type': 'AAAA', 'Value': '2001:db8::2'},
                ]},
            },
        ])

        records = client.get_records('example.com', 'sz', 'AAAA')

        self.assertEqual([record['RecordId'] for record in records], ['2'])
        second_page = client._get_response_data.call_args_list[1].args[0]
        self.assertEqual(second_page['PageNumber'], 2)

    def test_domain_check_propagates_api_failure(self):
        client = aliyun.Aliyun('id', 'secret')
        client._get_response_data = mock.Mock(side_effect=OSError('API unavailable'))

        with self.assertRaises(OSError):
            client.check_domain_exists('example.com')


class DdnsTests(unittest.TestCase):
    def tearDown(self):
        ddns.LocalIPV4 = None
        ddns.LocalIPV6 = None

    @mock.patch('ddns.get_local_ip', return_value='2001:db8::10')
    def test_lookup_failure_never_adds_record(self, _get_local_ip):
        client = mock.Mock()
        client.get_record.side_effect = OSError('temporary API failure')
        domain = {'name': 'example.com', 'sub_domains': ['sz'], 'ipv6': True}

        with self.assertRaises(OSError):
            ddns.ddns(client, domain)

        client.add_record.assert_not_called()
        client.record_ddns.assert_not_called()

    @mock.patch('ddns.get_local_ip', return_value='2001:db8::10')
    def test_missing_record_is_added_after_successful_lookup(self, _get_local_ip):
        client = mock.Mock()
        client.get_record.return_value = None
        domain = {'name': 'example.com', 'sub_domains': ['sz'], 'ipv6': True}

        ddns.ddns(client, domain)

        client.add_record.assert_called_once_with(
            'example.com', 'sz', 'AAAA', '2001:db8::10'
        )

    @mock.patch('ddns.get_local_ip', return_value='2001:db8::10')
    def test_unchanged_record_is_not_mutated(self, _get_local_ip):
        client = mock.Mock()
        client.get_record.return_value = {
            'RecordId': 'record-1',
            'Value': '2001:db8::10',
        }
        domain = {'name': 'example.com', 'sub_domains': ['sz'], 'ipv6': True}

        ddns.ddns(client, domain)

        client.add_record.assert_not_called()
        client.record_ddns.assert_not_called()

    @mock.patch('ddns.get_local_ip', return_value='2001:db8::10')
    def test_changed_record_is_updated_by_returned_id(self, _get_local_ip):
        client = mock.Mock()
        client.get_record.return_value = {
            'RecordId': 'record-1',
            'Value': '2001:db8::20',
        }
        domain = {'name': 'example.com', 'sub_domains': ['sz'], 'ipv6': True}

        ddns.ddns(client, domain)

        client.record_ddns.assert_called_once_with(
            'record-1', 'sz', 'AAAA', '2001:db8::10'
        )
        client.add_record.assert_not_called()

    @mock.patch('ddns.socket.socket')
    def test_ipv6_uses_local_route_source_not_external_service(self, socket_factory):
        probe = socket_factory.return_value.__enter__.return_value
        probe.getsockname.return_value = (
            '240e:3a8:4cc5:c800:caff:bfff:fe04:7e0e', 12345, 0, 0
        )

        result = ddns.get_ipv6()

        self.assertEqual(result, '240e:3a8:4cc5:c800:caff:bfff:fe04:7e0e')
        probe.connect.assert_called_once_with(ddns.IPV6_ROUTE_PROBES[0])


if __name__ == '__main__':
    unittest.main()
