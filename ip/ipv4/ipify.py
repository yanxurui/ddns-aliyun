#!/usr/bin/python
# -*- coding: UTF-8 -*-

import json
from urllib import request

from . import IPV4

class IPIFY(IPV4):
    def get_ip():
        return json.loads(request.urlopen('https://api.ipify.org/?format=json').read().decode('utf-8'))['ip']
