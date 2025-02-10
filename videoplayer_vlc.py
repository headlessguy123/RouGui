# -*- coding: utf-8 -*-

import os
import vlc
import time
import logging
from PyQt5.QtGui import QIcon, QPalette, QCursor
from PyQt5.QtCore import Qt, QRect, QSize, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QFrame, QPushButton, QLabel, QSlider, QVBoxLayout, QHBoxLayout
from config import basePath

os.environ['VLC_PLUGIN_PATH'] = '/Applications/VLC.app/Contents/MacOS/plugins'

class VlcPlayerThread(QThread):
    positionChanged = pyqtSignal(int, int)
    stateChanged = pyqtSignal()

    def __init__(self, player):
        super().__init__()
        self.player = player
        self.running = True

    def run(self):
        while self.running:
            if self.player.is_playing():
                media_pos = self.player.get_time()
                duration = self.player.get_length()
                self.positionChanged.emit(media_pos, duration)
            self.stateChanged.emit()
            self.msleep(100)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

    def start(self):
        self.running = True
        super().start()

class VideoPlayer(QWidget):

    def __init__(self, video, parent=None, **kwargs):
        super(VideoPlayer, self).__init__(parent)

        self.video = video
        self.current_position = 0
        self.setFocusPolicy(Qt.StrongFocus)  # 确保窗口可以接收键盘事件
        self.is_fullscreen = False

        self.initUI()
        self.setupConnections()

        self.instance = vlc.Instance()
        self.mediaplayer = self.instance.media_player_new()

        self.vlc_thread = VlcPlayerThread(self.mediaplayer)
        self.vlc_thread.positionChanged.connect(self.updateUI)
        self.vlc_thread.stateChanged.connect(self.checkState)
        self.vlc_thread.start()

    def initUI(self):
        self.setWindowTitle(f'{self.video["nameZh"]}')
        self.setWindowIcon(QIcon(os.path.join(basePath, 'resources', 'icon.png')))
        self.setGeometry(300, 300, 810, 600)
        self.setMinimumSize(400, 300)

        palette = QPalette()
        palette.setColor(QPalette.Background, Qt.gray)
        self.setPalette(palette)

        self.video_widget = QFrame(self)
        self.video_widget.setPalette(QPalette(Qt.black))
        self.video_widget.setAutoFillBackground(True)
        self.video_widget.setMouseTracking(True)
        self.video_widget.setFocusPolicy(Qt.StrongFocus)

        # 安装事件过滤器
        self.video_widget.installEventFilter(self)

        self.play_btn = self.createButton('play.png', '播放')
        self.pause_btn = self.createButton('pause.png', '暂停')
        self.pause_btn.hide()
        self.play_progress_label = QLabel('00:00:00 / 00:00:00')
        self.play_progress_slider = QSlider(Qt.Horizontal, self)
        self.play_progress_slider.setMinimum(0)
        self.play_progress_slider.setSingleStep(1)
        self.play_progress_slider.setGeometry(QRect(0, 0, 200, 10))

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.mute_btn = self.createButton(os.path.join(basePath, 'resources','sound.png'), '禁音')
        self.volume_label = QLabel('50')

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget, stretch=1)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(2)
        h_layout.setContentsMargins(10, 0, 10, 0)
        h_layout.addWidget(self.play_btn, 0, Qt.AlignCenter | Qt.AlignVCenter)
        h_layout.addWidget(self.pause_btn, 0, Qt.AlignCenter | Qt.AlignVCenter)
        h_layout.addWidget(self.play_progress_label, 0, Qt.AlignCenter | Qt.AlignVCenter)
        h_layout.addWidget(self.play_progress_slider, 15, Qt.AlignVCenter | Qt.AlignVCenter)
        h_layout.addWidget(self.mute_btn, 0, Qt.AlignCenter | Qt.AlignVCenter)
        h_layout.addWidget(self.volume_slider, 0, Qt.AlignCenter | Qt.AlignVCenter)
        h_layout.addWidget(self.volume_label, 0, Qt.AlignCenter | Qt.AlignVCenter)
        layout.addLayout(h_layout)

        self.setLayout(layout)

    def createButton(self, icon, tooltip):
        button = QPushButton(self)
        button.setIcon(QIcon(os.path.join(basePath, 'resources',f'{icon}')))
        button.setIconSize(QSize(25, 25))
        button.setStyleSheet('''QPushButton{border:none;}QPushButton:hover{border:none;border-radius:35px;}''')
        button.setCursor(QCursor(Qt.PointingHandCursor))
        button.setToolTip(tooltip)
        button.setFlat(True)
        return button

    def setupConnections(self):
        self.play_btn.clicked.connect(self.playvideo)
        self.pause_btn.clicked.connect(self.pausevideo)
        self.mute_btn.clicked.connect(self.mute)
        self.volume_slider.valueChanged.connect(self.setVolume)
        self.play_progress_slider.sliderPressed.connect(self.playProgressSliderPressed)
        self.play_progress_slider.sliderReleased.connect(self.playProgressSliderReleased)

    def playProgressSliderPressed(self):
        self.vlc_thread.stop()

    def playProgressSliderReleased(self):
        position = self.play_progress_slider.value()
        self.mediaplayer.set_time(position)
        self.vlc_thread.start()
        self.setFocus()  # 重新设置焦点回主窗口

    def playvideo(self):
        if self.mediaplayer.get_media() is None:
            return
        self.current_position = self.mediaplayer.get_time()
        if not self.mediaplayer.is_playing():
            self.openvideo(position=self.current_position)
        self.play_btn.hide()
        self.pause_btn.show()
        self.mediaplayer.play()
        self.setFocus()  # 重新设置焦点回主窗口

    def pausevideo(self):
        self.play_btn.show()
        self.pause_btn.hide()
        self.mediaplayer.pause()
        self.setFocus()  # 重新设置焦点回主窗口

    def mute(self):
        muted = self.mediaplayer.audio_get_mute()
        self.mediaplayer.audio_set_mute(not muted)
        if muted:
            self.mute_btn.setIcon(QIcon(os.path.join(basePath, 'resources','sound.png')))
        else:
            self.mute_btn.setIcon(QIcon(os.path.join(basePath, 'resources','mute.png')))

    def setVolume(self):
        value = self.volume_slider.value()
        self.mediaplayer.audio_set_volume(value)
        self.volume_label.setText(str(value))

    def formatTime(self, ms):
        seconds = int(ms / 1000)
        minutes = int(seconds / 60)
        hours = int(minutes / 60)
        minutes = minutes % 60
        seconds = seconds % 60
        return f'{str(hours).zfill(2)}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            current_volume = self.volume_slider.value()
            if current_volume + 5 <= 100:
                self.volume_slider.setValue(current_volume + 5)
            else:
                self.volume_slider.setValue(100)
        elif event.key() == Qt.Key_Down:
            current_volume = self.volume_slider.value()
            if current_volume - 5 >= 0:
                self.volume_slider.setValue(current_volume - 5)
            else:
                self.volume_slider.setValue(0)
        elif event.key() == Qt.Key_Right:
            current_time = self.mediaplayer.get_time()
            if current_time + 5000 <= self.mediaplayer.get_length():
                self.mediaplayer.set_time(current_time + 5000)
            else:
                self.mediaplayer.set_time(self.mediaplayer.get_length())
        elif event.key() == Qt.Key_Left:
            current_time = self.mediaplayer.get_time()
            if current_time - 5000 >= 0:
                self.mediaplayer.set_time(current_time - 5000)
            else:
                self.mediaplayer.set_time(0)

    def openvideo(self, position=0):
        if not self.video or 'nameZh' not in self.video or 'url' not in self.video:
            return
        media = self.instance.media_new(self.video['url'])
        self.mediaplayer.set_media(media)
        nsobject_id = int(self.video_widget.winId())
        self.mediaplayer.set_nsobject(nsobject_id)
        media.parse()
        self.play_btn.hide()
        self.pause_btn.show()
        self.mediaplayer.play()
        logging.info(f'播放-{self.video["nameZh"]}')
        while media.get_state() == vlc.State.Opening:
            time.sleep(0.1)

        if position > 0:
            self.mediaplayer.set_time(position)

        # 检测状态变化
        self.mediaplayer.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, self.on_video_end_to_restart)
        self.mediaplayer.event_manager().event_attach(vlc.EventType.MediaPlayerEncounteredError, self.on_video_end_to_restart)

    def closeEvent(self, event):
        self.vlc_thread.stop()
        self.mediaplayer.stop()

    def resizeEvent(self, event):
        if self.mediaplayer:
            nsobject_id = int(self.video_widget.winId())
            self.mediaplayer.set_nsobject(nsobject_id)
        super(VideoPlayer, self).resizeEvent(event)

    def checkState(self):
        if not self.mediaplayer.is_playing():
            self.play_btn.show()
            self.pause_btn.hide()
        else:
            self.play_btn.hide()
            self.pause_btn.show()

    def updateUI(self, media_pos, duration):
        if duration > 0:
            self.play_progress_slider.setMaximum(duration)
            self.play_progress_slider.setValue(media_pos)
            self.play_progress_label.setText(f'{self.formatTime(media_pos)} / {self.formatTime(duration)}')

    def on_video_end_to_restart(self, event):
        self.play_btn.show()
        self.pause_btn.hide()