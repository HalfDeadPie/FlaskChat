import logging as L
import sys
import requests
import CONSTANTS as CONST
import json

# LOGGING SETTINGS
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

class Connector:

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def build_url(self, ip, port):
        return 'http://' + ip + ':' + port + '/'

    def build_header(self, message_type, srcip, srcport):
        headers = {
            'message_type': message_type,
            'ip': srcip,
            'port': srcport
        }
        return headers

    def build_node_json(self, node):
        return json.dumps(node)

    def build_regular_message(self, text, time):
        message = {}
        message[CONST.MESSAGE_TEXT] = text
        message[CONST.MESSAGE_TIME] = time
        return json.dumps(message)

    def connect(self, dstip, dstport):
        headers = self.build_header(CONST.TYPE_CONNECT, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        result = requests.post(url, headers=headers, data='hello')
        return result.status_code

    def send_leader(self, dstip, dstport, leader):
        if leader:
            headers = self.build_header(CONST.TYPE_LEADER_INFO, self.ip, self.port)
            url = self.build_url(dstip, dstport)
            leader_data = self.build_node_json(leader)
            result = requests.post(url, headers=headers, json=leader_data)
        else:
            headers = self.build_header(CONST.TYPE_MISSING_LEADER, self.ip, self.port)
            url = self.build_url(dstip, dstport)
            result = requests.post(url, headers=headers)

    def send_message(self, dstip, dstport, text, time):
        headers = self.build_header(CONST.TYPE_MESSAGE, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        message_data = self.build_regular_message(text, time)
        result = requests.post(url, headers=headers, json=message_data)

    def send_candidate(self, dstip, dstport, info):
        headers = self.build_header(CONST.TYPE_CANDIDATE, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        candidate_data = self.build_node_json(info)
        result = requests.post(url, headers=headers, json=candidate_data)

    def send_back_setting(self, dstip, dstport, info):
        headers = self.build_header(CONST.TYPE_BACK, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        back_json = self.build_node_json(info)
        result = requests.post(url, headers=headers, json=back_json)

    def send_front_setting(self, dstip, dstport, info):
        headers = self.build_header(CONST.TYPE_FRONT, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        back_json = self.build_node_json(info)
        result = requests.post(url, headers=headers, json=back_json)

    def heartbeat(self, dstip, dstport):
        headers = self.build_header(CONST.TYPE_HEARTBEAT, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        result = requests.post(url, headers=headers)

