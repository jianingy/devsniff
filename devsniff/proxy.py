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
from devsniff.utils import route
from tornado.gen import coroutine
from tornado.netutil import Resolver
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.options import options as tornado_options
from tornado.web import RequestHandler, asynchronous
import logging
import socket
import tornado.escape
import tornado.iostream
import tornado.websocket

LOG = logging.getLogger('tornado.application')
Resolver.configure('tornado.platform.caresresolver.CaresResolver')


@route('[^/].*$')
class ProxyController(RequestHandler):
    content_length = 0
    # Add HEAD/CONNECT to supported methods
    SUPPORTED_METHODS = ('GET', 'HEAD', 'POST', 'DELETE', 'PATCH', 'PUT',
                         'OPTIONS', 'CONNECT', 'HEAD')

    def __init__(self, *args, **kwd):
        self._chunking_output = False
        super(ProxyController, self).__init__(*args, **kwd)

    # disable auto etag
    def compute_etag(self):
        return None

    def header_out(self, data):
        eol = data.find("\n")
        line = data[:eol].rstrip("\r")

        if line.startswith('HTTP'):
            proto, code, reason = line.split(' ', 2)
            try:
                self.set_status(int(code), reason)
            except ValueError:
                self.set_status(502, reason)
            LOG.debug('\t< %s %s %s', proto, code, reason)
        elif line.find(':') > -1:
            name, val = line.split(':', 1)
            self.set_header(name, val.strip())
            if name == 'Transfer-Encoding':
                self._chunking_output = True
            LOG.debug('\t< %s:%s', name, val)
        elif len(line) == 0:
            self.flush()
            # force chunking_output of current connection to be true
            self.request.connection._chunking_output = self._chunking_output
        else:
            LOG.warn('invalid header data: %s' % data)

    def data_out(self, chunk):
        self.write(chunk)
        if self._chunking_output:
            self.flush()
        self.chunks.append(chunk)

    def current_response(self):
        body = "".join(self.chunks)
        del self.chunks
        return (self._status_code, self._headers, body)

    @coroutine
    def pipe(self):
        self.chunks = []
        headers = self.request.headers

        LOG.debug('reqs: [%s] %s', self.request.method, self.request.uri)
        if tornado_options.debug:
            map(lambda x: LOG.debug('\t=> %s:%s', *x), headers.iteritems())
        request_id = db_api.add_request(self.request)
        try:
            # body must be none for GET request
            if self.request.method == 'GET':
                body = None
            else:
                body = self.request.body
            # replace proxy-connection header with connection
            if 'Proxy-Connection' in headers:
                headers['Connection'] = headers.pop('Proxy-Connection')
            if tornado_options.debug:
                map(lambda x: LOG.debug('\t|> %s:%s', *x), headers.iteritems())
            req = HTTPRequest(self.request.uri,
                              method=self.request.method,
                              body=body,
                              headers=headers,
                              streaming_callback=self.data_out,
                              header_callback=self.header_out,
                              follow_redirects=False,
                              decompress_response=False,
                              allow_nonstandard_methods=True)
            http_client = AsyncHTTPClient(max_clients=512)
            yield http_client.fetch(req, raise_error=False)
        except Exception as e:
            self.set_status(502)
            self.write("Proxy Server Error: %s" % e)
        finally:
            LOG.debug('done: [%s] %s', self.request.method, self.request.uri)
            status_code, headers, body = self.current_response()
            db_api.add_response(request_id, status_code, headers, body)
            self.finish()

    @asynchronous
    def get(self):
        return self.pipe()

    @asynchronous
    def post(self):
        return self.pipe()

    @asynchronous
    def put(self):
        return self.pipe()

    @asynchronous
    def delete(self):
        return self.pipe()

    @asynchronous
    def head(self):
        return self.pipe()

    @asynchronous
    def options(self):
        return self.pipe()

    @asynchronous
    def patch(self):
        return self.pipe()

    @asynchronous
    def connect(self):
        self.ssl_passthrough()

    def ssl_passthrough(self):

        def stream_close(stream, data=None):
            if stream.closed():
                return
            if data:
                stream.write(data)
            stream.close()

        def stream_write(stream, data=None):
            stream.write(data)

        def start_tunnel(future):
            local = self.request.connection.stream
            try:
                remote = future.result()
                LOG.debug('Tunnel to %s established', self.request.uri)
                remote.read_until_close(lambda x: stream_close(local, x),
                                        lambda x: stream_write(local, x))
                local.read_until_close(lambda x: stream_close(remote, x),
                                       lambda x: stream_write(remote, x))
                local.write(b'HTTP/1.0 200 Connection established\r\n\r\n')
            except Exception as e:
                LOG.warn('Error on tunneling to %s' % (e))
                local.close()

        LOG.info('CONNECT %s', self.request.uri)
        request_id = db_api.add_request(self.request)
        db_api.add_response(request_id, 000, {}, '')
        host, port = self.request.uri.split(':')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        remote = tornado.iostream.IOStream(s)
        future = remote.connect((host, int(port)))
        future.add_done_callback(start_tunnel)
