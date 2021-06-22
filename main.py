from pyboy import PyBoy, WindowEvent
from PIL import Image
from PIL import ImageEnhance
import numpy as np
import cv2
import sys
import time
import _thread

stdin_fileno = sys.stdin

def stdin_messages(boy):
    # Keeps reading from stdin and quits only if the word 'exit' is there
    # This loop, by default does not terminate, since stdin is open
    for line in stdin_fileno:
        # Remove trailing newline characters using strip()
        msg = line.strip()
        if 'exit' == msg:
            exit(0)
        if 'jump' == msg:
            boy.send_input(WindowEvent.PRESS_BUTTON_A)
            time.sleep(.1)
            boy.send_input(WindowEvent.RELEASE_BUTTON_A)
        if 'move' == msg:
            boy.send_input(WindowEvent.PRESS_ARROW_RIGHT)
            time.sleep(.1)
            boy.send_input(WindowEvent.RELEASE_ARROW_RIGHT)


def adjust_gamma(image, gamma=1.0):
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

def transform_translation(screen):
    screen = Image.fromarray(screen)
    # screen = screen.rotate(180)
    screen = screen.transpose(Image.FLIP_LEFT_RIGHT)
    img = screen.resize((48, 24), Image.ANTIALIAS)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2)
    B = np.asarray(img.convert('L'))
    B_copy = B.copy()
    B_copy[12, 15] = 0
    newData = B.ravel()
    transformData = ""
    for ele in newData:
        transformData += (" "+str(ele).rstrip('\n'))
    pass
    return transformData

def validate_contours(contours, frame1, frame2):
    newContours = []
    for contour in contours:
        (x, y, w, h) = cv2.boundingRect(contour)
        crop1 = frame1[y:y+h, x:x+w]
        crop2 = frame2[y:y+h, x:x+w]
        diff = cv2.absdiff(crop1, crop2)
        if diff.mean() < 15 and crop2.mean() < 177:
            newContours.append(contour)
    return newContours

def find_contours(frame1, frame2):
    diff = cv2.absdiff(frame1, frame2)
    diff_grey = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(diff_grey, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 8))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    dilated = cv2.dilate(thresh, None, iterations=3)
    if dilated.mean() > 177: # filter for when the background moves
        return []
    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return contours

def filter_contours_by_size(contours):
    filtered = []
    for contour in contours:
        (x, y, w, h) = cv2.boundingRect(contour)
        if 10 < w < 40 and 10 < h < 40:
            filtered.append(contour)
    return filtered

def draw_contours(contours, frame):
    for contour in contours:
        # (x, y, w,s h) = cv2.boundingRect(contour)
        cv2.drawContours(frame, contours, -1, (0, 0, 255), 1)

def filter_light_dark(lightFrame, contours):
    darkFrame = adjust_gamma(lightFrame, .1)
    lightFrame = adjust_gamma(lightFrame, 10)
    stencil = np.zeros(darkFrame.shape[:-1]).astype(np.uint8)
    mask_value = 255
    cv2.fillPoly(stencil, contours, mask_value)
    sel = stencil != mask_value
    darkFrame[sel] = lightFrame[sel]
    return darkFrame

def merge_contours(contours1, contours2):
    for contour in contours2:
        # (x, y, w,s h) = cv2.boundingRect(contour)
        contours1.append(contour)
    return contours1

def run_game(boy):
    # runs the pyboy frame loop
    frame1 = np.empty
    contours = []
    cv2.namedWindow("contours", cv2.WINDOW_NORMAL)

    while not boy.tick():
        screen = boy.botsupport_manager().screen().screen_image()
        frame2 = cv2.cvtColor(np.array(screen), cv2.COLOR_BGR2RGB)
        lightFrame = frame2.copy()
        if isinstance(frame1, np.ndarray):
            cachedContours = validate_contours(contours, frame1, frame2)
            newContours = find_contours(frame1, frame2)
            newContours = filter_contours_by_size(newContours)
            cachedContours = merge_contours(cachedContours, newContours)
            draw_contours(cachedContours, lightFrame)
            contours = cachedContours

        filterFrame = filter_light_dark(lightFrame, contours)

        frame1 = frame2
        cv2.imshow('contours', filterFrame)

        transformData = transform_translation(filterFrame)
        # send to stdout with print
        print(transformData)

if __name__ == "__main__":
    pyboy = PyBoy('ROM/mario.gb')
    try:
        _thread.start_new_thread(stdin_messages, (pyboy,))
        run_game(pyboy)
    except:
        print("Error: unable to start thread")

    while 1:
        pass
