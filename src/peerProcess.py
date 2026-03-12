from __future__ import annotations

import socket
import sys
import threading
import time

from config_parser import ConfigReader
from logger_manager import PeerLogger

HANDSHAKE_HEADER = b'P2PFILESHARINGPROJ'
HANDSHAKE_ZEROS = b'\x00' * 10
HANDSHAKE_LEN = 32

CONNECT_RETRY_DELAY = 1
MAX_CONNECT_RETRIES = 10


def build_handshake(peer_id: int) -> bytes:
    return HANDSHAKE_HEADER + HANDSHAKE_ZEROS + peer_id.to_bytes(4, 'big')


def parse_handshake(data: bytes) -> int | None:
    if len(data) != HANDSHAKE_LEN:
        return None
    if data[:18] != HANDSHAKE_HEADER:
        return None
    return int.from_bytes(data[28:32], 'big')


#read until the socket closes
def connection_worker(sock: socket.socket, remote_id: int, peer_id: int):
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                break
            #ignore payload for checkpoint
    except Exception:
        pass
    finally:
        try:
            sock.close()
        except Exception:
            pass

#server
#accept incoming connections from newer peers
def server_thread(peer_id: int, config: ConfigReader, logger: PeerLogger, connections: dict):
    my_port = config.peer_info[peer_id]['port']
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', my_port))
    srv.listen(10)
    print(f'[{peer_id}] listening on {my_port}')

    while True:
        try:
            conn, addr = srv.accept()
        except Exception:
            continue

        #server handshake
        try:
            hs = conn.recv(HANDSHAKE_LEN)
            remote = parse_handshake(hs)
            if remote is None:
                conn.close()
                continue
            conn.sendall(build_handshake(peer_id))

            logger.log_connected_from(remote)
            with threading.Lock():
                connections[remote] = conn

            t = threading.Thread(target=connection_worker, args=(conn, remote, peer_id), daemon=True)
            t.start()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass

#client
#connect to every peer with smaller id
def connect_to_peer(peer_id: int, target_id: int, config: ConfigReader, logger: PeerLogger, connections: dict):
    info = config.peer_info[target_id]
    host, port = info['host'], info['port']

    for attempt in range(MAX_CONNECT_RETRIES):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            break
        except Exception:
            time.sleep(CONNECT_RETRY_DELAY)
    else:
        print(f'[{peer_id}] failed to connect to {target_id}')
        return

    #client handshake
    try:
        sock.sendall(build_handshake(peer_id))
        hs = sock.recv(HANDSHAKE_LEN)
        remote = parse_handshake(hs)
        if remote != target_id:
            sock.close()
            return

        logger.log_connect_to(target_id)
        with threading.Lock():
            connections[target_id] = sock

        t = threading.Thread(target=connection_worker, args=(sock, target_id, peer_id), daemon=True)
        t.start()
    except Exception:
        try:
            sock.close()
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print('usage: python peerProcess.py <peer_id>')
        sys.exit(1)

    peer_id = int(sys.argv[1])
    config = ConfigReader()

    if peer_id not in config.peer_info:
        print(f'peer {peer_id} not in PeerInfo.cfg')
        sys.exit(1)

    logger = PeerLogger(peer_id)
    connections: dict[int, socket.socket] = {}

    #start server
    t_srv = threading.Thread(target=server_thread, args=(peer_id, config, logger, connections), daemon=True)
    t_srv.start()

    time.sleep(0.2)

    #connect to older peers
    older = [pid for pid in config.peer_info.keys() if pid < peer_id]
    for target in older:
        threading.Thread(target=connect_to_peer, args=(peer_id, target, config, logger, connections), daemon=True).start()

    #keep main alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f'[{peer_id}] shutting down')
        for s in list(connections.values()):
            try:
                s.close()
            except Exception:
                pass


if __name__ == '__main__':
    main()
