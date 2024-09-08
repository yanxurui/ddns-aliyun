#!/usr/bin/python
# -*- coding: UTF-8 -*-
from urllib import request

from . import IPV6

class IPSB(IPV6):
    @staticmethod
    def get_ip():
        return request.urlopen('https://api-ipv6.ip.sb/ip').read().decode('utf-8')
