#!/home/shai/Documents/Programming/.venv/bin/python3.10
import sys
import queue
import socket
import pickle


## Socket parameters
CONNECT: tuple = ('localhost', 12345)


## Print and keep the input prompt
def print_with_signature(*args):
    print(f"@Terminal >> ", end="")
    [print(arg, end="") for arg in args]
    print("", flush=True)


def SubServer(shared_data: queue.Queue):
    import subprocess

    # Create a new socket object
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client: socket.socket | None = None
    try:
        # Bind the socket to a local address and port
        print_with_signature("Binding to local host")
        server.bind(CONNECT)

        ## Start the client
        subprocess.run("konsole -e './terminal.py --client' &", shell=True)

        # Listen for incoming connections
        print_with_signature("Listening for connection")
        server.listen(1)
        # Accept an incoming connection
        print_with_signature("Waiting for client to accept")
        client, addr = server.accept()
        print_with_signature("Connection accepted")
        while True:
            # Receive data from the client in small chunks
            data = client.recv(4096)
            data = pickle.loads(data)
            shared_data.put(data)
            if data == 'exit': break
    except KeyboardInterrupt:
        print_with_signature("Caught interrupt")
    except Exception as exception:
        print_with_signature("Caught exception: ", exception)
    finally:
        print_with_signature("Closing sockets")
        # Close the socket
        if client: client.close()
        if server: server.close()


def SubClient():
    # Create a new socket object
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to a remote server
        print("Attempting to connect to server")
        client.connect(CONNECT)
        print("Type here and hit 'Enter' to send commands to main")
        while True:
            data: str = input('@Terminal >> ')
            client.sendall(pickle.dumps(data))
            if data == 'exit': break
    except KeyboardInterrupt:
        print("Caught interrupt")
    except Exception as exception:
        print("Caught exception: ", exception)
    finally:
        # Close the socket
        print("Closing sockets")
        client.close()


if __name__ == "__main__":
    if len(sys.argv[1:]) > 1:
        print("Too many arguments")
        exit()
    if sys.argv[1] == "--help":
        print("--server           To call server")
        print("--client           To call client")
        print("--help             To show this note")
    elif sys.argv[1] == "--server":
        SubServer(queue.Queue())
    elif sys.argv[1] == "--client":
        SubClient()
