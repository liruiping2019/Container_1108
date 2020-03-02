#_*_coding:utf-8_*_

import redis
from Container import settings

def redis_conn(django_settings):
    pool = redis.ConnectionPool(host=settings.REDIS_CONN['HOST'],
                                port=settings.REDIS_CONN['PORT'],
                                db=settings.REDIS_CONN['DB'],
                                password='123456')
    r = redis.Redis(connection_pool=pool)
    return r