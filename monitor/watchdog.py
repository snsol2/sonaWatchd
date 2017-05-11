# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys
import resource
import cmd_proc
import requests
import base64
import json

from datetime import datetime
from subprocess import Popen
from subprocess import PIPE
from api.config import CONF
from api.sona_log import LOG
from api.watcherdb import DB
from api.sbapi import SshCommand

def periodic(conn):
    LOG.info("Periodic checking...%s", str(CONF.watchdog()['check_system']))

    try:
        node_list = cmd_proc.get_node_list('all', 'nodename, ip_addr, username')

        if not node_list:
            LOG.info("Not Exist Node data ...")
            return
    except:
        LOG.exception()
        return

    for node_name, node_ip, user_name in node_list:
        ping = net_check(node_ip)
        app = ''

        if ping == 'ok':
            if node_ip in str(CONF.onos()['list']):
                app = onos_app_check(node_ip)
            elif node_ip in str(CONF.xos()['list']):
                app = xos_app_check(node_ip)
            elif node_ip in str(CONF.swarm()['list']):
                app = swarm_app_check(node_ip)
            elif node_ip in str(CONF.openstack()['list']):
                app = openstack_app_check(node_ip)
        else:
            app = 'nok'

        try:
            sql = 'UPDATE ' + DB.NODE_INFO_TBL + \
                  ' SET cpu = ' + str(resource.get_cpu_usage(user_name, node_ip, True)) + ',' + \
                  ' mem = ' + str(resource.get_mem_usage(user_name, node_ip, True)) + ',' + \
                  ' disk = ' + str(resource.get_disk_usage(user_name, node_ip, True)) + ',' + \
                  ' ping = \'' + ping + '\'' + ',' + \
                  ' app = \'' + app + '\'' + ',' + \
                  ' time = \'' + str(datetime.now()) + '\'' + \
                  ' WHERE nodename = \'' + node_name + '\''
            LOG.info('Update Resource info = ' + sql)
            conn.cursor().execute(sql)
            conn.commit()
        except:
            LOG.exception()

    # occur event (rest)
    header = {'Content-Type': 'application/json', 'Authorization': base64.b64encode('admin:admin')}
    req_body = {'evt': 'test text'}
    req_body_json = json.dumps(req_body)

    url = 'http://localhost:8001/event'

    try:
        requests.post(url, headers=header, data=req_body_json, timeout = 2)
    except:
        # rest timeout
        LOG.exception()


def net_check(node):
    if CONF.watchdog()['method'] == 'ping':
        timeout = CONF.watchdog()['timeout']
        if sys.platform == 'darwin':
            timeout = timeout * 1000

        cmd = 'ping -c1 -W%d -n %s' % (timeout, node)

        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("\'%s\' Network Check Error(%d) ", node, result.returncode)
            return 'nok'
        else:
            return 'ok'


def onos_app_check(node):

    app_rt = SshCommand.onos_ssh_exec(node, 'apps -a -s')

    app_active_list = list()
    if app_rt is not None:
        for line in app_rt.splitlines():
            app_active_list.append(line.split(".")[2].split()[0])
        if set(CONF.onos()['app_list']).issubset(app_active_list):
            return 'ok'
        else:
            LOG.error("\'%s\' Application Check Error", node)
            return 'nok'
    else:
        LOG.error("\'%s\' Application Check Error", node)
        return 'nok'


# TODO xos app check
def xos_app_check(node):
    return 'nok'


# TODO swarm app check
def swarm_app_check(node):
    return 'nok'


# TODO openstack app check
def openstack_app_check(node):
    return 'nok'


