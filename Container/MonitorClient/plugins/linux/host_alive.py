# #!usr/bin/python
# # -*- coding: utf-8 -*-
#
# import commands
#
# def monitor(first_invoke=1):
#     value_dic = {}
#     shell_command = 'uptime'
#     result = commands.Popen(shell_command,shell=True,stdout=subprocess.PIPE).stdout.read()
#
#     value_dic = {
#         'uptime':result,
#         'status':0
#     }
#     return value_dic
#
# print monitor()