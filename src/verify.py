import hashlib
import sys

#hash file content
def file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def main():
    if len(sys.argv) < 3:
        print('usage: python verify.py <original> <reassembled>')
        sys.exit(1)

    original = sys.argv[1]
    reassembled = sys.argv[2]

    h1 = file_hash(original)
    h2 = file_hash(reassembled)

    print(f'Original:    {h1}')
    print(f'Reassembled: {h2}')

    if h1 == h2:
        print('MATCH - files are identical')
    else:
        print('MISMATCH - files differ')
        sys.exit(1)

if __name__ == '__main__':
    main()
