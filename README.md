# networks-project

team members: 
- Thuy Le
- Alice Jiang
- Aadithi Arjun
- Nivedhaa Sankaran

## local testing

we have two ways to test the peer network locally: using the automated bash scripts (recommended) or running the peers manually.

### 1. automated testing (recommended)

our integrated test scripts will automatically create a temporary dummy file, run `setup_test.sh` to construct the peer directories and properly seed the file, start the peers, and verify everything works.

> **note for windows users:** please use **Git Bash** or **WSL** to run these `.sh` scripts.

to run a full file transfer and automatically verify file integrity:
```bash
bash tests/test_full_transfer.sh
```

to run a quick connection/handshake test:
```bash
bash tests/test_local_connections.sh
```

### 2. manual testing

if you want to manually start the peers to test specific features, run the setup script first.

#### 1. create a dummy test file
**mac / linux:**
```bash
dd if=/dev/urandom of=testfile.dat bs=1024 count=100
```
**windows (powershell):**
```powershell
fsutil file createnew testfile.dat 102400
```

#### 2. run the setup script
run this to construct the peer directories (`peer_1001/`, etc.) and seed the file. pass your filename as an argument (use git bash or wsl on windows):
```bash
bash setup_test.sh testfile.dat
```

#### 3. run the peers manually
run these commands in separate terminal windows (start them in numerical order):

**mac / linux:**
```bash
python3 src/peerProcess.py 1001
python3 src/peerProcess.py 1002
python3 src/peerProcess.py 1003
```
**windows:**
```powershell
python src/peerProcess.py 1001
python src/peerProcess.py 1002
python src/peerProcess.py 1003
```

#### 4. view the logs produced by the peers
once the peers have finished, you can read the log files in any text editor, or use the terminal:

**mac / linux:**
```bash
tail -n +1 log_peer_1001.log log_peer_1002.log log_peer_1003.log
```
**windows (powershell):**
```powershell
Get-Content log_peer_*.log
```
