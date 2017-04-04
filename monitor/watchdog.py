# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import sys
import time

from datetime import datetime

from subprocess import Popen
from subprocess import PIPE
from api.config import CONF
from api.sona_log import LOG
from api.watcherdb import DB
from api.sbapi import SshCommand


def periodic():
    LOG.info("Periodic checking...%s", str(CONF.watchdog()['check_system']))
    node_list = list()
    for node in CONF.watchdog()['check_system']:
        if str(node).lower() == 'onos':
            node_list += CONF.onos()['list']
        elif str(node).lower() == 'xos':
            node_list += CONF.xos()['list']
        elif str(node).lower() == 'k8s':
            node_list += CONF.k8s()['list']
        elif str(node).lower() == 'openstack':
            node_list += CONF.openstack_node()['list']

    result = dict()

    for node in node_list:
        node_name, node_ip = str(node).split(':')
        result[node_name] = [{'IP': net_check(node_ip)},
                             {'APP': onos_app_check(node_ip)}]

    try:
        with DB.connection() as conn:
            sql = "INSERT OR REPLACE INTO t_status VALUES (?, ?, ?)"
            conn.cursor().execute(sql, ('periodic', str(datetime.now()), str(result)))
            conn.commit()
    except:
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
            return 'nok'
    else:
        print 'nok'

    print app_active_list

