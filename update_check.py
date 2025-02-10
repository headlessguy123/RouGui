import requests
import logging
from PyQt5.QtCore import pyqtSignal, QThread
from config import version, server_version_url

class UpdateChecker(QThread):
    update_check_finished = pyqtSignal(bool, str, bool)

    def __init__(self):
        super().__init__()
        self.update_active = False
        self.server_version_url = server_version_url
        self.current_version = version

    def get_server_version(self, version_url):
        try:
            response = requests.get(version_url)
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.HTTPError as http_err:
            logging.debug(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            logging.debug(f"Request exception occurred: {req_err}")
        except Exception as e:
            logging.debug(f"An unexpected error occurred: {e}")
        
        return None

    def run(self):
        server_version = self.get_server_version(self.server_version_url)
        if server_version and server_version != self.current_version:
            self.update_check_finished.emit(True, server_version, self.update_active)
        else:
            self.update_check_finished.emit(False, server_version, self.update_active)
