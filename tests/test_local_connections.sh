#start 3 peers on localhost
#checks: handshake, connections, and logs
#from root run `bash tests/test_local_connections.sh`

set -e
cd "$(dirname "$0")/.."

echo "=== Cleaning up old logs and peer dirs ==="
rm -f log_peer_*.log
rm -rf peer_1001 peer_1002 peer_1003

if [ -f templates/PeerInfo.cfg ]; then
    cp templates/PeerInfo.cfg templates/PeerInfo.cfg.bak
fi
if [ -f templates/Common.cfg ]; then
    cp templates/Common.cfg templates/Common.cfg.bak
fi
cp templates/PeerInfo_local.cfg templates/PeerInfo.cfg
cp templates/Common_local.cfg templates/Common.cfg

echo "=== Creating dummy file and running setup_test.sh ==="
dd if=/dev/urandom of="testfile_local.dat" bs=1024 count=100 2>/dev/null
bash setup_test.sh testfile_local.dat

echo "starting peer 1001"
python3 src/peerProcess.py 1001 &
PID1=$!
sleep 1

echo "=== Starting Peer 1002 (background) ==="
echo "starting peer 1002"
python3 src/peerProcess.py 1002 &
PID2=$!
sleep 1

echo "=== Starting Peer 1003 (background) ==="
echo "starting peer 1003"
python3 src/peerProcess.py 1003 &
PID3=$!
sleep 3

echo ""
echo "=== Log files ==="
for f in log_peer_*.log; do
    echo "--- $f ---"
    cat "$f"
    echo ""
done

echo "=== Stopping peers ==="
kill $PID1 $PID2 $PID3 2>/dev/null || true
wait 2>/dev/null || true

if [ -f templates/PeerInfo.cfg.bak ]; then
    mv templates/PeerInfo.cfg.bak templates/PeerInfo.cfg
fi
if [ -f templates/Common.cfg.bak ]; then
    mv templates/Common.cfg.bak templates/Common.cfg
fi

echo "=== Done ==="
