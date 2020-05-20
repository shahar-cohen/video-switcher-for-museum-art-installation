# Switcher - a script to switch video output between an animation file and webcam upon detection of movement.
# Author - Shahar Cohen 6/5/19
#
# Instructions:
# change parameters in settings.txt files to change the behaviour of the program.
#
# default values are as mentioned in the example_settings.txt and util.py files.
#
# press q or left click mouse anywhere to quit.

import util  # util file containing static functions and constants

import cv2
import os
import time
import sys


class CamSwitch:

    def __init__(self):
        # init values that will remain constant throughout the program operation
        self.ANIMATION_FILE_NAME = util.DEFAULT_ANIMATION_FILE_NAME
        self.MOTION_DELAY = util.DEFAULT_MOTION_DELAY
        self.IDLE_DELAY = util.DEFAULT_IDLE_DELAY
        self.THRESHOLD = util.DEFAULT_THRESHOLD
        self.DELAY_BETWEEN_FRAMES = util.DEFAULT_DELAY_BETWEEN_FRAMES
        self.WIDTH = util.DEFAULT_WIDTH
        self.HEIGHT = util.DEFAULT_HEIGHT
        self.CAM_NUM = util.DEFAULT_CAM_NUM
        self.MIN_SIZE = util.DEFAULT_MIN_SIZE
        self.WINDOW_LOCATION_X = util.DEFAULT_WINDOW_LOCATION_X
        self.WINDOW_LOCATION_Y = util.DEFAULT_WINDOW_LOCATION_Y
        self.FLIP_MODE = util.DEFAULT_FLIP_MODE
        # init variables:
        self.camera = None
        self.animation = None
        self.prev_processed_frame = None
        self.curr_cam_frame = None
        self.curr_processed_frame = None
        self.animation_frame = None
        self.exit_required = False
        self.output_is_cam = False
        self.motion_detected = False
        self.motion_start_time = None
        self.idle_start_time = None
        self.counter = 0
        self.motion_counter = 0
        self.avg = 0

    def run(self):
        """
        initialize and run main loop
        """
        # load args from settings file and init video feed accordingly
        self.load_args_from_settings_file()
        self.init_video_feed()

        while not self.exit_required:  # main program operation loop
            self.check_motion()  # check if motion occurred
            self.update_frames()  # get new frames from feed
            self.change_output_according_to_motion()  # check if (lack of) motion requires to change video source
            self.output_single_frame()  # output frame from video source

            # check if q pressed
            if cv2.waitKey(self.DELAY_BETWEEN_FRAMES) & 0x7F == ord('q'):
                print("Exit requested.")
                break

        # exit gracefully:
        if self.animation is not None:
            self.animation.release()
        self.camera.release()
        cv2.destroyAllWindows()

    def init_video_feed(self, is_camera=True):
        """
        init video feed. if is_camera == True, init camera feed, otherwise init animation feed
        """
        # set source
        if is_camera:
            if self.CAM_NUM < 0:
                self.camera = cv2.VideoCapture(util.CAM_EXAMPLE)
            else:
                self.camera = cv2.VideoCapture(self.CAM_NUM)

            if not self.camera.isOpened():
                print("Error: Could not open camera number: " + str(self.CAM_NUM))
                sys.exit()

        else:
            self.animation = cv2.VideoCapture(self.ANIMATION_FILE_NAME)
            if not self.animation.isOpened():
                print("Error: Could not open video file.")
                sys.exit()

        # initialize first frames if not done yet:
        if self.prev_processed_frame is None:
            self.load_cam_frame()
            self.prev_processed_frame = self.curr_processed_frame

    def check_motion(self):
        """
        detect motion between the last two frames of camera feed
        """
        # Difference between the last two frames:
        diff_frame = cv2.absdiff(self.curr_processed_frame,
                                 self.prev_processed_frame)

        # process
        thresh_frame = cv2.threshold(diff_frame, self.THRESHOLD, 255, cv2.THRESH_BINARY)[1]
        thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)
        # Finding contour of moving object (try and except are for backwards compatibility)
        try:
            cnts, notreallyused = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        except ValueError:
            (_, cnts, _) = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False

        for contour in cnts:
            if cv2.contourArea(contour) > self.MIN_SIZE:
                motion_detected = True
                break

        self.motion_detected = motion_detected

    def load_animation_frame(self):
        """
        load the next frame of the animation video
        """
        if self.animation is None:
            self.init_video_feed(util.ANIMATION)
        is_valid, self.animation_frame = self.animation.read()

        # if failed, try to restart source and try again:
        if not is_valid:
            self.init_video_feed(util.ANIMATION)

            is_valid_now, self.animation_frame = self.animation.read()

            if not is_valid_now:
                print("capture malfunction.")
                sys.exit()

    def load_cam_frame(self):
        """
        load next frame from camera feed and preprocess it for use
        """
        is_valid, self.curr_cam_frame = self.camera.read()

        # if failed, try to restart source and try again:
        if not is_valid:
            print("cam found invalid")
            self.init_video_feed(util.CAMERA)
            is_valid_now, self.curr_cam_frame = self.camera.read()

            if not is_valid_now:
                print("capture malfunction.")
                sys.exit()

        # produce blurred greyscale frame from original frame:
        self.curr_processed_frame = cv2.GaussianBlur(cv2.cvtColor(self.curr_cam_frame, cv2.COLOR_BGR2GRAY), (21, 21), 0)

    def update_frames(self):
        """
        save curr_processed_frame to prev_processed_frame and obtain new curr_processed_frame
        """
        self.prev_processed_frame = self.curr_processed_frame
        self.load_cam_frame()

    def change_output_according_to_motion(self):
        """
        if in animation feed and motion has occurred for a substantial amount of time, change to camera feed.
        if in camera feed and no motion has been detected for a substantial amount of time, change to animation feed.
        """
        if self.motion_detected:

            if self.motion_start_time is None:
                self.motion_start_time = time.time()
            self.idle_start_time = None

        else:
            if self.idle_start_time is None:
                self.idle_start_time = time.time()

        if self.motion_start_time is not None:
            if time.time() - self.motion_start_time >= self.MOTION_DELAY:
                self.output_is_cam = True

        if self.idle_start_time is not None:
            if time.time() - self.idle_start_time >= self.IDLE_DELAY:
                self.output_is_cam = False
                self.motion_start_time = None

    def output_single_frame(self):
        """
        output image from current feed to window of parameters set by settings.txt
        """
        if self.output_is_cam:
            # restart animation source upon switching to camera output:
            if self.animation is not None:
                self.animation = None

        else:
            # initialize animation feed if not done yet:
            if self.animation is None:
                self.init_video_feed(util.ANIMATION)
            # get frame:
            self.load_animation_frame()

        # window settings:
        cv2.namedWindow(util.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(util.WINDOW_NAME, self.WIDTH, self.HEIGHT)
        cv2.moveWindow(util.WINDOW_NAME, self.WINDOW_LOCATION_X, self.WINDOW_LOCATION_Y)
        cv2.setWindowProperty(util.WINDOW_NAME, cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_KEEPRATIO)
        cv2.setMouseCallback(util.WINDOW_NAME, self.mouse_click)

        if self.output_is_cam:  # output camera frame
            if self.FLIP_MODE:
                cv2.flip(self.curr_cam_frame, 1, self.curr_cam_frame)

            cv2.imshow(util.WINDOW_NAME, self.curr_cam_frame)

        else:  # output animation frame
            cv2.imshow(util.WINDOW_NAME, self.animation_frame)

    def mouse_click(self, event, x, y, flags, param):  # args aren't used but needed to conform with click event binding
        """
        upon left mouse button click, denote that exit was required.
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            self.exit_required = True

    def load_args_from_settings_file(self):
        """
        checks each line that isn't a comment in the settings.txt file for relevant parameter.
        if parameter prefix is found, the parameter is loaded to the appropriate CamSwitch class attribute.
        if any parameter is out of bounds of acceptable values, an error message is printed and the program is exited.
        """
        file = open(util.SETTINGS_FILE, "r")

        lines = file.readlines()

        file.close()

        for line in lines:
            if line.startswith(util.COMMENT_TAG):
                continue

            line = line.split("#")[0].strip()  # remove comments ant trailing spaces.

            if line.startswith(util.ANIMATION_FILE_SETTING):
                self.ANIMATION_FILE_NAME = line.replace(util.ANIMATION_FILE_SETTING, "", 1).strip()
                if not os.path.isfile(self.ANIMATION_FILE_NAME):
                    util.exit_due_to_bad_settings_file("animation file not found")
                continue

            if line.startswith(util.MINIMAL_MOTION_TIME_SETTING):
                is_ok, self.MOTION_DELAY = util.parse_digit_arg(line, util.MINIMAL_MOTION_TIME_SETTING)

                if (not is_ok) or self.MOTION_DELAY <= 0:
                    util.exit_due_to_bad_settings_file("motion delay input error")

                continue

            if line.startswith(util.MINIMAL_IDLE_TIME_SETTING):
                is_ok, self.IDLE_DELAY = util.parse_digit_arg(line, util.MINIMAL_IDLE_TIME_SETTING)

                if (not is_ok) or self.IDLE_DELAY <= 0:
                    util.exit_due_to_bad_settings_file("idle delay input error")
                continue

            if line.startswith(util.MOTION_SENSITIVITY_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.MOTION_SENSITIVITY_SETTING)
                self.THRESHOLD = int(num)
                if (not is_ok) or (self.THRESHOLD < 1 or self.THRESHOLD > 255):
                    util.exit_due_to_bad_settings_file("motion sensitivity input error")
                continue

            if line.startswith(util.MOTION_SIZE_SENSITIVITY_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.MOTION_SIZE_SENSITIVITY_SETTING)
                self.MIN_SIZE = int(num)
                if (not is_ok) or (self.MIN_SIZE < 1):
                    util.exit_due_to_bad_settings_file("minimum motion size input error")
                continue

            if line.startswith(util.WINDOW_LOCATION_X_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.WINDOW_LOCATION_X_SETTING)
                self.WINDOW_LOCATION_X = int(num)
                if not is_ok:
                    util.exit_due_to_bad_settings_file("window x location input error")
                continue

            if line.startswith(util.WINDOW_LOCATION_Y_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.WINDOW_LOCATION_Y_SETTING)
                self.WINDOW_LOCATION_Y = int(num)
                if not is_ok:
                    util.exit_due_to_bad_settings_file("window y location input error")
                continue

            if line.startswith(util.WINDOW_WIDTH_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.WINDOW_WIDTH_SETTING)
                self.WIDTH = int(num)
                if (not is_ok) or self.WIDTH < 1:
                    util.exit_due_to_bad_settings_file("width input error")
                continue

            if line.startswith(util.WINDOW_HEIGHT_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.WINDOW_HEIGHT_SETTING)
                self.HEIGHT = int(num)
                if (not is_ok) or self.HEIGHT < 1:
                    util.exit_due_to_bad_settings_file("height input error")
                continue

            if line.startswith(util.FRAME_DELAY_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.FRAME_DELAY_SETTING)
                self.DELAY_BETWEEN_FRAMES = int(num)
                if (not is_ok) or self.DELAY_BETWEEN_FRAMES < 1:
                    util.exit_due_to_bad_settings_file("delay input error")
                continue

            if line.startswith(util.TEST_MODE_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.TEST_MODE_SETTING)
                self.CAM_NUM = int(num)
                if (not is_ok) or (num != 0 and num != 1):
                    util.exit_due_to_bad_settings_file("test mode input error")
                continue

            if line.startswith(util.FLIP_MODE_SETTING):
                is_ok, num = util.parse_digit_arg(line, util.FLIP_MODE_SETTING)
                if num == 0:
                    self.FLIP_MODE = False
                if (not is_ok) or (num != 0 and num != 1):
                    util.exit_due_to_bad_settings_file("flip mode input error")
                continue

        if self.CAM_NUM == 1:
            self.CAM_NUM = util.get_valid_cam_num()
        else:
            self.CAM_NUM = -1


if __name__ == '__main__':
    """
    create instance of CamSwitch and run it.
    """
    camSwitcher = CamSwitch()

    camSwitcher.run()
