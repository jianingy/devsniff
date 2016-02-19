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
from devsniff.utils import partition
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
    uri = "?".join(filter(None, [r.path, r.query]))
    cursor.execute(q, (req.method, uri, headers, buffer(req.body) or '',
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
def get_conversations(cursor, profile_name, start, limit):
    conds, vals = [], [abs(start)]
    if start < 0:
        conds.append('x.id > (SELECT max(id) FROM proxy_requests) - ?')
    else:
        conds.append('x.id > ?')

    def _filter(exprs, field, not_=False):
        exprs = map(lambda x: x.strip(), exprs)
        wildcards = filter(lambda x: x.find('*') > -1, exprs)
        exacts = filter(lambda x: x.find('*') < 0, exprs)
        holders = ','.join('?' * len(exacts))
        subconds = []
        if exacts:
            subconds.append('{0} IN ({1})'.format(field, holders))
            vals.extend(exacts)
        for val in wildcards:
            subconds.append('{0} LIKE ?'.format(field))
            vals.append(val.replace('*', '%'))
        if not subconds:
            return
        conds.append('%s (%s)' % ('NOT' if not_ else '',
                                  ' OR '.join(subconds)))

    profile = get_profile_by_name(profile_name)
    mime_in, mime_ex = partition(lambda x: x.startswith('-'),
                                 profile['mime_rules'].splitlines())
    _filter(mime_in, 'y.mimetype')
    _filter(mime_ex, 'y.mimetype', True)

    host_in, host_ex = partition(lambda x: x.startswith('-'),
                                 profile['host_rules'].splitlines())
    _filter(host_in, 'x.host')
    _filter(host_ex, 'x.host', True)

    vals.append(limit)

    q = ('SELECT x.id, method, uri, host, path,'
         ' y.status_code, y.mimetype, y.content_length'
         ' FROM proxy_requests x'
         ' INNER JOIN proxy_responses y ON x.id = y.request_id'
         ' WHERE %s'
         ' ORDER BY x.id ASC LIMIT ?' % " AND ".join(conds))
    LOG.debug('converstaion sql: %s with value %s' % (q, vals))
    result = cursor.execute(q, vals)
    return fetchall_as_dict(result)


@connection()
def get_profiles(cursor):
    q = ('SELECT id, name FROM proxy_profiles')
    result = cursor.execute(q)
    return fetchall_as_dict(result)


@connection()
def get_profile_by_id(cursor, profile_id):
    q = ('SELECT id, name, mime_rules, host_rules, host_mappings'
         ' FROM proxy_profiles WHERE id = ?')
    result = cursor.execute(q, (profile_id,))
    retval = fetchone_as_dict(result)
    return retval


@connection()
def get_profile_by_name(cursor, profile_name):
    q = ('SELECT id, name, mime_rules, host_rules, host_mappings'
         ' FROM proxy_profiles WHERE name = ?')
    result = cursor.execute(q, (profile_name,))
    retval = fetchone_as_dict(result)
    return retval


@connection()
def update_profile_by_id(cursor, profile_id, profile):
    q = ('UPDATE proxy_profiles SET name = ?, mime_rules = ?, '
         ' host_rules = ?, host_mappings = ?'
         ' WHERE id = ?')
    cursor.execute(q, (profile['name'], profile['mime_rules'],
                       profile['host_rules'], profile['host_mappings'],
                       profile_id))


@connection()
def create_profile_by_id(cursor, profile):
    q = ('INSERT INTO proxy_profiles'
         ' (name, mime_rules, host_rules, host_mappings)'
         ' VALUES(?, ?, ?, ?) ')
    cursor.execute(q, (profile['name'], profile['mime_rules'],
                       profile['host_rules'], profile['host_mappings']))
