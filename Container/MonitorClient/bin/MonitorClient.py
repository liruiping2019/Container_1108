# coding:utf-8
#__author__ = ''

import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from MonitorClient.core import main

if __name__ == "__main__":
    client = main.command_handler(sys.argv)