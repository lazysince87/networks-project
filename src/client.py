from strategy_manager import StrategyManager
import socket
import sys

def run():
    try:
        # Create a socket to connect to the server at localhost:8000
        request_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        request_socket.connect(('localhost', 8000))
        print("Connected to localhost in port 8000")
        
        while True:
            # Get Input from standard input
            message = input("Hello, please input a sentence: ")
            
            if not message:
                break
                
            # Send the sentence to the server
            request_socket.sendall(message.encode('utf-8'))
            
            # Receive the upperCase sentence from the server
            data = request_socket.recv(1024)
            MESSAGE = data.decode('utf-8')
            
            print(f"Receive message: {MESSAGE}")
            
    except ConnectionRefusedError:
        print("Connection refused. You need to initiate a server first.", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        request_socket.close()

if __name__ == "__main__":
    run()