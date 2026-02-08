import socket
import threading

# The server will be listening on this port number
S_PORT = 8000

def handle_client(connection, client_num):
    """
    A handler function (equivalent to the Handler class in Java).
    Responsible for dealing with a single client's requests.
    """
    print(f"Client {client_num} is connected!")
    try:
        while True:
            # Receive the message sent from the client (buffer size 1024)
            data = connection.recv(1024)
            if not data:
                break
                
            message = data.decode('utf-8')
            print(f"Receive message: {message} from client {client_num}")
            
            MESSAGE = message.upper()
            
            # Send MESSAGE back to the client
            connection.sendall(MESSAGE.encode('utf-8'))
            print(f"Send message: {MESSAGE} to Client {client_num}")
            
    except Exception as e:
        print(f"Disconnect with Client {client_num}")
    finally:
        # Close connections
        connection.close()

def main():
    print("The server is running.")
    # Create a TCP/IP socket
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('localhost', S_PORT))
    listener.listen(5)
    
    client_num = 1
    try:
        while True:
            connection, address = listener.accept()
            # Start a new thread to handle the client
            client_thread = threading.Thread(target=handle_client, args=(connection, client_num))
            client_thread.start()
            client_num += 1
    finally:
        listener.close()

if __name__ == "__main__":
    main()