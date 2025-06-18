# run_server.py
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

from app import app
from config import config

server = pywsgi.WSGIServer(
    ('0.0.0.0', config["port"]),
    app,
    handler_class=WebSocketHandler
)
server.serve_forever()
