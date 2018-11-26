import requests
import CONSTANTS as CONST

class Connector:

    @staticmethod
    def buildURL(ip, port):
        return 'http://' + ip + ':' + port + '/'

    @staticmethod
    def buildHeaders(message_type):
        return { 'message_type' : message_type }

    @staticmethod
    def connect(ip, port):
        headers = Connector.buildHeaders(CONST.TYPE_CONNECT)
        url = Connector.buildURL(ip, port)
        result = requests.post(url, headers=headers, data='hello')
        print(result.text)