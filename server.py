import cv2
import sys
import time
import numpy
import types
import queue
import socket
import threading
import traceback
import util.comms as comms
import ServerPC.MiDaS as MiDaS


## Print and keep the input prompt
def print_with_signature(*args):
    print(f"@Server >> ", end="")
    [print(arg, end=" ") for arg in args]
    print("", flush=True)


### TERMINAL FUNCTIONS:
# Variable shared between main and terminal process
VAR_TERMINAL: queue.Queue = queue.Queue()
DISPLAY_NAMES: list[str] = ["RPi Camera Feed", "MiDaS Depth -- Original", "MiDaS Depth --- Cropped"]

## Allows main thread to run without interruption
def control_via_terminal():
    import ServerPC.terminal as terminal
    terminal.SubServer(VAR_TERMINAL)


## Handle data from terminal
def Handle_Shared_Queue():
    RUNNING: bool = True

    # retrieve elements from the queue in a non-blocking manner
    while not VAR_TERMINAL.empty():
        try:
            stdout: str = VAR_TERMINAL.get_nowait()
            if stdout == 'exit': RUNNING = False
        except queue.Empty:
            pass

    return RUNNING


### MAIN -- ARGV, ARGC:
## Define terminal thread
xterm: threading.Thread | None = None

## Socket
print_with_signature(f"Server address is {comms.CONNECT}")
SOCKET: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
CLIENT: socket.socket | None = None
try:
    print_with_signature("Binding address to server")
    SOCKET.bind(comms.CONNECT)

    print_with_signature("Listening for clients")
    SOCKET.listen()

    print_with_signature("Waiting for client to accept")
    CLIENT, ADDRESS = SOCKET.accept()
    print_with_signature(f"Connected by {ADDRESS}")

    ## Start terminal control in another thread
    xterm = threading.Thread(target=control_via_terminal)
    xterm.start()

    ## Handle data from terminal and return if not quits
    while Handle_Shared_Queue():
        ## Record start time
        start: float = time.time()

        ## a. Decode from utf encoding, Deserialize from json
        recv: dict = comms.recv(CLIENT)
        if not recv: break
        print_with_signature("Took", time.time() - start, "seconds to receive image")

        ## b. Convert to numpy array -- this is the input image.!!
        ## ** Numpy should be shape: (80, 60, 3)
        image: numpy.ndarray = numpy.asarray(recv["image"], dtype=numpy.uint8)

        ## c. Send to multicore processes
        show, roi = MiDaS.main(image)

        ## d. Response to client w depth regions[xyz] and objects detected[class]
        comms.send(CLIENT, {"depth": roi})
        print_with_signature("Distance is ~", roi[0][4], "cm")

        ## e. Combine into one frame for display
        fusion: numpy.ndarray = numpy.zeros((
            max(image.shape[0], show[0].shape[0], show[1].shape[0]),
            image.shape[1] + show[0].shape[1] + show[1].shape[1], 3
        ), dtype=numpy.float32)
        image = numpy.array(image / 255, dtype=numpy.float32)
        cursor = 0
        fusion[:image.shape[0], cursor:cursor+image.shape[1]] = image
        cursor = cursor + image.shape[1]
        fusion[:show[0].shape[0], cursor:cursor+show[0].shape[1]] = show[0]
        cursor = cursor + show[0].shape[1]
        fusion[:show[1].shape[0], cursor:cursor+show[1].shape[1]] = show[1]
        cv2.imshow(" | ".join(DISPLAY_NAMES), fusion)
        cv2.waitKey(1)

        ## Inference FPS ~ Calculate time it took for this frame
        print_with_signature(int(1 / (time.time() - start)), "FPS")

except KeyboardInterrupt:
    print_with_signature("Caught interrupt")

except Exception as exception:
    print_with_signature("Caught exception: ", exception)
    # get the error details
    error_type, error_value = type(exception), exception.args[0]
    error_traceback = traceback.format_exception(error_type, exception, None)
    # extract the traceback object from the exception
    tb:  types.TracebackType|None = sys.exc_info()[2]
    # get the file name and line number where the error occurred
    tb_info: traceback.FrameSummary = traceback.extract_tb(tb)[-1]
    # print the error details
    print_with_signature('Error type: ', error_type)
    print_with_signature('Error value: ', error_value)
    print_with_signature('Error traceback: ')
    for line in error_traceback: print_with_signature(line.strip())
    print_with_signature('File: ', f"'{tb_info.filename}'")
    print_with_signature('Line: ', tb_info.lineno)
    print_with_signature('Function:', tb_info.name)

# Ask client to close their socket
if CLIENT: comms.send(CLIENT, None)
print_with_signature("Closing OpenCV windows")
cv2.destroyAllWindows()             # Close openCV windows
print_with_signature("Waiting for terminal to close. Use `exit`")
if xterm: xterm.join()              # Close external terminals
print_with_signature("Closing client socket")
if CLIENT: CLIENT.close()           # Close connected client
print_with_signature("Closing socket")
if SOCKET: SOCKET.close()           # Close this server
