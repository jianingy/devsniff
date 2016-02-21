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
from devsniff.utils import parse_bind_address, route
from tornado.options import (define as tornado_define,
                             options as tornado_options,
                             parse_config_file)
from os.path import join as path_join, dirname
from tornado.util import import_object
from tornado.web import Application as TornadoWebApplication

import tornado.ioloop
import tornado.httpserver


tornado_define("debug", default=False, help="debug", type=bool)
tornado_define("bind", default='0.0.0.0:8888',
               help="proxy listen address")
tornado_define("config", type=str, help="path to config file",
               callback=lambda path: parse_config_file(path, final=False))


def init_app():
    db_api.init()
    from devsniff.proxy import ProxyProfile
    ProxyProfile.instance().load(1)


def start():
    from tornado.log import enable_pretty_logging
    enable_pretty_logging()
    tornado.options.parse_command_line()

    import_object('devsniff.proxy')
    import_object('devsniff.admin')

    server_root = dirname(__file__)
    proxy_settings = dict(
        debug=tornado_options.debug,
        template_path=path_join(server_root, "templates"),
        static_path=path_join(server_root, "static"),
    )
    proxy_app = TornadoWebApplication(route.get_routes(), **proxy_settings)
    proxy_bind = parse_bind_address(tornado_options.bind)

    if tornado_options.debug:
        proxy_app.listen(proxy_bind[1], proxy_bind[0])
    else:
        server = tornado.httpserver.HTTPServer(proxy_app)
        server.bind(proxy_bind[1], proxy_bind[0])
        server.start(0)

    io_loop = tornado.ioloop.IOLoop.instance()
    io_loop.add_callback(init_app)
    io_loop.start()
