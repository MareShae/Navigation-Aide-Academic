# Import audio libraries
# Import pi camera libraries
import picamera
from picamera.array import PiRGBArray
# Import neural network libraries

#
camera = picamera.PiCamera()
camera.framerate = 60
# camera.rotation = 270
camera.resolution = (320, 240)
rawcapture = PiRGBArray(camera, size=(320, 240))

# Main Loop: Capture  timelapse sequences
for capture in camera.capture_continuous(rawcapture, format="rgb", use_video_port=True):
    # Capture from camera
    frame = capture.array

    # TODO: Stuff herew image.!!

    # Clear stream for next capture
    rawcapture.truncate(0)
