#!/usr/bin/env python
'''
github : https://github.com/liangxiao1/tipset

This tool is for install pkg from pkg name or pkg's file(eg. cmd, *.h......).

'''

from __future__ import print_function
import logging
import argparse
import os
import re
from collections import OrderedDict
import subprocess

LOG = logging.getLogger(__name__)
LOG_FORMAT = "%(levelname)s:%(message)s"
ARG_PARSER = argparse.ArgumentParser(
    description="install required pkg from specify pkg name or pkg's file \
        eg. python pkgone --pkg_name virt-install\
            python pkgone --file_name virt-what")

def run_cmd(cmd,
            expect_ret=None,
            expect_not_ret=None,
            expect_kw=None,
            expect_not_kw=None,
            expect_output=None,
            msg=None,
            timeout=60,
            ret_status=False,
            is_log_output=True,
            cursor=None
            ):
    """run cmd with/without check return status/keywords and save log

    Arguments:
        cmd {string} -- cmd to run
        expect_ret {int} -- expected return status
        expect_not_ret {int} -- unexpected return status
        expect_kw {string} -- string expected in output,seperate by ',' if
                              check multi words
        expect_not_kw {string} -- string not expected in output, seperate by
                                  ',' if check multi words
        expect_output {string} -- string exactly the same as output
        msg {string} -- addtional info to mark cmd run.
        ret_status {bool} -- return ret code instead of output
        is_log_output {bool} -- print cmd output or not
        cursor {string} -- skip content before cursor(line)

    Keyword Arguments:
        check_ret {bool} -- [whether check return] (default: {False})
    """
    LOG.info("CMD: %s", cmd)
    status = None
    output = None
    exception_hit = False

    try:
        ret = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, encoding='utf-8')
        status = ret.returncode
        if ret.stdout is not None:
            output = ret.stdout
    except Exception as err:
        LOG.error("Run cmd failed as %s" % err)
        status = None
        exception_hit = True

    if exception_hit:
        LOG.info("Try again")
        LOG.info("Test via uname, if still fail, please make sure no hang or panic in sys")
        try:
            ret = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, encoding='utf-8')
            status = ret.returncode
            if ret.stdout is not None:
               output = ret.stdout
            LOG.info("Return: {}".format(output.decode("utf-8")))
            ret = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, encoding='utf-8')
            status = ret.returncode
            if ret.stdout is not None:
               output = ret.stdout
        except Exception as err:
            LOG.error("Run cmd failed again {}".format(err))
    if cursor is not None and cursor in output:
        output = output[output.index(cursor):]
    if is_log_output:
        LOG.info("CMD ret: {} out:{}".format(status, output))
    else:
        LOG.info("CMD ret: {}".format(status))
    if expect_ret is not None:
        if expect_ret != status:
            LOG.info("ret is %s, expected is %s" % (status, expect_ret))
    if expect_not_ret is not None:
        if expect_not_ret == status:
            LOG.info("ret is %s, expected not ret is %s" % (status, expect_not_ret))
    if expect_kw is not None:
        for key_word in expect_kw.split(','):
            if output.count('\n') > 5:
                find_list = re.findall('\n.*{}.*\n'.format(key_word), output)
            else:
                find_list = re.findall('.*{}.*'.format(key_word), output)
            if len(find_list) > 0:
                LOG.info('expcted "{}" found in "{}"'.format(key_word, ''.join(find_list)))
            else:
                if output.count('\n') > 5:
                    LOG.error('expcted "{}" not found in output(check debug log as too many lines)'.format(key_word))
                else:
                     LOG.error('expcted "{}" not found in "{}"'.format(key_word,output))
    if expect_not_kw is not None:
        for key_word in expect_not_kw.split(','):
            if output.count('\n') > 5:
                find_list = re.findall('\n.*{}.*\n'.format(key_word), output)
            else:
                find_list = re.findall('.*{}.*'.format(key_word), output)
            if len(find_list) == 0:
                LOG.info('Unexpcted "{}" not found in output'.format(key_word))
            else:
                if output.count('\n') > 5:
                     LOG.error('Unexpcted "{}" found in {}'.format(key_word, ''.join(find_list)))
                else:
                     LOG.error('Unexpcted "{}" found in "{}"'.format(key_word,output))
    if expect_output is not None:
        if expect_output != output:
            LOG.info("exactly expected %s" % (expect_output))
    if ret_status:
        return status
    return output

def is_pkg_installed(pkg_name=None, is_install=True, cancel_case=False):
    '''
    check cmd exists status, if no, try to install it.
    Arguments:
        cmd {string} -- checked command
        is_install {bool} -- try to install it or not
    '''
    cmd_check = "rpm -q {}".format(pkg_name)
    ret = run_cmd(cmd_check, ret_status=True)
    if ret == 0:
        LOG.info("{} already installed".format(pkg_name))
        return True
    else:
        LOG.info("No %s found!" % pkg_name)
        return False

def is_yum_support():
    '''
    check whether it is a yum or dnf supported system.
    '''
    cmd = "yum --help"
    ret = run_cmd(cmd, ret_status=True, is_log_output=True)
    if ret == 0:
        LOG.info("yum supported")
        return True
    else:
        LOG.info("yum not supported")
        return False

def get_file_belong(file_name=None):
    '''
    Try to find out the file belong to which pkg
    Arguments:
        file_name {string} -- file name

    Return:
        pkg_name {string} -- pkg name if find
    '''
    arch = run_cmd('uname -p').rstrip('\n')
    pkg_find = "sudo yum provides %s" % file_name
    output = run_cmd(pkg_find, expect_ret=0)
    for i in [arch, 'noarch']:
        pkg_list = re.findall(".*%s" % arch, output)
        if len(pkg_list) > 0:
            break
    if len(pkg_list) == 0:
        LOG.error("Unable to determain pkg name {}".format(file_name))
        return None
    return pkg_list[0]

def pkg_install(pkg_name=None, pkg_url=None, file_name=None):
        """
        Install pkg in target system from default repo or pkg_url.
        Arguments:
            pkg_name {string} -- pkg name
            pkg_url {string} -- pkg url if it is not in default repo
        """
        if pkg_name is not None:
            if not is_pkg_installed(pkg_name=pkg_name):
                LOG.info("Try install {} automatically!".format(pkg_name))
                LOG.info("Install {} from default repo".format(pkg_name))
                cmd = 'sudo yum -y install %s' % pkg_name
                run_cmd(cmd, timeout=1200)

        if pkg_url is not None:
            LOG.info("Install {} from {}".format(pkg_name, pkg_url))
            cmd = 'sudo yum -y install %s' % pkg_url
            run_cmd(cmd, timeout=1200)

        if file_name is not None:
            pkg_name = get_file_belong(file_name=file_name)
            if pkg_name is not None:
                LOG.info("Try install {} automatically!".format(pkg_name))
                LOG.info("Install {} from default repo".format(pkg_name))
                cmd = 'sudo yum -y install %s' % pkg_name
                run_cmd(cmd, timeout=1200)

def main():
    ARG_PARSER.add_argument('-d', dest='is_debug', action='store_true',
                            help='run in debug mode', required=False)
    ARG_PARSER.add_argument('--pkg_url', dest='pkg_url', action='store', default=None,
                            help='install pkg from url directly', required=False)
    ARG_PARSER.add_argument('--pkg_name', dest='pkg_name', action='store', default=None,
                            help='install pkg name from repo', required=False)
    ARG_PARSER.add_argument('--file_name', dest='file_name', action='store', default=None,
                            help='file name if you do not know it belong to which pkg',
                            required=False)

    ARGS = ARG_PARSER.parse_args()

    if ARGS.is_debug:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    if ARGS.pkg_name is None and ARGS.pkg_url is None and ARGS.file_name is None:
        LOG.info("None of pkg_url, pkg_name or file_name specified")
    else:
        pkg_install(ARGS.pkg_name, ARGS.pkg_url, ARGS.file_name)

if __name__ == '__main__':
    main()
