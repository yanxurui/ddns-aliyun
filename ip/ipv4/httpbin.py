#!/usr/bin/python
# -*- coding: UTF-8 -*-

import json
from urllib import request

from . import IPV4

class Httpbin(IPV4):
    def get_ip():
        return json.loads(request.urlopen('http://httpbin.org/ip').read().decode('utf-8'))['origin']
