from __future__ import annotations

import os
import random
import socket
import sys
import threading
import time

from config_parser import ConfigReader
from file_manager import FileManager
from logger_manager import PeerLogger
from protocol import (
    CHOKE, UNCHOKE, INTERESTED, NOT_INTERESTED,
    HAVE, BITFIELD, REQUEST, PIECE,
    send_handshake, recv_handshake,
    send_message, recv_message,
)
from strategy_manager import StrategyManager

CONNECT_RETRY_DELAY = 1
MAX_CONNECT_RETRIES = 30

#bitfield helpers
def _has_bit(bf, idx):
    byte_n = idx // 8
    bit_n = 7 - (idx % 8)
    if byte_n >= len(bf):
        return False
    return bool((bf[byte_n] >> bit_n) & 1)

def _set_bit(bf, idx):
    byte_n = idx // 8
    bit_n = 7 - (idx % 8)
    if byte_n < len(bf):
        bf[byte_n] |= (1 << bit_n)

def _count_bits(bf, num_pieces):
    return sum(1 for i in range(num_pieces) if _has_bit(bf, i))

def _make_bitfield(num_pieces, fill):
    num_bytes = (num_pieces + 7) // 8
    if fill:
        bf = bytearray(b'\xff' * num_bytes)
        spare = num_bytes * 8 - num_pieces
        if spare:
            bf[-1] &= (0xFF << spare)
        return bf
    return bytearray(num_bytes)

class Peer:
    def __init__(self, peer_id):
        self.peer_id = peer_id
        self.config = ConfigReader()
        self.logger = PeerLogger(peer_id)

        self.num_pieces = self.config.num_pieces
        has_file = bool(self.config.peer_info[peer_id]['has_file'])

        self.my_bitfield = _make_bitfield(self.num_pieces, fill=has_file)

        self.file_manager = FileManager(
            peer_id,
            self.config.file_name,
            self.config.file_size,
            self.config.piece_size,
            has_file,
        )

        #state arrays and sync
        self.neighbors = {}
        self.state_lock = threading.RLock()

        self._optimistic_id = None
        self.shutdown_event = threading.Event()

    #neighbor tracking
    def _add_neighbor(self, remote_id, sock):
        with self.state_lock:
            self.neighbors[remote_id] = {
                'socket': sock,
                'bitfield': _make_bitfield(self.num_pieces, fill=False),
                'am_interested': False,
                'peer_interested': False,
                'am_choking': True,
                'peer_choking': True,
                'download_bytes': 0,
                'requested_piece': None,
            }

    def _remove_neighbor(self, remote_id):
        with self.state_lock:
            ni = self.neighbors.pop(remote_id, None)
        if ni:
            try:
                ni['socket'].close()
            except Exception:
                pass

    def _send_to(self, remote_id, msg_type, payload=b''):
        with self.state_lock:
            ni = self.neighbors.get(remote_id)
            if ni is None:
                return
            sock = ni['socket']
        try:
            send_message(sock, msg_type, payload)
        except Exception:
            pass

    #server thread
    def _server_thread(self):
        my_port = self.config.peer_info[self.peer_id]['port']
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(('0.0.0.0', my_port))
        srv.listen(10)
        srv.settimeout(1.0)

        while not self.shutdown_event.is_set():
            try:
                conn, _addr = srv.accept()
            except socket.timeout:
                continue
            except Exception:
                continue

            try:
                remote_id = recv_handshake(conn)
                if remote_id is None:
                    conn.close()
                    continue
                send_handshake(conn, self.peer_id)

                self.logger.log_connected_from(remote_id)
                self._add_neighbor(remote_id, conn)

                threading.Thread(
                    target=self._connection_worker,
                    args=(conn, remote_id),
                    daemon=True,
                ).start()
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass

        srv.close()

    #client handshake
    def _connect_to_peer(self, target_id):
        info = self.config.peer_info[target_id]
        host, port = info['host'], info['port']

        sock = None
        for _ in range(MAX_CONNECT_RETRIES):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((host, port))
                break
            except Exception:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass
                    sock = None
                time.sleep(CONNECT_RETRY_DELAY)
        else:
            return

        try:
            send_handshake(sock, self.peer_id)
            remote_id = recv_handshake(sock)
            if remote_id != target_id:
                sock.close()
                return

            self.logger.log_connect_to(target_id)
            self._add_neighbor(target_id, sock)

            self._connection_worker(sock, target_id)
        except Exception:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    #message processing
    def _connection_worker(self, sock, remote_id):
        try:
            with self.state_lock:
                bf_copy = bytes(self.my_bitfield)
            if any(b != 0 for b in bf_copy):
                self._send_to(remote_id, BITFIELD, bf_copy)

            while not self.shutdown_event.is_set():
                msg_type, payload = recv_message(sock)
                if msg_type is None:
                    break
                self._dispatch(remote_id, msg_type, payload)

        except Exception:
            pass
        finally:
            self._remove_neighbor(remote_id)

    #routing messages
    def _dispatch(self, remote_id, msg_type, payload):
        if msg_type == CHOKE:
            self._handle_choke(remote_id)
        elif msg_type == UNCHOKE:
            self._handle_unchoke(remote_id)
        elif msg_type == INTERESTED:
            self._handle_interested(remote_id)
        elif msg_type == NOT_INTERESTED:
            self._handle_not_interested(remote_id)
        elif msg_type == HAVE:
            self._handle_have(remote_id, payload)
        elif msg_type == BITFIELD:
            self._handle_bitfield(remote_id, payload)
        elif msg_type == REQUEST:
            self._handle_request(remote_id, payload)
        elif msg_type == PIECE:
            self._handle_piece(remote_id, payload)

    #message handlers
    def _handle_choke(self, rid):
        with self.state_lock:
            ni = self.neighbors.get(rid)
            if ni:
                ni['peer_choking'] = True
                ni['requested_piece'] = None
        self.logger.log_choked(rid)

    def _handle_unchoke(self, rid):
        with self.state_lock:
            ni = self.neighbors.get(rid)
            if ni:
                ni['peer_choking'] = False
        self.logger.log_unchoked(rid)
        self._request_piece(rid)

    def _handle_interested(self, rid):
        with self.state_lock:
            ni = self.neighbors.get(rid)
            if ni:
                ni['peer_interested'] = True
        self.logger.log_interested(rid)

    def _handle_not_interested(self, rid):
        with self.state_lock:
            ni = self.neighbors.get(rid)
            if ni:
                ni['peer_interested'] = False
        self.logger.log_not_interested(rid)

    def _handle_have(self, rid, payload):
        piece_idx = int.from_bytes(payload[:4], 'big')
        self.logger.log_have(rid, piece_idx)

        send_interested = False
        with self.state_lock:
            ni = self.neighbors.get(rid)
            if ni is None:
                return
            _set_bit(ni['bitfield'], piece_idx)

            if not _has_bit(self.my_bitfield, piece_idx) and not ni['am_interested']:
                ni['am_interested'] = True
                send_interested = True

        if send_interested:
            self._send_to(rid, INTERESTED)

        self._check_termination()

    def _handle_bitfield(self, rid, payload):
        send_type = None
        with self.state_lock:
            ni = self.neighbors.get(rid)
            if ni is None:
                return
            ni['bitfield'] = bytearray(payload)

            interested = any(
                _has_bit(ni['bitfield'], i) and not _has_bit(self.my_bitfield, i)
                for i in range(self.num_pieces)
            )
            ni['am_interested'] = interested
            send_type = INTERESTED if interested else NOT_INTERESTED

        self._send_to(rid, send_type)

    def _handle_request(self, rid, payload):
        piece_idx = int.from_bytes(payload[:4], 'big')

        with self.state_lock:
            ni = self.neighbors.get(rid)
            if ni is None or ni['am_choking']:
                return

        piece_data = self.file_manager.read_piece(piece_idx)
        if piece_data is not None:
            out = piece_idx.to_bytes(4, 'big') + piece_data
            self._send_to(rid, PIECE, out)

    def _handle_piece(self, rid, payload):
        piece_idx = int.from_bytes(payload[:4], 'big')
        piece_data = payload[4:]

        self.file_manager.write_piece(piece_idx, piece_data)

        with self.state_lock:
            _set_bit(self.my_bitfield, piece_idx)
            count = _count_bits(self.my_bitfield, self.num_pieces)
            ni = self.neighbors.get(rid)
            if ni:
                ni['download_bytes'] += len(piece_data)
                ni['requested_piece'] = None

        self.logger.log_downloaded_piece(rid, piece_idx, count)

        have_payload = piece_idx.to_bytes(4, 'big')
        with self.state_lock:
            nids = list(self.neighbors.keys())
        for nid in nids:
            self._send_to(nid, HAVE, have_payload)

        if count == self.num_pieces:
            self.logger.log_complete()
            self.file_manager.assemble_file()

        self._update_interest_all()

        self._request_piece(rid)

        self._check_termination()

    #logic to request next piece
    def _request_piece(self, rid):
        piece = None
        send_not_interested = False

        with self.state_lock:
            ni = self.neighbors.get(rid)
            if ni is None or ni['peer_choking']:
                return

            missing = [
                i for i in range(self.num_pieces)
                if _has_bit(ni['bitfield'], i) and not _has_bit(self.my_bitfield, i)
            ]

            already_requested = {
                n['requested_piece']
                for n in self.neighbors.values()
                if n['requested_piece'] is not None
            }
            available = [p for p in missing if p not in already_requested]

            if available:
                piece = random.choice(available)
                ni['requested_piece'] = piece
            elif not missing:
                ni['am_interested'] = False
                send_not_interested = True

        if send_not_interested:
            self._send_to(rid, NOT_INTERESTED)
        elif piece is not None:
            self._send_to(rid, REQUEST, piece.to_bytes(4, 'big'))

    def _update_interest_all(self):
        actions = []
        with self.state_lock:
            for rid, ni in self.neighbors.items():
                has_interesting = any(
                    _has_bit(ni['bitfield'], i) and not _has_bit(self.my_bitfield, i)
                    for i in range(self.num_pieces)
                )
                was = ni['am_interested']
                ni['am_interested'] = has_interesting
                if has_interesting and not was:
                    actions.append((rid, INTERESTED))
                elif not has_interesting and was:
                    actions.append((rid, NOT_INTERESTED))

        for rid, mt in actions:
            self._send_to(rid, mt)

    #check if everyone is complete
    def _check_termination(self):
        with self.state_lock:
            if _count_bits(self.my_bitfield, self.num_pieces) != self.num_pieces:
                return

            expected = set(self.config.peer_info.keys()) - {self.peer_id}
            if not expected.issubset(self.neighbors.keys()):
                return

            for rid in expected:
                ni = self.neighbors.get(rid)
                if ni is None:
                    return
                if _count_bits(ni['bitfield'], self.num_pieces) != self.num_pieces:
                    return

        self.shutdown_event.set()

    #timer callbacks
    def _get_interested_neighbors(self):
        with self.state_lock:
            return [rid for rid, ni in self.neighbors.items()
                    if ni['peer_interested']]

    def _get_choked_neighbors(self):
        with self.state_lock:
            return [rid for rid, ni in self.neighbors.items()
                    if ni['am_choking']]

    def _get_download_rates(self):
        with self.state_lock:
            rates = {}
            for rid, ni in self.neighbors.items():
                rates[rid] = ni['download_bytes']
                ni['download_bytes'] = 0
            return rates

    def _has_complete_file(self):
        with self.state_lock:
            return _count_bits(self.my_bitfield, self.num_pieces) == self.num_pieces

    def _on_preferred_selected(self, preferred):
        self.logger.log_preferred_neighbors(preferred)
        preferred_set = set(preferred)
        actions = []

        with self.state_lock:
            for rid, ni in self.neighbors.items():
                if rid in preferred_set:
                    if ni['am_choking']:
                        ni['am_choking'] = False
                        actions.append((rid, UNCHOKE))
                else:
                    if rid == self._optimistic_id:
                        continue
                    if not ni['am_choking']:
                        ni['am_choking'] = True
                        actions.append((rid, CHOKE))

        for rid, mt in actions:
            self._send_to(rid, mt)

    def _on_optimistic_selected(self, peer_id):
        if peer_id is None:
            return
        prev = self._optimistic_id
        self._optimistic_id = peer_id

        self.logger.log_optimistic_unchoked(peer_id)

        actions = []

        with self.state_lock:
            # re-choke previous optimistic neighbor if needed
            if prev is not None and prev != peer_id:
                prev_ni = self.neighbors.get(prev)
                if prev_ni and not prev_ni['am_choking']:
                    prev_ni['am_choking'] = True
                    actions.append((prev, CHOKE))

            # unchoke new optimistic neighbor
            ni = self.neighbors.get(peer_id)
            if ni and ni['am_choking']:
                ni['am_choking'] = False
                actions.append((peer_id, UNCHOKE))

        for rid, mt in actions:
            self._send_to(rid, mt)

    def start(self):
        threading.Thread(target=self._server_thread, daemon=True).start()
        time.sleep(0.3)

        older = self.config.get_peers_before(self.peer_id)
        for tid in older:
            threading.Thread(
                target=self._connect_to_peer, args=(tid,), daemon=True
            ).start()

        time.sleep(1.0)

        self.strategy = StrategyManager(
            k=self.config.num_preferred_neighbors,
            unchoking_interval=self.config.unchoking_interval,
            optimistic_interval=self.config.optimistic_unchoking_interval,
            get_interested_neighbors=self._get_interested_neighbors,
            get_choked_neighbors=self._get_choked_neighbors,
            get_download_rates=self._get_download_rates,
            has_complete_file=self._has_complete_file,
            on_preferred_selected=self._on_preferred_selected,
            on_optimistic_selected=self._on_optimistic_selected,
        )
        self.strategy.start()

        try:
            while not self.shutdown_event.is_set():
                self.shutdown_event.wait(timeout=1)
        except KeyboardInterrupt:
            pass

        self.strategy.stop()
        time.sleep(0.5)
        with self.state_lock:
            for ni in self.neighbors.values():
                try:
                    ni['socket'].close()
                except Exception:
                    pass

    def count_bits(bitfield, num_pieces):
        return sum(1 for i in range(num_pieces) if has_bit(bitfield, i))

def main():
    if len(sys.argv) < 2:
        sys.exit(1)

    peer_id = int(sys.argv[1])
    config = ConfigReader()

    if peer_id not in config.peer_info:
        sys.exit(1)

    peer = Peer(peer_id)
    peer.start()

if __name__ == '__main__':
    main()
