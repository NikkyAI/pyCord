import datetime
import yaml

class Message(object):

# {'text': '!test --help', 'channel': 'bridge-test', 'username': 'Nikky', 'avatar': 'https://cdn.discordapp.com/avatars/11222862436
# 6575616/6c8d3b490bd3e56afc2b2e191f9c0767.jpg', 'account': 'discord.teamdev', 'event': '', 'protocol': 'discord', 'gateway': 'test
# 2', 'timestamp': '2017-06-06T22:26:08.759413856+02:00'}
    def __init__(self, text: str, channel: str = None, username: str = None, avatar: str = None, account: str = None, event: str = None, protocol: str = None, gateway: str = None, timestamp: datetime = None):
        self.text = text
        self.channel = channel
        self.username = username
        self.avatar = avatar
        self.account = account
        self.event = event
        self.protocol = protocol
        self.gateway = gateway
        self.timestamp = timestamp

    def __repr__(self):
        return yaml.dump(self, default_flow_style=True)

    def create_response(self, response: str):
        #TODO: append original username in front of message string?
        response_message = Message(text = response, gateway = self.gateway)
        # self.libcord.send(response_message)
        return response_message