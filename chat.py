from .chattools import *
import time
import threading
from socket import *
from .manager import Manager

def now():
	return time.ctime(time.time())

#functions for manipulating 
def encode(data):
	msg = Frame.buildMessage(data.encode(),mask=False)
	return msg

def decode(f):
	return "".join([chr(x) for x in f.message()])

class SocketServer:
	def __init__(self,host,port,manager):
		self.manager = manager
		self.sock = socket(AF_INET,SOCK_STREAM)
		self.sock.bind((host,port))
		self.sock.listen(5)
		self.lock = threading.Lock()
	def start(self):
		while True:
			connection,address = self.sock.accept()
			print("New connection at " + now() + "!")
			Handler(connection,self.manager,self.lock).start()
		self.stop()
	def stop(self):
		self.sock.close()

class Client(threading.Thread):
	handshaken = []
	def __init__(self,con,manager,lock):
		self.lock = lock
		self.sock = con
		self.manager = manager
		self.uname = None
		self.thread = None
		self.password = None
		threading.Thread.__init__(self)
	def close(self):
		if self.sock in self.handshaken:
			self.handshaken.remove(self.sock)
		self.sock.close()
		self.manager.remove(self)
	def run(self):
		while True:
			if self.sock not in self.handshaken:
				data = self.sock.recv(10000)
				upgrade = Handshake.upgrade(data)
				if not upgrade:break
				self.handshaken.append(self.sock)
				self.sock.send(upgrade.encode())
				continue
			else:
				data = self.sock.recv(1024)
				if not data:break
				frame = Frame(data)
				if frame.opcode == 1:
					#actually not sure if this lock is necessary
					with self.lock:
						self.handle(decode(frame))
				else:
					break
		self.close()
		print("Connection closed! ", now())

class Handler(Client):
	#format : a: b\r\nc: d\r\n,query type is a must
	def parse_headers(self,headers):
		final = {}
		s = headers.split('\r\n')
		for val in s:
			if len(val) > 4:
				delim = val.find(":")
				final[val[:delim]] = val[delim+2:]
		return final
	def handle(self,query):
		data = self.parse_headers(query)
		qr = data.get('query')
		if not qr:return False
		if qr in "auth|message|subscribe|unsubscribe".split("|"):
			getattr(self,qr)(data)
		else:self.sock.send(encode("Invalid query!"))
	def auth(self,data):
		name = data.get('name')
		password = data.get('password')
		self.uname = name
		self.password = password
		action = self.manager.add(self)
		if action:
			self.uname = name
			self.sock.send(encode("You've connected!"))
			self.manager.send(self,encode("User "+ self.uname + " has connected!"))
		else:
			self.sock.send(encode("""You cannot connect as you did not log in on the server 
				or you have already logged in in the chat!"""))
	def message(self,data):
		if not self.check_auth():return
		message = data.get('message')
		if message:
			self.manager.send(self,encode("User " + self.uname + " : " + message))
		else:
			self.sock.send(encode("You cannot send this message =("))
	def subscribe(self,data):
		if not self.check_auth():return
		topic = data.get('topic')
		if topic:
			self.sock.send(encode("Trying to subscribe to the " + topic))
			sub = self.manager.subscribe(self,topic)
			if sub:self.manager.send(self,encode("User " + self.uname + " has joined us!"))
			else:self.sock.send(encode("Subscription failed!"))
		else:
			self.sock.send(encode("You did not define the topic!"))
	def unsubscribe(self,data):
		if not self.check_auth():return
		self.sock.send(encode("Unsubscribing..."))
		self.manager.send(self,encode("User " + self.uname + " unsubscribed"))
		unsub = self.manager.unsubscribe(self)
		if unsub:self.sock.send(encode("You've unsubscribed!"))
	def check_auth(self):
		if not self.uname:
			self.sock.send(encode("You should log in!"))
			return False
		return True



#if __name__ == '__main__':
	#manager = Manager([{'name':'test'}])
	#server = SocketServer('',50001,manager)
	#server.start()
