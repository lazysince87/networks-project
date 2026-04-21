import math
import os

class FileManager:
    def __init__(self, peer_id, file_name, file_size, piece_size, has_file):
        self.peer_id = peer_id
        self.file_name = file_name
        self.file_size = file_size
        self.piece_size = piece_size
        self.num_pieces = math.ceil(file_size / piece_size)
        self.peer_dir = f'peer_{peer_id}'

        os.makedirs(self.peer_dir, exist_ok=True)

        if has_file:
            self._split_file()

    #split complete file into initial pieces
    def _split_file(self):
        src_path = os.path.join(self.peer_dir, self.file_name)
        if not os.path.exists(src_path):
            raise FileNotFoundError(
                f'Source file not found: {src_path} '
                f'(make sure {self.file_name} is inside {self.peer_dir}/)')

        with open(src_path, 'rb') as src:
            for i in range(self.num_pieces):
                data = src.read(self.piece_size)
                if not data:
                    break
                piece_path = os.path.join(self.peer_dir, f'piece_{i}')
                with open(piece_path, 'wb') as pf:
                    pf.write(data)

    #read a piece from disk
    def read_piece(self, piece_index):
        path = os.path.join(self.peer_dir, f'piece_{piece_index}')
        if not os.path.exists(path):
            return None
        with open(path, 'rb') as f:
            return f.read()

    #write a downloaded piece to disk
    def write_piece(self, piece_index, data):
        path = os.path.join(self.peer_dir, f'piece_{piece_index}')
        with open(path, 'wb') as f:
            f.write(data)

    def has_piece(self, piece_index):
        path = os.path.join(self.peer_dir, f'piece_{piece_index}')
        return os.path.exists(path)

    #put all pieces together at the end
    def assemble_file(self):
        out_path = os.path.join(self.peer_dir, self.file_name)
        with open(out_path, 'wb') as out:
            for i in range(self.num_pieces):
                data = self.read_piece(i)
                if data:
                    out.write(data)

    def get_piece_size(self, piece_index):
        if piece_index == self.num_pieces - 1:
            remainder = self.file_size % self.piece_size
            return remainder if remainder != 0 else self.piece_size
        return self.piece_size
