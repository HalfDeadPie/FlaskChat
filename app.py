import json

import flask
from click._unicodefun import click
import CONSTANTS as CONST
from flask import Flask, request
from connector import Connector
from node import Node

app = Flask(__name__)
my_ip = None
my_port = None
my_friend = {}
my_state = CONST.STATE_FOLLOWER
my_messages = [ ]
my_leader = {}

# ----------------------------------------------------------------------------------------------------------------------
def isMine(ip):
    return ip == my_ip

def encode_id(ip, port):
    return ip + ':' + port

def decode_id(id):
    ip, port = id.split(':')
    return ip, port

def processRegularMessage(message):
    final_message = '[' + str(message[CONST.MESSAGE_TIME]) + ']: ' + str(message[CONST.MESSAGE_TEXT])
    my_messages.append(final_message)

def welcome(dstip, dstport):
    Connector.sendLeader(my_ip, my_port, dstip, dstport, my_leader)

def processLeaderInfo(leader_info):
    my_leader[CONST.STATE_LEADER] = leader_info[CONST.STATE_LEADER]

# ----------------------------------------------------------------------------------------------------------------------

def innerHandler():

    # CONNECTION
    if request.form['message_type'] == CONST.TYPE_IN_INIT:
        dstip = request.form['ip']
        dstport = request.form['port']
        result = Connector.connect(my_ip, my_port, dstip, dstport)
        if result == 200:
            global my_friend
            my_friend = { CONST.STATE_FRIEND: encode_id(dstip, dstport)}

    # MESSAGE
    elif request.form['message_type'] == CONST.TYPE_IN_MESSAGE:
        Connector.sendMessage(my_ip, my_port, '192.168.122.9', '5009', request.form['message'], 10)
        #TODO send message to LEADER
        #TODO make form on HTML!

    print('inner handler my friend:', my_friend)
    return flask.render_template('chat.html',
                                 messagelist=my_messages,
                                 friend = my_friend[CONST.STATE_FRIEND])

def outterHandler():
    headers = request.headers
    if 'Message-Type' in headers:
        message_type = headers['Message-Type']

        # CONNECTION
        if message_type == CONST.TYPE_CONNECT:
            dstip = headers[CONST.HEADER_IP]
            dstport = headers[CONST.HEADER_PORT]
            welcome(dstip, dstport)

        # LEADER
        elif message_type == CONST.TYPE_LEADER_INFO:
            received_leader_info = json.loads(request.json)
            processLeaderInfo(received_leader_info)

        # MISSING LEADER
        elif message_type == CONST.TYPE_MISSING_LEADER:
            print('RECEIVED MISSING LEADER INFO!')

        # MESSAGE
        elif message_type == CONST.TYPE_MESSAGE:
            print('Received regular message')
            received_message = json.loads(request.json)
            processRegularMessage(received_message)

    return flask.render_template('chat.html',
                                 messagelist=my_messages,
                                 friend=my_friend[CONST.STATE_FRIEND])

# ----------------------------------------------------------------------------------------------------------------------

def processGet():
    if isMine(request.remote_addr):
        return flask.render_template('index.html')
    else:
        return flask.render_template('error.html')

def processPost():
    if isMine(request.remote_addr):
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

@click.command()
@click.argument('ip')
@click.argument('port')
def runner(ip, port):
    global my_ip
    my_ip = ip

    global my_port
    my_port = port

    global my_friend
    my_friend = {CONST.STATE_FRIEND: None}

    global my_leader
    my_leader = {CONST.STATE_LEADER : None}

    app.run(host=ip, port=port)

if __name__ == '__main__':
    runner(obj={})

