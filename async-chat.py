import asyncio
import logging
import concurrent.futures
from chattools import *
from asyncmanager import Manager

def encode(msg):
    return Frame.buildMessage(msg.encode(),mask=False)

def decode(frm):
    return "".join([chr(x) for x in frm.message()])


class EchoServer(object):
    """Echo server class"""
    clients = []
    def __init__(self, host, port, loop=None):
        self._loop = loop or asyncio.get_event_loop() 
        self._server = asyncio.start_server(self.handle_connection, host=host, port=port)
        self.manager = Manager([{'name':'test'}])
    
    def start(self, and_loop=True):
        self._server = self._loop.run_until_complete(self._server)
        logging.info('Listening established on {0}'.format(self._server.sockets[0].getsockname()))
        if and_loop:
            self._loop.run_forever()
    
    def stop(self, and_loop=True):
        self._server.close()
        if and_loop:
            self._loop.close()
    def is_in(self,sock):
        return any([x['sock'] == sock for x in self.clients])
    def set_prop(self,writer,name,value):
                writer[name] = value
    def get_client(self,writer):
        for x in self.clients:
            if x['sock'] == writer:return x 
    def remove(self,sock):
        for x in self.clients:
            if x['sock'] == sock:
                del x
    def parse_headers(self,headers):
        final = {}
        s = headers.split('\r\n')
        for val in s:
            if len(val) > 4:
                delim = val.find(":")
                final[val[:delim]] = val[delim+2:]
        return final
    def handle(self,query,writer):
        data = self.parse_headers(query)
        qr = data.get('query')
        if not qr:return False
        if qr in "message|subscribe|unsubscribe|name".split("|"):
            getattr(self,qr)(data,writer)
        else:wirter.write(encode("Invalid query!"))
    def name(self,data,writer):
        name = data.get('name')
        if not name:
            writer['sock'].write(encode("You should specify your name!"))
            return
        self.set_prop(writer,'name',name)
        writer['sock'].write(encode("Your name is "+name))
    def message(self,data,writer):
        message = data.get('message')
        if message:
            self.manager.send(writer,encode("User " + writer.get('name') + " : " + message))
        else:
            writer['sock'].write(encode("You cannot send this message =("))
    def subscribe(self,data,writer):
        topic = data.get('topic')
        if topic:
            writer['sock'].write(encode("Trying to subscribe to the " + topic))
            sub = self.manager.subscribe(writer,topic)
            if sub:self.manager.send(writer,encode("User " + writer.get('name') + " has joined us!"))
            else:writer['sock'].write(encode("Subscription failed!"))
        else:
            writer.write(encode("You did not define the topic!"))
    def unsubscribe(self,data,writer):
        writer['sock'].write(encode("Unsubscribing..."))
        self.manager.send(writer,encode("User " + writer.get('name') + " unsubscribed"))
        unsub = self.manager.unsubscribe(writer)
        if unsub:writer['sock'].write(encode("You've unsubscribed!"))
    @asyncio.coroutine    
    def handle_connection(self, reader, writer):
        peername = writer.get_extra_info('peername')
        logging.info('Accepted connection from {}'.format(peername))
        while True:
            data = b""
            try:
                if not self.is_in(writer):
                    data = yield from reader.read(10000)
                    upgrade = Handshake.upgrade(data)
                    if not upgrade:break
                    writer.write(upgrade.encode())
                    self.clients.append({'sock':writer})
                    continue
                data = yield from reader.read(1024)
                if not data:break  
                frm = Frame(data)
                
                try:
                    if frm.opcode == 1:
                        dt = decode(frm)
                        client = self.get_client(writer)
                        self.handle(dt,client)
                except Exception:
                    pass
                finally:
                    yield from writer.drain()
            except concurrent.futures.TimeoutError:
                break
        writer.close()
        self.remove(writer)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    server = EchoServer('127.0.0.1', 50001)
    try:
        server.start()
    except KeyboardInterrupt:
        pass # Press Ctrl+C to stop
    finally:
        server.stop()
