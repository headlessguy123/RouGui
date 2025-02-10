# -*- coding: utf-8 -*-

import os
import re
from PyQt5.QtWidgets import QWidget, QProgressBar, QPushButton, QMessageBox, QStatusBar, QLineEdit, QGridLayout, QFileDialog
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon
import time
import logging
from config import cwd, basePath
import platform
from yt_dlp import YoutubeDL

class Downloader(QWidget):
    def __init__(self, video, *args, **kwargs):
        super(Downloader, self).__init__(*args, **kwargs)
        self.resize(500, 100)
        self.setMinimumSize(500, 100)
        self.setMaximumSize(500, 100)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)

        self.video = video
        self.setWindowTitle(f'下载-{self.video["nameZh"]}')
        self.setWindowIcon(QIcon(os.path.join(basePath, 'resources', 'logo.png')))

        self.down_path = QPushButton(self)
        self.down_path.setText("选择地址")
        layout.addWidget(self.down_path, 0, 0, 1, 1)
        self.path_out = QLineEdit(self)
        self.path_out.setPlaceholderText(os.path.join(cwd, 'Movies'))       # 默认影片文件夹
        layout.addWidget(self.path_out, 0, 1, 1, 4)
        # 增加进度条
        self.progressBar = QProgressBar(self)
        self.progressBar.setValue(0)
        layout.addWidget(self.progressBar, 1, 0, 1, 4)

        # 增加下载按钮
        self.downloadButton = QPushButton(self)
        self.downloadButton.setText("下载")
        layout.addWidget(self.downloadButton, 1, 4, 1, 1)

        # 增加状态栏
        self.statusBar = QStatusBar(self)
        layout.addWidget(self.statusBar, 2, 0, 1, 5)
        self.statusBar.setStyleSheet("background-color: transparent;")

        # 绑定按钮事件
        self.downloadButton.clicked.connect(self.start_download)
        self.down_path.clicked.connect(self.on_down_path_clicked)

        self.video_downloader = None

    def on_down_path_clicked(self):
        path = QFileDialog.getExistingDirectory(self, '选择储存地址', os.path.join(cwd, 'Movies'))      # 默认影片文件夹
        self.path_out.setText(path)
        return path

    def start_download(self):
        self.statusBar.showMessage('下载准备中……')

        start_time = time.time()
        m3u8url = self.video['url']
        title = self.video['name']
        save_path = self.path_out.text() or os.path.join(cwd, 'Movies')         # 默认影片文件夹

        self.video_downloader = VideoDownloader()
        self.video_downloader.outputPath = save_path
        self.video_downloader.m3u8Url = m3u8url
        self.video_downloader.title = title
        self.video_downloader.start_time = start_time
        self.video_downloader.progressUpdated.connect(self.set_progressbar_value)
        self.video_downloader.start()

    def set_progressbar_value(self, statusmessage, value):
        self.progressBar.setValue(value)
        self.statusBar.showMessage(statusmessage)
        if value == 101:
            self.progressBar.setValue(100)
            QMessageBox.information(self, "提示", statusmessage)
            return

class VideoDownloader(QThread):
    progressUpdated = pyqtSignal(str, int)  # 进度和状态栏提示信号

    def __init__(self, *args, **kwargs):
        super(VideoDownloader, self).__init__(*args, **kwargs)

        self.outputPath = None
        self.m3u8Url = None
        self.title = None
        self.start_time = None

    def format_title(self, title):
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for ch in invalid_chars:
            title = title.replace(ch, ' ')
        return title

    def remove_ansi_escape_sequences(self, text):
        ansi_escape = re.compile(r'\x1b\[([0-9]{1,2}(;[0-9]{1,2})?)?[m|K]')
        return ansi_escape.sub('', text)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent_str = self.remove_ansi_escape_sequences(d['_percent_str'])
            try:
                percent = float(percent_str.strip('%'))
                self.progressUpdated.emit(f"正在下载: {percent_str}", int(percent))
            except ValueError as e:
                logging.debug(f"进度解析失败: {e}")
        elif d['status'] == 'finished':
            end_time = time.time()
            duration = end_time - self.start_time
            gm_time = time.strftime('%H:%M:%S', time.gmtime(duration))
            self.progressUpdated.emit(f'视频下载完成，用时：{gm_time}', 101)

    def download_task(self, outputPath, m3u8Url, title, start_time):
        self.start_time = start_time

        if platform.system() == "Windows":
            ffmpeg_path = os.path.join('resources', 'ffmpeg.exe')
        elif platform.system() == "Darwin":  # macOS
            ffmpeg_path = os.path.join('resources', 'ffmpeg')
        else:
            raise RuntimeError("不支持的平台")

        logger = logging.getLogger()
        ydl_opts = {
            'format': 'best',  # 视频质量
            'outtmpl': os.path.join(outputPath, f"{self.format_title(title)}.%(ext)s"),
            'progress_hooks': [self.progress_hook],
            'ffmpeg_location': ffmpeg_path,  # 指定 ffmpeg 的路径
            'logger': logger,  # 使用 logging 模块作为 yt-dlp 的日志记录器
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([m3u8Url])
            logger.info(f'{title}\t下载成功！')
        except Exception as e:
            logger.debug(f"下载失败: {e}")
            self.progressUpdated.emit(f"下载失败: {e}", 0)

    def run(self):
        if self.outputPath and self.m3u8Url and self.title and self.start_time:
            self.download_task(self.outputPath, self.m3u8Url, self.title, self.start_time)
        else:
            self.progressUpdated.emit(f'任务失败，缺少必要的参数！', 0)


