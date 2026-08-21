#!/usr/bin/python
# -*- coding: UTF-8 -*-
import ipaddress
import json
import logging
import os
import socket

import aliyun
import ip
import logger


LocalIPV4 = None
LocalIPV6 = None
IPV6_ROUTE_PROBES = (
    ('2606:4700:4700::1111', 53),
    ('2001:4860:4860::8888', 53),
)


def init_domain(aliyun_client, domain):
    # Fail closed if AliDNS cannot confirm the domain. A transient lookup error
    # must not be treated as permission to create or mutate DNS resources.
    aliyun_client.check_domain_exists(domain['name'])


def ddns(aliyun_client, domain):
    record_type = 'AAAA' if domain.get('ipv6') else 'A'
    local_ip = get_local_ip(domain, record_type == 'AAAA')
    logging.info(f'Local ip is {local_ip}')

    if not local_ip:
        raise RuntimeError(f'Could not determine a valid local {record_type} address')

    for sub_domain in domain['sub_domains']:
        # One lookup returns the value and RecordId together. API/network errors
        # propagate, and duplicate matches abort rather than creating more.
        record = aliyun_client.get_record(domain['name'], sub_domain, record_type)
        if record is None:
            logging.info(f'Adding the {record_type} record of {sub_domain}.{domain["name"]} as {local_ip}')
            aliyun_client.add_record(domain['name'], sub_domain, record_type, local_ip)
        elif record['Value'] == local_ip:
            logging.info(f'No need to update the {record_type} record of {sub_domain}.{domain["name"]}')
        else:
            logging.info(f'Updating the {record_type} record of {sub_domain}.{domain["name"]} to {local_ip}')
            aliyun_client.record_ddns(record['RecordId'], sub_domain, record_type, local_ip)


def get_local_ip(domain, ipv6=False):
    return get_ipv6() if ipv6 else get_ipv4()


# Keep the old misspelled function name as an alias for callers of the original script.
def get_locat_ip(domain, ipv6=False):
    return get_local_ip(domain, ipv6)


def get_ipv4():
    global LocalIPV4
    if not LocalIPV4:
        LocalIPV4 = ip.IPV4.get_local_ip()
    try:
        address = ipaddress.ip_address(LocalIPV4)
    except (TypeError, ValueError):
        return None
    return str(address) if isinstance(address, ipaddress.IPv4Address) else None


def get_ipv6():
    """Return this machine's globally routed IPv6 source address.

    UDP connect() performs route/source-address selection without sending a
    packet. Unlike external "what is my IP" services, getsockname() returns the
    mini's own interface address before any router NAT66/masquerading.
    """
    if not socket.has_ipv6:
        logging.error('Local machine does not have IPv6 support.')
        return None

    global LocalIPV6
    if LocalIPV6:
        return LocalIPV6

    for target in IPV6_ROUTE_PROBES:
        try:
            with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as probe:
                probe.connect(target)
                candidate = probe.getsockname()[0].split('%', 1)[0]
            address = ipaddress.ip_address(candidate)
            if isinstance(address, ipaddress.IPv6Address) and address.is_global:
                LocalIPV6 = str(address)
                return LocalIPV6
            logging.warning(f'Ignoring non-global IPv6 source address {candidate}')
        except OSError as error:
            logging.warning(f'IPv6 route probe to {target[0]} failed: {error}')

    logging.error('Could not select a globally routed local IPv6 address.')
    return None


def main():
    logger.setup_logging()
    logging.info(f'starting ddns.py, pid: {os.getpid()}')
    try:
        config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'conf.json')
        with open(config_path, 'r') as config_file:
            conf = json.load(config_file)
        aliyun_client = aliyun.Aliyun(conf['access_key'], conf['access_secret'])

        initialized_domains = set()
        for domain in conf['domains']:
            if domain['name'] not in initialized_domains:
                init_domain(aliyun_client, domain)
                initialized_domains.add(domain['name'])
            ddns(aliyun_client, domain)
        return 0
    except Exception:
        logging.exception('DDNS update failed')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
