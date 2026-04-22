#!/bin/bash
set -e
cd "$(dirname "$0")/.."

FILE_NAME="testfile.dat"
FILE_SIZE=2097152

#cleanup old files
rm -f log_peer_*.log
rm -rf peer_1001 peer_1002 peer_1003

#use local configs (swap root-level configs that setup_test.sh and peerProcess.py read)
if [ -f PeerInfo.cfg ]; then
    cp PeerInfo.cfg PeerInfo.cfg.bak
fi
if [ -f Common.cfg ]; then
    cp Common.cfg Common.cfg.bak
fi
cp templates/PeerInfo_local.cfg PeerInfo.cfg
cp templates/Common_local.cfg  Common.cfg

#create dummy file in root
dd if=/dev/urandom of="${FILE_NAME}" bs=1024 count=$((FILE_SIZE / 1024)) 2>/dev/null

#run setup script
bash setup_test.sh "${FILE_NAME}"

#start seed and leechers
python3 src/peerProcess.py 1001 &
PID1=$!
sleep 2

python3 src/peerProcess.py 1002 &
PID2=$!
sleep 1

python3 src/peerProcess.py 1003 &
PID3=$!

TIMEOUT=180
ELAPSED=0

#wait loops
while [ $ELAPSED -lt $TIMEOUT ]; do
    DONE=true
    for PEER in 1002 1003; do
        if ! grep -q "downloaded the complete file" "log_peer_${PEER}.log" 2>/dev/null; then
            DONE=false
            break
        fi
    done

    if $DONE; then
        break
    fi

    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "TIMEOUT - not all peers completed"
fi

sleep 3

kill $PID1 $PID2 $PID3 2>/dev/null || true
wait 2>/dev/null || true

for f in log_peer_*.log; do
    cat "$f"
done

#check integrity
python3 src/verify.py "peer_1001/${FILE_NAME}" "peer_1002/${FILE_NAME}" || true
python3 src/verify.py "peer_1001/${FILE_NAME}" "peer_1003/${FILE_NAME}" || true

#clean up configs (restore root-level originals)
if [ -f PeerInfo.cfg.bak ]; then
    mv PeerInfo.cfg.bak PeerInfo.cfg
fi
if [ -f Common.cfg.bak ]; then
    mv Common.cfg.bak Common.cfg
fi
