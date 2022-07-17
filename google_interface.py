import datetime
import io
import json
import os
import threading
import time
from enum import Enum

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image, ImageOps

from util import *


class SheetType(Enum):
    """The type of data stored on a sheet."""

    CONFIG_GENERAL = 1
    CONFIG_PEOPLE = 2
    DATA_DEVICES = 3
    DATA_RECORDS = 4
    DATA_STATUS = 5

    def get_friendly_name(self):
        """Returns the expected title of this type of sheet."""
        return {
            __class__.CONFIG_GENERAL: "Config - General",
            __class__.CONFIG_PEOPLE: "Config - People",
            __class__.DATA_DEVICES: "Data - Devices",
            __class__.DATA_RECORDS: "Data - Records",
            __class__.DATA_STATUS: "Data - Status"
        }[self]


class GoogleInterface:
    """Connects to Google Drive and Google Sheets to read and write data."""

    _SCOPES = ["https://www.googleapis.com/auth/drive.readonly",
               "https://spreadsheets.google.com/feeds"]
    _CONFIG_KEYS = ["welcome_message", "background_folder", "ip_range_start", "ip_range_end", "ping_cycle_delay_secs",
                    "ping_timeout_secs", "ping_backoff_length_secs", "auto_grace_period_mins", "auto_timeout_mins",
                    "auto_extension_mins", "manual_timeout_hours", "manual_extension_hours"]
    _RECENT_RECORDS = 500  # Number of records to retrieve
    _CONFIG_CACHE_TIMES = [30, 60]
    _DATA_CACHE_TIMES = [10, 20, 30, 40, 50, 60]
    _STATUS_UPDATE_TIMES = [60]
    _BACKGROUND_HEIGHT = 1200  # Backgrounds are downscaled for fast loading

    _start_time = round(time.time())
    _connection_status = ConnectionStatus.DISCONNECTED
    _creds = None
    _gspread_client = None
    _gspread_spreadsheet = None
    _gspread_sheets = {}
    _gdrive_client = None

    def __init__(self, data_folder, cred_file_path, background_cache_folder, spreadsheet_id, status_callback, config_callback, data_callback, backgrounds_callback):
        """
        Creates a new GoogleInterface.

        Parameters:
            data_folder: The name of the local folder where data is stored.
            cred_file_path: The name of the local JSON file with Google credientials.
            background_cache_folder: The name of the local folder to store backgrounds.
            spreadsheet_id: The ID of the main spreadsheet on Google Drive.
            status_callback: A function that takes a single ConnectionStatus argument.
            config_callback: A function that accepts a single argument for config data.
            data_callback: A function that accepts a single argument for general data.
            backgrounds_callback: A function that is called when the set of backgrounds changes.
        """

        self._DATA_FOLDER = data_folder
        self._CRED_FILE_PATH = cred_file_path
        self._BACKGROUND_CACHE_FOLDER = background_cache_folder
        self._SPREADSHEET_ID = spreadsheet_id
        self._status_callback = status_callback
        self._config_callback = config_callback
        self._data_callback = data_callback
        self._backgrounds_callback = backgrounds_callback

    def _set_connection_status(self, status):
        """Sets the current connection status and updates it externally if necessary."""
        if status != self._connection_status:
            self._connection_status = status
            self._status_callback(self._connection_status)

    def _auth(self):
        """Connect to Google and reauthorize if necessary. Returns a boolean indicating whether the connection was successful."""

        # Check if authentication is required
        if self._connection_status == ConnectionStatus.CONNECTED and self._creds.valid:
            return True
        if self._connection_status == ConnectionStatus.CONNECTED:
            log("Invalid credentials, reconnecting to Google")

        # Authenticate to Google
        try:
            self._creds = Credentials.from_service_account_info(
                json.load(open(get_absolute_path(self._DATA_FOLDER, self._CRED_FILE_PATH))), scopes=self._SCOPES)
            self._gspread_client = gspread.authorize(self._creds)
            self._gdrive_client = build(
                "drive", "v3", credentials=self._creds)
        except:
            log("Failed to connect to Google using cred file \"" +
                self._CRED_FILE_PATH + "\"")
            self._set_connection_status(ConnectionStatus.DISCONNECTED)
            return False

        # Open spreadsheet
        sheets = []
        try:
            self._gspread_spreadsheet = self._gspread_client.open_by_key(
                self._SPREADSHEET_ID)
            sheets = self._gspread_spreadsheet.worksheets()
        except:
            log("Failed to open Google Sheet with ID \"" +
                self._SPREADSHEET_ID + "\"")
            self._set_connection_status(ConnectionStatus.DISCONNECTED)
            return False

        # Find sheets by title
        self._gspread_sheets = {}
        missing_sheets = []
        for type in SheetType:
            found_sheet = False
            for sheet in sheets:
                if sheet.title == type.get_friendly_name():
                    found_sheet = True
                    self._gspread_sheets[type] = sheet
                    break
            if not found_sheet:
                missing_sheets.append(type.get_friendly_name())
        if len(missing_sheets) > 0:
            log("Could not find one or more sheets: " +
                ", ".join(["\"" + x + "\"" for x in missing_sheets]))
            self._set_connection_status(ConnectionStatus.WARNING)
            return False

        log("Successfully connected to Google")
        self._set_connection_status(ConnectionStatus.CONNECTED)
        return True

    def _update_config(self, update_general=True, update_people=True, send_result=True):
        """Retrieves the current general config data and people list, sending it to the callback if valid."""
        if not self._auth():
            return None

        config = {"general": {}, "people": []}
        try:
            # Get general config
            if update_general:
                raw_data = self._gspread_sheets[SheetType.CONFIG_GENERAL].get(
                    "C2:C" + str(len(self._CONFIG_KEYS) + 1))
                for i, row in enumerate(raw_data):
                    key = self._CONFIG_KEYS[i]
                    if len(row) > 0:
                        value = row[0]
                    else:
                        value = None
                    if key == "ping_cycle_delay_secs" or key == "ping_timeout_secs" or key == "ping_backoff_length_secs" or key == "auto_grace_period_mins" or key == "auto_timeout_mins" or key == "auto_extension_mins" or key == "manual_timeout_hours" or key == "manual_extension_hours":
                        value = float(value)
                    config["general"][key] = value

            # Get people
            if update_people:
                raw_data = self._gspread_sheets[SheetType.CONFIG_PEOPLE].get(
                    "A:F")
                for row in raw_data[1:]:
                    if len(row[1]) > 0 and len(row[2]) > 0:
                        config["people"].append({
                            "id": int(row[0]),
                            "first_name": row[1],
                            "last_name": row[2],
                            "is_student": row[3] == "TRUE",
                            "is_active": row[4] == "TRUE",
                            "graduation_year": int(row[5]) if len(row) >= 6 and row[5] != "" else None
                        })
        except:
            log("Failed to read config from Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return None
        else:
            if send_result:
                log("Updated config from Google")
                self._config_callback(config)
            return config

    def _update_data(self, update_devices=True, update_records=True, send_result=True):
        """Retrievess a list of registered devices ("devices"), with keys "person", "mac", and "last_seen", and a list of recent records ("records"), with keys "person", "start_time", "end_time", "start_manual", "end_manual". The result is sent to the callback if valid. This data does not include the status table."""
        if not self._auth():
            return None

        data = {"devices": [], "records": []}
        try:
            # Get devices
            if update_devices:
                raw_data = self._gspread_sheets[SheetType.DATA_DEVICES].get(
                    "A:C")
                for row in raw_data[1:]:
                    if len(row[0]) > 0 and len(row[1]) > 0:
                        data["devices"].append({
                            "person": int(row[0]),
                            "mac": row[1],
                            "last_seen": int(row[2]) if len(row) > 2 else None
                        })

            # Get records
            if update_records:
                raw_data = self._gspread_sheets[SheetType.DATA_RECORDS].get(
                    "A2:E" + str(self._RECENT_RECORDS + 1))
                for row in raw_data:
                    if len(row[0]) > 0 and len(row[1]) > 0:
                        data["records"].append({
                            "person": int(row[0]),
                            "start_time": int(row[1]),
                            "end_time": int(row[2]) if len(row[2]) > 0 else None,
                            "start_manual": row[3] == "TRUE",
                            "end_manual": row[4] == "TRUE"
                        })
        except:
            log("Failed to read data from Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return None
        else:
            if send_result:
                log("Updated data from Google")
                self._data_callback(data)
            return data

    def _update_status(self):
        if not self._auth():
            return False

        try:
            # Get last start time
            sheet = self._gspread_sheets[SheetType.DATA_STATUS]
            last_start_time = int(sheet.get("A2")[0][0])

            # Add new row / update end time
            current_time = round(time.time())
            if last_start_time != self._start_time:
                sheet.insert_row([self._start_time, current_time], 2)
            else:
                sheet.update("B2", [[current_time]])

        except:
            log("Failed to send status data to Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return False
        else:
            log("Sent new status data to Google")
            return True

    def add_sign_in(self, person, is_manual, event_time=None):
        """Creates a new visit (or updates an existing visit), then updates the data cache."""
        if not self._auth():
            return False

        # Get current data
        current_data = self._update_data(False, True, False)
        if current_data == None:
            log("Failed to send sign-in data to Google (pre-update failed)")
            return False

        # Search for existing visit
        existing_row = None
        for index, record in enumerate(current_data["records"]):
            if record["person"] == person and record["end_time"] == None:
                existing_row = index + 2

        event_time = round(time.time()) if event_time == None else event_time
        try:
            sheet = self._gspread_sheets[SheetType.DATA_RECORDS]
            if existing_row == None:
                sheet.insert_row([person, event_time, None, is_manual], 2)
            else:
                sheet.update("B" + str(existing_row) + ":D" + str(existing_row),
                             [[event_time, None, is_manual]])

        except:
            log("Failed to send sign-in data to Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return False
        else:
            log("Sent new sign-in data to Google")
            self._update_data()
            return True

    def add_sign_out(self, person, is_manual, event_time=None):
        """Closes all visits for the specified person, then updates the data cache."""
        if not self._auth():
            return False

        # Get current data
        current_data = self._update_data(False, True, False)
        if current_data == None:
            log("Failed to send sign-out data to Google (pre-update failed)")
            return False

        # Find all visits
        visits = []
        for index, record in enumerate(current_data["records"]):
            if record["person"] == person and record["end_time"] == None:
                visits.append({
                    "row": index + 2,
                    "start_manual": record["start_manual"]
                })

        event_time = round(time.time()) if event_time == None else event_time
        try:
            sheet = self._gspread_sheets[SheetType.DATA_RECORDS]
            for visit in visits:
                sheet.update("C" + str(visit["row"]) + ":E" + str(visit["row"]),
                             [[event_time, visit["start_manual"], is_manual]])

        except:
            log("Failed to send sign-out data to Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return False
        else:
            log("Sent new sign-out data to Google")
            self._update_data()
            return True

    def add_device(self, person, mac):
        """Registers a new device to the specified person, then updates the data cache."""
        if not self._auth():
            return False

        # Get current data
        current_data = self._update_data(True, False, False)
        if current_data == None:
            log("Failed to send device registration data to Google (pre-update failed)")
            return False

        # Search for existing device
        already_registered = False
        for device in current_data["devices"]:
            if device["person"] == person and device["mac"] == mac:
                already_registered = True
        if already_registered:
            log("Skipped adding new device because it was already registered")
            return True

        try:
            sheet = self._gspread_sheets[SheetType.DATA_DEVICES]
            sheet.insert_row([person, mac, None], 2)

        except:
            log("Failed to device registration data to Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return False
        else:
            log("Sent new device registration data to Google")
            self._update_data()
            return True

    def remove_device(self, person, mac):
        """Removes the specified device, then updates the data cache."""
        if not self._auth():
            return False

        # Get current data
        current_data = self._update_data(True, False, False)
        if current_data == None:
            log("Failed to send device removal data to Google (pre-update failed)")
            return False

        # Search for devices
        rows = []
        for index, device in enumerate(current_data["devices"]):
            if device["person"] == person and device["mac"] == mac:
                rows.append(index + 2)

        try:
            sheet = self._gspread_sheets[SheetType.DATA_DEVICES]
            for row in rows:
                sheet.delete_rows(row)

        except:
            log("Failed to send device removal data to Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return False
        else:
            log("Sent new device removal data to Google")
            self._update_data()
            return True

    def update_device_last_seen(self, person, mac):
        """Sets the "last seen" time for the specified device to today, then updates the data cache."""
        if not self._auth():
            return False

        # Get current data
        current_data = self._update_data(True, False, False)
        if current_data == None:
            log("Failed to send device update data to Google (pre-update failed)")
            return False

        # Search for devices
        rows = []
        for index, device in enumerate(current_data["devices"]):
            if device["person"] == person and device["mac"] == mac:
                rows.append(index + 2)

        event_time = round(datetime.datetime.combine(
            datetime.datetime.today(), datetime.time.min).timestamp())
        try:
            sheet = self._gspread_sheets[SheetType.DATA_DEVICES]
            for row in rows:
                sheet.update("C" + str(row), [[event_time]])

        except:
            log("Failed to send device update data to Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return False
        else:
            log("Sent new device update data to Google")
            self._update_data()
            return True

    def _update_backgrounds(self, folder_id):
        """Syncs the local cache of backgrounds to Google Drive."""
        if not self._auth():
            return False

        changed = False
        try:
            # Get list from local cache
            local_images = os.listdir(get_absolute_path(
                self._DATA_FOLDER, self._BACKGROUND_CACHE_FOLDER))
            local_images = [x for x in local_images if x[0] != "."]

            # Get list from Google
            raw_data = self._gdrive_client.files().list(
                q="'" + folder_id + "' in parents and (mimeType = 'image/jpeg' or mimeType = 'image/png')").execute()["files"]
            google_images = []
            for google_image in raw_data:
                google_images.append(google_image["id"] + "." +
                                     google_image["mimeType"].split("/")[1])

            # Delete old images
            for image in local_images:
                if image not in google_images:
                    changed = True
                    os.remove(get_absolute_path(self._DATA_FOLDER,
                                                self._BACKGROUND_CACHE_FOLDER, image))
                    log("Deleted background \"" + image + "\"")

            # Download new images
            for image in google_images:
                if image not in local_images:
                    changed = True

                    # Download data
                    request = self._gdrive_client.files().get_media(
                        fileId=image.split(".")[0])
                    image_data = io.BytesIO()
                    downloader = MediaIoBaseDownload(image_data, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()

                    # Downscale image
                    image_data.seek(0)
                    pillow_image = Image.open(image_data)
                    pillow_image = ImageOps.exif_transpose(pillow_image)
                    aspect_ratio = pillow_image.width / pillow_image.height
                    new_width = round(aspect_ratio * self._BACKGROUND_HEIGHT)
                    pillow_image = pillow_image.resize(
                        (new_width, self._BACKGROUND_HEIGHT))
                    pillow_image.save(get_absolute_path(self._DATA_FOLDER,
                                                        self._BACKGROUND_CACHE_FOLDER, image))
                    log("Downloaded background \"" + image + "\"")

        except:
            log("Failed to sync backgrounds with Google")
            self._set_connection_status(ConnectionStatus.WARNING)
            return False
        else:
            if changed:
                self._backgrounds_callback()
            return True

    def _cache_thread(self):
        """Thread to regularly update config and data."""
        while True:
            current_secs = datetime.datetime.now().second
            next_update = next(x for x in sorted(
                set(self._CONFIG_CACHE_TIMES + self._DATA_CACHE_TIMES + self._STATUS_UPDATE_TIMES)) if x > current_secs)
            time.sleep(next_update - current_secs)

            if next_update in self._CONFIG_CACHE_TIMES:
                config = self._update_config()
                if config != None and "background_folder" in config["general"] and config["general"]["background_folder"] != None:
                    self._update_backgrounds(
                        config["general"]["background_folder"])

            if next_update in self._DATA_CACHE_TIMES:
                self._update_data()

            if next_update in self._STATUS_UPDATE_TIMES:
                self._update_status()

    def start(self):
        """Updates the config and data immediately, then starts the caching thread."""
        config = self._update_config()
        if config != None and "background_folder" in config["general"] and config["general"]["background_folder"] != None:
            self._update_backgrounds(config["general"]["background_folder"])
        self._update_data()
        self._update_status()

        threading.Thread(target=self._cache_thread, daemon=True).start()
