# -*- coding: utf-8 -*-

import os
import sys
import logging

cwd = os.path.expanduser('~')

if hasattr(sys, '_MEIPASS'):
    basePath = sys._MEIPASS
else:
    basePath = os.getcwd()

toolbar_list = ['OnlyFans', '國產AV', '麻豆傳媒', '糖心Vlog', '天美傳媒', '西瓜影視', '精東影業', '大象傳媒', '兔子先生', '探花', '自拍流出', '日本']

version = '0.1.0'
max_retries = 3
server_version_url = 'https://drive.google.com/uc?export=download&id=1HxPyGM_j8Yg4WUai2fv3CbS7fHefg5MS'
server_new_version_url = 'https://drive.proton.me/urls/KDSJ4QAAZC#WjaDb7YcRoOY'

log_file_path = os.path.join(basePath, "logfile.log")
log_level = "DEBUG"
log_format = "%(asctime)s - %(levelname)s - %(message)s"

class ProgressFilter(logging.Filter):
    def filter(self, record):
        return "frag" not in record.getMessage()

def setup_logging():
    level = getattr(logging, log_level.upper(), logging.DEBUG)
    logging.basicConfig(
        filename=log_file_path,
        level=level,
        format=log_format
    )

    # 创建一个过滤器并添加到全局日志记录器中，过滤yt-dlp的下载速率
    progress_filter = ProgressFilter()
    logger = logging.getLogger()
    logger.addFilter(progress_filter)

    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.WARNING)