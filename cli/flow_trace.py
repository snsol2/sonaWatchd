import time

from config import CONFIG
from log_lib import LOG
from subprocess import Popen, PIPE


class TRACE():
    TRACE_LOG = None
    trace_cond_list = []

    compute_id = ''
    compute_list = {}

    cookie_list = []

    @classmethod
    def set_trace_log(cls, trace_log):
        cls.TRACE_LOG = trace_log

    @classmethod
    def send_trace(cls, ip, condition):
        try:
            # req trace
            cls.TRACE_LOG.trace_log('START TRACE | ip = ' + ip + ', condition = ' + condition)
        except:
            LOG.exception_err_write()

    @classmethod
    def set_cnd_list(cls):
        try:
            cls.compute_id = CONFIG.get_trace_cpt_id()
            cpt_list = CONFIG.get_trace_cpt_list()

            for cpt in cpt_list.split(','):
                cpt = cpt.strip()

                tmp = cpt.split(':')

                if len(tmp) == 2:
                    cls.compute_list[tmp[0]] = tmp[1]

            cls.trace_cond_list = CONFIG.get_cnd_list()
        except:
            LOG.exception_err_write()

    @staticmethod
    def valid_IPv4(address):
        try:
            parts = address.split(".")

            if len(parts) != 4:
                return False
            for item in parts:
                if len(item) > 3:
                    return False
                if not 0 <= int(item) <= 255:
                    return False
            return True
        except:
            LOG.exception_err_write()
            return False


    ssh_options = '-o StrictHostKeyChecking=no ' \
                  '-o ConnectTimeout=' + str(CONFIG.get_ssh_timeout())
    @classmethod
    def exec_trace(cls, username, node, command):
        command = 'sudo ovs-appctl ofproto/trace ' + CONFIG.get_trace_base_bridge() + ' \'' + command + '\''

        cls.TRACE_LOG.trace_log('START TRACE | username = ' + username + ', ip = ' + node + ', condition = ' + command)

        cmd = 'ssh %s %s@%s %s' % (cls.ssh_options, username, node, command)
        cls.TRACE_LOG.trace_log('Command: ' + cmd)

        cls.get_cookie_list(username, node)

        return cls.parsing(cls.ssh_exec(cmd))


    @classmethod
    def get_cookie_list(cls, username, node):
        try:
            command = 'sudo ovs-ofctl -O OpenFlow13 dump-flows ' + CONFIG.get_trace_base_bridge()

            cls.TRACE_LOG.trace_log('GET COOKIES | username = ' + username + ', ip = ' + node + ', condition = ' + command)

            cmd = 'ssh %s %s@%s %s' % (cls.ssh_options, username, node, command)
            cls.TRACE_LOG.trace_log('Command: ' + cmd)

            result = cls.ssh_exec(cmd)

            for cookie in cls.cookie_list:
                cls.cookie_list.remove(cookie)

            for line in result.splitlines():
                if 'cookie' in line:
                    cookie = line.split(',')[0].split('=')[1].strip()
                    cls.cookie_list.append(cookie)
        except:
            LOG.exception_err_write()


    @classmethod
    def ssh_exec(cls, cmd):
        try:
            result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            output, error = result.communicate()

            if result.returncode != 0:
                cls.TRACE_LOG.trace_log("SSH_Cmd Fail, cause => " + error)
                return 'SSH FAIL\nCOMMAND = ' + cmd + '\nREASON = ' + error
            else:
                cls.TRACE_LOG.trace_log("ssh command execute successful\n" + output)
                return output
        except:
            LOG.exception_err_write()
            return 'error'


    @classmethod
    def parsing(cls, output):
        try:
            result_flow = ''
            lines = output.splitlines()

            is_base_bridge = False
            for line in lines:
                line = line.strip()

                if line.startswith('Rule:'):
                    cookie = line.split(' ')[2].split('=')[1].strip()

                    if not cookie == '0':
                        if cookie in cls.cookie_list:
                            if not is_base_bridge:
                                result_flow = result_flow + '-------------------------------- ' + CONFIG.get_trace_base_bridge() + ' --------------------------------\n'
                            is_base_bridge = True
                        else:
                            if is_base_bridge:
                                result_flow = result_flow + '----------------------------- other bridge -----------------------------\n'
                            is_base_bridge = False

                    result_flow = result_flow + line + '\n'
                elif line.startswith('OpenFlow actions='):
                    result_flow = result_flow + line + '\n\n'

            return result_flow
        except:
            LOG.exception_err_write()
            return 'parsing error\n' + output


    @classmethod
    def process_trace_rest(cls, src_ip, dst_ip):
        try:
            import os
            cmd = 'curl -X POST -u \'admin:admin\' -H \'Content-Type: application/json\' -d \'{"command": "flowtrace", "reverse": true, "transaction_id": "test1234", ' \
                  '"app_rest_url": "http://' + CONFIG.get_rest_ip() + ':' + str(CONFIG.get_rest_port()) + '/test", "matchingfields":{"source_ip": "' + src_ip \
                  + '","destination_ip": "' + dst_ip + '"}}\' ' + CONFIG.get_server_addr() + '/trace_request'
            LOG.debug_log(cmd)
            result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            output, error = result.communicate()


            if result.returncode != 0:
                LOG.debug_log('Cmd Fail : ' + error)
            else:
                print output
                timeout = 0
                print '\nwaiting...'

                if 'SUCCESS' in output:
                    while True:
                        time.sleep(1)
                        timeout = timeout + 1
                        if os.path.exists('log/flowtrace'):
                            time.sleep(2)
                            result_file = open('log/flowtrace', 'r')

                            print(result_file.read())

                            return

                        if timeout > 10:
                            print 'cli timeout'
                            return
        except:
            LOG.exception_err_write()
