import cv2
import numpy
import torch
import util.config as config
from midas.model_loader import load_model, default_models


## Print and keep the input prompt
def print_with_signature(*args):
    print(f"@MiDaS >> ", end="")
    [print(arg, end=" ") for arg in args]
    print("", flush=True)


## Parameters
NAME: str = "MiDaS Depth Estimation"
DEVICE = config.DEVICE
MODEL_TYPE: str = "dpt_levit_224"    # midas_v21_small_256, dpt_levit_224
MODEL_PATH: str = default_models[MODEL_TYPE]
SCALE: int = 6
THRESHOLD: float = 0.8

print_with_signature(f"{NAME.upper()}:")
print_with_signature("Device to use: ", DEVICE)
print_with_signature(f"Loading MiDaS model '{MODEL_TYPE}' from {MODEL_PATH}")
MODEL, TRANSFORM, _, _ = load_model(device=DEVICE, model_path=MODEL_PATH, model_type=MODEL_TYPE)

print_with_signature(f"Setting up reference and masking")
# The mask that allows converting relative depth to absolute depth
# Gradient is between ~ 1.4cm - 2.0cm
REF_LENGTH = 2.0    # Ref stick is length ~ 2cm
REF_VIEWABLE = 0.6  # Camera captures length ~ 0.6cm
REF_MASK = cv2.imread("./.temp/ref_mask.png", cv2.IMREAD_GRAYSCALE)  # Where the reference resides in the image
REF_BBOX = numpy.where(REF_MASK != 0)   # yy(0), xx(1) ~ pixels of the segment
REF_AREA = len(REF_BBOX[0])    # Area of the reference in pixels
REF_BBOX = min(REF_BBOX[0]), min(REF_BBOX[1]), max(REF_BBOX[0]), max(REF_BBOX[1])   # y1(0), x1(1), y2(2), x2(3)
REF_BBOX_MID = (REF_BBOX[0] + REF_BBOX[2]) // 2, (REF_BBOX[1] + REF_BBOX[3]) // 2   # my, mx ~ midpoint of the bounding box
REF_BBOX_HEIGHT, REF_BBOX_WIDTH = abs(REF_BBOX[2] - REF_BBOX[0]), abs(REF_BBOX[3] - REF_BBOX[1])  # size of the bounding box
print_with_signature(f"Generating reference gradient in real world units")
REF_CM: numpy.ndarray = numpy.zeros(REF_MASK.shape)     # b1 -- cm ~ real world gradient
for i, h in enumerate(range(REF_BBOX[0], REF_BBOX[2] + 1)):    # [y1, y2] - Assume linear interpolation
    # Row is stick_length - capture_length / pixel_length * index
    REF_CM[h][REF_MASK[h] != 0] = REF_LENGTH - REF_VIEWABLE / REF_BBOX_HEIGHT * i


## Find regions of interest within the image
def ROI(frame: numpy.ndarray, allowance: float = 0) -> list[numpy.ndarray]:
    result: list[numpy.ndarray] = []

    # Algorithm:
    # For each point on the edge:
    #   Get the moore neighbours
    #   For each moore neighbour:
    #       a. calculate the diff = abs(Surround - Centre)
    #       b. calculate the number of neighbours that are a part of the segment
    #   Pool the differences and find the min value for similar points
    #   If not all neighbours are part of the segment, it is an edge
    uncovered: numpy.ndarray = numpy.zeros(frame.shape)
    for y in range(frame.shape[0]):
        for x in range(frame.shape[1]):
            if uncovered[y, x] > 0: continue

            boundary: list[tuple] = [(y, x)]
            segment: numpy.ndarray = numpy.zeros(frame.shape)
            ## Check moore neighbours for each edge:
            while len(boundary) > 0:
                extended: set[tuple] = set()  # The new boundary
                # 1. Calculate the diff = abs(Surround - Centre):
                for point in boundary:
                    for ny, nx in [
                        (point[0] + dy, point[1] + dx)
                        for dy in range(-1, 2) for dx in range(-1, 2)
                        if not dy == dx == 0  # Eliminate centre
                    ]:  # a. Get the moore neighbours
                        # b. Check that it is in scope
                        if ny < 0 or ny >= frame.shape[0]: continue
                        if nx < 0 or nx >= frame.shape[1]: continue
                        # c. Check that it is not yet valid
                        if segment[ny, nx] > 0: continue
                        if (ny, nx) in extended: continue
                        if uncovered[ny, nx] > 0: continue
                        # d. Calculate the difference with centre
                        diff = abs(frame[y, x] - frame[ny, nx])
                        # e. Only append if the difference is valid
                        if diff <= allowance: extended.add((ny, nx))
                    ## Include extended as part of segment
                    segment[point[0], point[1]] = 1.0

                ## Swap boundary with extended
                boundary = list(extended)
            ## Combine segment with global
            uncovered[segment != 0] = 1.0

            ## Append result
            result.append(segment)

    return result


def normalise(frame: numpy.ndarray):
    depth_min, depth_max = frame.min(), frame.max()
    return (frame - depth_min) / (depth_max - depth_min)


## Main process
def main(image: numpy.ndarray):
    ## a. Apply Lightening Correction Techniques:
    ## ** Apply histogram equalization
    image = numpy.dstack(tuple(cv2.equalizeHist(image[:, :, c]) for c in range(3)))
    ## ** Apply gamma correction gamma = 1.5
    image = numpy.clip(numpy.power(image / 255, 2), 0.0, 1.0)

    ## b. Get Predictions on 2 Images, Scale and Localisation:
    ## ** Image for scale depth ~ Flip to RGB image
    orig_image = numpy.flip(image, 2)  # Flip to RGB
    ## ** Image for depth localisation - Crop the reference
    crop_image = orig_image[:REF_BBOX[0], :]
    ## ** Transform both images to fit the neural network
    shapes = orig_image.shape[:2], crop_image.shape[:2]
    orig_image, crop_image = [TRANSFORM({"image": x})["image"] for x in (orig_image, crop_image)]
    ## ** Depth Estimation Raw
    with torch.no_grad():   # Inference
        # ** Transform from numpy to torch tensor
        orig_image, crop_image = [torch.from_numpy(x).to('cpu').unsqueeze(0) for x in (orig_image, crop_image)]
        # ** Perform inference on both original and cropped
        raw_orig: numpy.ndarray = torch.nn.functional.interpolate(
            MODEL.forward(orig_image).unsqueeze(1),
            size=shapes[0], mode='bicubic', align_corners=False
        ).squeeze().cpu().numpy()
        raw_crop: numpy.ndarray = torch.nn.functional.interpolate(
            MODEL.forward(crop_image).unsqueeze(1),
            size=shapes[1], mode='bicubic', align_corners=False
        ).squeeze().cpu().numpy()
        # ** Artificially make mask region the brightest in the image
        offset = max(0, raw_orig.max() - raw_orig[REF_MASK != 0].max())
        raw_orig[REF_MASK == 0] = raw_orig[REF_MASK == 0] - offset
        raw_orig[REF_MASK != 0] = raw_orig[REF_MASK != 0] + offset
        # ** Exponentiate values to extend the range of the values
        raw_orig = numpy.power(raw_orig, 2)
        # ** Normalise values
        norm_orig: numpy.ndarray = normalise(raw_orig)
        norm_crop: numpy.ndarray = normalise(raw_crop)

    ## c. Calculate scale factor on original image inference assuming linear relationship
    ## ** DEPTH_CM = DEPTH_MIDAS * REF_CM / REF_MIDAS -- where b1 / a1 is scale
    scale: numpy.ndarray = numpy.array(norm_orig)    # copy temporary
    scale[REF_MASK == 0] = 0   # Acquire mask region -- a1 MiDaS
    # ** reference scale = REF_CM / REF_MIDAS
    scale[scale != 0] = REF_CM[scale != 0] / scale[scale != 0]
    # ** Observation: Scale increases as depth increases
    yy, xx = numpy.where(scale == scale[scale != 0].min())
    scale_avg_y1, scale_avg_x1 = scale[yy[0], xx[0]], norm_orig[yy[0], xx[0]]
    yy, xx = numpy.where(scale == scale[scale != 0].max())
    scale_avg_y2, scale_avg_x2 = scale[yy[0], xx[0]], norm_orig[yy[0], xx[0]]
    # ** Solve the linear equation -- SCALE = GRADIENT * NORM + INTERSECT
    scale_gradient = (scale_avg_y2 - scale_avg_y1) / (scale_avg_x2 - scale_avg_x1)
    scale_intersect = scale_avg_y1 - scale_gradient * scale_avg_x1
    # ** Apply linear gradient to calculate scale of every pixel
    scale: numpy.ndarray = numpy.array(norm_orig)  # Reset values
    scale[scale != 0] = scale_gradient * scale[scale != 0] + scale_intersect
    # ** Scale MiDaS original raw to real world units: DEPTH_MIDAS * scale
    scaled_orig: numpy.ndarray = numpy.array(raw_orig)                         # Copy
    scaled_orig[scaled_orig != 0] = scaled_orig[scaled_orig != 0] * scale[scaled_orig != 0]  # Apply scale
    scaled_orig = scaled_orig[:REF_BBOX[0], :]  # Crop to match ROI mask
    print_with_signature("Closest distance is", scaled_orig.min())
    print_with_signature("Furthest distance is", scaled_orig.max())

    ## d. Normalized original to between 0 and 1
    show_orig: numpy.ndarray = numpy.array(norm_orig)
    show_orig = numpy.dstack(tuple(show_orig for _ in range(3)))    # convert to rgb
    # ** Normalise the cropped inference
    show_crop: numpy.ndarray = numpy.array(norm_crop)
    show_crop = numpy.dstack(tuple(show_crop for _ in range(3)))    # convert to rgb
    # ** Apply threshold to the cropped inference for sectioning
    thresh_crop: numpy.ndarray = numpy.array(show_crop[:, :, 0])    # gray, not RGB
    thresh_crop[thresh_crop < THRESHOLD] = 0.0

    ## e. Rectangulate areas with similar pixels on the cropped inference
    roi: list = []  # returns a list of masks in the shape of the cropped image
    for mask in ROI(thresh_crop, 0.2):
        # ** non-maximum suppression - remove non-maxima masks
        if raw_crop[mask != 0].max() != raw_crop.max(): continue
        # ** Convert masks to bounding boxes (int):
        # ** y-location is auto-matched to original since it is smaller than
        ry, rx = numpy.where(mask != 0)
        y1, x1, y2, x2 = min(ry), min(rx), max(ry), max(rx)
        y1, x1, y2, x2 = int(y1), int(x1), int(y2), int(x2)
        # ** Estimated absolute min-depth within the segment
        ad = float(scaled_orig[mask != 0].min())
        # append to list - y1, x1, y2, x2, depth
        roi.append((y1, x1, y2, x2, ad))
        # draw bbox
        show_orig = cv2.rectangle(show_orig, (x1, y1), (x2, y2), (1.0, 0, 0), 1)
        show_crop = cv2.rectangle(show_crop, (x1, y1), (x2, y2), (1.0, 0, 0), 1)

    ## Package and send
    return (show_orig, show_crop), roi  # show(0), roi(1)... inference(2)
