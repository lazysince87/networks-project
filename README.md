# networks-project

team members: 
- Thuy Le
- Alice Jiang
- Aadithi Arjun
- Nivedhaa Sankaran

## local smoke test

1. make the test script executable and run it:

```bash
chmod +x tests/test_local_connections.sh
./tests/test_local_connections.sh
```

2. run a single peer manually (in separate terminals):

```bash
python3 src/peerProcess.py 1001
python3 src/peerProcess.py 1002
python3 src/peerProcess.py 1003
```

3. view logs produced by the peers:

```bash
tail -n +1 log_peer_1001.log log_peer_1002.log log_peer_1003.log
```