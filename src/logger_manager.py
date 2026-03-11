import datetime
import threading

class PeerLogger:
    def __init__(self, peer_id):
        self.peer_id = peer_id
        self.log_file = f'log_peer_{peer_id}.log'
        self.lock = threading.Lock() # Thread lock for safety

    def _get_time(self):
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _write(self, message):
        # formatted_message = f'[{self._get_time()}]: {message}\n'
        # print(formatted_message, end='')  # Print to console for testing

        with self.lock:
            with open(self.log_file, 'a') as f:
                f.write(f'[{self._get_time()}]: {message}\n')

    # Logging methods correspond to different events
    # Included Peer ID in logs for easier tracking and reading
    # Followed spec logging format
    def log_connect_to(self, target_id):
        self._write(f'Peer {self.peer_id} makes a connection to Peer {target_id}.')

    def log_connected_from(self, source_id):
        self._write(f'Peer {self.peer_id} is connected from Peer {source_id}.')

    def log_preferred_neighbors(self, neighbor_ids):
        ids = ','.join(str(n) for n in neighbor_ids)
        self._write(f'Peer {self.peer_id} has the preferred neighbors {ids}.')

    def log_optimistic_unchoked(self, neighbor_id):
        self._write(f'Peer {self.peer_id} has the optimistically unchoked neighbor {neighbor_id}.')

    def log_unchoked(self, neighbor_id):
        self._write(f'Peer {self.peer_id} is unchoked by {neighbor_id}.')

    def log_choked(self, neighbor_id):
        self._write(f'Peer {self.peer_id} is choked by {neighbor_id}.')

    def log_have(self, neighbor_id, piece_index):
        self._write(f"Peer {self.peer_id} received the 'have' message from {neighbor_id} for the piece {piece_index}.")

    def log_interested(self, neighbor_id):
        self._write(f"Peer {self.peer_id} received the 'interested' message from {neighbor_id}.")

    def log_not_interested(self, neighbor_id):
        self._write(f"Peer {self.peer_id} received the 'not interested' message from {neighbor_id}.")

    def log_downloaded_piece(self, neighbor_id, piece_index, current_count):
        self._write(f"Peer {self.peer_id} has downloaded the piece {piece_index} from {neighbor_id}. "
                    f"Now the number of pieces it has is {current_count}.")
        
    def log_complete(self):
        self._write(f'Peer {self.peer_id} has downloaded the complete file.')


# Testing purposes (should print in console and also write to log file)
# if __name__ == "__main__":
#     Logger = PeerLogger(1001)
#     Logger.log_connect_to(1002)
#     Logger.log_connected_from(1003)
#     Logger.log_preferred_neighbors([1002, 1003, 1004])
#     Logger.log_optimistic_unchoked(1005)
#     Logger.log_unchoked(1006)
#     Logger.log_choked(1007)
#     Logger.log_have(1008, 5)
#     Logger.log_interested(1009)
#     Logger.log_not_interested(1010)
#     Logger.log_downloaded_piece(1011, 3, 10)
#     Logger.log_complete()