import datetime
import json
import time
import CONSTANTS as C
import threading
import logging as L
import flask

from click._compat import raw_input
from asyncio import sleep
from click._unicodefun import click
from flask import Flask, request
from connector import Connector
from support import encode_id, decode_id, \
    format_regular_message, calc_value


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

chat_logger = L.getLogger()
chat_logger.handlers = []
chat_handler = L.StreamHandler()
chat_handler.setLevel(L.INFO)
formatter = L.Formatter("%(message)s")
chat_handler.setFormatter(formatter)
chat_logger.addHandler(chat_handler)


# support----------------------------------------------------------------------------------------------------------------------

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


def start_candidacy():
    try:
        dstip, dstport = decode_id(app.nodes[C.NODE_FRONT])
        app.conn.send_candidate(dstip, dstport, app.id)
    except:
        pass


def remove_node(dead_node):
    for node in app.topology:
        if str(node) == str(dead_node):
            app.topology.remove(node)


def report_dead_node(dead_node):
    leaderip, leaderport = decode_id(app.nodes[C.NODE_LEADER])
    remove_node(dead_node) if app.status == C.STATUS_LEADER else app.conn.death_report(leaderip, leaderport, dead_node)


def friendhit():
    frontip, frontport = decode_id(app.nodes[C.NODE_FRONT])
    try:
        # connector returns answer with backup front
        backup_front = app.conn.friendbeat(frontip, frontport)
        if backup_front == app.id:
            app.nodes[C.NODE_BACKUP_FRONT] = None
        else:
            app.nodes[C.NODE_BACKUP_FRONT] = backup_front
    except:
        chat_logger.debug("Lost connection to %s", app.nodes[C.NODE_FRONT])
        report_dead_node(encode_id(frontip, frontport))
        app.nodes[C.NODE_FRONT] = app.nodes[C.NODE_BACKUP_FRONT]
        if app.nodes[C.NODE_FRONT]:
            newfrontip, newfrontport = decode_id(app.nodes[C.NODE_FRONT])
            app.conn.send_back_setting(newfrontip, newfrontport, app.id)


def answer_friendbeat():
    front_friend_json = json.dumps(app.nodes[C.NODE_FRONT])
    # chat_logger.debug("Answering on friendbeat: %s", front_friend_json)
    # TODO make all the ifs when there are only two nodes
    # TODO make proper deleting nodes from the whole topology if is needed
    return front_friend_json, C.CODE_OK


def print_info():
    chat_logger.info("My address        : %s", app.id)

    try:
        chat_logger.info("Front address     : %s", app.nodes[C.NODE_FRONT])
    except:
        chat_logger.info("Front address     : None" )

    try:
        chat_logger.info("Back address      : %s", app.nodes[C.NODE_BACK])
    except:
        chat_logger.info("Back address     : None")

    try:
        chat_logger.info("Leader address    : %s", app.nodes[C.NODE_LEADER])
    except:
        chat_logger.info("Leader address    : None")

    try:
        chat_logger.info("Bck Front address : %s", app.nodes[C.NODE_BACKUP_FRONT])
    except:
        chat_logger.info("Bck Front address : None")

    if app.status == C.STATUS_LEADER:
        chat_logger.info("Topology: %s", app.topology)


# message processing----------------------------------------------------------------------------------------------------------------------

def process_regular_message(message):
    if app.status == C.STATUS_LEADER:
        message[C.MESSAGE_TIME] = str(datetime.datetime.now())
        app.conn.broadcast(message, app.topology)
    chat_logger.info(format_regular_message(message))


def send_regular_message_from_leader(text):
    message = {C.MESSAGE_TEXT: text,
               C.MESSAGE_TIME: str(datetime.datetime.now()),
               C.MESSAGE_ORIGIN: app.id}
    chat_logger.info(format_regular_message(message))
    app.conn.broadcast(message, app.topology)


def process_leader_message(leader_json):
    if leader_json == app.id:
        chat_logger.debug(C.DEBUG + 'Leader information distributed successfully')
        backip, backport = app.nodes[C.NODE_BACK]
    elif app.nodes[C.NODE_FRONT]:
        dstip, dstport = decode_id(app.nodes[C.NODE_FRONT])
        app.conn.send_leader(dstip, dstport, leader_json)

    chat_logger.debug(C.DEBUG + 'Starting to set leader')
    app.nodes[C.NODE_LEADER] = leader_json
    chat_logger.info('New leader: %s', app.nodes[C.NODE_LEADER])


def process_back_friend_json(back_friend_json):
    app.nodes[C.NODE_BACK] = back_friend_json


def process_front_friend_json(front_friend_json):
    app.nodes[C.NODE_FRONT] = front_friend_json


def process_candidate_json(candidate_json):
    candidate_value = calc_value(candidate_json)

    if app.status != C.STATUS_LEADER:
        try:
            dstip, dstport = decode_id(app.nodes[C.NODE_FRONT])

            if int(candidate_value) > int(app.value):
                app.conn.send_candidate(dstip, dstport, candidate_json)

            elif int(app.value) > int(candidate_value) and app.nodes[C.NODE_LEADER]:
                start_candidacy()

            elif int(app.value) == int(candidate_value):
                chat_logger.debug(C.DEBUG + '**LEADER STATE**')
                app.status = C.STATUS_LEADER
                app.nodes[C.NODE_LEADER] = app.id
                app.conn.send_leader(dstip, dstport, app.id)
        except:
            pass


# ----------------------------------------------------------------------------------------------------------------------

def outterHandler():
    headers = request.headers
    if C.HEADER_MESSAGE in headers:
        message_type = headers[C.HEADER_MESSAGE]

        # CONNECTION
        if message_type == C.TYPE_CONNECT:
            dstip = headers[C.HEADER_IP]
            dstport = headers[C.HEADER_PORT]
            chat_logger.debug(C.DEBUG + "Welcoming %s", encode_id(dstip, dstport))
            welcome(dstip, dstport)

            # LEADER
        elif message_type == C.TYPE_LEADER_INFO:
            leader = json.loads(request.json)
            chat_logger.debug(C.DEBUG + "Received leader %s", leader)
            process_leader_message(leader)

        #  MESSAGE
        elif message_type == C.TYPE_MESSAGE:
            received_message = json.loads(request.json)
            process_regular_message(received_message)

        # CANDIDATE
        elif message_type == C.TYPE_CANDIDATE:
            candidate = json.loads(request.json)
            chat_logger.debug(C.DEBUG + 'Received candidate: %s', candidate)
            process_candidate_json(candidate)

        # FRONT FRIEND
        elif message_type == C.TYPE_FRONT:
            front_friend = json.loads(request.json)
            chat_logger.debug(C.DEBUG + 'Received front friend message: %s', front_friend)
            process_front_friend_json(front_friend)

        # BACK FRIEND
        elif message_type == C.TYPE_BACK:
            back_friend = json.loads(request.json)
            chat_logger.debug(C.DEBUG + 'Received back friend message: %s', back_friend)
            process_back_friend_json(back_friend)

        # HEART BEAT
        elif message_type == C.TYPE_HEARTBEAT:
            node = encode_id(headers[C.HEADER_IP], headers[C.HEADER_PORT])

            if node not in app.topology:
                app.topology.append(node)
                chat_logger.debug(C.DEBUG + '**topology change**')
                chat_logger.debug(app.topology)

        # DEATH REPORT
        elif message_type == C.TYPE_DEATH_REPORT:
            dead_node = json.loads(request.json)
            chat_logger.info("%s lost connection", dead_node)
            remove_node(dead_node)


# ----------------------------------------------------------------------------------------------------------------------

def processGet():
    return 'CLI only!'


def processPost():
    if request.headers[C.HEADER_MESSAGE] == C.TYPE_FRIENDBEAT:
        return answer_friendbeat()
    elif app.ip != request.remote_addr:
        outterHandler()
        return C.CODE_OK
    else:
        return 'CLI only!'


# ----------------------------------------------------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def index():
    method = request.method
    if method == 'GET':
        return processGet()
    elif method == 'POST':
        return processPost()


#  THREAD TARGETS-----------------------------------------------------------------------

def heartbeat():
    while True:
        try:
            leader_ip, leaderport = decode_id(app.nodes[C.NODE_LEADER])
            if app.status != C.STATUS_LEADER:
                app.conn.heartbeat(leader_ip, leaderport)
        except:
            app.nodes[C.NODE_LEADER] = None
        finally:
            time.sleep(C.SLEEP_TIME)


def frontbeat():
    while True:
        if app.nodes[C.NODE_FRONT] and app.nodes[C.NODE_LEADER]:
            friendhit()
            time.sleep(C.SLEEP_TIME)


def leader_checker():
    while True:
        if not app.nodes[C.NODE_LEADER]:
            chat_logger.debug(C.DEBUG + 'Missing leader...')
            start_candidacy()
            time.sleep(C.SLEEP_TIME)


def connection(ip, port):
    chat_logger.debug(C.DEBUG + 'Waiting for a friend...')
    while not app.nodes[C.NODE_FRONT]:
        try:
            connect(ip, port)
        except:
            pass
        finally:
            time.sleep(C.SLEEP_TIME)


def input():
    while True:
        input_string = raw_input()
        if (input_string == '--info'):
            print_info()
        else:
            try:
                if app.status == C.STATUS_LEADER:
                    send_regular_message_from_leader(input_string)
                else:
                    dstip, dstport = decode_id(app.nodes[C.NODE_LEADER])
                    app.conn.send_message(dstip, dstport, input_string, 0)
                chat_logger.debug(C.DEBUG + 'Sending message: %s', input_string)
            except:
                chat_logger.debug(C.DEBUG + 'Message has not been sent.')
                pass


def main_handler(ip, port):
    app.ip = ip
    app.port = port
    app.conn = Connector(ip, port)
    app.value = calc_value(encode_id(app.ip, app.port))
    app.id = encode_id(app.ip, app.port)
    app.nodes = {C.NODE_FRONT: None, C.NODE_BACK: None, C.NODE_LEADER: None}
    app.status = C.STATUS_FOLLOWER
    app.topology = []
    app.run(host=ip, port=port)


@click.command()
@click.argument('ipport')
@click.argument('friend')
@click.option('--DEBUG', '-d', is_flag=True)
def runner(ipport, friend, debug):
    if debug:
        chat_handler.setLevel(L.DEBUG)

    ip, port = decode_id(ipport)
    friend_ip, friend_port = decode_id(friend)

    # main thread for request handlers and processing
    m = threading.Thread(name='main_handler', target=main_handler, args=(ip, port))
    m.setDaemon(True)

    #  daemon thread for heartbeat to leader
    h = threading.Thread(name='heartbeat', target=heartbeat)
    h.setDaemon(True)

    # daemon thread for leader checking
    s = threading.Thread(name='leader_checker', target=leader_checker)
    s.setDaemon(True)

    # daemon thread for leader checking
    i = threading.Thread(name='raw_input', target=input)
    i.setDaemon(True)

    # daemon thread for leader checking
    c = threading.Thread(name='connection', target=connection, args=(friend_ip, friend_port))
    c.setDaemon(True)

    # daemon thread for leader checking
    f = threading.Thread(name='frontbeat', target=frontbeat)
    f.setDaemon(True)

    m.start()
    h.start()
    s.start()
    i.start()
    c.start()
    f.start()

    while True:
        sleep(1)


if __name__ == '__main__':
    runner(obj={})

#TODO LOGOUT
#TODO TESTING