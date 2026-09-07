"""Application-specific paths used by the desktop and scheduled jobs."""

import os


# Keep the HNIT build separate from other ClassPush school builds installed on
# the same Windows account. Do not reuse the generic ``.ClassPush`` folder:
# it can contain another school's WxPusher AppToken/UID and cached timetable.
APP_DATA_DIR_NAME = ".ClassPush_HNIT"


def get_app_data_dir():
    path = os.path.join(os.path.expanduser("~"), APP_DATA_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path
