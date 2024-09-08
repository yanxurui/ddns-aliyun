#!/usr/bin/python
# -*- coding: UTF-8 -*-

import json
from urllib import request

from . import IPV4

class IpApi(IPV4):
    def get_ip():
        return json.loads(request.urlopen('http://ip-api.com/json').read().decode('utf-8'))['query']
