#!/usr/bin/python
# -*- coding: UTF-8 -*-
import base64
import datetime
import hmac
import json
import logging
import uuid
from urllib import parse, request


HEADERS = {
    'Accept': 'text/json',
    'Content-type': 'application/x-www-form-urlencoded',
    'User-Agent': 'ddns-aliyun/0.2.0',
}


class DuplicateRecordError(RuntimeError):
    """Raised when more than one exact DNS record matches a configured name/type."""


class Aliyun:
    def __init__(self, access_key_id, access_key_secret, timeout=20):
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._timeout = timeout

    def _params(self, action, **kwargs):
        """Build fresh parameters for every request.

        Reusing one mutable dictionary caused parameters from an A-record update
        to filter the following AAAA lookup, which in turn created duplicates.
        """
        params = {
            'Format': 'json',
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureVersion': '1.0',
            'Timestamp': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'Version': '2015-01-09',
            'AccessKeyId': self._access_key_id,
            'Action': action,
        }
        params.update(kwargs)
        return params

    def check_domain_exists(self, domain_name):
        # Let API/network errors propagate. They must never be interpreted as a
        # missing domain, because doing so could trigger an unsafe create call.
        self._get_response_data(self._params('DescribeDomainInfo', DomainName=domain_name))
        return True

    def get_records(self, domain_name, sub_domain, record_type):
        """Return all exact records for an RR/type, following API pagination."""
        records = []
        page_number = 1
        while True:
            data = self._get_response_data(self._params(
                'DescribeDomainRecords',
                DomainName=domain_name,
                RRKeyWord=sub_domain,
                TypeKeyWord=record_type,
                SearchMode='EXACT',
                PageNumber=page_number,
                PageSize=500,
            ))
            page_records = data.get('DomainRecords', {}).get('Record', [])
            records.extend(
                record for record in page_records
                if record.get('RR') == sub_domain and record.get('Type') == record_type
            )
            total_count = int(data.get('TotalCount', len(page_records)))
            page_size = int(data.get('PageSize', 500))
            if page_number * page_size >= total_count:
                break
            page_number += 1
        return records

    def get_record(self, domain_name, sub_domain, record_type):
        records = self.get_records(domain_name, sub_domain, record_type)
        fqdn = f'{sub_domain}.{domain_name}'
        if not records:
            return None
        if len(records) > 1:
            values = ', '.join(record.get('Value', '<unknown>') for record in records)
            raise DuplicateRecordError(
                f'Found {len(records)} {record_type} records for {fqdn}: {values}. '
                'Refusing to choose or create another record.'
            )
        record = records[0]
        logging.info(f"The {record_type} record of {fqdn} is {record['Value']}")
        return record

    def add_record(self, domain_name, sub_domain, record_type, local_ip):
        data = self._get_response_data(self._params(
            'AddDomainRecord',
            DomainName=domain_name,
            RR=sub_domain,
            Type=record_type,
            Value=local_ip,
        ))
        return data['RecordId']

    def record_ddns(self, record_id, sub_domain, record_type, local_ip):
        data = self._get_response_data(self._params(
            'UpdateDomainRecord',
            RR=sub_domain,
            RecordId=record_id,
            Type=record_type,
            Value=local_ip,
        ))
        return data['RecordId']

    def _get_response_data(self, params):
        # Work on a copy so signing never mutates the caller's request.
        signed_params = dict(params)
        signed_params['SignatureNonce'] = str(uuid.uuid4())
        signed_params = self._sort_dict(signed_params)
        signed_params['Signature'] = self._sign(signed_params)
        req = request.Request(
            url=f"https://alidns.aliyuncs.com/?{parse.urlencode(signed_params)}",
            headers=HEADERS,
            method='GET',
        )
        with request.urlopen(req, timeout=self._timeout) as response:
            return json.loads(response.read().decode('utf-8'))

    @staticmethod
    def _sort_dict(values):
        return {key: values[key] for key in sorted(values)}

    def _sign(self, params):
        string_to_sign = 'GET&%2F&' + parse.quote(parse.urlencode(params))
        digest = hmac.new(
            (self._access_key_secret + '&').encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod='sha1',
        ).digest()
        return base64.b64encode(digest).decode('utf-8')
