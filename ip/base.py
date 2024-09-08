#!/usr/bin/python
# -*- coding: UTF-8 -*-

import logging
import pkgutil
import importlib
import os

from collections import defaultdict

class IP(object):
    @classmethod
    def get_local_ip(cls):
        if cls.__subclasses__().__len__() == 0:
            logging.info(f"No functions are registered for {cls.__name__}")
            return

        ipDict = defaultdict(int)
        for sub in cls.__subclasses__():
            try:
                ip = sub.get_ip()
                if ip:
                    ipDict[ip.strip()] += 1
            except Exception as e:
                logging.exception(e)

        if ipDict.__len__() == 0:
            logging.info(f"Local machine has no {cls.__name__}.")
            return
        LocalIP = sorted(ipDict.items(), key=lambda d:d[1], reverse = True)[0][0]
        return LocalIP

    @staticmethod
    def get_ip():
        '''Need to be override by sub classes'''
        pass

def import_all_modules(file, name):
    # Current directory
    current_dir = os.path.dirname(file)

    # Iterate over modules in the current directory
    for _, module_name, _ in pkgutil.iter_modules([current_dir]):
        if module_name != '__init__':
            full_module_name = f"{name}.{module_name}"
            importlib.import_module(full_module_name)

