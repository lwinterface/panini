import os
import json


def get_topic_include():
    if 'TOPIC_INCLUDE' in os.environ:
        return json.loads(os.environ['TOPIC_INCLUDE']), True
    return None, False
