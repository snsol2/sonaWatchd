import ConfigParser

COMMAND_SECTION_NAME = 'command'
TRACE_SECTION_NAME = 'condition'
REST_SECTION_NAME = 'rest-server'
LOG_SECTION_NAME = 'log'

REST_ID_KEY_NAME = 'id'
REST_PW_KEY_NAME = 'pw'
COMMAND_OPT_KEY_NAME = 'option_list'
CLI_LOG_KEY_NAME = 'cli_log'
TRACE_LOG_KEY_NAME = 'trace_log'

CLI_CONFIG_FILE = 'config/cli_config.ini'
TRACE_CONFIG_FILE = 'config/trace_config.ini'

class CONFIG():

    LOG = None
    config_cli = ConfigParser.RawConfigParser()
    config_trace = ConfigParser.RawConfigParser()

    @classmethod
    def init_config(cls, LOG):
        cls.LOG = LOG
        try:
            # read config
            cls.config_cli.read(CLI_CONFIG_FILE)
            cls.config_trace.read(TRACE_CONFIG_FILE)
        except:
            cls.LOG.exception_err_write()
            pass

    @classmethod
    def get_cmd_list(cls):
        try:
            return cls.config_cli.options(COMMAND_SECTION_NAME)
        except:
            cls.LOG.exception_err_write()
            return []

    @classmethod
    def get_cnd_list(cls):
        try:
            return cls.config_trace.options(TRACE_SECTION_NAME)
        except:
            cls.LOG.exception_err_write()
            return []

    @classmethod
    def get_value(cls, section_name, key):
        try:
            return cls.config_cli.get(section_name, key)
        except:
            cls.LOG.exception_err_write()
            return ''

    @classmethod
    def get_config_instance(cls):
        return cls.config_cli

    @staticmethod
    def get_cmd_opt_key_name():
        return COMMAND_OPT_KEY_NAME

    @classmethod
    def get_rest_id(cls):
        return cls.get_value(REST_SECTION_NAME, REST_ID_KEY_NAME)

    @classmethod
    def get_rest_pw(cls):
        return cls.get_value(REST_SECTION_NAME, REST_PW_KEY_NAME)

    @classmethod
    def get_cli_log(cls):
        return cls.get_value(LOG_SECTION_NAME, CLI_LOG_KEY_NAME)

    @classmethod
    def get_trace_log(cls):
        try:
            return cls.config_trace.get(LOG_SECTION_NAME, TRACE_LOG_KEY_NAME)
        except:
            cls.LOG.exception_err_write()
            return ''