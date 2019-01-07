import logging as L
import sys
import requests
import CONSTANTS as CONST
import json

# LOGGING SETTINGS
from support import encode_id, decode_id

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

    def build_regular_message(self, text, time, origin):
        message = {}
        message[CONST.MESSAGE_TEXT] = text
        message[CONST.MESSAGE_TIME] = time
        message[CONST.MESSAGE_ORIGIN] = origin
        return json.dumps(message)

    def build_message_from_dict(self, message):
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
        origin = encode_id(self.ip, self.port)
        message_data = self.build_regular_message(text, time, origin)
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

    def send_front_front_setting(self, dstip, dstport, info):
        headers = self.build_header(CONST.TYPE_FRONT_FRONT, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        back_json = self.build_node_json(info)
        result = requests.post(url, headers=headers, json=back_json)

    def heartbeat(self, dstip, dstport):
        headers = self.build_header(CONST.TYPE_HEARTBEAT, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        result = requests.post(url, headers=headers)
        return result.status_code

    def friendbeat(self, dstip, dstport):
        headers = self.build_header(CONST.TYPE_FRIENDBEAT, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        result = requests.post(url, headers=headers)
        if str(result.status_code) == CONST.CODE_OK:
            return result.json()
        else:
            return None

    def death_report(self, dstip, dstport, dead_node):
        headers = self.build_header(CONST.TYPE_DEATH, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        dead_node_data = self.build_node_json(dead_node)
        result = requests.post(url, headers=headers, json=dead_node_data)

    def logout_report(self, dstip, dstport, loggedout_node):
        headers = self.build_header(CONST.TYPE_LOGOUT, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        dead_node_data = self.build_node_json(loggedout_node)
        result = requests.post(url, headers=headers, json=dead_node_data)

    def new_node_report(self, dstip, dstport, new_node):
        headers = self.build_header(CONST.TYPE_NEW, self.ip, self.port)
        url = self.build_url(dstip, dstport)
        dead_node_data = self.build_node_json(new_node)
        result = requests.post(url, headers=headers, json=dead_node_data)

    def broadcast(self, message, topology):
        headers = self.build_header(CONST.TYPE_MESSAGE, self.ip, self.port)
        message_data = self.build_message_from_dict(message)
        for node in topology:
            try:
                dstip, dstport = decode_id(node)
                url = self.build_url(dstip, dstport)
                result = requests.post(url, headers=headers, json=message_data)
            except:
                pass

    def broadcast_loggedout_node(self, loggedout_node, topology):
        headers = self.build_header(CONST.TYPE_INFO_LOGOUT, self.ip, self.port)
        loggedout_data = self.build_node_json(loggedout_node)
        for node in topology:
            try:
                dstip, dstport = decode_id(node)
                url = self.build_url(dstip, dstport)
                result = requests.post(url, headers=headers, json=loggedout_data)
            except:
                pass

    def broadcast_new_node(self, new_node, topology):
        headers = self.build_header(CONST.TYPE_INFO_NEW, self.ip, self.port)
        new_data = self.build_node_json(new_node)
        for node in topology:
            try:
                dstip, dstport = decode_id(node)
                url = self.build_url(dstip, dstport)
                result = requests.post(url, headers=headers, json=new_data)
            except:
                pass

    def broadcast_dead_node(self, dead_node, topology):
        headers = self.build_header(CONST.TYPE_INFO_DEATH, self.ip, self.port)
        dead_data = self.build_node_json(dead_node)
        for node in topology:
            try:
                dstip, dstport = decode_id(node)
                url = self.build_url(dstip, dstport)
                result = requests.post(url, headers=headers, json=dead_data)
            except:
                pass