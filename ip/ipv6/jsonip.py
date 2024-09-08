#!/usr/bin/python
# -*- coding: UTF-8 -*-

import json
from urllib import request

from . import IPV6

class JsonIp(IPV6):
    @staticmethod
    def get_ip():
        return json.loads(request.urlopen('http://jsonip.com').read().decode('utf-8'))['ip']
