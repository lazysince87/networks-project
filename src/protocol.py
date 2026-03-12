import struct


#Handshake constant

HANDSHAKE_HEADER = b'P2PFILESHARINGPROJ'
HANDSHAKE_ZEROS = b'\x00' * 10
HANDSHAKE_FORMAT = "!18s10sI"

#Msg types

CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7

class Protocol:
    @staticmethod
    def create_handshake(peer_id: int) -> bytes:
        return struct.pack(HANDSHAKE_FORMAT, HANDSHAKE_HEADER, HANDSHAKE_ZEROS, peer_id)

    @staticmethod
    def parse_handshake(data: bytes):
        if len(data) !=32:
            return None, None
        header, zeros, peer_id = struct.unpack(HANDSHAKE_FORMAT, data)
        return header,peer_id
    
    @staticmethod
    def create_message(msg_type: int, payload=b'') -> bytes:
        msg_length = len(payload) + 1
        header = struct.pack("!IB", msg_length, msg_type)
        return header + payload
    
    @staticmethod
    def parse_message(data: bytes):
        if len(data) < 5:
            return None, None
        return struct.unpack("!IB", data[:5])
    