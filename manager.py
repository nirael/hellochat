from hashlib import md5

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
	def __init__(self,t,u):
		self.threads = {'base':Topic('base'),'base1':Topic('base1')}
		self.users = {}
		for x in t:
			self.threads[x.name] = Topic(x.name)
		for x in u:
			self.users[x.name] = md5(x.password.encode()).hexdigest()
		print(str(self.users))
	def add_user(self,t):
		if t[0] not in self.users:
			self.users[t[0]] = t[1]
			return True
		return False
	def add_thread(self,t):
		if t not in self.threads:
			self.threads[t[0]] = Topic(t[1])
			return True
		return True
	def drop_user(self,uname):
		#the user is his password initially, so if there's an object , it should be unsubscribed and 
		#removed from the line of active users
		if not uname in self.users:return False
		if not isinstance(self.users.get(uname),str):
			usr = self.users.get(uname)
			self.remove(usr)
			usr.close()
		del self.users[uname]
		return True

	def drop_thread(self,tname):
		if self.threads.get(tname):
			thread = self.threads.get(tname)
			for x in thread.users:
				self.unsubscribe(x)
		else:return False
		del self.threads[tname]
		return True
	def send(self,client,msg):
		#send messages to all the users in the user thread , if there's not any , subscribe
		#user to the base thread
		thread = client.thread
		if not thread:
			self.threads['base'].add(client)
			client.thread = 'base'
			self.threads['base'].send(msg)
		else:
			self.threads[thread].send(msg)
	def add(self,client):
		#this is auth
		if client.uname in self.users:
			if isinstance(self.users[client.uname],str):
				print("adding client...")
				if self.users[client.uname] == client.password:
					self.users[client.uname] = client
					return True
		return False
	def remove(self,client):
		#logout
		if client.uname in self.users:
			if client.thread:
				self.threads[client.thread].remove(client)
			self.users[client.uname] = client.password
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
		if client.thread:
			client.thread = 'base'
			self.thread['base'].add(client)
			return self.threads[client.thread].remove(client)
		return False

