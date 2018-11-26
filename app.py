import flask
import CONSTANTS as CONST
from flask import Flask, request
from connector import Connector

app = Flask(__name__)

def connect(ip, port):
    Connector.connect(ip, port)

def acceptConnection():
    print('Connection Accepted')

def processGet():
    """
    Processing GET method
    :return:
    """
    return flask.render_template('index.html')


def processPost():
    """
    Processing POST method
    """
    if 'Message-Type' in request.headers:
        message_type = request.headers['Message-Type']
        if message_type == CONST.TYPE_CONNECT:
            print('Someone is trying to connect!')
            return 'Are you connecting?'
    else:
        ip = request.form['ip']
        port = request.form['port']
        print(ip)
        print(port)
        connect(ip, port)
        return flask.render_template('chat.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Process connecting to default route (index)
    """
    method = request.method
    if method == 'GET':
        return processGet()
    elif method == 'POST':
        return processPost()

if __name__ == '__main__':
    app.run()
