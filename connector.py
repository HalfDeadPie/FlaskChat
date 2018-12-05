import logging
import sys
import requests
import CONSTANTS as CONST
import json

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

class Connector:

    @staticmethod
    def build_url(ip, port):
        return 'http://' + ip + ':' + port + '/'

    @staticmethod
    def build_header(message_type, srcip, srcport):
        headers = {
            'message_type': message_type,
            'ip': srcip,
            'port': srcport
        }
        return headers

    @staticmethod
    def build_node_data(node):
        return json.dumps(node)

    @staticmethod
    def build_regular_message(text, time):
        message = {}
        message[CONST.MESSAGE_TEXT] = text
        message[CONST.MESSAGE_TIME] = time
        return json.dumps(message)

    @staticmethod
    def connect(srcip, srcport, dstip, dstport):
        headers = Connector.build_header(CONST.TYPE_CONNECT, srcip, srcport)
        url = Connector.build_url(dstip, dstport)
        result = requests.post(url, headers=headers, data='hello')
        print('Connecting...code ', str(result.status_code))
        return result.status_code

    @staticmethod
    def send_leader(srcip, srcport, dstip, dstport, leader):
        if leader:
            headers = Connector.build_header(CONST.TYPE_LEADER_INFO, srcip, srcport)
            url = Connector.build_url(dstip, dstport)
            leader_data = Connector.build_node_data(leader)
            result = requests.post(url, headers=headers, json=leader_data)
            logging.debug('Sending leader information...code %s', str(result.status_code))
        else:
            headers = Connector.build_header(CONST.TYPE_MISSING_LEADER, srcip, srcport)
            url = Connector.build_url(dstip, dstport)
            result = requests.post(url, headers=headers)
            logging.debug('Sending missing leader information...code %s', str(result.status_code))

    @staticmethod
    def send_message(srcip, srcport, dstip, dstport, text, time):
        headers = Connector.build_header(CONST.TYPE_MESSAGE, srcip, srcport)
        url = Connector.build_url(dstip, dstport)
        message_data = Connector.build_regular_message(text, time)
        result = requests.post(url, headers=headers, json=message_data)
        logging.debug('Sending message...code ', str(result.status_code))

    @staticmethod
    def send_candidate_info(srcip, srcport, dstip, dstport, info):
        headers = Connector.build_header(CONST.TYPE_CANDIDATE, srcip, srcport)
        url = Connector.build_url(dstip, dstport)
        candidate_data = Connector.build_node_data(info)
        result = requests.post(url, headers=headers, json=candidate_data)
        print('Sending candidate...code ', str(result.status_code))