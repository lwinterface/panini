import redis


class RedisQueue:
    def __init__(self, name, namespace="queue", host="127.0.0.1", port=6379, db=0):
        self.__db = redis.Redis(host=host, port=port, db=db)
        self.key = "%s:%s" % (namespace, name)

    def qsize(self):
        return self.__db.llen(self.key)

    def empty(self):
        return self.qsize() == 0

    def put(self, item):
        self.__db.rpush(self.key, item)

    def get(self, block=True, timeout=None):
        if block:
            item = self.__db.blpop(self.key, timeout=timeout)
        else:
            item = self.__db.lpop(self.key)

        if item:
            item = item[1]
        return item

    def get_all(self):
        return self.__db.lrange(self.key, 0, self.qsize() - 1)

    def delete_all(self):
        return self.__db.delete(self.key)

    def get_nowait(self):
        return self.get(False)
