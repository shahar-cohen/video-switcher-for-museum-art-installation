#  util file for CamSwitch.py.
#  contains static functions and constants

import cv2

# ============ default values ============
DEFAULT_ANIMATION_FILE_NAME = "animation.mp4"
DEFAULT_MOTION_DELAY = 0.1
DEFAULT_IDLE_DELAY = 7.0
DEFAULT_THRESHOLD = 15
DEFAULT_DELAY_BETWEEN_FRAMES = 1
DEFAULT_WIDTH = 500
DEFAULT_HEIGHT = 500
DEFAULT_CAM_NUM = 0
DEFAULT_MIN_SIZE = 500
DEFAULT_WINDOW_LOCATION_X = -10
DEFAULT_WINDOW_LOCATION_Y = -10
DEFAULT_FLIP_MODE = True
SETTINGS_FILE = "settings.txt"
WINDOW_NAME = "camSwitcher"
CAM_EXAMPLE = "cam_example.mp4"

# ============ "magic nums" ============
ANIMATION = False
CAMERA = True
COMMENT_TAG = "#"

# ============ prefixes for settings in settings.txt ============
ANIMATION_FILE_SETTING = "animation:"
MINIMAL_MOTION_TIME_SETTING = "minimal motion time:"
MINIMAL_IDLE_TIME_SETTING = "minimal idle time:"
MOTION_SENSITIVITY_SETTING = "motion sensitivity:"
MOTION_SIZE_SENSITIVITY_SETTING = "motion size sensitivity:"
WINDOW_LOCATION_X_SETTING = "location x:"
WINDOW_LOCATION_Y_SETTING = "location y:"
WINDOW_WIDTH_SETTING = "width:"
WINDOW_HEIGHT_SETTING = "height:"
FRAME_DELAY_SETTING = "frame delay:"
TEST_MODE_SETTING = "test mode:"
FLIP_MODE_SETTING = "flip:"

# ============ static functions ============


def parse_digit_arg(raw_string, setting_string):
    extracted_string = raw_string.replace(setting_string, "", 1).strip()
    try:
        extracted_number = float(extracted_string)
    except ValueError:
        return False, -1

    return True, extracted_number


def exit_due_to_bad_settings_file(message):
    print(message + "\n" + "input error, consult example_settings.txt")
    exit(-1)


def get_valid_cam_num():
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i)
            if cap is None or not cap.isOpened():
                continue

            return i

        except cv2.error:
            continue

    print('Warning: unable to open video source. exiting program.')
    exit(-1)
