import os

TYPE_CONNECT = 'CONNECT'
TYPE_ACCEPT_CONNECTION = 'ACCEPT_CONNECTION'
TYPE_LEADER_INFO = 'LEADER_INFO'
TYPE_MISSING_LEADER = 'MISSING_LEADER'
TYPE_MESSAGE = 'REGULAR_MESSAGE'
TYPE_CANDIDATE = 'CANDIDATE'

TYPE_IN_MESSAGE = 'IN_REGULAR_MESSAGE'
TYPE_IN_INIT = 'IN_INIT'

HEADER_MESSAGE = 'Message-Type'
HEADER_IP = 'ip'
HEADER_PORT = 'port'
HEADER_NICKNAME = 'nickname'
HEADER_STATE = 'state'

MESSAGE_TEXT = 'text'
MESSAGE_TIME = 'time'

STATE_FRIEND = 'FRIEND'
STATE_FOLLOWER = 'FOLLOWER'
STATE_LEADER = 'LEADER'
STATE_VOTING = 'VOTING'