import os
import logging
import logging_loki
from typing import Dict
from multiprocessing import Queue


class Logger(logging_loki.LokiQueueHandler):
    def __init__(self, **kwargs):
        url = kwargs.get("stream")
        tags = kwargs.get("tags", {})
        version = kwargs.get("version")
        super().__init__(
            Queue(-1),
            url=url,
            tags=tags,
            version=str(version),
        )

    @staticmethod
    def make_custom_logger(logger_config, custom_tags: Dict = None):
        """ add loki tags if loki logger params in config """
        if "loki" in logger_config["handlers"]:
            if custom_tags:
                logger_config["handlers"]["loki"]["tags"].update(custom_tags)
            for tag in logger_config["handlers"]["loki"]["tags"]:
                if not '-' in tag:
                    continue
                raise Exception("Loki tags do not support symbol '-'")
            if not "version" in logger_config["handlers"]["loki"]:
                logger_config["handlers"]["loki"]["version"] = logger_config["version"]
        for conf in logger_config['handlers'].values():
            if 'filename' in conf:
                os.makedirs(os.path.dirname(conf['filename']), exist_ok=True)
        logging.config.dictConfig(logger_config)
        logger = logging.getLogger(None)
        return logger
