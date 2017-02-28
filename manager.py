

class Topic:
	def __init__(self,name):
		self.uname = name
		self.users = []
	def send(self,msg):
		for x in self.users:
			try:
				x.sock.send(msg)
			except OSError:
				self.users.remove(x)
	def add(self,client):
		if not client in self.users:
			self.users.append(client)
			return True
		else:return False
	def remove(self,client):
		if client in self.users:
			self.users.remove(client)
			return True
		return False

class Manager:
	def __init__(self,t):
		self.threads = {'base':Topic('base'),'base1':Topic('base1')}
		self.users = {'test':'test','test1':'ttt'}
		for x in t:
			self.threads[x['name']] = Topic(x['name'])
	def send(self,client,msg):
		thread = client.thread
		if not thread:
			self.threads['base'].add(client)
			client.thread = 'base'
			self.threads['base'].send(msg)
		else:
			self.threads[thread].send(msg)
	def add(self,client):
		if client.uname in self.users:
			if isinstance(self.users[client.uname],str):
				print("adding client...")
				if self.users[client.uname] == client.password:
					self.users[client.uname] = client
					return True
		return False
	def remove(self,client):
		if client.uname in self.users:
			if client.thread:
				self.threads[client.thread].remove(client)
			self.users[client.uname] = client.password
	def unlog(self,name):
		pass
	def subscribe(self,client,t):
		thread = self.threads.get(t)
		if thread:
			if client.thread:
				try:
					self.threads[client.thread].remove(client)
				except KeyError:
					pass
				client.thread = thread.uname
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

