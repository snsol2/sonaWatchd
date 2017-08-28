import json
from datetime import datetime

from api.sbapi import SshCommand
from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF

def parse_command(req_obj):
    try:
        res_body = dict()
        res_body['command'] = req_obj['command']
        res_body['system'] = req_obj['system']

        try:
            res_body['param'] = req_obj['param']
        except:
            res_body['param'] = ''
            req_obj['param'] = ''

        ret = COMMAND_MAP[req_obj['command']](req_obj['system'], req_obj['param'])
        res_body['result'] = ret
        res_body['time'] = str(datetime.now())

        return res_body
    except:
        LOG.exception()
        return {'Result': 'FAIL'}

def regi_url(url, auth):
    try:
        sql = 'SELECT * FROM ' + DB.REGI_SYS_TBL + ' WHERE url = \'' + url + '\''

        with DB.connection() as conn:
            url_info = conn.cursor().execute(sql).fetchall()
        conn.close()

        # if already exist
        if len(url_info) == 1:
            res_body = {'Result': 'SUCCESS'}
        else:
            # insert db
            sql = 'INSERT INTO ' + DB.REGI_SYS_TBL + ' VALUES (\'' + url  + '\', \'' + auth + '\' )'

            ret = DB.sql_execute(sql)

            if ret == 'SUCCESS':
                res_body = {'Result': 'SUCCESS'}
            else:
                res_body = {'Result': 'FAIL'}

        return res_body
    except:
        LOG.exception()
        return {'Result': 'FAIL'}

def get_event_list(url, auth):
    try:
        sql_evt = 'SELECT * FROM ' + DB.EVENT_TBL

        with DB.connection() as conn:
            evt_list = conn.cursor().execute(sql_evt).fetchall()
        conn.close()

        event_list = []

        for nodename, item, grade, pre_grade, reason, time in evt_list:
            evt = {'event': 'occur', 'system': nodename, 'item': item, 'grade': grade, 'pre_grade': pre_grade, 'reason': 'fail_reason', 'time': time}
            event_list.append(evt)

            res_body = {'Result': 'SUCCESS', 'Event list': event_list}

        return res_body
    except:
        LOG.exception()
        return {'Result': 'FAIL'}

def unregi_url(url):
    try:
        sql = 'SELECT * FROM ' + DB.REGI_SYS_TBL + ' WHERE url = \'' + url + '\''

        with DB.connection() as conn:
            url_info = conn.cursor().execute(sql).fetchall()

        conn.close()

        # if no exist
        if len(url_info) == 0:
            res_body = {'Result': 'SUCCESS'}
        else:
            # delete db
            sql = 'DELETE FROM ' + DB.REGI_SYS_TBL + ' WHERE url = \'' + url + '\''

            ret = DB.sql_execute(sql)

            if ret == 'SUCCESS':
                res_body = {'Result': 'SUCCESS'}
            else:
                res_body = {'Result': 'FAIL'}

        return res_body
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_system(node, dummy):
    try:
        result = dict()

        for sys_type in CONF.watchdog()['check_system']:
            event_list = DB.get_event_list(sys_type)

            sql = 'SELECT ' + DB.STATUS_TBL + '.nodename, ' + DB.NODE_INFO_TBL + '.ip_addr, ' + ", ".join(event_list) + ' FROM ' + DB.STATUS_TBL + \
                  ' INNER JOIN ' + DB.NODE_INFO_TBL + ' ON ' + DB.STATUS_TBL + '.nodename = ' + DB.NODE_INFO_TBL + '.nodename WHERE type = \'' + sys_type + '\''

            if not node == 'all':
                sql = sql + ' and ' + DB.NODE_INFO_TBL + '.nodename = \'' + node + '\''

            with DB.connection() as conn:
                nodes_info = conn.cursor().execute(sql).fetchall()
            conn.close()

            for row in nodes_info:
                line = dict()
                line['TYPE'] = sys_type
                line['IP'] = row[1]
                i = 2
                for item in event_list:
                    line[item] = row[i]
                    i = i + 1

                result[row[0]] = line

        return result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_resource(node, param):
    try:
        nodes_info = get_node_list(node, 'nodename, ' + param, DB.RESOURCE_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, value in nodes_info:
            if value < 0:
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = value

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_onos(node, param):
    try:
        if param == 'app':
            nodes_info = get_node_list(node, 'nodename, applist', DB.ONOS_TBL)

        if param == 'rest':
            nodes_info = get_node_list(node, 'nodename, weblist', DB.ONOS_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, app_rest_list in nodes_info:
            if app_rest_list == 'fail' or app_rest_list == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(app_rest_list)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_log(node, param):
    cmd = 'ld'

    try:
        if param == 'debug':
            cmd = 'ld -l DEBUG'
        elif param == 'info':
            cmd = 'ld -l INFO'
        elif param == 'error':
            cmd = 'ld -l ERROR'
        elif param == 'exception':
            cmd = 'log:exception-display'

        nodes_info = get_node_list(node, 'nodename, ip_addr, type')

        res_result = dict()
        for node_name, ip, type in nodes_info:
            if type.upper() == 'ONOS':
                log_crt = SshCommand.onos_ssh_exec(ip, cmd)

                if log_crt is not None:
                    res_result[node_name] = log_crt
                else:
                    res_result[node_name] = 'FAIL'

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_vrouter(node, param):
    try:
        nodes_info = get_node_list(node, 'nodename, ' + param, DB.OPENSTACK_TBL, 'sub_type = \'GATEWAY\'')

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, list in nodes_info:
            if list == 'fail' or list == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(list)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_gwratio(node, dummy):
    try:
        nodes_info = get_node_list(node, 'nodename, gw_ratio', DB.OPENSTACK_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, ratio in nodes_info:
            if list == 'fail' or ratio == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(ratio)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_traffic_vxlan(node, dummy):
    try:
        nodes_info = get_node_list(node, 'nodename, vxlan_traffic', DB.OPENSTACK_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, ratio in nodes_info:
            if list == 'fail' or ratio == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(ratio)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_traffic_internal(node, dummy):
    try:
        nodes_info = get_node_list(node, 'nodename, internal_traffic', DB.OPENSTACK_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, ratio in nodes_info:
            if list == 'fail' or ratio == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(ratio)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_traffic_controller(node, dummy):
    try:
        nodes_info = get_node_list(node, 'nodename, traffic_stat', DB.ONOS_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, stat in nodes_info:
            if list == 'fail' or stat == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(stat)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_swarm(node, param):
    try:
        nodes_info = get_node_list(node, 'nodename, ' + param, DB.SWARM_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, list in nodes_info:
            if list == 'fail' or list == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(list)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_xos(node, param):
    try:
        nodes_info = get_node_list(node, 'nodename, xos_status', DB.XOS_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, xos_list in nodes_info:
            if xos_list == 'fail' or xos_list == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(xos_list)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_swarm_sync(node, param):
    try:
        nodes_info = get_node_list(node, 'nodename, synchronizer', DB.XOS_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, xos_list in nodes_info:
            if xos_list == 'fail' or xos_list == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(xos_list)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_ha(dummy, param):
    try:
        sql = 'SELECT stats FROM ' + DB.HA_TBL + ' WHERE ha_key = \'HA\''

        with DB.connection() as conn:
            nodes_info = conn.cursor().execute(sql).fetchone()
        conn.close()

        for value in nodes_info:
            return json.loads(str(value).replace('\'', '\"'))

        return {'HA': 'FAIL'}
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_node(node, param):
    try:
        if param == 'list':
            nodes_info = get_node_list(node, 'nodename, nodelist', DB.ONOS_TBL)
        elif param == 'port':
            nodes_info = get_node_list(node, 'nodename, port', DB.ONOS_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, value in nodes_info:
            if value == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(value)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def proc_dis_connection(node, param):
    try:
        nodes_info = get_node_list(node, 'nodename, ' + param, DB.ONOS_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        res_result = dict()
        for nodename, value in nodes_info:
            if value == 'none':
                res_result[nodename] = 'FAIL'
            else:
                res_result[nodename] = eval(value)

        return res_result
    except:
        LOG.exception()
        return {'Result': 'FAIL'}


def exist_command(req):
    try:
        cmd = req['command']

        if cmd not in COMMAND_MAP.keys():
            return False
        return True
    except:
        LOG.exception()
        return False


def get_node_list(nodes, param, tbl = DB.NODE_INFO_TBL, add_cond = ''):
    try:
        if nodes == 'all':
            sql = 'SELECT ' + param + ' FROM ' + tbl

            if not add_cond == '':
                sql = sql + ' WHERE ' + add_cond
        else:
            sql = 'SELECT ' + param + ' FROM ' + tbl + ' WHERE nodename = \'' + nodes + '\''

            if not add_cond == '':
                sql = sql + ' and ' + add_cond

        with DB.connection() as conn:
            nodes_info = conn.cursor().execute(sql).fetchall()

        conn.close()
        return nodes_info
    except:
        LOG.exception()
        return None


def proc_onos_cmd(node, cmd):
    try:
        nodes_info = get_node_list(node, 'ip_addr, type', DB.NODE_INFO_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        for ip, type in nodes_info:
            if not type == 'ONOS':
                return {'fail': 'This is not a command on the target system.'}
            else:
                res_result = dict()
                cmd_rt = SshCommand.onos_ssh_exec(ip, cmd)

                if not cmd_rt is None:
                    res_result[node] = str(cmd_rt)
                else:
                    return {'fail': 'Invalid command.'}

                return res_result
    except:
        LOG.exception()


def proc_shell_cmd(node, cmd):
    try:
        nodes_info = get_node_list(node, 'username, ip_addr', DB.NODE_INFO_TBL)

        if len(nodes_info) == 0:
            return {'fail': 'This is not a command on the target system.'}

        for username, ip in nodes_info:
            res_result = dict()
            cmd_rt = SshCommand.ssh_exec(username, ip, cmd)

            if not cmd_rt is None:
                res_result[node] = str(cmd_rt)
            else:
                return {'fail': 'Invalid command.'}

            return res_result
    except:
        LOG.exception()


COMMAND_MAP = {'resource': proc_dis_resource,
               'onos-svc': proc_dis_onos,
               'onos-log': proc_dis_log,
               'gateway': proc_dis_vrouter,
               'swarm-svc': proc_dis_swarm,
               'xos-svc': proc_dis_xos,
               'synchronizer': proc_dis_swarm_sync,
               'ha-proxy': proc_dis_ha,
               'openstack-node': proc_dis_node,
               'onos-conn': proc_dis_connection,
               'traffic-gw': proc_dis_gwratio,
               'port-stat-vxlan': proc_dis_traffic_vxlan,
               'traffic-controller': proc_dis_traffic_controller,
               'traffic-internal': proc_dis_traffic_internal,
               #internal command
               'system-status':proc_dis_system,
               'onos-shell':proc_onos_cmd,
               'os-shell':proc_shell_cmd
               }
