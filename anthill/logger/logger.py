import os, sys
import logging, logging.handlers
import datetime



class Logger:
    """Generate logging systems which display any level on the console
    and starting from INFO into logging file
    self.name: string, name of the logger,
    self.log_file: string, name of the file where to place the log datas.
    self.log_formatter: string, how the log is formated. See Formatter logging
        rules.
    self.console_level: logging object, the logging level to display in the
        console. Need to be superior to logging_level.
    self.file_level: logging object, the logging level to put in the
        logging file. Need to be superior to logging_level.
    self.logging_level: logging object, optional, the level of logging to catch.
    return: logging object, contain rules for logging.
    """
    def __init__(self, name,
                 log_file: str = None,
                 log_formatter: str = '%(message)s',
                 console_level: int = logging.DEBUG,
                 file_level: int = logging.DEBUG,
                 logging_level: int = logging.DEBUG,
                 root_path: str = None,
                 ):
        self.name = name
        if log_file is not None:
            self.log_file = log_file
        else:
            if 'CLIENT_ID' in os.environ:
                self.log_file = f"{os.environ['CLIENT_ID']}.log"
                self.client_id = os.environ['CLIENT_ID']
            else:
                self.log_file = f"{name}.log"
        if not hasattr(self, 'client_id'):
            self.client_id = name
        self.log_formatter = log_formatter
        self.console_level = console_level
        self.file_level = file_level
        self.logging_level = logging_level
        if root_path is not None:
            self.root_path = root_path
        else:
            try:
                self.root_path = os.environ['SERVICE_ROOT_PATH']
            except:
                self.root_path = '/'
        if log_file:
            separate_file = True
        else:
            separate_file = False
        self.logger = self.create(separate_file=separate_file)

    def create(self, separate_file: bool = False):
        dir_name = f'{self.root_path}logfiles'
        self._create_dir_when_none(dir_name)
        log_file = f'{dir_name}/{self.log_file}'
        if separate_file:
            logger = logging.getLogger(self.log_file)
        else:
            try:
                logger = logging.getLogger(os.environ['SERVICE_NAME'])
            except:
                logger = logging.getLogger(self.log_file)
        if not logger.handlers:
            logger.setLevel(self.logging_level)
            formatter = logging.Formatter(self.log_formatter)
            # Console handler stream
            ch = logging.StreamHandler()
            ch.setLevel(self.console_level)
            ch.setFormatter(formatter)
            # File Handler stream
            try:
                fh = logging.FileHandler(log_file)
            except:
                log_file = os.path.dirname(sys.argv[0])+log_file
                fh = logging.FileHandler(log_file)
            fh.setLevel(self.file_level)
            fh.setFormatter(formatter)
            logger.addHandler(ch)
            logger.addHandler(fh)
            handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=2000000, backupCount=20)
            logger.addHandler(handler)
        return logger

    def _create_dir_when_none(self, dir_name: str):
        """Check if a directory exist or create one.
        return: bool."""
        try:
            if dir_name[0] == '/':
                dir_name = dir_name[1:]
            if not os.path.isdir(dir_name):
                os.makedirs(dir_name)
                return False
            else:
                return True
        except OSError as e:
            pass

    def log(self, msg: str, level: str = 'info', from_: str = None, print_: bool = False, **log):
        if from_:
            log['from'] = self.name + '__' + from_
        else:
            log['from'] = self.name
        log['timestamp'] = datetime.datetime.now().timestamp()
        log['msg'] = msg
        log['level'] = level
        log['client_id'] = self.client_id
        if level == 'warning':
            self.logger.warning(log)
        elif level == 'error':
            self.logger.error(log)
        elif level == 'debug' or level == 'dev':
            self.logger.debug(log)
        elif level == 'critical':
            self.logger.critical(log)
        # add your custom log type here..
        else:
            self.logger.info(log)
        if print_:
            print(msg)



class InterServicesRequestLogger(Logger):
    def __init__(self, name: str,
                 log_file: str = None,
                 log_formatter: str = '%(message)s',
                 console_level: int = logging.DEBUG,
                     file_level: int = logging.DEBUG,
                 logging_level: int = logging.DEBUG,
                 root_path: str = None,
                 separated_file: bool = False,
                 ):
        self.name = name
        if log_file is not None:
            self.log_file = log_file
        else:
            self.log_file = f"inter_services_requests.log"
        if not hasattr(self, 'client_id'):
            self.client_id = name
        self.log_formatter = log_formatter
        self.console_level = console_level
        self.file_level = file_level
        self.logging_level = logging_level
        if root_path is not None:
            self.root_path = root_path
        else:
            try:
                self.root_path = "/".join(os.environ['SERVICE_ROOT_PATH'][:-1].split('/')[:-1])+"/messanger/"
            except:
                self.root_path = '/'
        self.logger = self.create(separate_file=separated_file)

    def isr_log(self, message: str, **kwargs):
        if not 'from_' in kwargs:
            kwargs['from_'] = os.environ['CLIENT_ID']
        self.log(message, **kwargs)