import requests

TYPE_CONNECT = 'CONNECT'

class Requestor:

    @staticmethod
    def buildURL(ip, port):
        return 'http://' + ip + ':' + port + '/'

    @staticmethod
    def buildHeaders(message_type):
        return { 'message_type' : message_type }

    @staticmethod
    def connect(ip, port):
        headers = Requestor.buildHeaders(TYPE_CONNECT)
        url = Requestor.buildURL(ip, port)
        result = requests.post(url, headers=headers, data='hello')
        print(result.text)

Requestor.connect('127.0.0.1', '5000')