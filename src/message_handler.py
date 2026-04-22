import random
import logging
import struct

# Message ID Constants
CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7

class MessageHandler:
    def __init__(self, file_manager, my_info, all_peers):
        self.file_manager = file_manager
        self.my_info = my_info  
        self.all_peers = all_peers  
        self.logger = logging.getLogger("MessageHandler")

    def handle_choke(self, peer):
        eer['peer_choking'] = True
        peer['requested_piece'] = None  # Reset pending request
        self.logger.info(f"Peer {peer['peer_id']} choked us.")

    def handle_unchoke(self, peer):
        peer.peer_choking = False
        self.logger.info(f"Peer {peer.peer_id} unchoked us.")
        self.request_piece(peer)

    def handle_interested(self, peer):
        peer.peer_interested = True
        self.logger.info(f"Peer {peer.peer_id} is interested.")

    def handle_not_interested(self, peer):
        peer.peer_interested = False
        self.logger.info(f"Peer {peer.peer_id} is NOT interested.")

    def handle_have(self, peer, payload):
        # Fix: Unpack returns a tuple
        piece_index = struct.unpack(">I", payload[:4])
        set_bit(peer.bitfield, piece_index)
        self.logger.info(f"Peer {peer.peer_id} sent HAVE for piece {piece_index}")

        if not has_bit(self.my_info.my_bitfield, piece_index):
            peer.send_interested()

    def handle_bitfield(self, peer, payload):
        peer.bitfield = bytearray(payload)
        self.logger.info(f"Received BITFIELD from {peer.peer_id}")
        if self._is_interesting(peer):
            peer.send_interested()
        else:
            peer.send_not_interested()

    def handle_request(self, peer, payload):
        if peer.am_choking:
            return
        piece_index = struct.unpack(">I", payload[:4])
        piece_data = self.file_manager.read_piece(piece_index)
        if piece_data:
            peer.send_piece(piece_index, piece_data)

    def handle_piece(self, peer, payload):
        piece_index = struct.unpack(">I", payload[:4])
        piece_data = payload[4:]
        self.file_manager.write_piece(piece_index, piece_data)
        
        set_bit(self.my_info.my_bitfield, piece_index)
        self.logger.info(f"Downloaded piece {piece_index} from {peer.peer_id}")

        # Broadcast HAVE to all
        for other in self.all_peers.values():
            other.send_have(piece_index)

        self._reevaluate_interests()
        self.request_piece(peer)

    def request_piece(self, peer):
        if peer.peer_choking:
            return
        
        # Logic: Pick random missing piece not already requested
        needed = []
        for i in range(self.file_manager.num_pieces):
            if has_bit(peer.bitfield, i) and not has_bit(self.my_info.my_bitfield, i):
                # Check if someone else is already getting this
                already_asked = any(p.requested_piece == i for p in self.all_peers.values())
                if not already_asked:
                    needed.append(i)

        if needed:
            target = random.choice(needed)
            peer.requested_piece = target
            peer.send_request(target)

    def _is_interesting(self, peer):
        for i in range(self.file_manager.num_pieces):
            if has_bit(peer.bitfield, i) and not has_bit(self.my_info.my_bitfield, i):
                return True
        return False

    def _reevaluate_interests(self):
        for p in self.all_peers.values():
            if p.am_interested and not self._is_interesting(p):
                p.send_not_interested()
                p.am_interested = False

# --- Bitfield Utilities ---
def set_bit(bitfield, index):
    byte_index = index // 8
    bit_offset = 7 - (index % 8)
    bitfield[byte_index] |= (1 << bit_offset)

def has_bit(bitfield, index):
    byte_index = index // 8
    bit_offset = 7 - (index % 8)
    if byte_index >= len(bitfield): return False
    return (bitfield[byte_index] >> bit_offset) & 1

def count_bits(bitfield, num_pieces):
    return sum(1 for i in range(num_pieces) if has_bit(bitfield, i))

def create_bitfield(num_pieces, has_file=False):
    num_bytes = (num_pieces + 7) // 8
    bf = bytearray([0xFF if has_file else 0x00] * num_bytes)
    if has_file:
        # Clear trailing padding bits
        for i in range(num_pieces, num_bytes * 8):
            byte_idx = i // 8
            bit_off = 7 - (i % 8)
            bf[byte_idx] &= ~(1 << bit_off)
    return bf