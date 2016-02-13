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
from devsniff import db_api
from devsniff.utils import route, format_http_body
from tornado.httputil import HTTPHeaders
from tornado.web import RequestHandler, HTTPError
from tornado.escape import xhtml_escape
import hexdump


@route('/')
class IndexController(RequestHandler):

    def get(self):
        self.redirect('/admin', True)


@route('/admin')
class AdminIndexController(RequestHandler):

    def get(self):
        self.render('admin.html')


@route('/api/v1/requests/(\d+)')
class RequestResource(RequestHandler):

    def get(self, request_id):
        req = db_api.get_request(request_id)
        if not req:
            raise HTTPError(404)
        req['headers'] = dict(HTTPHeaders.parse(req['headers']).items())
        self.write(req)


@route('/api/v1/requests/(\d+)/body')
class RequestBodyResource(RequestHandler):

    def get(self, request_id):
        resp = db_api.get_request_body(request_id)
        if not resp:
            raise HTTPError(404)
        mimetype = resp['mimetype']
        body = xhtml_escape(str(resp['body']).decode('UTF-8', 'ignore'))

        self.write(dict(mimetype=mimetype, body=body))


@route('/api/v1/requests/(\d+)/body/auto')
class RequestBodyAutoResource(RequestHandler):

    def get(self, request_id):
        resp = db_api.get_request_body(request_id)
        if not resp:
            raise HTTPError(404)
        mimetype = resp['mimetype']
        encoding = resp['content_encoding']
        out = format_http_body(encoding, mimetype, resp['body'])
        self.write(out)


@route('/api/v1/requests/(\d+)/body/hex')
class RequestBodyHexResource(RequestHandler):

    def get(self, request_id):
        resp = db_api.get_request_body(request_id)
        if not resp:
            raise HTTPError(404)
        mimetype = resp['mimetype']
        encoding = resp['content_encoding']
        out = hexdump.hexdump(resp['body'], 'return')
        self.write(dict(mimetype=mimetype, encoding=encoding, body=out))


@route('/api/v1/responses/(\d+)')
class ResponseResource(RequestHandler):

    def get(self, request_id):
        resp = db_api.get_response(request_id)
        if not resp:
            raise HTTPError(404)
        resp['headers'] = dict(HTTPHeaders.parse(resp['headers']).items())
        self.write(resp)


@route('/api/v1/responses/(\d+)/body')
class ResponseBodyResource(RequestHandler):

    def get(self, request_id):
        resp = db_api.get_response_body(request_id)
        if not resp:
            raise HTTPError(404)
        mimetype = resp['mimetype']
        body = xhtml_escape(str(resp['body']).decode('UTF-8', 'ignore'))

        self.write(dict(mimetype=mimetype, body=body))


@route('/api/v1/responses/(\d+)/body/auto')
class ResponseBodyAutoResource(RequestHandler):

    def get(self, request_id):
        resp = db_api.get_response_body(request_id)
        if not resp:
            raise HTTPError(404)
        mimetype = resp['mimetype']
        encoding = resp['content_encoding']
        out = format_http_body(encoding, mimetype, resp['body'])
        self.write(out)


@route('/api/v1/responses/(\d+)/body/raw')
class ResponseBodyRawResource(RequestHandler):

    def get(self, request_id):
        resp = db_api.get_response_body(request_id)
        if not resp:
            raise HTTPError(404)
        self.set_header('Content-Type', resp['mimetype'])
        self.write(str(resp['body']))


@route('/api/v1/responses/(\d+)/body/hex')
class ResponseBodyHexResource(RequestHandler):

    def get(self, request_id):
        resp = db_api.get_response_body(request_id)
        if not resp:
            raise HTTPError(404)
        mimetype = resp['mimetype']
        encoding = resp['content_encoding']
        out = hexdump.hexdump(resp['body'], 'return')
        self.write(dict(mimetype=mimetype, encoding=encoding, body=out))


@route('/api/v1/conversations')
class ConversationCollection(RequestHandler):

    def get(self):
        start = int(self.get_argument('start', 0))
        limit = int(self.get_argument('limit', 20))
        includes = self.get_arguments('include')
        excludes = self.get_arguments('exclude')
        resp = db_api.get_conversations(start, limit, includes, excludes)
        start = resp[-1]['id'] if resp else start
        self.write(dict(num=len(resp), start=start, data=resp))
