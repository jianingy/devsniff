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

from tornado.escape import xhtml_escape
from gzip import GzipFile
from StringIO import StringIO
import json
import tornado.web
import re

# The route helpers were originally written by
# Jeremy Kelley (http://github.com/nod).


class route(object):
    """
    decorates RequestHandlers and builds up a list of routables handlers

    Tech Notes (or 'What the *@# is really happening here?')
    --------------------------------------------------------

    Everytime @route('...') is called, we instantiate a new route object which
    saves off the passed in URI.  Then, since it's a decorator, the function is
    passed to the route.__call__ method as an argument.  We save a reference to
    that handler with our uri in our class level routes list then return that
    class to be instantiated as normal.

    Later, we can call the classmethod route.get_routes to return that list of
    tuples which can be handed directly to the tornado.web.Application
    instantiation.

    Example
    -------

    @route('/some/path')
    class SomeRequestHandler(RequestHandler):
        pass

    @route('/some/path', name='other')
    class SomeOtherRequestHandler(RequestHandler):
        pass

    my_routes = route.get_routes()
    """
    _routes = []

    def __init__(self, uri, name=None):
        self._uri = uri
        self.name = name

    def __call__(self, _handler):
        """gets called when we class decorate"""
        name = self.name and self.name or _handler.__name__
        self._routes.append(tornado.web.url(self._uri, _handler, name=name))
        return _handler

    @classmethod
    def get_routes(self):
        return self._routes


def route_redirect(from_, to, name=None):
    route._routes.append(tornado.web.url(from_,
                                         tornado.web.RedirectHandler,
                                         dict(url=to), name=name))


def parse_bind_address(addr):
    pairs = addr.split(':', 1)
    if pairs[0]:
        bind = pairs[0]
    else:
        bind = '0.0.0.0'
    port = int(pairs[1])
    return (bind, port)


def format_http_body(encoding, mimetype, body):
    if encoding.find('gzip') > -1:
        gz = GzipFile(fileobj=StringIO(body))
        body = gz.read()
    else:
        body = str(body)

    if mimetype.startswith('application/json'):
        body = json.dumps(json.loads(body), indent=4)
        body = re.sub(r'\\u[a-z0-9A-Z]+',
                      lambda x: x.group(0).decode('unicode-escape'),
                      body)
        return dict(mimetype=mimetype, body=xhtml_escape(body))

    body = xhtml_escape(body.decode('UTF-8', 'ignore'))
    return dict(mimetype=mimetype, body=body)
