import sys
import os
import datetime

class minilog():
    """simple and diy self log module
    especillay when run in parallel
    """
    def __init__(self):
        self.logfile = sys.stdout
        self.show_level = True
        self.show_time = True
        self.show_debug = False

    def write_msg(self, level, msg=''):
        if self.show_level:
            msg = level + ':' + str(msg)
        if self.show_time:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            msg = str(timestamp) + ' ' + str(msg)
        if not self.show_debug and 'DEBUG' in level:
            return None
        if isinstance(self.logfile,str):
            with open(self.logfile, 'a+') as fh:
                print(msg, file=fh)
        else:
            print(msg, file=self.logfile)

    def info(self, msg=''):
        self.write_msg('INFO', msg=msg)

    def error(self, msg=''):
        self.write_msg('ERROR', msg=msg)

    def debug(self, msg=''):
        self.write_msg('DEBUG', msg=msg)
    
    def get_logger(self):
        pass