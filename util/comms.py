import socket
import struct
import msgpack


CHUNKS: int = 4096
CONNECT: tuple = "10.42.0.1", 6789
#CONNECT: tuple = "10.0.0.220", 6789
#CONNECT: tuple = "134.87.173.141", 6789


def send(sock: socket.socket, data: dict|None = None) -> None:
    _data: bytes = msgpack.packb(data)   # Serialize
    print("Sending package of", len(_data))
    ## Prefix each message with a 4-byte length (network byte order)
    sock.sendall(struct.pack('>I', len(_data)))
    sock.sendall(_data)


def recv(sock) -> dict:
    _data_len = struct.unpack('>I', sock.recv(4))[0]
    data: bytes = b''
    while len(data) < _data_len:
        chunk = sock.recv(_data_len - len(data))
        if not chunk: break
        data += chunk
    return msgpack.unpackb(data)
