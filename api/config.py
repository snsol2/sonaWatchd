# Copyright (c) 2017 by Telcoware
# All Rights Reserved.
# SONA Monitoring Solutions.

import ConfigParser

DEFAULT_CONF_FILE = "config/config.ini"


class ConfReader:
    conf_map = dict()

    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.__conf_file(None))
        self.__load_config_map()

    def __load_config_map(self):
        for section in self.config.sections():
            self.conf_map[section] = {key: value for key, value in self.config.items(section)}


    @staticmethod
    def __list_opt(value):
        return list(str(value).replace(" ", "").split(','))

    @staticmethod
    def __conf_file(file_name=None):
        if file_name is not None:
            return file_name
        else:
            return DEFAULT_CONF_FILE

    def base(self):
        value = dict()
        try:
            value['pidfile'] = str(self.conf_map['BASE']['pidfile'])
            value['log_file_name'] = str(self.conf_map['BASE']['log_file_name'])
            value['log_rotate_time'] = str(self.conf_map['BASE']['log_rotate_time'])
            value['log_backup_count'] = int(self.conf_map['BASE']['log_backup_count'])
            value['db_file'] = str(self.conf_map['BASE']['db_file'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def watchdog(self):
        value = dict()
        try:
            value['interval'] = int(self.conf_map['WATCHDOG']['interval'])
            value['check_system'] = self.__list_opt(self.conf_map['WATCHDOG']['check_system'])
            value['method'] = str(self.conf_map['WATCHDOG']['method'])
            value['timeout'] = int(self.conf_map['WATCHDOG']['timeout'])
            value['retry'] = int(self.conf_map['WATCHDOG']['retry'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def ssh_conn(self):
        value = dict()
        try:
            value['ssh_req_timeout'] = int(self.conf_map['SSH_CONN']['ssh_req_timeout'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def rest(self):
        value = dict()
        try:
            value['rest_server_port'] = int(self.conf_map['REST']['rest_server_port'])
            value['user_password'] = self.__list_opt(self.conf_map['REST']['user_password'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def onos(self):
        value = dict()
        try:
            value['list'] = self.__list_opt(self.conf_map['ONOS']['list'])
            value['account'] = str(self.conf_map['ONOS']['account'])
            value['app_list'] = self.__list_opt(self.conf_map['ONOS']['app_list'])
            value['rest_list'] = self.__list_opt(self.conf_map['ONOS']['rest_list'])
            value['rest_auth'] = str(self.conf_map['ONOS']['rest_auth'])

            if self.config.has_option('ONOS', 'alarm_off_list'):
                value['alarm_off_list'] = self.__list_opt(self.conf_map['ONOS']['alarm_off_list'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def ha(self):
        value = dict()
        try:
            value['list'] = self.__list_opt(self.conf_map['HA']['list'])
            value['account'] = str(self.conf_map['HA']['account'])
            value['ha_proxy_server'] = str(self.conf_map['HA']['ha_proxy_server'])
            value['ha_proxy_account'] = str(self.conf_map['HA']['ha_proxy_account'])

            if self.config.has_option('HA', 'alarm_off_list'):
                value['alarm_off_list'] = self.__list_opt(self.conf_map['HA']['alarm_off_list'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def xos(self):
        value = dict()
        try:
            value['list'] = self.__list_opt(self.conf_map['XOS']['list'])
            value['account'] = str(self.conf_map['XOS']['account'])
            value['xos_rest_server'] = str(self.conf_map['XOS']['xos_rest_server'])
            value['xos_rest_account'] = str(self.conf_map['XOS']['xos_rest_account'])

            if self.config.has_option('XOS', 'alarm_off_list'):
                value['alarm_off_list'] = self.__list_opt(self.conf_map['XOS']['alarm_off_list'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def swarm(self):
        value = dict()
        try:
            value['list'] = self.__list_opt(self.conf_map['SWARM']['list'])
            value['account'] = str(self.conf_map['SWARM']['account'])
            value['app_list'] = self.__list_opt(self.conf_map['SWARM']['app_list'])

            if self.config.has_option('SWARM', 'alarm_off_list'):
                value['alarm_off_list'] = self.__list_opt(self.conf_map['SWARM']['alarm_off_list'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def openstack(self):
        value = dict()
        try:
            value['gateway_list'] = self.__list_opt(self.conf_map['OPENSTACK']['gateway_list'])
            value['compute_list'] = self.__list_opt(self.conf_map['OPENSTACK']['compute_list'])
            value['account'] = str(self.conf_map['OPENSTACK']['account'])
            value['docker_list'] = self.__list_opt(self.conf_map['OPENSTACK']['docker_list'])
            value['onos_vrouter_app_list'] = self.__list_opt(self.conf_map['OPENSTACK']['onos_vrouter_app_list'])

            if self.config.has_option('OPENSTACK', 'alarm_off_list'):
                value['alarm_off_list'] = self.__list_opt(self.conf_map['OPENSTACK']['alarm_off_list'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def alarm(self):
        value = dict()
        try:
            value['cpu'] = self.__list_opt(self.conf_map['ALARM']['cpu'])
            value['memory'] = self.__list_opt(self.conf_map['ALARM']['memory'])
            value['disk'] = self.__list_opt(self.conf_map['ALARM']['disk'])
            value['ha_proxy'] = int(self.conf_map['ALARM']['ha_proxy'])
            value['gw_ratio'] = int(self.conf_map['ALARM']['gw_ratio'])
            value['node_traffic_ratio'] = int(self.conf_map['ALARM']['node_traffic_ratio'])
            value['controller_traffic_ratio'] = int(self.conf_map['ALARM']['controller_traffic_ratio'])
            value['controller_traffic_minimum_inbound'] = int(self.conf_map['ALARM']['controller_traffic_minimum_inbound'])
            value['internal_traffic_ratio'] = int(self.conf_map['ALARM']['internal_traffic_ratio'])

            return value
        except KeyError as KE:
            return dict({'fail': KE})

    def get_pid_file(self):
        try:
            return str(self.conf_map['BASE']['pidfile'])
        except KeyError as KE:
            return dict({'fail': KE})

CONF = ConfReader()


