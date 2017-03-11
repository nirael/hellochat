from hashlib import md5
#for the future use 
import asyncio

class Topic:
	def __init__(self,name):
		self.uname = name
		self.users = []
	def send(self,msg):
		for x in self.users:
				x['sock'].write(msg)
	def add(self,client):
		if not self.is_in(client['sock']):
			self.users.append(client)
			return True
		else:return False
	def remove(self,client):
		if self.is_in(client['sock']):
			self.users.remove(client)
			return True
		return False
	def is_in(self,obj):
		return any([x['sock'] == obj for x in self.users])

class Manager:
	def __init__(self,t):
		self.threads = {'base':Topic('base'),'base1':Topic('base1')}
		for x in t:
			self.threads[x['name']] = Topic(x['name'])
	def send(self,client,msg):
		thread = client.get('thread')
		if not thread:
			self.threads['base'].add(client)
			client['thread'] = 'base'
			self.threads['base'].send(msg)
		else:
			self.threads[thread].send(msg)
	def subscribe(self,client,t):
		thread = self.threads.get(t)
		if thread:
			if client.get('thread'):
				try:
					self.threads[client['thread']].remove(client)
				except KeyError:
					pass
				client['thread'] = thread.uname
			return thread.add(client)
		return False
	def unsubscribe(self,client):
		return self.subscribe(client,'base')
		#possible error
		if client.thread:
			client.thread = 'base'
			self.thread['base'].add(client)
			return self.threads[client.thread].remove(client)
		return False

