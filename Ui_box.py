# -*- coding: utf-8 -*-

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QToolButton, QLabel, QGridLayout, QScrollArea, QToolBar, QDialog, QFileDialog, QLineEdit, QPushButton, QMainWindow, QSizePolicy, QStatusBar, QAction, QWidgetAction, QDesktopWidget
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter, QFontMetrics, QCursor, QIcon
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSignal, QEvent
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from videoplayer_vlc import VideoPlayer
from locallock import *
from config import *
from Ui_downloader_bar_dlp import Downloader
from update_check import UpdateChecker

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class VideoWidget(QWidget):
    videoClicked = pyqtSignal(dict)
    videoDownload = pyqtSignal(dict)
    network_manager = None

    def __init__(self, video):
        super().__init__()
        self.video = video
        self.setFixedSize(300, 240)
        layout = QVBoxLayout()

        self.retry_count = 0

        self.image_label = ClickableLabel(self)
        pixmap = QPixmap(260, 200)
        self.draw_loading_text(pixmap)
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.load_image_from_url(video['coverImageUrl'])
        self.image_label.clicked.connect(self.emit_video_clicked)

        # 视频名称
        name_label = ClickableLabel(self)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFixedWidth(280)
        name_font = QFont()
        name_font.setPointSize(12)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        name_label.setWordWrap(True)

        # 设置最多显示两行文本
        self.set_two_line_text(name_label, video['nameZh'])
        name_label.clicked.connect(self.emit_video_clicked)

        # 创建时间
        created_at_label = QLabel(video['createdAt'][:10])
        created_at_label.setAlignment(Qt.AlignCenter)

        # 播放次数
        view_count_label = QLabel(f"热度：{video['viewCount']}")
        view_count_label.setAlignment(Qt.AlignCenter)

        # 时长
        duration_label = QLabel(self.convert_seconds(video['duration']))
        duration_label.setAlignment(Qt.AlignCenter)

        # 创建一个水平布局，将三个标签放在一行
        info_layout = QHBoxLayout()
        info_layout.addWidget(view_count_label)
        info_layout.addWidget(duration_label)
        info_layout.addWidget(created_at_label)

        # 设置创建时间、播放次数、时长的字体和颜色
        info_font = QFont()
        info_font.setPointSize(10)
        created_at_label.setFont(info_font)
        view_count_label.setFont(info_font)
        duration_label.setFont(info_font)

        # 设置三个标签的颜色
        info_color = QColor("#555555")  # 灰色
        created_at_label.setStyleSheet(f"color: {info_color.name()};")
        view_count_label.setStyleSheet(f"color: {info_color.name()};")
        duration_label.setStyleSheet(f"color: {info_color.name()};")

        # 创建一个容器小部件并设置其样式，以包含info_layout
        info_container = QWidget()
        info_container.setLayout(info_layout)

        # 行间距和边距调整
        layout.setSpacing(8)
        layout.setContentsMargins(0, 5, 0, 5)

        layout.addWidget(self.image_label)
        layout.addWidget(name_label)
        layout.addWidget(info_container)

        self.setLayout(layout)

        # 创建选项悬浮小部件
        self.option_widget = QWidget(self)
        self.option_widget.setFixedSize(200, 60)
        option_layout = QHBoxLayout()
        option_layout.setContentsMargins(10, 0, 10, 0)
        self.option_widget.setLayout(option_layout)
        self.option_play_button = QPushButton("播放", self.option_widget)
        self.option_download_button = QPushButton("下载", self.option_widget)
        button_style = """
            QPushButton {
                background-color: rgba(255, 99, 71, 180);  /* 番茄红色，带透明度 */
                border: 1px solid #FF6347;  /* 边框颜色为番茄红 */
                border-radius: 5px;
                color: #FFFFFF;  /* 白色字体 */
                font-size: 14px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 69, 0, 200);  /* 深橙色，略深的颜色 */
                font-weight: bold;
            }
        """
        self.option_play_button.setStyleSheet(button_style)
        self.option_download_button.setStyleSheet(button_style)
        option_layout.addWidget(self.option_play_button)
        option_layout.addStretch()
        option_layout.addWidget(self.option_download_button)
        self.option_widget.hide()

        # 选项按钮的点击事件
        self.option_play_button.clicked.connect(self.emit_video_clicked)
        self.option_download_button.clicked.connect(self.emit_video_download)

        # 安装事件过滤器
        self.installEventFilter(self)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Enter and source == self:
            # 鼠标进入 VideoWidget
            self.option_widget.move((self.width() - self.option_widget.width()) // 2, (self.height() - self.option_widget.height()) // 2)
            self.option_widget.show()
        elif event.type() == QEvent.Leave and source == self:
            # 鼠标离开 VideoWidget
            self.option_widget.hide()
        return super().eventFilter(source, event)

    def set_two_line_text(self, label, text):
        font_metrics = QFontMetrics(label.font())
        available_width = label.width()
        line_height = font_metrics.lineSpacing()
        max_height = line_height * 2

        # 分割文本以适应两行
        elided_text = font_metrics.elidedText(text, Qt.ElideRight, available_width)
        words = text.split()

        final_text = ""
        current_text = ""
        for word in words:
            test_text = current_text + " " + word if current_text else word
            if font_metrics.boundingRect(0, 0, available_width, max_height, Qt.TextWordWrap, test_text).height() <= max_height:
                current_text = test_text
            else:
                if len(final_text) == 0:
                    final_text = current_text
                    current_text = word
                else:
                    final_text += "\n" + current_text
                    current_text = word
                if font_metrics.boundingRect(0, 0, available_width, max_height, Qt.TextWordWrap, final_text + "\n" + current_text).height() > max_height:
                    final_text += "\n" + font_metrics.elidedText(current_text, Qt.ElideRight, available_width)
                    break

        label.setText(final_text if final_text else current_text)

    def draw_loading_text(self, pixmap):
        painter = QPainter(pixmap)
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 12))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "加载中……")
        painter.end()

    def load_image_from_url(self, url):
        if VideoWidget.network_manager is None:
            VideoWidget.network_manager = QNetworkAccessManager()
        self.reply = VideoWidget.network_manager.get(QNetworkRequest(QUrl(url)))
        self.reply.finished.connect(self.on_image_downloaded)
    
    def on_image_downloaded(self):
        if self.reply.error() == QNetworkReply.NoError:
            image_data = self.reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            pixmap = pixmap.scaled(250, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)
            self.retry_count = 0
        else:
            self.handle_error()
        self.reply.deleteLater()

    def handle_error(self):
        error_code = self.reply.error()
        error_str = self.reply.errorString()
        logging.debug(f"Error occurred: {error_code}, {error_str}")  # Log the error

        if self.retry_count < max_retries:
            self.retry_count += 1
            logging.debug(f"Retrying... ({self.retry_count}/{max_retries})")
            QTimer.singleShot(2000, lambda: self.load_image_from_url(self.reply.url().toString()))  # Retry after 2 seconds
        else:
            logging.debug("Maximum retry limit reached. Giving up.")

    def convert_seconds(self, seconds):
        if seconds and seconds >= 0:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds_remaining = seconds % 60
            if hours > 0:
                return f"{hours}小时{minutes}分{seconds_remaining:.2f}秒"
            else:
                return f"{minutes}分{seconds_remaining:.2f}秒"
        return f"未知时间"

    def emit_video_clicked(self):
        self.videoClicked.emit(self.video)

    def emit_video_download(self):
        self.videoDownload.emit(self.video)

class MainWindow(QMainWindow):

    def __init__(self, videos):
        super().__init__()
        self.setWindowIcon(QIcon(os.path.join(basePath, 'resources/logo.webp')))

        self.video_player = None
        self.video_downloader = None

        self.config = user_config()
        self.authorized = self.check_user_config()
        self.initUI()

        self.all_videos = videos
        self.rearrange_videos()

        self.check_update = None
        self.check_update_thread()

    def initUI(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # 菜单栏
        menubar = self.menuBar()

        # 设置菜单
        settings_menu = menubar.addMenu('帮助')

        # 授权信息
        auth_code_action = QAction('授权信息', self)
        auth_code_action.triggered.connect(self.show_auth_code)
        settings_menu.addAction(auth_code_action)

        # 分割线
        settings_menu.addSeparator()

        # 检查更新
        update_button = QAction('检查更新', self)
        update_button.triggered.connect(self.check_update_thread_active)
        settings_menu.addAction(update_button)

        # 分割线
        settings_menu.addSeparator()

        # 关于
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about_dialog)
        settings_menu.addAction(about_action)

        # 导航栏
        self.toolbar = QToolBar("导航")
        self.toolbar.setAllowedAreas(Qt.TopToolBarArea | Qt.BottomToolBarArea)  # 限制导航栏只能在顶部或底部
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.add_nav_button(toolbar_list)

        # 添加弹性空间
        spacer1 = QWidget()
        spacer1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer1)

        # 添加搜索框
        search_widget = QWidget()
        search_layout = QHBoxLayout()
        search_widget.setLayout(search_layout)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('搜索...')
        self.search_box.setFixedWidth(200)
        self.search_box.returnPressed.connect(self.on_search)
        self.search_button = QPushButton('搜索')
        self.search_button.clicked.connect(self.on_search)
        search_layout.addStretch()
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.search_button)

        # 将搜索框添加到工具栏
        search_action = QWidgetAction(self)
        search_action.setDefaultWidget(search_widget)
        self.toolbar.addAction(search_action)

        # 视频显示区域
        self.container = QWidget()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.container)
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.scroll)
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        self.grid_layout = QGridLayout()
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.container.setLayout(self.grid_layout)

        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(1280, 800)

        self.center()

    def center(self):
        screen = QDesktopWidget().availableGeometry().center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(screen)
        self.move(frame_geometry.topLeft())

    def check_user_config(self):
        user_type = self.config.get('user_type', 'free')
        logging.info(f"user type is {user_type}")
        if user_type == 'free':
            free_num = self.config.get('free_num', 0)
            return free_num > 0
        return False

    def show_message_box(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setWindowIcon(QIcon(os.path.join(basePath, 'resources/logo.webp')))
        msg_box.exec_()

    def rearrange_videos(self):
        self.clear_layout(self.grid_layout)
        for index, video in enumerate(self.all_videos):
            video_widget = VideoWidget(video)
            video_widget.videoClicked.connect(self.play_video)
            video_widget.videoDownload.connect(self.download_video)
            row = index // 4
            col = index % 4
            self.grid_layout.addWidget(video_widget, row, col)

    def on_scroll(self):
        if self.scroll.verticalScrollBar().value() == self.scroll.verticalScrollBar().maximum() and not self.loading:
            self.loading = True
            self.start_thread(generator=self.thread.generator)

    def create_menu_label(self, text):
        label = QLabel()
        label.setText(text)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        return label

    def create_menu_dialog(self, title, message):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 去掉问号按钮

        layout = QVBoxLayout()

        label = self.create_menu_label(message)
        layout.addWidget(label)

        button = QPushButton("关闭")
        button.clicked.connect(dialog.accept)
        button.setFixedWidth(button.sizeHint().width())  # 设置按钮宽度为推荐宽度
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(button)
        button_layout.addStretch(1)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        return dialog

    def show_auth_code(self):
        match self.config['user_type']:
            case 'free':
                auth_message = f"ID: {self.config['id']}\n\n类型: 免费版\n"

        dialog = self.create_menu_dialog("授权码信息", auth_message)
        dialog.exec_()

    def show_about_dialog(self):
        about_message = (
            f'<p>版本: {version}</p>'
            '<p>Twitter: <a href="https://x.com/rouvideogui">@rouvideogui</a></p>'
            '<p>Telegram: <a href="https://t.me/+tUcwTL751KdhZTRh">@RouVideoGui</a></p>'
        )
        dialog = self.create_menu_dialog("关于", about_message)
        dialog.exec_()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                layout.removeItem(item)

    def add_nav_button(self, toolbar_list, font_size=12):
        self.buttons = []
        for name in toolbar_list:
            button = QToolButton(self)
            button.setText(name)
            font = QFont()
            font.setPointSize(font_size)
            button.setFont(font)
            button.clicked.connect(lambda checked, btn=button: self.on_nav_button_clicked(btn))
            self.toolbar.addWidget(button)
            self.buttons.append(button)

    def on_nav_button_clicked(self, clicked_button):
        for button in self.buttons:
            if button == clicked_button:
                button.setStyleSheet("""
                    background-color: #FFDAB9;  /* 淡橙色背景 */
                    border: 1px solid black;
                    border-radius: 5px;  /* 圆角边框 */
                    color: black;
                    font-size: 12px;
                """)
            else:
                button.setStyleSheet("")
        self.show_limited_window()

    def on_search(self):
        self.show_limited_window()

    def play_video(self, video):
        if not self.authorized:
            self.show_limited_window()
            logging.info("播放受限")
            return

        if self.video_player is not None:
            self.video_player.close()
            self.video_player.deleteLater()
            self.video_player = None
        self.rewrite_free_num()
        self.video_player = VideoPlayer(video)
        self.video_player.openvideo()
        self.video_player.show()

    def download_video(self, video):
        if not self.authorized:
            self.show_limited_window()
            logging.info("下载受限")
            return

        if self.video_downloader is not None:
            self.video_downloader.close()
            self.video_downloader.deleteLater()
            self.video_downloader = None
        self.rewrite_free_num()
        self.video_downloader = Downloader(video)
        self.video_downloader.show()

    def rewrite_free_num(self):
        if self.config['user_type'] == 'free':
            self.config['free_num'] -= 1
            if self.config['free_num'] < 0:
                self.authorized = False

    def show_limited_window(self):
        limited_window = QMessageBox(self)
        limited_window.setIcon(QMessageBox.Information)
        limited_window.setWindowTitle("功能受限")
        limited_window.setText("开源测试版功能受限，请下载完整版！\n")
        limited_window.exec_()

    def download_update(self):
        import webbrowser
        try:
            webbrowser.open(server_new_version_url)
            QMessageBox.information(None, '更新', 
                                    "请下载并使用新版本替代当前版本，已有权限不受影响。")
        except Exception as e:
            QMessageBox.critical(None, '错误', f"An error occurred while trying to open the browser: {e}")

    def check_update_thread_helper(self, update_active=False):
        if self.check_update is not None and self.check_update.isRunning():
            self.check_update.quit()
            self.check_update.wait()

        self.check_update = UpdateChecker()
        self.check_update.update_active = update_active
        self.check_update.update_check_finished.connect(self.show_update_result)
        self.check_update.start()

    def check_update_thread(self):
        self.check_update_thread_helper(update_active=False)

    def check_update_thread_active(self):
        self.check_update_thread_helper(update_active=True)

    def show_update_result(self, update_available, server_version, update_active):
        if update_available:
            response = QMessageBox.question(None, '发现新版本', 
                                            f"发现一个新版本 ({server_version}) 可以更新，想要现在更新吗？",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response == QMessageBox.Yes:
                self.download_update()
                logging.debug("download updated.")
        else:
            if update_active:
                QMessageBox.information(None, '没有可用的更新', 
                                        f"当前版本{server_version}已是最新版本，没有可用的更新。")
                logging.debug("You are using the latest version by active.")

if __name__ == '__main__':
    setup_logging()
    app = QApplication(sys.argv)
    from spider import load_video
    videos = load_video()
    window = MainWindow(videos=videos)
    window.show()
    sys.exit(app.exec_())