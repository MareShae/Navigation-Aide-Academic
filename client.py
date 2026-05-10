#!/home/naviaide/venv/bin/python3.9

import cv2
import sys
import time
import types
import socket
import traceback
import multiprocessing.connection
import util.comms as comms
import util.config as config
from util.parallel import Parallel


### TERMINAL FUNCTIONS:
## Print and keep the input prompt
def print_with_signature(*args):
    print(f"@Client >> ", end="")
    [print(arg, end=" ") for arg in args]
    print("", flush=True)


### AUDIO PROCESSING FUNCTIONS:
## Virtual sound synthesis
def sound_synthesis(conn: multiprocessing.connection.Connection):
    import ClientRPi.acoustics as acoustics
    acoustics.main(conn)


### MAIN -- ARGV, ARGC:
## Socket
SOCKET: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

## Camera access via OpenCV (faster than picamera)
print_with_signature("Initialise camera")
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAPTURE_SX[0])
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAPTURE_SX[1])
camera.set(cv2.CAP_PROP_FPS, 36)

## Multicore Process
acoustics: Parallel = Parallel(target=sound_synthesis, args=())
acoustics.start()
if acoustics.recv() is Parallel.BREAK:
    print_with_signature("Unable to initialise audio processes")
    acoustics.close()
    exit()

try:
    print_with_signature("Establishing connection to server")
    SOCKET.connect(comms.CONNECT)

    while True:
        ## Data between server and client
        data: dict = {}

        ## Capture frame from the camera
        _, frame = camera.read()
        ## Scale for real-time compatibility
        frame = cv2.resize(frame, config.ROOM_DIM)
        ## Rotate to proper orientation
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        ## Convert to native type
        data["image"] = frame.tolist()

        ## Send image to the server
        comms.send(SOCKET, data)
        ## Receive response from the server
        data = comms.recv(SOCKET)
        ## Break condition
        if not data: break

        ## Handle incoming data
        start: float = time.time()
        acoustics.send(data["depth"])
        if acoustics.recv() is Parallel.BREAK: break
        print_with_signature("Took", time.time() - start, "seconds for audio")

except KeyboardInterrupt:
    print_with_signature("Caught interrupt")

except Exception as exception:
    print_with_signature("Caught exception: ", exception)
    # get the error details
    error_type, error_value = type(exception), exception.args[0]
    error_traceback = traceback.format_exception(error_type, exception, None)
    # extract the traceback object from the exception
    tb: types.TracebackType|None = sys.exc_info()[2]
    # get the file name and line number where the error occurred
    tb_info: traceback.FrameSummary = traceback.extract_tb(tb)[-1]
    # print the error details
    print_with_signature('Error type:', error_type)
    print_with_signature('Error value:', error_value)
    print_with_signature('Error traceback:')
    for line in error_traceback: print_with_signature(line.strip())
    print_with_signature('File:', f"'{tb_info.filename}'")
    print_with_signature('Line:', tb_info.lineno)
    print_with_signature('Function:', tb_info.name)

print_with_signature("Closing audio process")
acoustics.close()
print_with_signature("Closing sockets")
SOCKET.close()
