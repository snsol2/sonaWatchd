# Copyright (c) 2017 by Telcoware kimjt
# All Rights Reserved.
# SONA Monitoring Solutions.

import json
import threading
import base64
import requests
import multiprocessing as multiprocess
import monitor.cmd_proc as command

from subprocess import Popen, PIPE
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from api.config import CONF
from api.sona_log import LOG

import sonatrace as trace
import sona_traffic_test as traffic_test


class RestHandler(BaseHTTPRequestHandler):
    # write buffer; 0: unbuffered, -1: buffering; rf) default rbufsize(rfile) is -1.
    wbufsize = -1

    def do_HEAD(self, res_code):
        self.send_response(res_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        LOG.info('[REST-SERVER] RESPONSE CODE = ' + str(res_code))

    def do_GET(self):
        # health check
        if self.path.startswith('/alive-check'):
            self.do_HEAD(200)
            self.wfile.write('ok\n')
            return

        if not self.authentication():
            self.do_HEAD(401)
            return
        else:
            if not self.headers.getheader('Content-Length'):
                self.do_HEAD(400)
                self.wfile.write('Bad Request, Content Length is 0\n')
                return
            else:
                request_size = int(self.headers.getheader("Content-Length"))
                request_string = self.rfile.read(request_size)
                request_obj = json.loads(request_string)

            LOG.info('[REST-SERVER] CLIENT INFO = ' + str(self.client_address))
            LOG.info('[REST-SERVER] RECV BODY = \n' + json.dumps(request_obj, sort_keys=True, indent=4))

            if self.path.startswith('/command'):
                try:
                    if command.exist_command(request_obj):
                        res_body = command.parse_command(request_obj)

                        self.do_HEAD(200)
                        self.wfile.write(json.dumps(res_body))

                        LOG.info('[REST-SERVER] RES BODY = \n%s',
                                 json.dumps(res_body, sort_keys=True, indent=4))
                    else:
                        self.do_HEAD(404)
                        self.wfile.write('command not found')

                        LOG.info('[REST-SERVER] ' + 'command not found')
                except:
                    LOG.exception()

            elif self.path.startswith('/regi'):
                try:
                    self.do_HEAD(200)

                    url = str(request_obj['url'])

                    res_body = command.regi_url(url, self.headers.getheader('Authorization'))

                    self.wfile.write(json.dumps(res_body))

                    LOG.info('[REST-SERVER] RES BODY = \n%s',
                             json.dumps(res_body, sort_keys=True, indent=4))
                except:
                    LOG.exception()

            elif self.path.startswith('/event_list'):
                try:
                    self.do_HEAD(200)

                    url = str(request_obj['url'])

                    res_body = command.get_event_list(url, self.headers.getheader('Authorization'))

                    self.wfile.write(json.dumps(res_body))

                    LOG.info('[REST-SERVER] RES BODY = \n%s',
                             json.dumps(res_body, sort_keys=True, indent=4))
                except:
                    LOG.exception()

            elif self.path.startswith('/unregi'):
                try:
                    self.do_HEAD(200)

                    url = str(request_obj['url'])

                    res_body = command.unregi_url(url)

                    self.wfile.write(json.dumps(res_body))

                    LOG.info('[REST-SERVER] RES BODY = \n%s',
                             json.dumps(res_body, sort_keys=True, indent=4))
                except:
                    LOG.exception()

            else:
                self.do_HEAD(404)
                self.wfile.write(self.path + ' not found\n')

                LOG.info('[REST-SERVER] ' + self.path + ' not found')

    def do_POST(self):
        if not self.authentication():
            self.do_HEAD(401)
            self.wfile.write(str({"result": "FAIL"}))
        else:
            if self.path.startswith('/trace_request'):
                trace_mandatory_field = ['command', 'transaction_id', 'app_rest_url', 'matchingfields']
                matching_mandatory_field = ['source_ip', 'destination_ip']

                trace_condition_json = self.get_content()
                if not trace_condition_json:
                    return
                else:
                    if (not all(x in dict(trace_condition_json['matchingfields']).keys() for x in matching_mandatory_field))\
                            or (not all(x in dict(trace_condition_json).keys() for x in trace_mandatory_field)):
                        self.do_HEAD(400)
                        self.wfile.write(str({"result": "FAIL", "fail_reason": "Not Exist Mandatory Attribute\n"}))
                        return
                    elif (valid_IPv4(trace_condition_json['matchingfields']['source_ip']) == False) or \
                            (valid_IPv4(trace_condition_json['matchingfields']['destination_ip']) == False):
                        self.do_HEAD(400)
                        self.wfile.write(str({"result": "FAIL", "fail_reason": "Type of IP Address is wrong\n"}))
                        return
                    else:
                        # process trace, send noti
                        process_thread = threading.Thread(target=send_response_trace_test,
                                                          args=(trace_condition_json,
                                                                 str(self.headers.getheader("Authorization"))))
                        process_thread.daemon = False
                        process_thread.start()

                        self.do_HEAD(200)
                        self.wfile.write(str({"result": "SUCCESS"}))

            # traffic test for exited VM
            elif self.path.startswith('/traffictest_request'):
                trace_mandatory_field = ['command', 'transaction_id', 'app_rest_url', 'traffic_test_list']
                test_mandatory_field = ['node', 'instance_id', 'vm_user_id', 'vm_user_password', 'traffic_test_command']

                trace_condition_json = self.get_content()
                if not trace_condition_json:
                    return
                else:
                    if not all(x in dict(trace_condition_json).keys() for x in trace_mandatory_field):
                        self.do_HEAD(400)
                        self.wfile.write(str({"result": "FAIL", "fail_reason": "Not Exist Mandatory Attribute\n"}))
                        return
                    else:
                        for test in trace_condition_json['traffic_test_list']:
                            if not all(x in dict(test).keys() for x in test_mandatory_field):
                                self.do_HEAD(400)
                                self.wfile.write(str({"result": "FAIL", "fail_reason": "Not Exist Mandatory Attribute\n"}))
                                return

                            for x in test_mandatory_field:
                                if len(test[x]) == 0:
                                    self.do_HEAD(400)
                                    self.wfile.write(
                                        str({"result": "FAIL", "fail_reason": x + " condition empty\n"}))
                                    return

                        # process traffic test, send noti
                        process_thread = threading.Thread(target=send_response_traffic_test_old,
                                                          args=(trace_condition_json,
                                                                 str(self.headers.getheader("Authorization"))))
                        process_thread.daemon = False
                        process_thread.start()

                        self.do_HEAD(200)
                        self.wfile.write(str({"result": "SUCCESS"}))

            # create VM and traffic test for exclusive performance VM
            elif self.path.startswith('/tperf_request'):
                perf_mandatory_field = ['transaction_id',
                                        'app_rest_url',
                                        'server',
                                        'client',
                                        'test_options']

                perf_condition = dict(self.get_content())
                if not perf_condition:
                    return
                else:
                    if not all(x in perf_condition.keys() for x in perf_mandatory_field):
                        LOG.error('[Data Check Fail] Mandatory Attribute is Wrong')
                        self.do_HEAD(400)
                        self.wfile.write(str({"result": "FAIL", "fail_reason": "Not Exist Mandatory Attribute\n"}))
                        return
                    else:
                        # process traffic test, send noti
                        process_thread = threading.Thread(target=tperf_test_run,
                                                          args=(perf_condition, ))
                        process_thread.daemon = False
                        LOG.info("[Run Traffic Test Start] ---- ")
                        process_thread.start()

                        self.do_HEAD(200)
                        self.wfile.write(str({"result": "SUCCESS"}))

            else:
                self.do_HEAD(404)
                self.wfile.write(str({"result": "FAIL", "fail_reason": "Not Found path \"" + self.path + "\"\n"}))

    def get_content(self):
        if not self.headers.getheader('content-length'):
            self.do_HEAD(400)
            self.wfile.write(str({"result": "FAIL", "fail_reason": "Bad Request, Content Length is 0\n"}))
            LOG.info('[Data Check] Received No Data from %s', self.client_address)
            return False
        else:
            try:
                receive_data = json.loads(self.rfile.read(int(self.headers.getheader("content-length"))))
                LOG.info('%s', '[Received Data] \n' + json.dumps(receive_data, sort_keys=True, indent=4))
                return receive_data
            except:
                LOG.exception()
                error_reason = 'Json Data Parsing Error\n'
                self.do_HEAD(400)
                self.wfile.write(str({"result": "FAIL", "fail_reason": error_reason}))
                LOG.info('[Check Content] %s', error_reason)
                return False

    def authentication(self):
        try:
            if not self.headers.getheader("authorization"):
                self.wfile.write('No Authorization Header\n')
                return False
            else:
                request_auth = self.headers.getheader("authorization")
                id_pw_list = CONF.rest()['user_password']

                try:
                    request_account = base64.b64decode(str(request_auth).split()[-1])

                    for id_pw in id_pw_list:
                        if id_pw.strip() == request_account:
                            LOG.info('[REST-SERVER] AUTH SUCCESS = %s, from %s', id_pw, self.client_address)
                            return True
                except:
                    LOG.exception()

                self.wfile.write('Request Authentication User ID or Password is Wrong \n')
                LOG.info('[REST-SERVER] AUTH FAIL = %s, from %s',
                         base64.b64decode(str(request_auth).split()[-1]), self.client_address)
                return False

        except:
            LOG.exception()
            return False


def send_response_trace_test(cond, auth):
    trace_result_data = {}

    try:
        is_success, result, fail_reason = trace.flow_trace(cond)

        if is_success:
            trace_result_data['result'] = 'SUCCESS'
        else:
            trace_result_data['result'] = 'FAIL'
            if fail_reason == '':
                trace_result_data['fail_reason'] = 'The source ip does not exist.'
            else:
                trace_result_data['fail_reason'] = result

        if result != None:
            trace_result_data.update(result)

        trace_result_data['transaction_id'] = cond['transaction_id']
        LOG.info(json.dumps(trace_result_data, sort_keys=True, indent=4))

        req_body_json = json.dumps(trace_result_data)

        try:
            url = str(cond['app_rest_url'])
            #requests.post(str(url), headers=header, data=req_body_json, timeout=2)

            LOG.info('AUTH = ' + auth)
            if str(auth).startswith('Basic '):
                auth = str(auth).split(' ')[1]
            cmd = 'curl -X POST -u \'' + CONF.onos()['rest_auth'] + '\' -H \'Content-Type: application/json\' -d \'' + str(req_body_json) + '\' ' + url
            LOG.error('%s', 'curl = ' + cmd)
            result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            result.communicate()

            if result.returncode != 0:
                # Push noti does not respond
                pass
        except:
            LOG.exception()
            pass

    except:
        LOG.exception()


def tperf_test_run(perf_conditions):
    tperf_result = dict()
    request_headers = {'Authorization': CONF.onos()['rest_auth'], 'Accept': 'application/json', 'Content-Type': 'application/json'}

    try:
        # 1. creeate instance
        LOG.info("[T-perf server/client VM create] --- ")
        server_vm, client_vm, client_floatingip = traffic_test.create_instance(perf_conditions['server'],
                                                                               perf_conditions['client'])

        # 2. run performance test
        if server_vm and client_vm:
            tperf_result = traffic_test.tperf_command_exec(server_vm.__dict__['addresses'].values()[0][0]['addr'],
                                                           client_floatingip.ip,
                                                           perf_conditions['test_options'])
        else:
            tperf_result.update({'result': 'FAIL', 'fail_reason': 'Fail to create instance.'})

        tperf_result.update({'transaction_id': perf_conditions['transaction_id']})

        LOG.info("[Traffic Performance Test] Return Result = %s", json.dumps(tperf_result))

        # send tperf test result to ONOS
        response = requests.post(perf_conditions['app_rest_url'],
                                 data=str(json.dumps(tperf_result)),
                                 headers=request_headers)
        LOG.info("[Tperf Result Send] Response = %s %s", response.status_code, response.reason)

        # delete tperf test instance
        traffic_test.delete_test_instance(server_vm, client_vm, client_floatingip)

    except:
        LOG.exception()


def send_response_traffic_test_old(cond, auth):
    trace_result_data = {}

    try:
        is_success, result = trace.traffic_test_old(cond)

        if is_success:
            trace_result_data['result'] = 'SUCCESS'
        else:
            trace_result_data['result'] = 'FAIL'
            # trace_result_data['fail_reason'] = 'The source ip does not exist.'

        if result != None:
            trace_result_data['traffic_test_result'] = result

        trace_result_data['transaction_id'] = cond['transaction_id']
        try:
            LOG.info('%s', json.dumps(trace_result_data, sort_keys=True, indent=4))
        except:
            pass

        req_body_json = json.dumps(trace_result_data)

        try:
            url = str(cond['app_rest_url'])
            #requests.post(str(url), headers=header, data=req_body_json, timeout=2)

            if str(auth).startswith('Basic '):
                auth = str(auth).split(' ')[1]

            cmd = 'curl -X POST -u \'' + CONF.onos()['rest_auth'] + '\' -H \'Content-Type: application/json\' -d \'' + str(req_body_json) + '\' ' + url
            LOG.error('%s', 'curl = ' + cmd)
            result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            result.communicate()

            if result.returncode != 0:
                # Push noti does not respond
                pass
        except:
            LOG.exception()
            pass


    except:
        LOG.exception()


def run():
    try:
        server_address = ("", int(CONF.rest()['rest_server_port']))
        httpd = HTTPServer(server_address, RestHandler)
        httpd.serve_forever()
    except:
        print 'Rest Server failed to start'
        LOG.exception()


def rest_server_start():
    LOG.info("--- REST Server Start --- ")

    rest_server_daemon = multiprocess.Process(name='rest_server', target=run)
    rest_server_daemon.daemon = True
    rest_server_daemon.start()


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

