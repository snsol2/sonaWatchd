# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import os
import sys
import sqlite3

from sona_log import LOG
from config import CONF

class DB(object):
    NODE_INFO_TBL = 't_nodes'
    REGI_SYS_TBL = 't_regi'
    EVENT_TBL = 't_event'
    STATUS_TBL = 't_status'
    RESOURCE_TBL = 't_resource'
    ONOS_TBL = 't_onos'
    SWARM_TBL = 't_swarm'
    OPENSTACK_TBL = 't_openstack'
    HA_TBL = 't_ha'
    OF_TBL = 't_of'

    common_event_list = ['NETWORK', 'CPU', 'MEMORY', 'DISK']
    onos_event_list = ['ONOS_APP', 'ONOS_REST', 'ONOS_OVSDB', 'ONOS_OF', 'ONOS_CLUSTER', 'ONOS_HA_LIST',
                       'ONOS_HA_RATIO', 'OPENSTACK_NODE', 'TRAFFIC_CONTROLLER']
    swarm_event_list = ['SWARM_SVC', 'SWARM_NODE']
    openstack_event_list = ['VROUTER', 'TRAFFIC_GW', 'TRAFFIC_NODE']
    xos_event_list = []

    item_list = ", ".join(common_event_list + onos_event_list + swarm_event_list + openstack_event_list + xos_event_list)

    @staticmethod
    def get_event_list(sys_type):
        if sys_type == 'ONOS':
            event_list = DB.common_event_list + DB.onos_event_list
        elif sys_type == 'SWARM':
            event_list = DB.common_event_list + DB.swarm_event_list
        elif sys_type == 'OPENSTACK':
            event_list = DB.common_event_list + DB.openstack_event_list
        elif sys_type == 'XOS':
            event_list = DB.common_event_list + DB.xos_event_list
        else:
            event_list = DB.common_event_list

        return event_list

    def __init__(self):
        self._conn = self.connection()
        self._conn.commit()

    @staticmethod
    def connection():
        try:
            conn = sqlite3.connect(CONF.base()['db_file'])
            conn.isolation_level = None
            return conn
        except:
            LOG.exception()
            sys.exit(1)

    @classmethod
    def db_cursor(cls):
        return cls.connection().cursor()

    # init DB table
    # make to empty table by default
    @classmethod
    def db_initiation(cls):
        try:
            db_path = CONF.base()['db_file']
            if os.path.isfile(db_path):
                os.remove(db_path)

            LOG.info("--- Initiating SONA DB ---")
            init_sql = ['CREATE TABLE ' + cls.NODE_INFO_TBL +
                            '(nodename text primary key, ip_addr, username, type, sub_type)',
                        'CREATE TABLE ' + cls.STATUS_TBL +
                        '(nodename text primary key, ' + cls.item_list + ', time)',
                        'CREATE TABLE ' + cls.RESOURCE_TBL + '(nodename text primary key, cpu real, memory real, disk real)',
                        'CREATE TABLE ' + cls.REGI_SYS_TBL + '(url text primary key, auth)',
                        'CREATE TABLE ' + cls.ONOS_TBL + '(nodename text primary key, applist, weblist, nodelist, port, haproxy, ovsdb, of, cluster, traffic_stat)',
                        'CREATE TABLE ' + cls.SWARM_TBL + '(nodename text primary key, node, service, ps)',
                        'CREATE TABLE ' + cls.OPENSTACK_TBL + '(nodename text primary key, sub_type, docker, onosApp, routingTable, gw_ratio, vxlan_traffic)',
                        'CREATE TABLE ' + cls.HA_TBL + '(ha_key text primary key, stats)',
                        'CREATE TABLE ' + cls.OF_TBL + '(hostname text primary key, of_id)',
                        'CREATE TABLE ' + cls.EVENT_TBL + '(nodename, item, grade, desc, time, PRIMARY KEY (nodename, item))']
            for sql in init_sql:
                sql_rt = cls.sql_execute(sql)

                if "already exist" in sql_rt:
                    table_name = sql_rt.split()[1]
                    LOG.info("\'%s\' table already exist. Delete all tuple of this table...",
                             table_name)
                    sql = 'DELETE FROM ' + table_name
                    sql_rt = cls.sql_execute(sql)
                    if sql_rt != 'SUCCESS':
                        LOG.info("DB %s table initiation fail\n%s", table_name, sql_rt)
                        sys.exit(1)
                elif sql_rt != 'SUCCESS':
                    LOG.info("DB initiation fail\n%s", sql_rt)
                    sys.exit(1)

            LOG.info('Insert nodes information ...')
            for node_type in CONF.watchdog()['check_system']:
                if node_type == 'OPENSTACK':
                    cls.sql_insert_nodes((CONF_MAP[node_type.upper()]())['gateway_list'],
                                         str((CONF_MAP[node_type.upper()]())['account']).split(':')[0], node_type, 'GATEWAY')
                    cls.sql_insert_nodes((CONF_MAP[node_type.upper()]())['compute_list'],
                                         str((CONF_MAP[node_type.upper()]())['account']).split(':')[0], node_type,
                                         'COMPUTE')
                else:
                    cls.sql_insert_nodes((CONF_MAP[node_type.upper()]())['list'],
                                     str((CONF_MAP[node_type.upper()]())['account']).split(':')[0], node_type)

            # set ha proxy tbl
            sql = 'INSERT INTO ' + cls.HA_TBL + ' VALUES (\'' + 'HA' + '\', \'none\')'
            LOG.info('%s', sql)
            sql_rt = cls.sql_execute(sql)
            if sql_rt != 'SUCCESS':
                LOG.info(" [HA PROXY TABLE] Node data insert fail \n%s", sql_rt)
                sys.exit(1)
        except:
            LOG.exception()


    @classmethod
    def sql_insert_nodes(cls, node_list, username, type, sub_type = 'none'):
        for node in node_list:
            name, ip = str(node).split(':')
            LOG.info('Insert node [%s %s %s %s]', name, ip, username, type)
            sql = 'INSERT INTO ' + cls.NODE_INFO_TBL + \
                  ' VALUES (\'' + name + '\', \'' + ip + '\', \'' + username + '\', \'' + type.upper() + '\', \'' + sub_type.upper() + '\')'
            LOG.info('%s', sql)
            sql_rt = cls.sql_execute(sql)
            if sql_rt != 'SUCCESS':
                LOG.info(" [NODE TABLE] Node data insert fail \n%s", sql_rt)
                sys.exit(1)

            # set status tbl
            sql = 'INSERT INTO ' + cls.STATUS_TBL + \
                  ' VALUES (\'' + name + '\', \'none\', \'none\', \'none\', \'none\', \'none\', \'none\', \'none\', \'none\', \'none\', ' \
                                         '\'none\', \'none\', \'none\', \'none\', \'none\', \'none\', \'none\', \'none\', \'none\', \'none\')'
            LOG.info('%s', sql)
            sql_rt = cls.sql_execute(sql)
            if sql_rt != 'SUCCESS':
                LOG.info(" [STATUS TABLE] Node data insert fail \n%s", sql_rt)
                sys.exit(1)

            # add Alarm Items
            evt_list = DB.get_event_list(type)
            for item in evt_list:
                LOG.info('Insert item [%s %s]', name, item)
                sql = 'INSERT INTO ' + cls.EVENT_TBL + \
                      ' VALUES (\'' + name + '\',\'' + item + '\',\'none\', \'none\', \'none\')'
                LOG.info('%s', sql)
                sql_rt = cls.sql_execute(sql)
                if sql_rt != 'SUCCESS':
                    LOG.info(" [ITEM TABLE] Item data insert fail \n%s", sql_rt)
                    sys.exit(1)

            # set resource tbl
            sql = 'INSERT INTO ' + cls.RESOURCE_TBL + ' VALUES (\'' + name + '\', -1, -1, -1)'
            LOG.info('%s', sql)
            sql_rt = cls.sql_execute(sql)
            if sql_rt != 'SUCCESS':
                LOG.info(" [RESOURCE TABLE] Node data insert fail \n%s", sql_rt)
                sys.exit(1)

            if type.upper() == 'ONOS':
                # set app tbl
                sql = 'INSERT INTO ' + cls.ONOS_TBL + ' VALUES (\'' + name + '\', \'none\', \'none\', \'none\', \'none\', ' \
                                                                             '\'none\', \'none\', \'none\', \'none\', \'none\')'
                LOG.info('%s', sql)
                sql_rt = cls.sql_execute(sql)
                if sql_rt != 'SUCCESS':
                    LOG.info(" [APP TABLE] Node data insert fail \n%s", sql_rt)
                    sys.exit(1)

            elif type.upper() == 'SWARM':
                # set swarm tbl
                sql = 'INSERT INTO ' + cls.SWARM_TBL + ' VALUES (\'' + name + '\', \'none\', \'none\', \'none\')'
                LOG.info('%s', sql)
                sql_rt = cls.sql_execute(sql)
                if sql_rt != 'SUCCESS':
                    LOG.info(" [SWARM TABLE] Node data insert fail \n%s", sql_rt)
                    sys.exit(1)

            elif type.upper() == 'OPENSTACK':
                # set vrouter tbl
                sql = 'INSERT INTO ' + cls.OPENSTACK_TBL + \
                      ' VALUES (\'' + name + '\', \'' + sub_type + '\', \'none\', \'none\', \'none\', \'none\', \'none\')'
                LOG.info('%s', sql)
                sql_rt = cls.sql_execute(sql)
                if sql_rt != 'SUCCESS':
                    LOG.info(" [VROUTER TABLE] Node data insert fail \n%s", sql_rt)
                    sys.exit(1)

    @classmethod
    def sql_execute(cls, sql, conn = None):
        try:
            if conn == None:
                with cls.connection() as conn:
                    conn.cursor().execute(sql)
                    conn.commit()

                conn.close()
            else:
                conn.cursor().execute(sql)
                conn.commit()

            return 'SUCCESS'
        except sqlite3.OperationalError, err:
            LOG.error(err.message)
            return err.message
        except:
            LOG.exception()
            return 'FAIL'

DB_CONN = DB().connection()

CONF_MAP = {'ONOS': CONF.onos,
            'XOS': CONF.xos,
            'SWARM': CONF.swarm,
            'OPENSTACK': CONF.openstack}