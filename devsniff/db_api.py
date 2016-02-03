# -*- coding: utf-8 -*-
#
# This piece of code is written by
#    Jianing Yang <jianingy.yang@gmail.com>
# with love and passion!
#
#        H A P P Y    H A C K I N G !
#              _____               ______
#     ____====  ]OO|_n_n__][.      |    |
#    [________]_|__|________)<     |YANG|
#     oo    oo  'oo OOOO-| oo\\_   ~o~~~o~
# +--+--+--+--+--+--+--+--+--+--+--+--+--+
#                             23 Jan, 2016
#
from tornado.options import (define as tornado_define,
                             options as tornado_options)
from urlparse import urlparse
import functools
import sqlite3
import logging


tornado_define('database', default='sqlite:///tmp/sqlite.db',
               help="path to sqlite file")


LOG = logging.getLogger('tornado.application')


class SQLiteConnectorError(Exception):
    pass


class SQLiteConnector(object):

    _instances = dict()

    @staticmethod
    def instance(name='master'):
        if name not in SQLiteConnector._instances:
            SQLiteConnector._instances[name] = SQLiteConnector()
        return SQLiteConnector._instances[name]

    @classmethod
    def connection(cls):
        if not hasattr(cls, '_connection') or not cls._connection:
            raise SQLiteConnectorError('not connected')
        return cls._connection

    @classmethod
    def connect(cls, **kwd):
        r = urlparse(tornado_options.database)
        if r.scheme.lower() != 'sqlite':
            raise SQLiteConnector('uri should starts with sqlite://')

        cls._connection = sqlite3.connect(r.path)
        cls._connection.text_factory = str

    @classmethod
    def disconnect(cls):
        return cls.connection().close()


def init():
    SQLiteConnector.instance().connect()


def connection(method=None, name="master"):

    def wrapper(function):

        @functools.wraps(function)
        def f(*args, **kwds):
            conn = SQLiteConnector.instance(name).connection()
            cursor = conn.cursor()
            val = function(cursor, *args, **kwds)
            conn.commit()
            cursor.close()
            return val
        return f

    return wrapper


def fetchall_as_dict(cursor):
    """fetch all cursor results and returns them as a list of dicts"""
    names = [x[0] for x in cursor.description]
    rows = cursor.fetchall()
    if rows:
        return [dict(zip(names, row)) for row in rows]
    else:
        return []


def fetchone_as_dict(cursor):
    """fetch all cursor results and returns them as a list of dicts"""
    names = [x[0] for x in cursor.description]
    row = cursor.fetchone()
    if row:
        return dict(zip(names, row))
    else:
        return None


@connection()
def add_request(cursor, req):
    content_length = len(req.body)
    encoding = req.headers.get('Content-Encoding', '').strip()
    mimetype = req.headers.get('Content-Type', '').strip().split(';', 1)[0]
    headers = "\r\n".join(['%s: %s' % x for x in req.headers.iteritems()])
    q = ('INSERT INTO proxy_requests '
         '(method, uri, headers, body, host, path, '
         ' content_encoding, content_length, mimetype)'
         ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);')
    r = urlparse(req.uri)
    cursor.execute(q, (req.method, req.uri, headers, buffer(req.body) or '',
                       r.hostname, r.path, encoding, content_length, mimetype))
    return cursor.lastrowid


@connection()
def add_response(cursor, request_id, status_code, headers, body):
    content_length = len(body)
    encoding = headers.get('Content-Encoding', '').strip()
    mimetype = headers.get('Content-Type', '').strip().split(';', 1)[0]
    headers = "\r\n".join(['%s: %s' % x for x in headers.iteritems()])
    q = ('INSERT INTO proxy_responses '
         ' (request_id, status_code, headers, body,'
         ' content_encoding, content_length, mimetype)'
         ' VALUES (?, ?, ?, ?, ?, ?, ?);')
    cursor.execute(q, (request_id, status_code, headers, buffer(body),
                       encoding, content_length, mimetype))
    return cursor.lastrowid


@connection()
def get_request(cursor, request_id):
    q = ('SELECT id, method, uri, headers, host, path,'
         ' content_length, mimetype'
         ' FROM proxy_requests WHERE id = ?')
    result = cursor.execute(q, (request_id,))

    return fetchone_as_dict(result)


@connection()
def get_request_body(cursor, request_id):
    q = ('SELECT content_encoding, mimetype, body FROM proxy_requests'
         ' WHERE id = ?')
    result = cursor.execute(q, (request_id,))

    return fetchone_as_dict(result)


@connection()
def get_response(cursor, request_id):
    q = ('SELECT id, request_id, status_code, headers,'
         ' content_length, mimetype'
         ' FROM proxy_responses'
         ' WHERE request_id = ?')
    result = cursor.execute(q, (request_id,))

    return fetchone_as_dict(result)


@connection()
def get_response_body(cursor, request_id):
    q = ('SELECT content_encoding, mimetype, body FROM proxy_responses'
         ' WHERE request_id = ?')
    result = cursor.execute(q, (request_id,))

    return fetchone_as_dict(result)


@connection()
def get_conversations(cursor, start=0, limit=20):
    if start < 0:
        cond = 'x.id > (SELECT max(id) FROM proxy_requests) - ?'
    else:
        cond = 'x.id > ?'
    q = ('SELECT x.id, method, uri, host, path,'
         ' y.status_code, y.mimetype, y.content_length'
         ' FROM proxy_requests x'
         ' INNER JOIN proxy_responses y ON x.id = y.request_id'
         ' WHERE %s'
         ' ORDER BY x.id ASC LIMIT ?' % cond)
    result = cursor.execute(q, (abs(start), limit))
    return fetchall_as_dict(result)
