import json
import sys
import flask
import CONSTANTS as CONST
import threading
import logging

from click._unicodefun import click
from flask import Flask, request
from connector import Connector
from support import  encode_id, decode_id, \
    format_regular_message, build_node, calc_value

class FlaskChat(flask.Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

app = FlaskChat(__name__)

# logging configuration
LEVELS = { 'debug':logging.DEBUG,
            'info':logging.INFO,
            'warning':logging.WARNING,
            'error':logging.ERROR,
            'critical':logging.CRITICAL,
            }

if len(sys.argv) > 1:
    level_name = sys.argv[1]
    level = LEVELS.get(level_name, logging.NOTSET)
    logging.basicConfig(level=level)

# ----------------------------------------------------------------------------------------------------------------------

def process_regular_message(message):
    app.my_messages.append(format_regular_message(message))

def welcome(dstip, dstport):
    if not app.my_friend[CONST.STATE_FRIEND]:
        app.my_friend[CONST.STATE_FRIEND] = encode_id(dstip, dstport)
    Connector.send_leader(app.my_ip, app.my_port, dstip, dstport, app.my_leader)

def process_leader_info(leader_info):
    if leader_info[CONST.STATE_LEADER] == encode_id(app.my_ip, app.my_port):
        logging.debug('Leader information distributed sucessfuly')
    else:
        dstip, dstport = decode_id(app.my_friend[CONST.STATE_FRIEND])
        Connector.send_leader(app.my_ip, app.my_port, dstip, dstport, leader_info)

    app.my_leader[CONST.STATE_LEADER] = leader_info[CONST.STATE_LEADER]


def process_candidate_info(candidate_info):
    candidate_id = candidate_info[CONST.TYPE_CANDIDATE]
    candidate_value = calc_value(candidate_id)
    my_value = calc_value(encode_id(app.my_ip, app.my_port))
    dstip, dstport = decode_id(app.my_friend[CONST.STATE_FRIEND])

    if candidate_value > my_value:
        Connector.send_candidate_info(app.my_ip, app.my_port, dstip, dstport, candidate_info)
    elif my_value > candidate_value and app.my_leader:
        start_candidacy()
    elif my_value == candidate_value:
        logging.debug('I AM THE LEADER!')
        leader_info = build_node(CONST.STATE_LEADER, app.my_ip, app.my_port)
        Connector.send_leader(app.my_ip, app.my_port, dstip, dstport, leader_info)


# ----------------------------------------------------------------------------------------------------------------------

def innerHandler():

    # CONNECTION
    if request.form['message_type'] == CONST.TYPE_IN_INIT:
        dstip = request.form['ip']
        dstport = request.form['port']
        result = Connector.connect(app.my_ip, app.my_port, dstip, dstport)
        if result == 200:
            app.my_friend = { CONST.STATE_FRIEND: encode_id(dstip, dstport)}

    # MESSAGE
    elif request.form['message_type'] == CONST.TYPE_IN_MESSAGE:
        Connector.send_message(app.my_ip, app.my_port, '192.168.122.9', '5009', request.form['message'], 10)
        #TODO send message to LEADER
        #TODO make form on HTML!

    return flask.render_template('chat.html',
                                 messagelist=app.my_messages,
                                 friend = app.my_friend[CONST.STATE_FRIEND])

def outterHandler():
    headers = request.headers
    if CONST.HEADER_MESSAGE in headers:
        message_type = headers[CONST.HEADER_MESSAGE]

        # CONNECTION
        if message_type == CONST.TYPE_CONNECT:
            dstip = headers[CONST.HEADER_IP]
            dstport = headers[CONST.HEADER_PORT]
            welcome(dstip, dstport)

        # LEADER
        elif message_type == CONST.TYPE_LEADER_INFO:
            received_leader_info = json.loads(request.json)
            process_leader_info(received_leader_info)

        # MISSING LEADER
        elif message_type == CONST.TYPE_MISSING_LEADER:
            # TODO: MISSING LEADER, not sure if needed
            logging.debug('RECEIVED MISSING LEADER INFO!')

        # MESSAGE
        elif message_type == CONST.TYPE_MESSAGE:
            received_message = json.loads(request.json)
            logging.debug('Received regular message: %s', received_message[CONST.MESSAGE_TEXT])
            process_regular_message(received_message)

        elif message_type == CONST.TYPE_CANDIDATE:
            received_candidate_info = json.loads(request.json)
            logging.debug('Received candidate message: %s', received_candidate_info)
            process_candidate_info(received_candidate_info)


    return flask.render_template('chat.html',
                                 messagelist=app.my_messages,
                                 friend=app.my_friend[CONST.STATE_FRIEND])

# ----------------------------------------------------------------------------------------------------------------------

def processGet():
    if app.my_ip == request.remote_addr:
        return flask.render_template('index.html')
    else:
        return flask.render_template('error.html')

def processPost():
    if app.my_ip == request.remote_addr:
        return innerHandler()
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
    logging.debug('Starting election. Sending me as a candidate')
    dstip, dstport = decode_id(app.my_friend[CONST.STATE_FRIEND])
    me_candidate = build_node(CONST.TYPE_CANDIDATE, app.my_ip, app.my_port)
    Connector.send_candidate_info(app.my_ip, app.my_port,
                                  dstip, dstport,
                                  me_candidate)
    # TODO TEST
    app.my_leader[CONST.STATE_LEADER] = 'lol'

def heartbeat():
    logging.debug('heartbeat')

def leader_checker():
    while True:
        if not app.my_leader and app.my_friend[CONST.STATE_FRIEND]:
            start_candidacy()

def main_handler(ip, port):
    app.my_ip = ip
    app.my_port = port
    app.my_friend = {CONST.STATE_FRIEND: None}
    app.my_state = {CONST.STATE_LEADER : None}
    app.my_messages = []
    app.my_leader = {}
    app.run(host=ip, port=port)

@click.command()
@click.argument('ip')
@click.argument('port')
def runner(ip, port):
    # main thread for request handlers and processing
    m = threading.Thread(name='main_handler', target=main_handler, args=(ip, port))

    # daemon thread for heartbeat to friend
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

