import os
import datetime
import random


def create_client_code_by_hostname(name):
    return '__'.join([
        name,
        os.environ['HOSTNAME'] if 'HOSTNAME' in os.environ else 'non_docker_env_'+str(random.randint(1,1000000)),
        # str(datetime.datetime.now())
        str(random.randint(1,1000000))
    ])

def create_service_name_from_docker(default=None):
    try:
        return _get_docker_name()
    except Exception as e:
        if default:
            return default
        raise Exception(f'create_service_name error: {str(e)}(also make sure that you have an access to docker socket)')

def _get_docker_name():
    import docker
    hostname = os.environ['HOSTNAME']
    cli = docker.from_env()
    for c in cli.containers.list():
        if hostname in c.id[:len(hostname)]:
            return c.name
    raise Exception(f'{hostname} is upsent in docker containers')