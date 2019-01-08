import datetime
import json
import os
import time

import CONSTANTS as C
import threading
import logging
import flask

from click._compat import raw_input
from asyncio import sleep
from click._unicodefun import click
from flask import Flask, request
from connector import Connector
from support import encode_id, decode_id, \
    format_regular_message, calc_value, debug_stamp, info_stamp


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

# disable Flask logger
flask_logger = logging.getLogger('werkzeug')
flask_logger.disabled = True

request_logger = logging.getLogger('urllib3.connectionpool')
request_logger.disabled = True

app_logger = logging.getLogger('flaskchat')
app_logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('history.log')
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

my_formatter = logging.Formatter('%(levelname)s - %(message)s')

fh.setFormatter(my_formatter)
ch.setFormatter(my_formatter)

app_logger.addHandler(fh)
app_logger.addHandler(ch)


# support----------------------------------------------------------------------------------------------------------------------

def welcome(newip, newport):
    if not app.nodes[C.NODE_FRONT]:
        app.nodes[C.NODE_FRONT] = encode_id(newip, newport)
    old_back_friend = app.nodes[C.NODE_BACK]
    app.nodes[C.NODE_BACK] = encode_id(newip, newport)

    if app.nodes[C.NODE_FRONT] == app.nodes[C.NODE_BACK]:
        try:
            app.conn.send_back_setting(newip, newport, app.id)
        except:
            pass
    else:
        try:
            old_back_ip, old_back_port = decode_id(old_back_friend)
            app.conn.send_front_setting(old_back_ip, old_back_port, app.nodes[C.NODE_BACK])
            app.conn.send_back_setting(newip, newport, old_back_friend)
            app.conn.send_leader(newip, newport, app.nodes[C.NODE_LEADER])
            new_node = encode_id(newip, newport)
            if app.status == C.STATUS_LEADER:
                app_logger.info(info_stamp() + "%s joined", new_node)
                app.conn.broadcast_new_node(new_node, app.topology)
            else:
                leaderip, leaderport = decode_id(app.nodes[C.NODE_LEADER])
                app.conn.new_node_report(leaderip, leaderport, new_node)
        except:
            pass


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
    try:
        leaderip, leaderport = decode_id(app.nodes[C.NODE_LEADER])
        if app.status == C.STATUS_LEADER:
            app_logger.info(info_stamp() + "%s lost connection", dead_node)
            app.conn.broadcast_dead_node(dead_node, app.topology)
            remove_node(dead_node)
        else:
            app.conn.death_report(leaderip, leaderport, dead_node)
    except:
        pass


def report_logout(loggedout_node):
    try:
        leaderip, leaderport = decode_id(app.nodes[C.NODE_LEADER])
        app.conn.logout_report(leaderip, leaderport, loggedout_node)
    except:
        app_logger.debug(debug_stamp() + 'Logging off without reporting')


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
        app_logger.debug(debug_stamp() + "Lost direct connection to %s", app.nodes[C.NODE_FRONT])
        app.nodes[C.NODE_FRONT] = app.nodes[C.NODE_BACKUP_FRONT]
        if app.nodes[C.NODE_FRONT]:
            newfrontip, newfrontport = decode_id(app.nodes[C.NODE_FRONT])
            try:
                app.conn.send_back_setting(newfrontip, newfrontport, app.id)
            except:
                pass
        if app.nodes[C.NODE_BACK] == encode_id(frontip, frontport):
            app.nodes[C.NODE_BACK] = None
        report_dead_node(encode_id(frontip, frontport))


def logout():
    if app.nodes[C.NODE_FRONT] != app.nodes[C.NODE_BACK]:
        backip, backport = decode_id(app.nodes[C.NODE_BACK])
        frontip, frontport = decode_id(app.nodes[C.NODE_FRONT])
        app.conn.send_front_setting(backip, backport, app.nodes[C.NODE_FRONT])
        app.conn.send_back_setting(frontip, frontport, app.nodes[C.NODE_BACK])
    if app.status == C.STATUS_LEADER:
        app.conn.broadcast_loggedout_node(app.id, app.topology)

    app_logger.info(info_stamp() + "Logging out...")
    report_logout(app.id)
    os._exit(0)


def print_info():
    app_logger.info("My address        : %s", app.id)

    try:
        app_logger.info("Front address     : %s", app.nodes[C.NODE_FRONT])
    except:
        app_logger.info("Front address     : None")

    try:
        app_logger.info("Back address      : %s", app.nodes[C.NODE_BACK])
    except:
        app_logger.info("Back address     : None")

    try:
        app_logger.info("Leader address    : %s", app.nodes[C.NODE_LEADER])
    except:
        app_logger.info("Leader address    : None")

    try:
        app_logger.info("Bck Front address : %s", app.nodes[C.NODE_BACKUP_FRONT])
    except:
        app_logger.info("Bck Front address : None")

    if app.status == C.STATUS_LEADER:
        app_logger.info("Topology: %s", app.topology)


# message processing----------------------------------------------------------------------------------------------------------------------

def process_regular_message(message):
    if app.status == C.STATUS_LEADER:
        message[C.MESSAGE_TIME] = str(datetime.datetime.now())
        app.conn.broadcast(message, app.topology)
    app_logger.info(format_regular_message(message))


def send_regular_message_from_leader(text):
    message = {C.MESSAGE_TEXT: text,
               C.MESSAGE_TIME: str(datetime.datetime.now()),
               C.MESSAGE_ORIGIN: app.id}
    app_logger.info(format_regular_message(message))
    app.conn.broadcast(message, app.topology)


def process_leader_message(leader_json):
    if leader_json == app.id:
        app_logger.debug(debug_stamp() + 'Leader information distributed successfully')
        backip, backport = decode_id(app.nodes[C.NODE_BACK])
    elif app.nodes[C.NODE_FRONT]:
        dstip, dstport = decode_id(app.nodes[C.NODE_FRONT])
        app.conn.send_leader(dstip, dstport, leader_json)

    app.nodes[C.NODE_LEADER] = leader_json
    app_logger.info(info_stamp() + 'New leader: %s', app.nodes[C.NODE_LEADER])


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
                app_logger.debug(debug_stamp() + 'Resending candidate: %s', candidate_json)
                app.conn.send_candidate(dstip, dstport, candidate_json)

            elif int(app.value) > int(candidate_value) and app.nodes[C.NODE_LEADER]:
                app_logger.debug(debug_stamp() + 'Swapping me as a candidate: %s', candidate_json)
                start_candidacy()

            elif int(app.value) == int(candidate_value):
                app_logger.debug(debug_stamp() + 'Setting the leader state')
                app.status = C.STATUS_LEADER
                app.nodes[C.NODE_LEADER] = app.id
                app.conn.send_leader(dstip, dstport, app.id)
        except:
            pass


def process_friendbeat():
    front_friend_json = json.dumps(app.nodes[C.NODE_FRONT])
    return front_friend_json, C.CODE_OK


def process_logout(loggedout_node):  # leader
    # TODO report death to all nodes
    app_logger.info(info_stamp() + "%s logged out", loggedout_node)
    remove_node(loggedout_node)
    app.conn.broadcast_loggedout_node(loggedout_node, app.topology)


def process_info_loggedout(loggedout_node):  # follower
    app_logger.info(info_stamp() + "%s logged out", loggedout_node)


def process_new_node(new_node):  # leader
    app_logger.info(info_stamp() + "%s joined", new_node)
    app.conn.broadcast_new_node(new_node, app.topology)


def process_info_new(new_node):  # follower
    app_logger.info(info_stamp() + "%s joined", new_node)


def process_dead_node(dead_node):
    app_logger.info(info_stamp() + "%s lost connection", dead_node)
    remove_node(dead_node)
    app.conn.broadcast_dead_node(dead_node, app.topology)


def process_info_death(dead_node):  # follower
    app_logger.info(info_stamp() + "%s lost connection", dead_node)


# ----------------------------------------------------------------------------------------------------------------------

def outterHandler():
    headers = request.headers
    if C.HEADER_MESSAGE in headers:
        message_type = headers[C.HEADER_MESSAGE]

        # CONNECTION
        if message_type == C.TYPE_CONNECT:
            dstip = headers[C.HEADER_IP]
            dstport = headers[C.HEADER_PORT]
            app_logger.debug(debug_stamp() + "Welcoming %s", encode_id(dstip, dstport))
            welcome(dstip, dstport)

            # LEADER
        elif message_type == C.TYPE_LEADER_INFO:
            leader = json.loads(request.json)
            app_logger.debug(debug_stamp() + "Received leader %s", leader)
            process_leader_message(leader)

        #  MESSAGE
        elif message_type == C.TYPE_MESSAGE:
            received_message = json.loads(request.json)
            process_regular_message(received_message)

        # CANDIDATE
        elif message_type == C.TYPE_CANDIDATE:
            candidate = json.loads(request.json)
            process_candidate_json(candidate)

        # FRONT FRIEND
        elif message_type == C.TYPE_FRONT:
            front_friend = json.loads(request.json)
            app_logger.debug(debug_stamp() + 'Front-friend setting received: %s', front_friend)
            process_front_friend_json(front_friend)

        # BACK FRIEND
        elif message_type == C.TYPE_BACK:
            back_friend = json.loads(request.json)
            app_logger.debug(debug_stamp() + 'Back-friend setting received: %s', back_friend)
            process_back_friend_json(back_friend)

        # HEART BEAT
        elif message_type == C.TYPE_HEARTBEAT:
            node = encode_id(headers[C.HEADER_IP], headers[C.HEADER_PORT])

            if node not in app.topology:
                app.topology.append(node)
                app_logger.debug(debug_stamp() + 'New node in the topology %s', node)

        # DEATH REPORT
        elif message_type == C.TYPE_DEATH:
            # TODO report death to all nodes
            dead_node = json.loads(request.json)
            process_dead_node(dead_node)

        # INFO DEATH
        elif message_type == C.TYPE_INFO_DEATH:  # follower
            dead_node = json.loads(request.json)
            process_info_death(dead_node)

        # LOGOUT
        elif message_type == C.TYPE_LOGOUT:  # leader
            loggedout_node = json.loads(request.json)
            process_logout(loggedout_node)

        # INFO LOGOUT
        elif message_type == C.TYPE_INFO_LOGOUT:  # follower
            loggedout_node = json.loads(request.json)
            process_info_loggedout(loggedout_node)

        # NEW
        elif message_type == C.TYPE_NEW:  # leader
            new_node = json.loads(request.json)
            process_new_node(new_node)

        # INFO NEW
        elif message_type == C.TYPE_INFO_NEW:  # follower
            new_node = json.loads(request.json)
            process_info_new(new_node)


# ----------------------------------------------------------------------------------------------------------------------

def processGet():
    return 'CLI only!'


def processPost():
    if request.headers[C.HEADER_MESSAGE] == C.TYPE_FRIENDBEAT:
        return process_friendbeat()
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
            if app.nodes[C.NODE_LEADER]:
                app_logger.info(info_stamp() +
                                "%s lost connection", app.nodes[C.NODE_LEADER])
            app.nodes[C.NODE_LEADER] = None
        finally:
            time.sleep(C.SLEEP_TIME)


def frontbeat():
    while True:
        if app.nodes[C.NODE_FRONT]:  # and app.nodes[C.NODE_LEADER]:
            friendhit()
            time.sleep(C.SLEEP_TIME)


def leader_checker():
    while True:
        if not app.nodes[C.NODE_LEADER]:
            app_logger.debug(debug_stamp() + 'Missing leader...')
            start_candidacy()
            time.sleep(C.SLEEP_TIME)


def connection(ip, port):
    app_logger.debug(debug_stamp() + 'Waiting for a friend...')
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
        if input_string == '--i' or input_string == '--info':
            print_info()
        elif input_string == '--l' or input_string == '--logout':
            logout()
        elif input_string == '--d' or input_string == '--debug':
            ch.setLevel(logging.DEBUG) if ch.level == logging.INFO else ch.setLevel(logging.DEBUG)
        else:
            try:
                if app.status == C.STATUS_LEADER:
                    send_regular_message_from_leader(input_string)
                else:
                    dstip, dstport = decode_id(app.nodes[C.NODE_LEADER])
                    app.conn.send_message(dstip, dstport, input_string, 0)
                app_logger.debug(debug_stamp() + 'Sending message: %s', input_string)
            except:
                app_logger.debug(debug_stamp() + 'Message has not been sent.')
                pass


def main_handler(ip, port):
    app.ip = ip
    app.port = port
    app.conn = Connector(ip, port)
    app.value = calc_value(encode_id(app.ip, app.port))
    app.id = encode_id(app.ip, app.port)
    app.nodes = {C.NODE_FRONT: None,
                 C.NODE_BACK: None,
                 C.NODE_LEADER: None,
                 C.NODE_BACKUP_FRONT: None}
    app.status = C.STATUS_FOLLOWER
    app.topology = []
    app.run(host=ip, port=port)


@click.command()
@click.argument('ipport')
@click.argument('friend')
@click.option('--DEBUG', '-d', is_flag=True)
def runner(ipport, friend, debug):
    if debug:
        ch.setLevel(logging.DEBUG)

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

# TODO LOGOUT
# TODO TESTING
