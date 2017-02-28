"""
Morgan Reece Phillips
linux-poetry.com mrrrgn.com @linuxpoetry
"""

import random
from base64 import b64encode
from hashlib import sha1
from re import search

class Frame(object):
    """
    A highly documented class implementing everything required to decode and
    encode byte arrays as data frames following WebSocket specification.
    For more information see:
    http://www.altdevblogaday.com/2012/01/23/writing-your-own-websocket-server/
    """

    def __init__(self,  buf):
        # FIRST BYTE OF HEADER
        # | fin 1bit | rsv1 1bit | rsv2 1bit | rsv3 1bit | opcode 4bit |
        self.fin = 0  # Is this the final fragment?
        self.opcode = 0  # What kind of data is this?

        # SECOND BYTE OF HEADER
        # | mask 1bit | payload length 7 bit |
        self.mask = 0  # Is there a mask?
        self.payload_length = 0

        self.mask_key = bytearray()  # mask key, 32 random bits
        self.len = 0  # payload length -or- extended payload length
        self.buf = buf
        self.msg = bytearray()  # payload data
        self.frame_length = 0  # total data frame size (payload + header)
        self.isReady()

    def isReady(self):
        """
        Parse the current buffer data and perform sanity checks.
        """

        buf = self.buf
        # The min header size is two bytes, so anything less is FUBAR.
        if len(buf) < 2:
            raise Exception("Incomplete Frame: HEADER DATA")

        # Parse the first two bytes of header.
        self.fin = buf[0] >> 7
        self.opcode = buf[0] & 0b1111
        self.payload_length = buf[1] & 0b1111111
        self.mask = buf[1] >> 7

        # Trim header off the data buffer.
        buf = buf[2:]

        # payload length can denote different things depending on its value:
        if self.payload_length < 126:

            # payload_length of 126 indicates that the actual payload length is
            self.len = self.payload_length

            if self.mask:
                # 32 bit mask + 16 bit header
                self.frame_length = 6 + self.len
            else:
                # just 16 bit header
                self.frame_length = 2 + self.len

            # Sanity checking the buffer sizes against header fields.
            if self.frame_length > len(self.buf):
                raise Exception("Incomplete Frame: FRAME DATA")
            if len(buf) < 4 and self.mask:
                raise Exception("Incomplete Frame: KEY DATA")

            if self.mask:
                # the mask key value
                self.mask_key = buf[:4]
                # strip the mask key from the buffer
                buf = buf[4:4+len(buf)+1]
            else:
                # no mask so we're good to go
                buf = buf[:self.len]

        # A payload_length of 126 indicates that payload size is
        # actually stored in a 16 bit 'extended payload' field.
        elif self.payload_length == 126:

            # Sanity check.
            if len(buf) < 6 and self.mask:
                raise Exception("Incomplete Frame: KEY DATA")

            # Concatenate the next two bytes into a single 16 bit int.
            for k, i in [(0, 1), (1, 0)]:
                self.len += buf[k] * 1 << (8*i)

            if self.mask:
                # 16 bit extended + 16 bit header + 32 bit mask
                self.frame_length = 8 + self.len
            else:
                self.frame_length = 4 + self.len

            # Sanity check.
            if self.frame_length > len(self.buf):
                raise Exception("Incomplete Frame: FRAME DATA")

            # Strip the remaining header data from the buffer.
            buf = buf[2:]
            if self.mask:
                self.mask_key = buf[:4]
                buf = buf[4:4+len(buf)+1]
            else:
                buf = buf[:self.len]

        # A payload length of 127 indicates a 64 bit extended payload length
        else:

            # Sanity check.
            if len(buf) < 10 and self.mask:
                raise Exception("Incomplete Frame: KEY DATA")

            # Concatenate the next 8 bytes into a 64 bit integer.
            for k, i in [(0, 7), (1, 6), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1), (7, 0)]:
                self.len += buf[k] * 1 << (8*i)

            if self.mask:
                # 16 bit header + 64 bit extended payload + 32 bit mask
                self.frame_length = 14 + self.len
            else:
                self.frame_length = 10 + self.len

            # Sanity check.
            if self.frame_length > len(self.buf):
                raise Exception("Incomplete Frame: FRAME DATA")

            # Strip remaining header data from the buffer.
            buf = buf[8:]
            if self.mask:
                self.mask_key = buf[:4]
                buf = buf[4:4+len(buf)+1]
            else:
                buf = buf[self.len]

        # everything remaining is just the payload/message
        self.msg = buf

    def message(self):
        """
        Return payload data, with masking if necessary.
        """
        if not self.mask:
            return self.msg
        decoded_msg = bytearray()
        for i in range(self.len):
            # Each byte in the message should be not-ored against a
            # byte of the mask key.  The mask key byte rotates via modulus.
            c = self.msg[i] ^ self.mask_key[i % 4]
            decoded_msg.append(c)
        return decoded_msg

    def length(self):
        return self.frame_length

    @staticmethod
    def encodeMessage(buf, key):
        """ Apply a mask to some message data."""
        encoded_msg = bytearray()
        buf_len = len(buf)
        for i in range(buf_len):
            c = buf[i] ^ key[i % 4]
            encoded_msg.append(c)
        return encoded_msg

    @staticmethod
    def buildMessage(buf, mask=True):
        """
        Build a data frame from scratch.
        """
        msg = bytearray()

        # Generate a mask key: 32 random bits.
        if mask:
            key = [(random.randrange(1, 255)) for i in range(4)]

        # Build the first byte of header.
        ##
        # The first byte indicates that this is the final data frame
        # opcode is set to 0x1 to indicate a text payload.
        msg.append(0x81)  # 1 0 0 0 0 0 0 1

        # Build rest of the header and insert a payload.
        ##
        # How we build remaining header depends on buf size.
        buf_len = len(buf)

        if buf_len < 126:
            msg_header = buf_len  # prepare the payload size field

            if mask:
                # set the mask flag to 1
                msg.append(msg_header + (1 << 7))
            else:
                msg.append(msg_header)

            # Apply a mask and insert the payload.
            if mask:
                msg.append(key)  # insert the mask key as a header field
                msg.append(Frame.encodeMessage(buf, key))
            else:
                msg += bytearray(buf)
            return msg

        # If the buffer size is greater than can be described by 7 bits but
        # will fit into 16 bits use an extended payload size of 16 bits
        if buf_len <= ((1 << 16) - 1):

            if mask:
                # Make the payload field (7 bits 126) and set the mask flag
                msg.append(126 + (1 << 7))
            else:
                # No need to set the mask flag.
                msg.append(126)

            # Convert the buffer size into a 16 bit integer
            for i in range(1, 3):
                msg_header = (buf_len >> (16 - (8*i))) & (2**8 - 1)
                msg.append(msg_header)

            # Insert the payload and apply a mask key if necessary
            if mask:
                msg.append(key)
                msg.append(Frame.encodeMessage(buf, key))
            else:
                msg += buf
            return msg

        # If the buffer length can only be described by something larger than
        # a 16 bit int, extended payload will be 64 bits.
        if buf_len <= ((1 << 64) - 1):

            # Same as previous except with a payload field indicating 64 bit
            # extended playload header.
            if mask:
                msg.append(127 + (1 << 7))
            else:
                msg.append(127)

            for i in range(1, 9):
                # Make the buffer size a 64 bit int.
                msg_header = (buf_len >> (64 - (8*i))) & (2**8 - 1)
                msg.append(msg_header)

            # Prepare/insert the payload.
            if mask:
                msg.append(key)
                msg.append(Frame.encodeMessage(buf, key))
            else:
                msg += bytearray(buf)
            return msg

#Handshake

class Handshake:
        def prkey(s):
                if not s:return False
                s += '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
                return str(b64encode(sha1(s.encode()).digest()))[2:-1]
        def parse_h(headers):
                headers = str(headers).split("\\r\\n")
                #return str(headers)
                p = [x for x in headers if x[0:19] == "Sec-WebSocket-Key: "]
                return p[0][19:] if p and p[0] else False
        def upgrade(headers):
                #val =  Handshake.parse_headers(headers)
                #return "\n" + Handshake.prkey(val) if val else "none"
                key = Handshake.prkey(Handshake.parse_h(headers))
                if not key:return key
                ret = """HTTP/1.1 101 Web Socket Protocol Handshake\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: """ + str(key) + """\r\n\r\n"""
                return ret
