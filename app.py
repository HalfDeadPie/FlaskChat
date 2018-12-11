import json
import sys
import time

import flask
import CONSTANTS as C
import threading
import logging as L

from click._unicodefun import click
from flask import Flask, request

from connector import Connector
from support import encode_id, decode_id, \
    format_regular_message, build_node_dict, calc_value


class FlaskChat(flask.Flask):
    def __init__(self, *args, **kwargs):
        self.ip = None
        self.port = None
        self.conn = None
        self.value = None
        self.id = None
        self.status = None
        self.nodes = []
        self.messages = []
        self.topology = []
        super().__init__(*args, **kwargs)


app = FlaskChat(__name__)

# LOGGING SETTINGS
flask_logger = L.getLogger('werkzeug')
flask_logger.disabled = True
app.logger.disabled = True
request_logger = L.getLogger('urllib3.connectionpool')
request_logger.disabled = True
LEVELS = {'debug': L.DEBUG,
          'info': L.INFO,
          'warning': L.WARNING,
          'error': L.ERROR,
          'critical': L.CRITICAL,
          }
if len(sys.argv) > 1:
    level_name = sys.argv[1]
    level = LEVELS.get(level_name, L.NOTSET)
    L.basicConfig(level=level)


# ----------------------------------------------------------------------------------------------------------------------

def process_regular_message(message):
    app.messages.append(format_regular_message(message))
    if app.status == C.STATUS_LEADER:
        # TODO implement BROADCAST MESSAGE
        # TODO implement time to messages
        pass

def welcome(newip, newport):
    if not app.nodes[C.NODE_FRONT]:
        app.nodes[C.NODE_FRONT] = encode_id(newip, newport)
    old_back_friend = app.nodes[C.NODE_BACK]
    app.nodes[C.NODE_BACK] = encode_id(newip, newport)

    if app.nodes[C.NODE_FRONT] == app.nodes[C.NODE_BACK]:
        app.conn.send_back_setting(newip, newport, app.id)
    else:
        old_back_ip, old_back_port = decode_id(old_back_friend)
        app.conn.send_front_setting(old_back_ip, old_back_port, app.nodes[C.NODE_BACK])
        app.conn.send_back_setting(newip, newport, old_back_friend)

    app.conn.send_leader(newip, newport, app.nodes[C.NODE_LEADER])


def connect(dstip, dstport):
    if app.conn.connect(dstip, dstport) == 200:
        app.nodes[C.NODE_FRONT] = encode_id(dstip, dstport)


def process_leader_message(leader_json):
    if leader_json == app.id:
        L.debug('Leader information distributed successfully')
    else:
        dstip, dstport = decode_id(app.nodes[C.NODE_FRONT])
        app.conn.send_leader(dstip, dstport, leader_json)

    app.nodes[C.NODE_LEADER] = leader_json


def process_back_friend_json(back_friend_json):
    app.nodes[C.NODE_BACK] = back_friend_json


def process_front_friend_json(front_friend_json):
    app.nodes[C.NODE_FRONT] = front_friend_json


def process_candidate_json(candidate_json):
    candidate_value = calc_value(candidate_json)

    try:
        dstip, dstport = decode_id(app.nodes[C.NODE_FRONT])

        if candidate_value > app.value:
            app.conn.send_candidate(dstip, dstport, candidate_json)

        elif app.value > candidate_value and app.nodes[C.NODE_LEADER]:
            start_candidacy()

        elif app.value == candidate_value:
            L.debug('**LEADER STATE**')
            app.status = C.STATUS_LEADER
            app.nodes[C.NODE_LEADER] = app.id
            app.conn.send_leader(dstip, dstport, app.id)
    except:
        pass


# ----------------------------------------------------------------------------------------------------------------------

def innerHandler():
    """
    Handling messages from my adress
    """

    # CONNECTION
    if request.form['message_type'] == C.TYPE_IN_INIT:
        connect(request.form['ip'], request.form['port'])

    # MESSAGE
    elif request.form['message_type'] == C.TYPE_IN_MESSAGE:
        try:
            dstip, dstport = decode_id(app.nodes[C.NODE_LEADER])
            app.conn.send_message(dstip, dstport, request.form['message'], 0)
            L.debug('Sending message: %s', str(request.form['message']))
        except:
            L.debug('Message has not been sent.')

    # render a page
    return flask.render_template('chat.html',
                                 messagelist=app.messages,
                                 front_friend=app.nodes[C.NODE_FRONT],
                                 back_friend=app.nodes[C.NODE_BACK],
                                 leader=app.nodes[C.NODE_LEADER])

def outterHandler():
    """
    Handling messages from outter world
    """
    headers = request.headers
    if C.HEADER_MESSAGE in headers:
        message_type = headers[C.HEADER_MESSAGE]

        # CONNECTION
        if message_type == C.TYPE_CONNECT:
            dstip = headers[C.HEADER_IP]
            dstport = headers[C.HEADER_PORT]
            welcome(dstip, dstport)

        # LEADER
        elif message_type == C.TYPE_LEADER_INFO:
            leader = json.loads(request.json)
            process_leader_message(leader)

        #  MESSAGE
        elif message_type == C.TYPE_MESSAGE:
            received_message = json.loads(request.json)
            L.debug('Received message: %s', received_message[C.MESSAGE_TEXT])
            process_regular_message(received_message)

        # CANDIDATE
        elif message_type == C.TYPE_CANDIDATE:
            candidate = json.loads(request.json)
            L.debug('Received candidate: %s', candidate)
            process_candidate_json(candidate)

        # FRONT FRIEND
        elif message_type == C.TYPE_FRONT:
            front_friend = json.loads(request.json)
            L.debug('Received front friend message: %s', front_friend)
            process_front_friend_json(front_friend)

        # BACK FRIEND
        elif message_type == C.TYPE_BACK:
            back_friend = json.loads(request.json)
            L.debug('Received back friend message: %s', back_friend)
            process_back_friend_json(back_friend)

        # HEART BEAT
        elif message_type == C.TYPE_HEARTBEAT:
            node = encode_id(headers[C.HEADER_IP], headers[C.HEADER_PORT])

            if node not in app.topology:
                app.topology.append(node)
                L.debug('**TOPOLOGY**')
                L.debug(app.topology)

    # render a page
    return flask.render_template('chat.html',
                                 messagelist=app.messages,
                                 front_friend=app.nodes[C.NODE_FRONT],
                                 back_friend=app.nodes[C.NODE_BACK],
                                 leader=app.nodes[C.NODE_LEADER])


# ----------------------------------------------------------------------------------------------------------------------

def processGet():
    # if requests come from my address
    if app.ip == request.remote_addr:
        return flask.render_template('index.html')
    # else show error
    else:
        return flask.render_template('error.html')


def processPost():
    # if requests come from my address, inner handler will process it
    if app.ip == request.remote_addr:
        return innerHandler()
    # else outter handler will process it
    else:
        return outterHandler()


# ----------------------------------------------------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def index():
    method = request.method
    if method == 'GET':
        return processGet()
    elif method == 'POST':
        return processPost()


# ----------------------------------------------------------------------------------------------------------------------

def start_candidacy():
    try:
        #L.debug('Starting election. Sending me as a candidate')
        dstip, dstport = decode_id(app.nodes[C.NODE_FRONT])
        app.conn.send_candidate(dstip, dstport, app.id)
    except:
        pass


def heartbeat():
    while True:
        try:
            leader_ip, leaderport = decode_id(app.nodes[C.NODE_LEADER])
            app.conn.heartbeat(leader_ip, leaderport)
        except:
            pass
        finally:
            time.sleep(5)


def leader_checker():
    while True:
        if not app.nodes[C.NODE_LEADER] and app.nodes[C.NODE_FRONT]:
            start_candidacy()
        time.sleep(5)


def main_handler(ip, port):
    app.ip = ip
    app.port = port
    app.conn = Connector(ip, port)
    app.value = calc_value(encode_id(app.ip, app.port))
    app.id = encode_id(app.ip, app.port)
    app.nodes = {C.NODE_FRONT: None, C.NODE_BACK: None, C.NODE_LEADER: None}
    app.status = C.STATUS_FOLLOWER
    app.messages = []
    app.topology = []
    app.run(host=ip, port=port)


@click.command()
@click.argument('ip')
@click.argument('port')
def runner(ip, port):

    # main thread for request handlers and processing
    m = threading.Thread(name='main_handler', target=main_handler, args=(ip, port))

    #  daemon thread for heartbeat to friend
    h = threading.Thread(name='heartbeat', target=heartbeat)
    h.setDaemon(True)

    # daemon thread for leader checking
    s = threading.Thread(name='leader_checker', target=leader_checker)
    s.setDaemon(True)

    m.start()
    h.start()
    s.start()


if __name__ == '__main__':
    runner(obj={})
