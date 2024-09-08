#!/usr/bin/python
# -*- coding: UTF-8 -*-

from urllib import request

from . import IPV4

class IPSB(IPV4):
    def get_ip():
        return request.urlopen('https://api-ipv4.ip.sb/ip').read().decode('utf-8')
