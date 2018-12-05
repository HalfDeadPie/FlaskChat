import CONSTANTS as CONST
import string

class Del:
  def __init__(self, keep=string.digits):
    self.comp = dict((ord(c),c) for c in keep)
  def __getitem__(self, k):
    return self.comp.get(k)

DD = Del()

def encode_id(ip, port):
    return ip + ':' + port

def decode_id(id):
    ip, port = id.split(':')
    return ip, port

def format_regular_message(message):
    return '[' + str(message[CONST.MESSAGE_TIME]) + ']: ' + str(message[CONST.MESSAGE_TEXT])

def build_node(name, ip, port):
    return {name: encode_id(ip, port)}

def calc_value(id):
    return id.translate(DD)