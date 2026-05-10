import sys
import math
import numpy
import types
import traceback
import multiprocessing
import multiprocessing.connection
import util.config as config
from util.parallel import Parallel


## Print and keep the input prompt
def print_with_signature(*args):
    print(f"@Ambisonics >> ", end="")
    [print(arg, end=" ") for arg in args]
    print("", flush=True)


## Parameters for Sound Field Synthesis
NAME: str = "Ambisonics - Sound Field"
CHUNK: int = 4410   # Number of frames per audio chunk
SAMPLING: int = 44100   # Sampling frequency
DURATION: float = 0.1   # Duration of the generated audio in seconds
AMPLITUDE: float = 1
FREQ_L: float = 440     # Frequency of the sound source in Hz
FREQ_H: float = 4400    # Frequency of the sound source in Hz
FREQ_GRAD: float = FREQ_H - FREQ_L  # Linear gradient


## Create a virtual room for Sound Field Synthesis
ROOM_DIM: tuple = config.ROOM_DIM  # Room dimensions in meters (x, y, z)
# Receiver Location
HEAD = tuple([(dim + 1) // 2 for dim in ROOM_DIM[:2]] + [0])    # Middle of the room
print_with_signature(f"Virtual room set at {ROOM_DIM} in meters")
print_with_signature(f"Listener placed at {HEAD}")

print_with_signature(f"{NAME.upper()}:")
print_with_signature("Generating base audio feedback as NumPy array")
SIGNAL: numpy.ndarray = numpy.arange(int(SAMPLING * DURATION)).astype(numpy.float32)
SIGNAL = 2 * numpy.pi * SIGNAL / SAMPLING


## Calculate horizontal (α) and vertical (β) angles between listener and source
def azimuth_and_elevation(listener, source):
    dy, dx, dz = [c2 - c1 for c1, c2 in zip(listener, source)]
    # α = atan2(y2 - y1, x2 - x1)
    azimuth = math.atan2(dy, dx)
    # β = atan2(z2 - z1, sqrt((x2 - x1)^2 + (y2 - y1)^2))
    elevation = math.atan2(dz, math.sqrt(dx**2 + dy**2))
    return azimuth, elevation


## Simulates (up, down), (left, right), (fore, back) audio
def acoustics(source, frequency):
    # Calculate horizontal and vertical angles to sound source
    azimuth, elevation = azimuth_and_elevation(HEAD, source)

    # Vector-Based Panning - gain of L and R based on the azimuth
    gain_L, gain_R = numpy.cos(azimuth), numpy.sin(azimuth)
    # Volume attenuation based on the distance given by MiDaS
    depth_attenuation = 1.0 / source[2] if source[2] > 1.0 else 1.0   # Btw 0.0 and 1.0

    # Apply gain and volume attenuation to L and R audio
    signal = numpy.sin(SIGNAL * frequency)
    L = signal * gain_L * depth_attenuation
    R = signal * gain_R * depth_attenuation

    return numpy.column_stack((L, R))


## Main process
def main(conn: multiprocessing.connection.Connection):
    PROCESS_POOL = multiprocessing.Pool()

    ## Multicore Process
    player: Parallel = Parallel(target=playback, args=())
    player.start()
    if player.recv() is Parallel.BREAK:
        print_with_signature("Unable to initialise playback processes")
        player.close()
        conn.send(Parallel.BREAK)
        return

    try:
        ## Send confirmation to the main body
        conn.send(Parallel.CARRY)
        ## Sound Array - this runs until exit
        while True:
            recv = conn.recv()
            if recv is Parallel.BREAK: break

            ## Send 'continue' after reception
            conn.send(Parallel.CARRY)

            ## MiDaS simulation - keys: y1, y2, x1, x2, depth
            print_with_signature("Post-processing MiDaS")
            poi: tuple[tuple, ...] = tuple((
                # Position - x, y, and z-depth
                ((y1 + y2) / 2, (x1 + x2) / 2, ad),
                # Frequency - The bigger the bounding box, the lower the frequency
                FREQ_H - max((y2 - y1) / ROOM_DIM[0], (x2 - x1) / ROOM_DIM[1]) * FREQ_GRAD
            ) for y1, x1, y2, x2, ad in recv)
            ## Pass parameters to multiprocess pool
            if len(poi):
                poi: list = PROCESS_POOL.starmap(acoustics, poi)
                poi: numpy.ndarray = numpy.sum(poi, axis=0)

            ## Send to player
            print_with_signature("Send to sounddevice")
            player.send(poi)
            if player.recv() is Parallel.BREAK: break

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
        print_with_signature('Error type: ', error_type)
        print_with_signature('Error value: ', error_value)
        print_with_signature('Error traceback: ')
        for line in error_traceback: print_with_signature(line.strip())
        print_with_signature('File: ', f"'{tb_info.filename}'")
        print_with_signature('Line: ', tb_info.lineno)
        print_with_signature('Function:', tb_info.name)

    finally:
        conn.send(Parallel.BREAK)
        print_with_signature("Closing playback stream")
        player.close()
        print_with_signature("Closing audio multiprocess pool")
        PROCESS_POOL.close()
        PROCESS_POOL.join()


def playback(conn: multiprocessing.connection.Connection):
    import sounddevice

    # Set buffer at length of audio to prevent under/overrun
    sounddevice.default.blocksize = 4410

    try:
        ## Send confirmation to the main body
        conn.send(Parallel.CARRY)
        ## Audio - this runs until exit
        while True:
            recv = conn.recv()
            if recv is Parallel.BREAK: break

            ## Send 'continue' after reception
            conn.send(Parallel.CARRY)

            ## c. Handle playing audio
            print_with_signature("Playing audio")
            recv = numpy.array(recv, dtype=numpy.float32)
            sounddevice.play(recv, 44100)
            sounddevice.wait()

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
        print_with_signature('Error type: ', error_type)
        print_with_signature('Error value: ', error_value)
        print_with_signature('Error traceback: ')
        for line in error_traceback: print_with_signature(line.strip())
        print_with_signature('File: ', f"'{tb_info.filename}'")
        print_with_signature('Line: ', tb_info.lineno)
        print_with_signature('Function:', tb_info.name)

    finally:
        conn.send(Parallel.BREAK)
        print_with_signature("Closing playback process")
