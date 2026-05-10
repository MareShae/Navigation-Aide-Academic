DISPLAY_NAME: str = "BME-ECE 499"

# imaginary depth of 100 px
CAPTURE_SX: tuple = (320, 320, 100)

ROOM_DIM: tuple = tuple(c // 4 for c in CAPTURE_SX[:2])

AREA: int = ROOM_DIM[0] * ROOM_DIM[1]

DEVICE: str = "cpu"
