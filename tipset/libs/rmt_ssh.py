# Because of paramiko lack of rsa-sha2-256 and rsa-sha2-512 algorithms support(https://github.com/paramiko/paramiko/pull/1643)
# It is a problem for comming usage of it.
# TODO:
# - move ssh part to pexpect which is a wrapper of ssh cmd, ssh works, my module works.

try:
    import paramiko
except ImportError as error:
    print("Please install paramiko to use this module")

import logging
import time
import sys
import os
from . import minilog

def build_connection(rmt_node=None, rmt_user='ec2-user', rmt_password=None, rmt_keyfile=None, timeout=180, log=None):
    if log == None:
        log = minilog.minilog()
    log.info("Try to make connection: {}@{}".format(rmt_user, rmt_node))
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    #ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy())
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    start_time = time.time()
    while True:
        try:
            end_time = time.time()
            if end_time-start_time > timeout:
                log.info("Unable to make connection!")
                return None
            if rmt_keyfile is None and rmt_password is None:
                log.info("no password or keyfile for ssh access")
                ssh_client.load_system_host_keys()
                ssh_client.connect(rmt_node, username=rmt_user)
            if rmt_password is not None and rmt_password != 'None':
                log.info("login system using password")
                ssh_client.connect(
                    rmt_node,
                    username=rmt_user,
                    password=rmt_password,
                    look_for_keys=False,
                    timeout=60
                )
            else:
                log.info("login system using keyfile")
                if not os.path.exists(rmt_keyfile):
                    log.error("{} not found".format(rmt_keyfile))
                    return None
                ssh_client.connect(
                    rmt_node,
                    username=rmt_user,
                    key_filename=rmt_keyfile,
                    look_for_keys=False,
                    timeout=60
                )
            log.info("connected!")
            return ssh_client
        except Exception as e:
            log.info("*** Failed to connect to {}: {}".format(rmt_node, e))   
            log.info("Retry again, timeout {}!".format(timeout))
            time.sleep(10)
    return None

def cli_run(ssh_client, cmd,timeout,rmt_get_pty=False, log=None):
    if log == None:
        log = minilog.minilog()
    stdin, stdout, stderr = ssh_client.exec_command(
                            cmd, timeout=timeout, get_pty=rmt_get_pty)
                            #cmd, timeout=timeout, get_pty=True)
    start_time = time.time()
    while not stdout.channel.exit_status_ready():
        current_time = time.time()
        if current_time - start_time > timeout:
            log.info('Timeout to run cmd {}s'.format(timeout))
            stdout.channel.close()
            break
    while not stdout.channel.exit_status_ready() and stdout.channel.recv_exit_status():
        time.sleep(1)
        log.info("Wait command complete......")
    output = ''.join(stdout.readlines())
    errlog = ''.join(stderr.readlines())
    ret = stdout.channel.recv_exit_status()
    return ret, output, errlog

def remote_excute(ssh_client, cmd,timeout, redirect_stdout=False, redirect_stderr=False, rmt_get_pty=False, log=None):
    if log == None:
        log = minilog.minilog()
    if redirect_stdout or redirect_stderr:
        cmd = cmd + " 1>/tmp/cmd.out 2>/tmp/cmd.err"
    log.info("Run on remote: {}".format(cmd))
    
    status, output, errlog = cli_run(ssh_client, cmd, timeout, rmt_get_pty=rmt_get_pty)
    if redirect_stdout or redirect_stderr:
        _, output, _ = cli_run(ssh_client, 'cat /tmp/cmd.out', timeout, rmt_get_pty=rmt_get_pty)
        _, _, errlog = cli_run(ssh_client, 'cat /tmp/cmd.err', timeout, rmt_get_pty=rmt_get_pty)
    if len(errlog) > 2:
        log.info("cmd err: {}".format(errlog))
    return status, output
