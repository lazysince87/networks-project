import math

class ConfigReader:
    def __init__(self, common_file='templates/Common.cfg',
                 peer_file='templates/PeerInfo.cfg'):
        self.common_file = common_file
        self.peer_file = peer_file
        self.common_cfg = {}
        #{peer_id:{'host': str, 'port': int, 'has_file': int}}
        self.peer_info = {}
        self.num_pieces = 0

        self._parse_common()
        self._parse_peers()

    #helpers
    def _parse_common(self):
        with open(self.common_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    key, val = parts[-2], parts[-1]
                    self.common_cfg[key] = val

        #calc total number of pireces
        file_size = int(self.common_cfg.get('FileSize', 0))
        piece_size = int(self.common_cfg.get('PieceSize', 1))
        self.num_pieces = math.ceil(file_size / piece_size)

    def _parse_peers(self):
        with open(self.peer_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    peer_id  = int(parts[-4])
                    host     = parts[-3]
                    port     = int(parts[-2])
                    has_file = int(parts[-1])
                    self.peer_info[peer_id] = {
                        'host': host,
                        'port': port,
                        'has_file': has_file,
                    }

    @property
    def num_preferred_neighbors(self) -> int:
        return int(self.common_cfg.get('NumberOfPreferredNeighbors', 2))

    @property
    def unchoking_interval(self) -> int:
        return int(self.common_cfg.get('UnchokingInterval', 5))

    @property
    def optimistic_unchoking_interval(self) -> int:
        return int(self.common_cfg.get('OptimisticUnchokingInterval', 15))

    @property
    def file_name(self) -> str:
        return self.common_cfg.get('FileName', '')

    @property
    def file_size(self) -> int:
        return int(self.common_cfg.get('FileSize', 0))

    @property
    def piece_size(self) -> int:
        return int(self.common_cfg.get('PieceSize', 1))

    def get_peer_ids(self) -> list:
        return list(self.peer_info.keys())

    def get_peers_before(self, peer_id: int) -> list:
        return [pid for pid in self.peer_info if pid < peer_id]

    def get_peers_after(self, peer_id: int) -> list:
        return [pid for pid in self.peer_info if pid > peer_id]


if __name__ == '__main__':
    config = ConfigReader()

    #smoke output for checkpoint
    print(f'file_name: {config.file_name}')
    print(f'file_size: {config.file_size}')
    print(f'piece_size: {config.piece_size}')
    print(f'num_pieces: {config.num_pieces}')
    print(f'num_preferred_neighbors: {config.num_preferred_neighbors}')
    print(f'unchoking_interval: {config.unchoking_interval}s')
    print(f'optimistic_unchoking_interval: {config.optimistic_unchoking_interval}s')

    #peers list
    for pid, info in sorted(config.peer_info.items()):
        print(f'peer {pid}: {info["host"]}:{info["port"]} has_file={info["has_file"]}')