# Because of paramiko lack of rsa-sha2-256 and rsa-sha2-512 algorithms support(https://github.com/paramiko/paramiko/pull/1643)
# It is a problem for comming usage of it.
# TODO:
# - move ssh part to pexpect which is a wrapper of ssh cmd, ssh works, my module works.

try:
    import paramiko
except ImportError as error:
    print("Please install paramiko-fork if do remote access")

import logging
import time
import sys
import os
from . import minilog


class RemoteSSH():
    """
    quick example:
    from tipset.libs import rmt_ssh
    X = rmt_ssh.RemoteSSH()
    X.rmt_node = 'xxxxxx'
    X.rmt_user = 'xxxxxx'
    X.rmt_password = 'xxxxxx'
    X.create_connection()
    ret, out, err = X.cli_run(cmd='uname -r')
    print(out)
    X.put_file(local_file='/tmp/test.log',rmt_file='/root/test.log')
    X.get_file(rmt_file='/root/test.log',local_file='/tmp/1/me')
    """
    def __init__(self):
        self.rmt_node=None
        self.rmt_user=None
        self.rmt_password=None
        self.rmt_keyfile=None
        self.timeout=180
        self.log=None

    def create_connection(self):
        self.ssh_client = build_connection(rmt_node=self.rmt_node, rmt_user=self.rmt_user,
                rmt_password=self.rmt_password, rmt_keyfile=self.rmt_keyfile, timeout=self.timeout, log=self.log)

    def cli_run(self, cmd=None, timeout=180, rmt_get_pty=False):
        return cli_run(self.ssh_client, cmd, timeout, rmt_get_pty=rmt_get_pty, log=self.log)

    def remote_excute(self, cmd, timeout=180, redirect_stdout=False, redirect_stderr=False, rmt_get_pty=False):
        return remote_excute(self.ssh_client, cmd, timeout, redirect_stdout=redirect_stdout, redirect_stderr=redirect_stderr, rmt_get_pty=rmt_get_pty, log=self.log)

    def put_file(self, local_file = None, rmt_file = None):
        if self.log is None:
            self.log = minilog.minilog()
        if isinstance(self.log, logging.Logger):
            logging.getLogger("paramiko").setLevel(logging.INFO)
        if os.path.isdir(local_file):
            self.log.info("{} is dir, only file supported now.".format(local_file))
            return False
        if not os.path.exists(local_file):
            self.log.info('{} not found'.format(local_file))
            return False
        self.ftp_client = self.ssh_client.open_sftp()
        try:
            self.ftp_client.put(local_file, rmt_file)
        except FileNotFoundError:
            self.log.info('{} must be a filename or not found on remote'.format(rmt_file))
            return False
        self.ftp_client.close()
        return True

    def get_file(self, rmt_file = None, local_file = None):
        if self.log is None:
            self.log = minilog.minilog()
        if isinstance(self.log, logging.Logger):
            logging.getLogger("paramiko").setLevel(logging.INFO)
        if os.path.isdir(local_file):
            self.log.info("{} is dir, only file supported now.".format(local_file))
            return False
        self.ftp_client = self.ssh_client.open_sftp()
        try:
            self.ftp_client.get(rmt_file,local_file)
        except FileNotFoundError:
            self.log.info('{} must be a filename or not found on remote'.format(rmt_file))
            return False
        self.ftp_client.close()
        return True

def build_connection(rmt_node=None, rmt_user='ec2-user', rmt_password=None, rmt_keyfile=None, timeout=180, log=None):
    if log is None:
        log = minilog.minilog()
    if isinstance(log, logging.Logger):
        logging.getLogger("paramiko").setLevel(logging.INFO)
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
            if rmt_password is not None:
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
                exception_list=[]
                pkey_RSAKey = paramiko.RSAKey.from_private_key_file(rmt_keyfile)
                pkey_RSASHA256Key = paramiko.RSASHA256Key.from_private_key_file(rmt_keyfile)
                pkey_RSASHA512Key = paramiko.RSASHA512Key.from_private_key_file(rmt_keyfile)
                for pkey in [pkey_RSAKey, pkey_RSASHA256Key, pkey_RSASHA512Key]:
                    try:
                        log.info("Try to use {}".format(pkey.get_name()))
                        ssh_client.connect(
                            rmt_node,
                            username=rmt_user,
                            #key_filename=rmt_keyfile,
                            pkey=pkey,
                            look_for_keys=False,
                            timeout=60
                        )
                        return ssh_client
                    except Exception as e:
                        exception_list.append(e)
                raise Exception(exception_list)
            return ssh_client
        except Exception as e:
            log.info("*** Failed to connect to {}: {}".format(rmt_node, e))   
            log.info("Retry again, timeout {}!".format(timeout))
            time.sleep(10)
    return None

def cli_run(ssh_client, cmd,timeout,rmt_get_pty=False, log=None):
    if log is None:
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
    if log is None:
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
    return status, output + errlog
