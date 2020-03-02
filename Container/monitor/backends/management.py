#_*_coding:utf-8_*_
import os,sys
import django
django.setup()
from monitor.backends import data_processing,trigger_handler
from Container import settings

class ManagementUtility(object):
    def __init__(self,argv=None):
        self.argv = argv or sys.argv[:]
        self.prog_name = os.path.basename(self.argv[0])
        self.settings_exception = None
        self.registered_actions = {
            'start':self.start,
            'stop':self.stop,
            'trigger_watch':self.trigger_watch,
        }
        self.argv_check()

    def argv_check(self):
        if len(self.argv) < 2:
            self.main_help_text()
        if self.argv[1] not in self.registered_actions:
            self.main_help_text()
        else:
            self.registered_actions[sys.argv[1]]()

    def start(self):
        '''start to listen triggers，检测主机和服务是否正常运行'''
        reactor = data_processing.DataHandler(settings)
        reactor.looping()

    def stop(self):
        '''stop monitor server'''

    def trigger_watch(self):
        '''start monitor server frontend and backend'''
        trigger_watch = trigger_handler.TriggerHandler(settings)
        trigger_watch.start_watching()

    def main_help_text(self,commands_only=False):
        if not commands_only:
            print("supported commands as flow:")
            for k,v in self.registered_actions.items():
                print("     %s%s" % (k.ljust(20),v.__doc__))
            exit()

    def excute(self):
        '''
        run according to user's input
        :return:
        '''

def execute_from_command_line(argv=None):

    utility = ManagementUtility(argv)
    utility.execute()
