#!/usr/bin/env bash
# setup_test.sh
# Creates peer subdir and seeds the src file into peer_1001/
# for local testing. Run this once before starting any peer processes.
#
# Usage:
#   bash setup_test.sh [path/to/source/file]
#
# If no file argument is given the script looks for FileName value
# inside templates/Common_local.cfg and expects that file to already exist in
# the current working directory.

set -euo pipefail

# 1 Read FileName from Common.cfg
CFG="templates/Common.cfg"
if [[ ! -f "$CFG" ]]; then
    echo "ERROR: $CFG not found. Run this script from your project root."
    exit 1
fi

FILE_NAME=$(grep -E '^[[:space:]]*FileName[[:space:]]' "$CFG" | awk '{print $NF}')
if [[ -z "$FILE_NAME" ]]; then
    echo "ERROR: Could not read FileName from $CFG."
    exit 1
fi

# Allow caller to override the source file path
SOURCE_FILE="${1:-$FILE_NAME}"

if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "ERROR: Source file '$SOURCE_FILE' not found."
    echo "       Place the file in the project root or pass its path as an argument."
    exit 1
fi

# 2 Read peer IDs from PeerInfo.cfg
PEER_CFG="templates/PeerInfo.cfg"
if [[ ! -f "$PEER_CFG" ]]; then
    echo "ERROR: $PEER_CFG not found."
    exit 1
fi

# Extract the first col (peer IDs) and skip blank lines/comments
PEER_IDS=( $(awk 'NF >= 4 {print $1}' "$PEER_CFG") )

if [[ ${#PEER_IDS[@]} -eq 0 ]]; then
    echo "ERROR: No peers found in $PEER_CFG."
    exit 1
fi

# The peer that starts with has_file=1 gets the actual file.
# We read the fourth col to find it (may be more than one).
SEEDED_PEERS=( $(awk 'NF >= 4 && $4 == 1 {print $1}' "$PEER_CFG") )

# 3 Create peer directories
echo "Creating peer directories..."
for PID in "${PEER_IDS[@]}"; do
    DIR="peer_${PID}"
    mkdir -p "$DIR"
    echo "  $DIR/"
done

# 4 Copy src file into every seeded peer's directory
echo ""
echo "Seeding '$FILE_NAME' into peer directories with has_file=1..."
for PID in "${SEEDED_PEERS[@]}"; do
    DEST="peer_${PID}/$FILE_NAME"
    cp "$SOURCE_FILE" "$DEST"
    echo "  Copied -> $DEST"
done

# 5 Completion messages for debugging/confirmation
echo ""
echo "Setup complete."
echo ""
echo "Peer directories created  : ${PEER_IDS[*]}"
echo "Peers seeded with the file: ${SEEDED_PEERS[*]}"
echo ""
echo "Start peers in order with:"
for PID in "${PEER_IDS[@]}"; do
    echo "  python src/peerProcess.py $PID"
done
