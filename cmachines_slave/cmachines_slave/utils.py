# -*- coding: utf-8 -*-
import subprocess
import sys, traceback
import json
import os
from subprocess import CalledProcessError


def get_default_settings():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    default_settings_path = os.path.join(dir_path, "../config/crontab_update_machines.json")
    default_settings = json.load(open(default_settings_path, "r"))
    return default_settings

def exe_cmd_on_local(cmd, ret_msg=False):
    if isinstance(cmd, basestring):
        cmd = cmd.split(" ")
    if ret_msg:
        try:
            out = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                )
            return 0, out
        except CalledProcessError as exc:
            #print "Exception in user code:"
            #print '-'*60
            #var = traceback.format_exc()
            #traceback.print_exc(file=sys.stdout)
            #print '-'*60
            #print exc.output
            return exc.returncode, exc.output
    else:
        ret = subprocess.call(cmd)
        return ret

def exe_cmd_on_remote(remote_login, remote_host, cmd, ret_msg=False):
    new_cmd = ["ssh", "%s@%s" % (remote_login, remote_host), cmd]
    ret = exe_cmd_on_local(new_cmd, ret_msg)
    return ret

def make_port_mapping_from_remote_to_local_port(remote_login, remote_host,
                                                your_sshd_port, forwarding_port,
                                                bridge_password,
                                                local_server_port, ):
    '''
    see https://github.com/JinpengLI/docker-image-reverse-ssh-tunnel
    '''
    data = {}
    data["remote_login"] = remote_login
    data["remote_host"] = remote_host
    data["your_sshd_port"] = your_sshd_port
    data["forwarding_port"] = forwarding_port
    data["bridge_password"] = bridge_password
    data["local_server_port"] = local_server_port

    ## public server configuration
    cmd = "docker run -d -e ROOT_PASS=%(bridge_password)s -p %(your_sshd_port)d:22 -p %(forwarding_port)d:1080 jinpengli/docker-image-reverse-ssh-tunnel"
    cmd = cmd % data
    print("cmd ", cmd)
    ret = exe_cmd_on_remote(remote_login, remote_host, cmd)
    if ret != 0:
        print("fail to start docker on remote machine %s" % remote_host)
        return ret
    cmd = "docker run -d -e PUBLIC_HOST_ADDR=%(remote_host)s -e PUBLIC_HOST_PORT=%(your_sshd_port)d -e ROOT_PASS=%(bridge_password)s -e PROXY_PORT=%(local_server_port)d --net=host jinpengli/docker-image-reverse-ssh-tunnel"
    cmd = cmd % data
    print("cmd ", cmd)
    ret = exe_cmd_on_local(cmd)
    if ret != 0:
        print("fail to start docker on local machine " )
        return ret
    return 0
