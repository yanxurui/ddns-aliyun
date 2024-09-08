#!/usr/bin/python
# -*- coding: UTF-8 -*-
import json, os, logging, socket
import aliyun
import logger
import ipv4, ipv6

global LocalIPV4
LocalIPV4 = ''

global LocalIPV6
LocalIPV6 = ''

def init_domain(aliyun_client, domain):
    domain_exists = aliyun_client.check_domain_exists(domain['name'])
    if domain_exists == False:
        aliyun_client.create_domain(domain['name'])


def ddns(aliyun_client, domain):
    record_type = 'AAAA' if domain.__contains__('ipv6') and domain['ipv6'] else 'A'
    if record_type == 'AAAA' and socket.has_dualstack_ipv6 == False:
        logging.error("Local machine does not have ipv6.")
        return
    
    ip = get_locat_ip(domain, record_type=='AAAA')
    logging.info(f"Local ip is {ip}")

    if ip is None or ip == '':
        return
    
    for sub_domain in domain['sub_domains']:
        record_value = aliyun_client.get_record_value(domain['name'], sub_domain, record_type)
        if record_value == 0:
            aliyun_client.add_record(domain['name'], sub_domain, record_type, ip)
        elif record_value == ip:
            logging.info(f"No need to update the {record_type} record of {sub_domain}.{domain['name']}")
        else:
            logging.info(f"Updating the {record_type} record of {sub_domain}.{domain['name']} to {ip}")
            record_id = aliyun_client.get_record_id(domain['name'], sub_domain, record_type)
            aliyun_client.record_ddns(record_id, sub_domain, record_type, ip)


def get_locat_ip(domain, ipv6=False):
    if ipv6:
        return get_ipv6()
    else:
        return get_ipv4()


def get_ipv4():
    global LocalIPV4
    if LocalIPV4.strip() == '':
        v4 = ipv4.IPV4()
        LocalIPV4 = v4.get_local_ip()
    return LocalIPV4


def get_ipv6():
    global LocalIPV6
    if LocalIPV6.strip() == '':
        v6 = ipv6.IPV6()
        LocalIPV6 = v6.get_local_ip()
    return LocalIPV6


if __name__ == '__main__':
    try:
        logger.setup_logging()
        conf = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "conf.json"), "r"))
        Domains = conf['domains']
        access_key = conf['access_key']
        access_secret = conf['access_secret']
        aliyun_client = aliyun.Aliyun(access_key, access_secret)
        for domain in Domains:
            init_domain(aliyun_client, domain)
            ddns(aliyun_client, domain)
    except Exception as e:
        logging.error(e)
        pass
