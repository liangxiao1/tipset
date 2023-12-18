# Because of paramiko lack of rsa-sha2-256 and rsa-sha2-512 algorithms support(https://github.com/paramiko/paramiko/pull/1643)
# It is a problem for comming usage of it.
# TODO:
# - move ssh part to pexpect which is a wrapper of ssh cmd, ssh works, my module works.

try:
    import paramiko
    from paramiko import BadHostKeyException
except ImportError as error:
    print("Please install paramiko if do remote access")

import logging
import time
import sys
import os
from . import minilog
import threading
import select
import argparse
import socket

def sig_handler(signum, frame):
    logging.info('Got signal %s, exit!', signum)
    sys.exit(0)


def handler(chan, host, port):
    sock = socket.socket()
    try:
        sock.connect((host, port))
    except Exception as e:
        logging.info("Forwarding request to %s:%d failed: %r" % 
                  (host, port, e))
        return

    logging.info(
        "Connected!  Tunnel open %r -> %r -> %r"
        % (chan.origin_addr, chan.getpeername(), (host, port))
    )
    retry_count = 0
    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if len(data) == 0:
                retry_count+=1
                if retry_count>100:
                    logging.info("No data received from sock")
                    break
            else:
                chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if len(data) == 0:
                if retry_count>100:
                    logging.info("No data received from chan")
                    break
            else:
                sock.send(data)
    chan.close()
    sock.close()
    logging.info("Tunnel closed from %r" % (chan.origin_addr,))
 
 
def reverse_forward_tunnel(server_port, remote_host, remote_port, transport):
    transport.request_port_forward("", server_port)

    while True:
        chan = transport.accept(1000)
        if chan is None:
            continue
        thr = threading.Thread(
            target=handler, args=(chan, remote_host, remote_port)
        )
        thr.setDaemon(True)
        thr.start()

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
        self.ssh_client = None
        self.rmt_node = None
        self.port = 22
        self.rmt_user = None
        self.rmt_password = None
        self.rmt_keyfile = None
        self.rmt_proxy = None 
        self.timeout = 180
        self.interval = 10
        self.log = None

    def create_connection(self):
        self.ssh_client = build_connection(rmt_node=self.rmt_node, port=self.port, rmt_user=self.rmt_user,
                rmt_password=self.rmt_password, rmt_keyfile=self.rmt_keyfile, rmt_proxy=self.rmt_proxy, timeout=self.timeout, interval=self.interval, log=self.log)

    def cli_run(self, cmd=None, timeout=180, rmt_get_pty=False):
        return cli_run(self.ssh_client, cmd, timeout, rmt_get_pty=rmt_get_pty, log=self.log)

    def remote_excute(self, cmd, timeout=180, is_log_cmd=True, redirect_stdout=False, redirect_stderr=False, rmt_get_pty=False):
        return remote_excute(self.ssh_client, cmd, timeout, is_log_cmd, redirect_stdout=redirect_stdout, redirect_stderr=redirect_stderr, rmt_get_pty=rmt_get_pty, log=self.log)

    def put_file(self, local_file = None, rmt_file = None):
        if self.log is None:
            self.log = minilog.minilog()
        if isinstance(self.log, logging.Logger):
            logging.getLogger("paramiko").setLevel(logging.INFO)
        if os.path.isdir(local_file):
            self.log.info("{} is dir, only file supported now.".format(local_file))
            return False
        self.log.info('sending {} from local to remote {}'.format(local_file,rmt_file))
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
        self.log.info('retriving {} from remote to local {}'.format(rmt_file,local_file))
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

    def close(self):
        if self.ssh_client is not None:
            self.ssh_client.close()

    def is_active(self):
        if not self.ssh_client:
            self.log.info("connection is not active")
            return False
        ssh_transport = self.ssh_client.get_transport()
        if not ssh_transport.is_active():
            self.log.info("connection is not active from transport")
            return False
        if ssh_transport.in_kex:
            self.log.info("connection is in negotiate keys, considering it as not active")
            return False
        try:
            ssh_transport.send_ignore()
        except EOFError as e:
            # connection is closed
            self.log.info("connection is not active because send_ignore fail")
            return False
        ret, _, _ = self.cli_run(cmd='uname -r')
        if ret != 0:
            self.log.info("connection is not active via sending cmd")
            return False
        self.log.info("connection is active")
        return True

def build_connection(rmt_node=None, port=22, rmt_user='ec2-user', rmt_password=None, rmt_keyfile=None, rmt_proxy=None, timeout=180, interval=10, log=None):
    if log is None:
        log = minilog.minilog()
    if isinstance(log, logging.Logger):
        logging.getLogger("paramiko").setLevel(logging.INFO)
    log.info("Try to make connection {}@{}:{}".format(rmt_user, rmt_node, port))
    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    #ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy())
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    start_time = time.time()
    while True:
        badhostkey = False
        try:
            end_time = time.time()
            if end_time-start_time > timeout:
                log.info("timeout({}s) to make connection!".format(timeout))
                return None
            if rmt_keyfile is None and rmt_password is None:
                log.info("no password or keyfile for ssh access, use default ssh key setting")
                ssh_client.load_system_host_keys()
                ssh_client.connect(rmt_node, port=port, username=rmt_user)
            elif rmt_password is not None:
                log.info("login system using password")
                ssh_client.connect(
                    rmt_node,
                    port=port,
                    username=rmt_user,
                    password=rmt_password,
                    look_for_keys=False,
                    timeout=60
                )
            else:
                log.info("login system using keyfile:{}".format(rmt_keyfile))
                if not os.path.exists(rmt_keyfile):
                    log.error("{} not found".format(rmt_keyfile))
                    return None
                exception_list=[]
                pkey_RSAKey = paramiko.RSAKey.from_private_key_file(rmt_keyfile)
                try:
                    log.info("Try to use {}".format(pkey_RSAKey.get_name()))
                    ssh_client.connect(
                        rmt_node,
                        port=port,
                        username=rmt_user,
                        #key_filename=rmt_keyfile,
                        pkey=pkey_RSAKey,
                        look_for_keys=False,
                        timeout=60
                    )
                    if rmt_proxy is not None:
                        log.info(
                            "Now forwarding remote port 8080 to %s ..."
                            % (rmt_proxy))
                        try:
                            th_reverse = threading.Thread(target=reverse_forward_tunnel, args=(
                                8080, rmt_proxy.split(':')[0], int(rmt_proxy.split(':')[
                                    1]),ssh_client.get_transport()))
                            th_reverse.setDaemon(True)
                            th_reverse.start()
                        except KeyboardInterrupt:
                            print("C-c: Port forwarding stopped.")
                    return ssh_client
                except BadHostKeyException as e:
                    badhostkey = True
                    exception_list.append(e)
                except Exception as e:
                    exception_list.append(e)         
                raise Exception(exception_list)
            return ssh_client
        except Exception as e:
            log.info("*** Failed to connect to {}: {}".format(rmt_node, e))
            if 'Name or service not known' in str(e):
                break
            log.info("Retry again, timeout {}!".format(timeout))
            time.sleep(interval)
            if 'does not match' in str(e) or badhostkey:
                try:
                    know_hosts = paramiko.hostkeys.HostKeys(filename=os.path.expanduser("~/.ssh/known_hosts"))
                    know_hosts.lookup(rmt_node)
                    log.info("try to remove {} from known_hosts".format(rmt_node))
                    know_hosts.pop(rmt_node)
                    know_hosts.save(os.path.expanduser("~/.ssh/known_hosts"))
                    ssh_client = paramiko.SSHClient()
                    ssh_client.load_system_host_keys()
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                except Exception as e:
                    log.info('exception while cleaning known_hosts: {}'.format(e))
    return None

def cli_run(ssh_client, cmd,timeout,rmt_get_pty=False, log=None):
    if log is None:
        log = minilog.minilog()
    stdin, stdout, stderr = ssh_client.exec_command(
                            cmd, timeout=timeout, get_pty=rmt_get_pty)
                            #cmd, timeout=timeout, get_pty=True)
    start_time = time.time()
    is_health = True
    while not stdout.channel.exit_status_ready():
        current_time = time.time()
        if current_time - start_time > timeout:
            log.info('Timeout to run cmd {}s'.format(timeout))
            stdout.channel.close()
            break
        ssh_transport = ssh_client.get_transport()
        if not ssh_transport.is_active():
            log.info("connection is not active")
            is_health = False
            break
        else:
            try:
                ssh_transport.send_ignore()
            except EOFError as e:
                # connection is closed
                is_health = False
                break
    while not stdout.channel.exit_status_ready() and stdout.channel.recv_exit_status():
        if not is_health:
            break
        time.sleep(1)
        log.info("Wait command complete......")
    output = ''.join(stdout.readlines())
    errlog = ''.join(stderr.readlines())
    ret = stdout.channel.recv_exit_status()
    return ret, output, errlog

def remote_excute(ssh_client, cmd,timeout, is_log_cmd=True, redirect_stdout=False, redirect_stderr=False, rmt_get_pty=False, log=None):
    if log is None:
        log = minilog.minilog()
    if redirect_stdout or redirect_stderr:
        cmd = cmd + " 1>/tmp/cmd.out 2>/tmp/cmd.err"
    if is_log_cmd:
        log.info("Run on remote: {}".format(cmd))
         
    status, output, errlog = cli_run(ssh_client, cmd, timeout, rmt_get_pty=rmt_get_pty, log=log)
    if redirect_stdout or redirect_stderr:
        _, output, _ = cli_run(ssh_client, 'cat /tmp/cmd.out', timeout, rmt_get_pty=rmt_get_pty, log=log)
        _, _, errlog = cli_run(ssh_client, 'cat /tmp/cmd.err', timeout, rmt_get_pty=rmt_get_pty, log=log)
    if len(errlog) > 2:
        log.info("cmd err: {}".format(errlog))
    return status, output + errlog
