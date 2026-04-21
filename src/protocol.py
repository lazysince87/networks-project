import struct

#constants
HANDSHAKE_HEADER = b'P2PFILESHARINGPROJ'
HANDSHAKE_ZEROS = b'\x00' * 10
HANDSHAKE_LEN = 32

#message types
CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7

#read exactly n bytes from tcp socket
def recv_exact(sock, n):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

#handshake messages
def build_handshake(peer_id):
    return HANDSHAKE_HEADER + HANDSHAKE_ZEROS + peer_id.to_bytes(4, 'big')

def send_handshake(sock, peer_id):
    sock.sendall(build_handshake(peer_id))

def recv_handshake(sock):
    data = recv_exact(sock, HANDSHAKE_LEN)
    if data is None:
        return None
    if data[:18] != HANDSHAKE_HEADER:
        return None
    return int.from_bytes(data[28:32], 'big')

#actual messages
def build_message(msg_type, payload=b''):
    msg_length = 1 + len(payload)
    return struct.pack('!IB', msg_length, msg_type) + payload

def send_message(sock, msg_type, payload=b''):
    sock.sendall(build_message(msg_type, payload))

def recv_message(sock):
    length_bytes = recv_exact(sock, 4)
    if length_bytes is None:
        return None, None
    msg_length = struct.unpack('!I', length_bytes)[0]
    if msg_length == 0:
        return None, None

    body = recv_exact(sock, msg_length)
    if body is None:
        return None, None

    msg_type = body[0]
    payload = body[1:]
    return msg_type, payload