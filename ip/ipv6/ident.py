#!/usr/bin/python
# -*- coding: UTF-8 -*-
from urllib import request

from . import IPV6

class Ident(IPV6):
    @staticmethod
    def get_ip():
        return request.urlopen('https://v6.ident.me').read().decode('utf-8')
