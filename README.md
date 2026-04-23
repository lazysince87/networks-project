# networks-project

team members: 
- Thuy Le
- Alice Jiang
- Aadithi Arjun
- Nivedhaa Sankaran

## testing

you can configure the network in `PeerInfo.cfg` by adding the peer ids, machine ips, and ports you want to test across. `Common.cfg` contains the parameters like piece size and unchoking intervals for testing different scenarios.

once the configs are consistent across all computers, manually create a directory for your peer on your machine (like `peer_1002/`). the seed machine must have the target file placed inside its peer directory before starting.

to start the network, run this command for your peer id:
`python3 src/peerProcess.py <peer_id>`

as the peers boot up, they will establish tcp handshakes and begin sending bitfield messages. the log files `log_peer_<peer_id>.log` will automatically populate with real time updates on choked neighbors, piece requests, and file completion.

once all processes terminate cleanly, run the verification script to prove the reconstructed file matches the original perfectly:
`python3 src/verify.py original_file transferred_file`
