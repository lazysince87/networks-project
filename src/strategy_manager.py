# To do in file
# Missing piece logic: Compare two bitfields and return the list of piece indices that the current peer is missing but the neighbor has.
# Random piece selection: From the available missing pieces, choose one valid piece at random that has not already been requested.
# Preferred neighbor selection: Every p seconds, select the top k interested neighbors based on download rate (or randomly if the full file is already owned).
# Optimistic unchoke selection: Every m seconds, randomly select one interested neighbor that is currently choked to be optimistically unchoked.

from __future__ import annotations
import random
import threading

# Assumes bitfield is bytes or bytearray.
# Piece 0 = highest bit of first byte.
# Piece 7 = lowest bit of first byte.
# Piece 8 = highest bit of second byte, etc.

def has_bit(bitfield, piece_index):
    byte_num = piece_index // 8
    bit_num = 7 - (piece_index % 8)

    if piece_index < 0:
        return False

    if byte_num >= len(bitfield):
        return False

    return (bitfield[byte_num] >> bit_num) & 1 == 1

# Compare my bitfield with a neighbor's and return pieces they have that I don't.
def find_missing(my_bits, neighbor_bits, num_pieces):
    missing = []

    for i in range(num_pieces):
        if has_bit(neighbor_bits, i) and not has_bit(my_bits, i):
            missing.append(i)

    return missing

# Pick one random piece that hasn't already been requested.
def select_piece(candidate_pieces, requested_pieces):
    available = [p for p in candidate_pieces if p not in requested_pieces]

    if not available:
        return None

    return random.choice(available)

# Decide if we should send an "interested" message.
def is_interested(my_bits, neighbor_bits, num_pieces):
    return len(find_missing(my_bits, neighbor_bits, num_pieces)) > 0

# Neighbor Selection Logic: 
# Select top k preferred neighbors.
# If we don't have the full file, choose neighbors with highest download rate.
# If we already have the full file, choose randomly among interested neighbors.
def select_preferred_neighbors(interested_neighbors, download_rates, k, has_complete_file):
    interested = list(interested_neighbors)

    if k <= 0 or not interested:
        return []

    # If we already have full file, choose randomly.
    if has_complete_file:
        random.shuffle(interested)
        return interested[:k]

    # Otherwise sort by download rate (highest first).
    # Break ties randomly.
    rate_groups = {}

    for peer_id in interested:
        rate = download_rates.get(peer_id, 0.0)
        rate_groups.setdefault(rate, []).append(peer_id)

    selected = []

    for rate in sorted(rate_groups.keys(), reverse=True):
        peers = rate_groups[rate]
        random.shuffle(peers)  # random tie-break

        for peer_id in peers:
            if len(selected) < k:
                selected.append(peer_id)

        if len(selected) >= k:
            break

    return selected

# Choose one random neighbor that is currently choked and interested.
def select_optimistic_unchoke(choked_neighbors, interested_neighbors):
    candidates = list(set(choked_neighbors).intersection(interested_neighbors))

    if not candidates:
        return None

    return random.choice(candidates)

# Strategy Manager (Timer Loops)
class StrategyManager:
    # Initialize with intervals and callback functions.
    # The callbacks will be implemented by the main peer code.
    def __init__(
        self,
        k,
        unchoking_interval,
        optimistic_interval,
        get_interested_neighbors,
        get_choked_neighbors,
        get_download_rates,  # should return download rates measured over the previous unchoking interval
        has_complete_file,
        on_preferred_selected,
        on_optimistic_selected
    ):
        self.k = k
        self.p = max(1, unchoking_interval)
        self.m = max(1, optimistic_interval)

        self.get_interested_neighbors = get_interested_neighbors
        self.get_choked_neighbors = get_choked_neighbors
        self.get_download_rates = get_download_rates
        self.has_complete_file = has_complete_file

        self.on_preferred_selected = on_preferred_selected
        self.on_optimistic_selected = on_optimistic_selected

        self.stop_event = threading.Event()

    def start(self):
        threading.Thread(target=self.preferred_loop, daemon=True).start()
        threading.Thread(target=self.optimistic_loop, daemon=True).start()

    def stop(self):
        self.stop_event.set()

    # Runs every p seconds to choose preferred neighbors.
    def preferred_loop(self):
        while not self.stop_event.is_set():
            try:
                interested = self.get_interested_neighbors()
                rates = self.get_download_rates()
                complete = self.has_complete_file()
                preferred = select_preferred_neighbors(interested, rates, self.k, complete)
                self.on_preferred_selected(preferred)
            except Exception:
                pass
            self.stop_event.wait(self.p)

    # Runs every m seconds to choose optimistic unchoke neighbor.
    def optimistic_loop(self):
        while not self.stop_event.is_set():
            try:
                choked = self.get_choked_neighbors()
                interested = self.get_interested_neighbors()
                optimistic = select_optimistic_unchoke(choked, interested)
                self.on_optimistic_selected(optimistic)
            except Exception:
                pass
            self.stop_event.wait(self.m)