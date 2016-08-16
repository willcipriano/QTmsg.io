import string
import random
from random import randint
import time
import threading
import primegen
import mailer
import config

# Global assets
config = config.configurationData('chat')
room_list = dict()
primes = primegen.primes

# Vigenere with a OTP generated by Duffie-Hellman for key exchange between server and client.
# Not suitable for spies, soldiers, or Snowden but maybe useful to somebody.

keytable = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()-_=+{}|:;<>?,. "


def vigenere_encode(pw,string):

    config.debug('Vigenere encoding started on key ' + string)

    while len(str(pw) * 2) < len(string):
        pw = str(pw) + str(pw)
        config.debug('Weak Duffie-Hellman key detected "' + str(pw)[:len(string)] + '" used as key.',l=4)

    pw = str(pw)
    string = list(string)
    output = str()
    for i in range(len(string)):

        key = keytable.index(string[i]) + int(pw[:2])
        while key > len(keytable) - 1:
            key = key - len(keytable)
        pw = pw[2:]
        key = keytable[key]
        output = output + key


    config.debug('Vigenere encoding completed with output: ' + output)

    return output

def cur_time():
    return time.strftime(config.lookup('time_format'))


def token_gen(length):
    return ''.join(random.SystemRandom().choice(
        string.ascii_lowercase + string.ascii_uppercase
        + string.digits)
                   for _ in range(int(length)))


def room_update():
    to_be_removed = list()
    refresh_time = time.time() - 3600
    for chat_room in room_list:
        if room_list[chat_room].last_refresh <= refresh_time:
            to_be_removed.append(chat_room)
    for room in to_be_removed:
        del room_list[room]
    threading.Timer(60, room_update).start()



class Room:
    def __init__(self, room_name):
        randkey_length = randint(32, 64)
        salt_length = randint(16, 32)

        self.room = str(room_name)
        self.admin_tokens = list()
        self.users = dict()
        self.tokens = dict()
        self.chat = dict()
        self.randKey = token_gen(randkey_length)
        self.salt = token_gen(salt_length)
        self.password = False

        self.chat[1] = 'roomUpdate*<b>' + 'Welcome to ' + self.room + ', it is ' + cur_time() + '.'

        self.last_update = time.time()
        self.last_refresh = time.time()
        self.duffie_hellman_keys = dict()

    def check_admin(self, token):
        print token
        print self.admin_tokens
        if token in self.admin_tokens:
            return True
        else:
            return False

    def message(self, token, message, crypto):
        if token in self.tokens:
            self.last_update = time.time()
            username = self.tokens[str(token)]
            if crypto != 'false':
                self.chat[len(self.chat) + 1] = 'crypt*' + str(username) + ': ' + str(message)
            else:
                self.chat[len(self.chat) + 1] = 'msg*' + str(username) + ': ' + str(message)
            return True
        else:
            return False

    def get_chat(self, last_id, token):

        if token in self.tokens:
            self.last_refresh = time.time()
            new_messages = dict()
            for messageid in self.chat:
                if int(messageid) > int(last_id):
                    new_messages[messageid] = self.chat[messageid]
            return new_messages
        else:
            return False

    def new_user(self, username):
        token_len = randint(20, 30)
        token = token_gen(token_len)
        if username not in self.users.keys():
            if len(self.tokens) <= 0:
                self.admin_tokens.append(token)
            self.users[username] = token
            self.tokens[token] = username
            self.chat[len(self.chat) + 1] = 'roomUpdate*' + str(username) + ' has joined the room at ' + cur_time()
            return self.users[username]
        else:
            return False


    def set_crypto(self, token):
        if self.check_admin(token):
            self.chat[len(self.chat) + 1] = 'cryptUpdate*<b>' + self.tokens[
                str(token)] + ' has enabled cryptography for this chat, at ' + cur_time()
            return True
        else:
            return False

    def roll_die(self, token, sides):
        if token in self.tokens:
            if sides > 1:
                roll_result = randint(1, int(sides))
            else:
                roll_result = 1
            self.chat[len(self.chat) + 1] = 'diceRoll*' + self.tokens[str(token)] + ' rolled a ' + str(
                roll_result) + '/' + str(sides)
            return roll_result
        else:
            return False

    def invite_user(self, token, recipient, message):
        if token in self.tokens:
            username = self.tokens[str(token)]
            mailer.invite_user(username, recipient, message, self.room)
            self.chat[len(self.chat) + 1] = 'newUserInvite*' + self.tokens[
                str(token)] + ' invited ' + recipient + ' to the chat at ' + cur_time()
            return True
        else:
            return False

    def admin_exec(self, token, function, argument):
        if token in self.tokens:
            if self.check_admin(token):

                # Admins are immune to admin actions
                if self.users[argument] in self.admin_tokens:
                    return False

                if function == 'kick':
                    for user in self.users:
                        if user == argument:
                            try:
                                del self.tokens[self.users[argument]]
                                del self.users[argument]
                                self.chat[len(self.chat) + 1] = 'roomUpdate*<i>' + user + ' has been kicked from ' + self.room + ' at ' + cur_time() + '.</i>'
                                return True
                            except KeyError:
                                return False
                    return False

                if function == 'promote':
                    for user in self.users:
                        print user
                        print argument
                        if user == argument:
                            try:
                                if self.tokens[self.users[argument]] not in self.admin_tokens:
                                    self.admin_tokens.append(self.users[argument])
                                    self.chat[len(self.chat) + 1] = 'roomUpdate*<i>' + user + ' has been promoted to admin on ' + self.room + ' at ' + cur_time() + '.</i'
                                return True
                            except KeyError:
                                return False
                    return False

    def user_list(self, token):
        if token in self.tokens:
            x = 0
            users = dict()
            for user in self.users:
                users[x] = user
                x += 1
            return users

    def duffie_hellman_negotiate(self, token):
        if token in self.tokens:
            public_n = random.choice(primes)
            public_g = random.choice(primes)
            while public_n is public_g:
                public_g = random.choice(primes)
            private_key = random.SystemRandom().getrandbits(config.lookup('dh_private_bits'))
            public_key = (public_g**private_key)%public_n
            while public_key is 0:
                private_key = random.SystemRandom().getrandbits(config.lookup('dh_private_bits'))
                public_key = (public_g**private_key)%public_n
            key_storage = {'public_n':public_n,'public_g':public_g,'private_key':private_key}
            self.duffie_hellman_keys[token] = key_storage
            return {'public_n':str(public_n),'public_g':str(public_g),'server_key':str(public_key)}
        else:
            return False

    def duffie_hellman_calculate(self,token,client_public_key):
        if token in self.tokens:
            keydata = self.duffie_hellman_keys[token]
            crypto_key = (int(client_public_key)**keydata['private_key'])%keydata['public_n']
            # XOR chat key with DH key we just created and send to client
            # NOTE:
            # I understand this is mostly a heavy level of obfuscation as opposed to security, but this should
            # also be wrapped in SSL.This is merely a countermeasure to prevent nosy sysadmins in
            # corporate environments.
            return vigenere_encode(crypto_key,self.randKey + ':' + self.salt)
        else:
            return False

def get_room(room):
    global room_list
    if room not in room_list:
        room_list[room] = Room(room)
        return room_list[room]
    else:
        return room_list[room]


room_update()
