import os


def create_service_name_from_docker(default: str = None):
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
