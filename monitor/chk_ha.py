from subprocess import Popen, PIPE
import csv

from api.sona_log import LOG
from api.watcherdb import DB
from api.config import CONF


def onos_ha_check(conn, db_log):
    try:
        stats_url = CONF.ha()['ha_proxy_server']
        account = CONF.ha()['ha_proxy_account']

        cmd = 'curl --user ' + account + ' --header \'Accept: text/html, application/xhtml+xml, image/jxr, */*\' \"' + stats_url + '\"'
        result = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        output, error = result.communicate()

        if result.returncode != 0:
            LOG.error("Cmd Fail, cause => %s", error)
            return None
        else:
            report_data = csv.DictReader(output.lstrip('# ').splitlines())

        dic_stat = dict()
        for row in report_data:
            if row['pxname'].strip() == 'stats' or row['svname'].strip() == 'BACKEND':
                continue

            dtl_list = {'name': row['svname'], 'req_count': row['stot'], 'succ_count': row['hrsp_2xx'], 'node_sts': row['status']}

            svc_type = row['pxname']

            if (dic_stat.has_key(svc_type)):
                dic_stat[svc_type].append(dtl_list)
            else:
                dic_stat[svc_type] = list()
                dic_stat[svc_type].append(dtl_list)

        try:
            str_dic_stat = str(dic_stat)

            sql = 'UPDATE ' + DB.HA_TBL + \
                  ' SET stats = \"' + str_dic_stat + '\"' + \
                  ' WHERE ha_key = \"' + 'HA' + '\"'
            db_log.write_log('----- UPDATE HA INFO -----\n' + sql)

            if DB.sql_execute(sql, conn) != 'SUCCESS':
                db_log.write_log('[FAIL] HA DB Update Fail.')
        except:
            LOG.exception()

        return dic_stat
    except:
        LOG.exception()
        return None


def get_ha_stats(ha_dic):
    try:
        ha_status = 'ok'
        ha_ratio = 'ok'

        list_reason = []
        ratio_reason = []

        frontend = 0
        backend = 0

        for key in dict(ha_dic).keys():
            for line in ha_dic[key]:
                host = dict(line)['name']
                status = dict(line)['node_sts']

                if host == 'FRONTEND':
                    if not 'OPEN' in status:
                        list_json = {'key': key, 'hostname': host, 'status': 'nok'}
                        list_reason.append(list_json)
                        ha_status = 'nok'

                    frontend = int(dict(line)['req_count'])
                else:
                    if not 'UP' in status:
                        list_json = {'key': key, 'hostname': host, 'status': 'nok'}
                        list_reason.append(list_json)
                        ha_status = 'nok'

                    backend = backend + int(dict(line)['succ_count'])

        ratio = float(backend) * 100 / frontend

        if ratio < float(CONF.alarm()['ha_proxy']):
            ha_ratio = 'nok'
            ratio_reason.append(str(format(ratio, '.2f')))
    except:
        LOG.exception()
        ha_status = 'fail'
        ha_ratio = 'fail'

    return ha_status, ha_ratio, list_reason, ratio_reason

