import requests
import CONSTANTS as CONST
import json


class Connector:

    @staticmethod
    def buildURL(ip, port):
        return 'http://' + ip + ':' + port + '/'

    @staticmethod
    def buildHeaders(message_type, srcip, srcport):
        headers = {
            'message_type': message_type,
            'ip': srcip,
            'port': srcport
        }
        return headers

    @staticmethod
    def buildLeaderData(leader):
        return json.dumps(leader)

    @staticmethod
    def buildRegularMessage(text, time):
        message = {}
        message[CONST.MESSAGE_TEXT] = text
        message[CONST.MESSAGE_TIME] = time
        return json.dumps(message)

    @staticmethod
    def connect(srcip, srcport, dstip, dstport):
        headers = Connector.buildHeaders(CONST.TYPE_CONNECT, srcip, srcport)
        url = Connector.buildURL(dstip, dstport)
        result = requests.post(url, headers=headers, data='hello')
        print('Connecting [{}]' .format(result.status_code))
        return result.status_code

    @staticmethod
    def sendLeader(srcip, srcport, dstip, dstport, leader):
        if leader:
            headers = Connector.buildHeaders(CONST.TYPE_LEADER_INFO, srcip, srcport)
            url = Connector.buildURL(dstip, dstport)
            leader_data = Connector.buildLeaderData(leader)
            result = requests.post(url, headers=headers, json=leader_data)
            print('Sending leader information [{}]' .format(result.status_code))
        else:
            headers = Connector.buildHeaders(CONST.TYPE_MISSING_LEADER, srcip, srcport)
            url = Connector.buildURL(dstip, dstport)
            result = requests.post(url, headers=headers)
            print('Sending missing leader information [{}]' .format(result.status_code))

    @staticmethod
    def sendMessage(srcip, srcport, dstip, dstport, text, time):
        headers = Connector.buildHeaders(CONST.TYPE_MESSAGE, srcip, srcport)
        url = Connector.buildURL(dstip, dstport)
        message_data = Connector.buildRegularMessage(text, time)
        result = requests.post(url, headers=headers, json=message_data)
        print('Sending message [{}]' .format(result.status_code))