#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MainWindow - 主窗口类
PyQt5主窗口，协调所有GUI组件和业务逻辑
"""

import os
from typing import List
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QMessageBox, QDialog, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QMutex
from PyQt5.QtGui import QIcon

from ..config.config_manager import ConfigManager
from ..database.database import Database
from ..monitoring.file_monitor import FileMonitor
from ..file_processing.file_processor import FileProcessor
from ..file_management.file_checker import FileChecker
from ..file_management.file_deleter import FileDeleter
from ..extraction.extractor import Extractor
from .file_list_widget import FileListWidget
from .filter_widget import FilterWidget
from .config_dialog import ConfigDialog
from .log_widget import LogWidget


class FileProcessingWorker(QThread):
    """文件处理工作线程"""
    
    # 定义信号
    status_update = pyqtSignal(str)  # 状态更新信号
    processing_finished = pyqtSignal()  # 处理完成信号
    error_occurred = pyqtSignal(str)  # 错误信号
    
    def __init__(self, file_processor, file_path, is_in_unpack_folder=False):
        super().__init__()
        self.file_processor = file_processor
        self.file_path = file_path
        self.is_in_unpack_folder = is_in_unpack_folder
        self._mutex = QMutex()
    
    def run(self):
        """在后台线程中运行文件处理"""
        try:
            self._mutex.lock()
            self.status_update.emit(f"开始处理文件: {os.path.basename(self.file_path)}")
            
            # 执行文件处理
            self.file_processor.process_file(self.file_path, self.is_in_unpack_folder)
            
            self.status_update.emit(f"文件处理完成: {os.path.basename(self.file_path)}")
            self.processing_finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"处理文件时出错: {str(e)}")
        finally:
            self._mutex.unlock()


class MainWindow(QMainWindow):
    """主窗口类
    
    协调所有GUI组件和业务逻辑
    """
    
    # 定义信号用于线程安全的GUI更新
    new_file_signal = pyqtSignal(str)
    unpack_file_signal = pyqtSignal(str)  # 解压文件夹的新文件信号
    status_message_signal = pyqtSignal(str)  # 用于显示状态消息
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 连接信号到槽函数
        self.new_file_signal.connect(self._process_new_file_in_main_thread)
        self.unpack_file_signal.connect(self._process_unpack_file_in_main_thread)
        self.status_message_signal.connect(self._show_status_message)
        
        # 初始化业务逻辑组件
        self._init_business_components()
        
        # GUI组件
        self.file_list_widget = None
        self.filter_widget = None
        self.log_widget = None  # 日志组件
        self.start_button = None
        self.stop_button = None
        self.config_button = None
        self.status_label = None
        self.progress_bar = None  # 进度条
        self.is_log_view = False  # 是否显示日志视图
        
        # 监控状态
        self.is_monitoring = False
        
        # 异步处理相关
        self.processing_workers = []  # 存储工作线程
        self.processing_queue = []    # 处理队列
        self.max_concurrent_workers = 3  # 最大并发工作线程数
        
        # 自动刷新定时器
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_records)
        self.refresh_timer.setInterval(5000)  # 每5秒刷新一次
        
        # 初始化UI
        self.init_ui()
        
        # 加载初始记录
        self.load_records()
        
        # 启动自动刷新
        self.refresh_timer.start()
    
    def _init_business_components(self) -> None:
        """初始化业务逻辑组件"""
        # 初始化ConfigManager
        self.config_manager = ConfigManager('config.json')
        self.config = self.config_manager.load()
        
        # 验证配置
        is_valid, error_msg = self.config_manager.validate(self.config)
        if not is_valid:
            QMessageBox.warning(
                None, 
                '配置错误', 
                f'配置文件无效: {error_msg}\n\n请在启动后配置正确的参数。'
            )
        
        # 初始化Database
        db_path = 'file_records.db'
        self.db = Database(db_path)
        
        # 根据配置选择首选解压软件
        preferred = getattr(self.config, 'preferred_extractor', 'bandizip')
        use_bandizip = (preferred == 'bandizip')
        
        # 初始化Extractor
        extractor = Extractor(use_bandizip=use_bandizip)
        
        # 检查解压工具是否可用
        if use_bandizip:
            if not extractor.check_bandizip_available():
                QMessageBox.warning(
                    None,
                    '警告',
                    'Bandizip工具不可用，将使用7-Zip作为备选。'
                )
        else:
            if not extractor.check_7z_available():
                QMessageBox.critical(
                    None,
                    '错误',
                    '7z工具不可用，请检查7z.exe是否存在。'
                )
        
        # 初始化FileProcessor
        if self.config.unpack_folder:
            self.file_processor = FileProcessor(
                self.config.unpack_folder,
                extractor,
                self.db,
                self.config,
                status_callback=self._on_processing_status  # 添加状态回调
            )
        else:
            self.file_processor = None
        
        # 初始化FileMonitor（暂不启动）
        if self.config.target_folder and self.file_processor:
            self.file_monitor = FileMonitor(
                self.config.target_folder,
                self._on_new_file_in_target_folder
            )
        else:
            self.file_monitor = None
        
        # 不再监控解压文件夹，避免递归触发和文件访问冲突
        # 解压文件夹中的文件由 RecursiveHandler 主动扫描处理
        self.unpack_monitor = None
        
        # 初始化FileChecker
        if self.config.unpack_folder:
            self.file_checker = FileChecker(self.db, self.config.unpack_folder)
            # 启动时检查所有文件
            self.file_checker.check_all_files()
            # 启动定期检查
            self.file_checker.start_periodic_check()
        else:
            self.file_checker = None
        
        # 初始化FileDeleter
        if self.config.unpack_folder:
            self.file_deleter = FileDeleter(self.db, self.config.unpack_folder)
        else:
            self.file_deleter = None
    
    def _on_new_file_in_target_folder(self, file_path: str) -> None:
        """目标文件夹监控回调函数
        
        Args:
            file_path: 新文件路径
        """
        # 使用信号发射到主线程处理（移动到解压文件夹）
        self.new_file_signal.emit(file_path)
    
    def _on_new_file_in_unpack_folder(self, file_path: str) -> None:
        """解压文件夹监控回调函数
        
        Args:
            file_path: 新文件路径
        """
        # 使用信号发射到主线程处理（直接解压）
        self.unpack_file_signal.emit(file_path)
    
    def _process_new_file_in_main_thread(self, file_path: str) -> None:
        """在主线程中处理目标文件夹的新文件（移动到解压文件夹）
        
        Args:
            file_path: 新文件路径
        """
        if self.file_processor:
            self._start_async_processing(file_path, is_in_unpack_folder=False)
    
    def _process_unpack_file_in_main_thread(self, file_path: str) -> None:
        """在主线程中处理解压文件夹的新文件（直接解压）
        
        Args:
            file_path: 新文件路径
        """
        if self.file_processor:
            self._start_async_processing(file_path, is_in_unpack_folder=True)
    
    def _start_async_processing(self, file_path: str, is_in_unpack_folder: bool = False) -> None:
        """启动异步文件处理
        
        Args:
            file_path: 文件路径
            is_in_unpack_folder: 是否在解压文件夹中
        """
        # 检查是否已达到最大并发数
        active_workers = [w for w in self.processing_workers if w.isRunning()]
        
        if len(active_workers) >= self.max_concurrent_workers:
            # 添加到队列等待处理
            self.processing_queue.append((file_path, is_in_unpack_folder))
            self._show_status_message(f"文件已加入处理队列: {os.path.basename(file_path)} (队列中: {len(self.processing_queue)})")
            return
        
        # 创建工作线程
        worker = FileProcessingWorker(self.file_processor, file_path, is_in_unpack_folder)
        
        # 连接信号
        worker.status_update.connect(self._show_status_message)
        worker.processing_finished.connect(lambda: self._on_processing_finished(worker))
        worker.error_occurred.connect(self._on_processing_error)
        
        # 添加到工作线程列表
        self.processing_workers.append(worker)
        
        # 显示进度条
        self._update_progress_bar()
        
        # 启动线程
        worker.start()
        self._show_status_message(f"开始异步处理: {os.path.basename(file_path)}")
    
    def _on_processing_finished(self, worker: FileProcessingWorker) -> None:
        """处理完成回调
        
        Args:
            worker: 完成的工作线程
        """
        # 从工作线程列表中移除
        if worker in self.processing_workers:
            self.processing_workers.remove(worker)
        
        # 检查文件状态并刷新文件列表
        self._check_and_update_file_status()
        self.load_records()
        
        # 处理队列中的下一个文件
        if self.processing_queue:
            file_path, is_in_unpack_folder = self.processing_queue.pop(0)
            self._start_async_processing(file_path, is_in_unpack_folder)
        
        # 更新进度条
        self._update_progress_bar()
        
        # 清理完成的线程
        worker.deleteLater()
    
    def _on_processing_error(self, error_message: str) -> None:
        """处理错误回调
        
        Args:
            error_message: 错误消息
        """
        self._show_status_message(f"处理错误: {error_message}")
        QMessageBox.warning(self, "处理错误", error_message)
    
    def _update_progress_bar(self) -> None:
        """更新进度条显示"""
        active_workers = [w for w in self.processing_workers if w.isRunning()]
        queue_count = len(self.processing_queue)
        total_tasks = len(active_workers) + queue_count
        
        if total_tasks > 0:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(total_tasks)
            self.progress_bar.setValue(total_tasks - queue_count)
            self.progress_bar.setFormat(f"处理中: {len(active_workers)}, 队列: {queue_count}")
        else:
            self.progress_bar.setVisible(False)
    
    def _on_processing_status(self, message: str) -> None:
        """处理文件处理状态回调
        
        Args:
            message: 状态消息
        """
        # 使用信号发射到主线程显示
        self.status_message_signal.emit(message)
    
    def _show_status_message(self, message: str) -> None:
        """在主线程中显示状态消息
        
        Args:
            message: 状态消息
        """
        print(message)  # 在主线程中安全地打印消息
        
        # 添加到日志组件
        if self.log_widget:
            self.log_widget.add_log(message)
        
        # 如果是递归处理相关的成功消息，检查状态并刷新文件列表
        if any(keyword in message for keyword in ["成功解压嵌套压缩包", "成功解压单图片文件"]):
            self._check_and_update_file_status()
            self.load_records()
    
    def init_ui(self) -> None:
        """初始化UI组件"""
        # 设置窗口标题和图标
        self.setWindowTitle('🗜️ 自动解压管理器 - Auto Unpack Manager')
        
        # 设置窗口大小和最小尺寸
        self.resize(1200, 700)
        self.setMinimumSize(800, 500)
        
        # 设置样式表 - 黑暗模式
        self.setStyleSheet("""
            /* 主窗口背景 */
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            
            /* 通用控件样式 */
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            
            /* 按钮样式 */
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 14px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 20px;
            }
            
            QPushButton:hover {
                background-color: #45a049;
            }
            
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
            
            /* 停止按钮 */
            QPushButton#stopButton {
                background-color: #f44336;
            }
            
            QPushButton#stopButton:hover {
                background-color: #da190b;
            }
            
            /* 配置按钮 */
            QPushButton#configButton {
                background-color: #2196F3;
            }
            
            QPushButton#configButton:hover {
                background-color: #1976D2;
            }
            
            /* 刷新按钮 */
            QPushButton#refreshButton {
                background-color: #FF9800;
            }
            
            QPushButton#refreshButton:hover {
                background-color: #F57C00;
            }
            
            /* 标签样式 */
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            
            QLabel#statusLabel {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #4CAF50;
                margin: 10px 0;
            }
            
            /* 表格样式 */
            QTableWidget {
                background-color: #3c3c3c;
                alternate-background-color: #404040;
                color: #ffffff;
                gridline-color: #555555;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #555555;
            }
            
            QTableWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            
            QTableWidget::item:hover {
                background-color: #484848;
            }
            
            /* 表头样式 */
            QHeaderView::section {
                background-color: #404040;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #555555;
                font-weight: bold;
            }
            
            QHeaderView::section:hover {
                background-color: #4a4a4a;
            }
            
            /* 滚动条样式 */
            QScrollBar:vertical {
                background-color: #404040;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background-color: #666666;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            
            QScrollBar:horizontal {
                background-color: #404040;
                height: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:horizontal {
                background-color: #666666;
                border-radius: 6px;
                min-width: 20px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background-color: #777777;
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            
            /* 进度条样式 */
            QProgressBar {
                border: 2px solid #555555;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            
            /* 复选框和单选按钮样式 */
            QCheckBox, QRadioButton {
                color: #ffffff;
                spacing: 8px;
            }
            
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #666666;
                border-radius: 3px;
                background-color: #3c3c3c;
            }
            
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
                image: none;
            }
            
            QCheckBox::indicator:hover, QRadioButton::indicator:hover {
                border-color: #4CAF50;
            }
            
            QCheckBox::indicator:checked:hover, QRadioButton::indicator:checked:hover {
                background-color: #45a049;
                border-color: #45a049;
            }
            
            /* 输入框样式 */
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                font-size: 14px;
            }
            
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
                border-color: #4CAF50;
            }
            
            /* 组合框样式 */
            QComboBox {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
                min-width: 100px;
            }
            
            QComboBox:hover {
                border-color: #4CAF50;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
            }
            
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                selection-background-color: #4CAF50;
                color: #ffffff;
            }
        """)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 添加标题
        title_label = QLabel('📁 文件解压监控管理')
        title_label.setObjectName('titleLabel')
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建顶部工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        
        # 监控控制按钮
        self.start_button = QPushButton('▶️ 启动监控')
        self.start_button.clicked.connect(self.start_monitoring)
        self.start_button.setMinimumHeight(40)
        toolbar_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton('⏹️ 停止监控')
        self.stop_button.setObjectName('stopButton')
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        self.stop_button.setMinimumHeight(40)
        toolbar_layout.addWidget(self.stop_button)
        
        # 配置按钮
        self.config_button = QPushButton('⚙️ 配置')
        self.config_button.setObjectName('configButton')
        self.config_button.clicked.connect(self.on_config_clicked)
        self.config_button.setMinimumHeight(40)
        toolbar_layout.addWidget(self.config_button)
        
        # 刷新按钮
        refresh_button = QPushButton('🔄 刷新')
        refresh_button.setObjectName('refreshButton')
        refresh_button.clicked.connect(self.refresh_records)
        refresh_button.setMinimumHeight(40)
        toolbar_layout.addWidget(refresh_button)
        
        # 添加弹性空间
        toolbar_layout.addStretch()
        
        # 状态标签
        self.status_label = QLabel('状态: 未启动 ⏸️')
        self.status_label.setObjectName('statusLabel')
        toolbar_layout.addWidget(self.status_label)
        
        main_layout.addLayout(toolbar_layout)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)  # 默认隐藏
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # 筛选控件
        self.filter_widget = FilterWidget()
        self.filter_widget.filter_changed.connect(self.on_filter_changed)
        self.filter_widget.log_button_clicked.connect(self.on_log_button_clicked)
        main_layout.addWidget(self.filter_widget)
        
        # 文件列表控件
        self.file_list_widget = FileListWidget()
        # 连接信号
        self.file_list_widget.delete_file_clicked.connect(self.on_delete_file_clicked)
        self.file_list_widget.delete_record_clicked.connect(self.on_delete_record_clicked)
        self.file_list_widget.open_folder_clicked.connect(self.on_open_folder_clicked)
        self.file_list_widget.extract_clicked.connect(self.on_extract_clicked)
        self.file_list_widget.batch_delete_files_clicked.connect(self.on_batch_delete_files_clicked)
        self.file_list_widget.batch_delete_records_clicked.connect(self.on_batch_delete_records_clicked)
        main_layout.addWidget(self.file_list_widget, 1)  # 占据剩余空间
        
        # 日志控件（初始隐藏）
        self.log_widget = LogWidget()
        self.log_widget.hide()
        main_layout.addWidget(self.log_widget, 1)
        
        # 设置窗口居中
        self._center_window()
    
    def _center_window(self) -> None:
        """将窗口居中显示"""
        frame_geometry = self.frameGeometry()
        from PyQt5.QtWidgets import QDesktopWidget
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
    
    def start_monitoring(self) -> None:
        """启动文件监控"""
        # 重新加载配置文件以获取最新配置
        try:
            self.config = self.config_manager.load()
            print(f"重新加载配置: target_folder={self.config.target_folder}, unpack_folder={self.config.unpack_folder}")
        except Exception as e:
            QMessageBox.critical(
                self,
                '配置错误',
                f'加载配置文件失败: {e}'
            )
            return
        
        # 验证配置
        is_valid, error_msg = self.config_manager.validate(self.config)
        if not is_valid:
            QMessageBox.warning(
                self,
                '配置错误',
                f'配置文件无效: {error_msg}\n\n请先配置正确的参数。'
            )
            return
        
        # 检查目标文件夹是否存在
        if not os.path.exists(self.config.target_folder):
            QMessageBox.warning(
                self,
                '错误',
                f'目标文件夹不存在: {self.config.target_folder}'
            )
            return
        
        # 重新初始化业务组件以应用新配置
        self._reinit_business_components()
        
        # 检查FileMonitor是否已初始化
        if not self.file_monitor:
            QMessageBox.warning(
                self,
                '错误',
                '文件监控器初始化失败，无法启动监控。'
            )
            return
        
        # 检查解压文件夹监控器是否已初始化
        # 不再监控解压文件夹，避免递归触发和文件访问冲突
        # 解压文件夹中的文件由 RecursiveHandler 主动扫描处理
        
        try:
            # 启动目标文件夹监控
            self.file_monitor.start()
            
            # 不再启动解压文件夹监控
            
            # 更新UI状态
            self.is_monitoring = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText('状态: 监控中 🟢')
            self.status_label.setStyleSheet("QLabel#statusLabel { background-color: #1e5631; border-color: #4CAF50; color: #4CAF50; }")
            
            print(f"已启动监控: 目标文件夹={self.config.target_folder}, 解压文件夹={self.config.unpack_folder}")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                '错误',
                f'启动监控失败: {e}'
            )
            print(f"启动监控失败: {e}")
    
    def stop_monitoring(self) -> None:
        """停止文件监控"""
        try:
            # 停止目标文件夹监控
            if self.file_monitor:
                self.file_monitor.stop()
            
            # 清理Bandizip进程（防止占用压缩包）
            self._cleanup_bandizip_processes()
            
            # 更新UI状态
            self.is_monitoring = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status_label.setText('状态: 已停止 🔴')
            self.status_label.setStyleSheet("QLabel#statusLabel { background-color: #5c1e1e; border-color: #f44336; color: #f44336; }")
            
            print("已停止监控")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                '错误',
                f'停止监控失败: {e}'
            )
            print(f"停止监控失败: {e}")
    
    def load_records(self) -> None:
        """加载文件记录到列表"""
        if not self.db:
            return
        
        try:
            # 获取当前选中的筛选状态
            selected_statuses = []
            if self.filter_widget:
                selected_statuses = self.filter_widget.get_selected_statuses()
            
            # 根据筛选条件获取记录
            if not selected_statuses or 'all' in selected_statuses:
                records = self.db.get_all_records()
            else:
                # 获取所有选中状态的记录
                records = []
                for status in selected_statuses:
                    status_records = self.db.get_records_by_status(status)
                    records.extend(status_records)
                
                # 去重
                seen_ids = set()
                unique_records = []
                for record in records:
                    if record.id not in seen_ids:
                        seen_ids.add(record.id)
                        unique_records.append(record)
                records = unique_records
            
            # 将记录显示到文件列表控件
            if self.file_list_widget:
                self.file_list_widget.set_records(records)
            
            # 更新筛选计数
            if self.filter_widget:
                self._update_filter_counts()
            
            print(f"加载了 {len(records)} 条文件记录")
            
        except Exception as e:
            print(f"加载文件记录失败: {e}")
            QMessageBox.warning(self, '错误', f'加载文件记录失败: {e}')
    
    def refresh_records(self) -> None:
        """刷新文件记录显示"""
        # 先检查文件状态并更新数据库
        self._check_and_update_file_status()
        
        # 重新加载记录
        self.load_records()
        
        # 更新筛选控件的统计信息
        if self.filter_widget and self.db:
            self._update_filter_counts()
    
    def _check_and_update_file_status(self) -> None:
        """检查并更新文件状态"""
        if not self.file_checker:
            return
        
        try:
            # 检查所有文件并获取已删除的文件ID列表
            deleted_ids = self.file_checker.check_all_files()
            
            if deleted_ids:
                print(f"检测到 {len(deleted_ids)} 个文件已被手动删除，已更新状态")
                
                # 显示状态消息
                self._show_status_message(f"检测到 {len(deleted_ids)} 个文件已被手动删除")
            
        except Exception as e:
            print(f"检查文件状态时出错: {e}")
            self._show_status_message(f"检查文件状态时出错: {e}")
    
    def _update_filter_counts(self) -> None:
        """更新筛选控件的状态计数"""
        if not self.db or not self.filter_widget:
            return
        
        try:
            # 获取各状态的计数
            counts = {}
            
            # 定义所有状态
            statuses = [
                'moved',
                'success',
                'failed',
                'password_error',
                'corrupted',
                'deleted'
            ]
            
            # 统计每个状态的数量
            for status in statuses:
                records = self.db.get_records_by_status(status)
                counts[status] = len(records)
            
            # 更新筛选控件
            self.filter_widget.set_status_counts(counts)
            
        except Exception as e:
            print(f"更新筛选计数失败: {e}")
    
    def on_filter_changed(self, selected_statuses: list) -> None:
        """处理筛选条件变化
        
        Args:
            selected_statuses: 选中的状态列表
        """
        # 如果点击了其他筛选按钮，取消日志按钮的选中状态
        if self.is_log_view and self.filter_widget:
            self.filter_widget.uncheck_log_button()
            self.is_log_view = False
            self.log_widget.hide()
            self.file_list_widget.show()
        
        if not self.db:
            return
        
        try:
            # 如果选中"全部"或列表为空，显示所有记录
            if 'all' in selected_statuses or not selected_statuses:
                records = self.db.get_all_records()
            else:
                # 获取所有选中状态的记录
                records = []
                for status in selected_statuses:
                    status_records = self.db.get_records_by_status(status)
                    records.extend(status_records)
                
                # 去重（如果有记录被多次添加）
                seen_ids = set()
                unique_records = []
                for record in records:
                    if record.id not in seen_ids:
                        seen_ids.add(record.id)
                        unique_records.append(record)
                records = unique_records
            
            # 更新文件列表显示
            if self.file_list_widget:
                self.file_list_widget.set_records(records)
            
            print(f"筛选条件变化: {selected_statuses}, 找到 {len(records)} 条记录")
            
        except Exception as e:
            print(f"筛选记录失败: {e}")
            QMessageBox.warning(self, '错误', f'筛选记录失败: {e}')
    
    def on_log_button_clicked(self, is_active: bool) -> None:
        """处理日志按钮点击
        
        Args:
            is_active: 是否激活日志视图
        """
        self.is_log_view = is_active
        
        if is_active:
            # 显示日志视图，隐藏文件列表
            self.file_list_widget.hide()
            self.log_widget.show()
        else:
            # 显示文件列表，隐藏日志视图
            self.log_widget.hide()
            self.file_list_widget.show()
            # 刷新文件列表
            self.refresh_records()
    
    def on_open_folder_clicked(self, record_id: int) -> None:
        """处理打开文件夹按钮点击
        
        Args:
            record_id: 记录ID
        """
        # 从数据库获取记录
        record = self.db.get_record_by_id(record_id)
        if not record:
            QMessageBox.warning(self, '错误', '找不到该记录')
            return
        
        # 获取解压文件夹路径
        import os
        folder_path = os.path.dirname(record.original_path)
        
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, '错误', f'文件夹不存在: {folder_path}')
            return
        
        try:
            # 使用系统默认方式打开文件夹
            import subprocess
            if os.name == 'nt':  # Windows
                # Windows explorer 需要反斜杠路径
                windows_path = folder_path.replace('/', '\\')
                # explorer 命令有时会返回非零退出码，但实际已成功打开
                # 使用 check=False 忽略退出码检查
                subprocess.run(['explorer', windows_path], check=False)
            elif os.name == 'darwin':  # macOS
                subprocess.run(['open', folder_path], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', folder_path], check=True)
            
            self.status_message_signal.emit(f'已打开文件夹: {folder_path}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'无法打开文件夹: {e}')
    
    def on_extract_clicked(self, record_id: int) -> None:
        """处理解压按钮点击
        
        Args:
            record_id: 记录ID
        """
        if not self.file_processor:
            QMessageBox.warning(self, '错误', '文件处理器未初始化')
            return
        
        # 从数据库获取记录
        record = self.db.get_record_by_id(record_id)
        if not record:
            QMessageBox.warning(self, '错误', '找不到该记录')
            return
        
        # 检查文件是否存在
        import os
        if not os.path.exists(record.original_path):
            QMessageBox.warning(self, '错误', f'压缩包文件不存在: {record.original_path}')
            return
        
        # 确认解压
        reply = QMessageBox.question(
            self,
            '确认解压',
            f'确定要解压该文件吗？\n\n{record.filename}',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 更新状态为解压中
                self.db.update_status(record_id, 'extracting', '开始解压')
                
                # 在新线程中处理文件，避免阻塞GUI
                import threading
                def process_in_thread():
                    try:
                        self.file_processor.process_file(record.original_path)
                    except Exception as e:
                        self.logger.error(f'解压失败: {e}')
                        self.db.update_status(record_id, 'failed', f'解压失败: {e}')
                
                thread = threading.Thread(target=process_in_thread, daemon=True)
                thread.start()
                
                # 显示状态消息
                self._show_status_message(f'开始解压: {record.filename}')
                
                # 刷新文件列表
                self.refresh_records()
                
            except Exception as e:
                QMessageBox.critical(self, '错误', f'解压失败: {e}')
                self.db.update_status(record_id, 'failed', f'解压失败: {e}')
    
    def on_delete_file_clicked(self, record_id: int) -> None:
        """处理删除文件按钮点击
        
        Args:
            record_id: 记录ID
        """
        if not self.file_deleter:
            QMessageBox.warning(self, '错误', '文件删除器未初始化')
            return
        
        # TODO: 显示确认对话框（任务14中实现）
        # 临时使用标准确认对话框
        reply = QMessageBox.question(
            self,
            '确认删除',
            '确定要删除该压缩包吗？\n\n这将只删除压缩包文件，解压文件夹将被保留。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success, message = self.file_deleter.delete_file(record_id)
                
                if success:
                    QMessageBox.information(self, '成功', message)
                    # 刷新文件列表
                    self.refresh_records()
                else:
                    QMessageBox.warning(self, '失败', message)
                
            except Exception as e:
                QMessageBox.critical(self, '错误', f'删除文件时出错: {e}')
    
    def on_delete_record_clicked(self, record_id: int) -> None:
        """处理删除记录按钮点击
        
        Args:
            record_id: 记录ID
        """
        if not self.file_deleter:
            QMessageBox.warning(self, '错误', '文件删除器未初始化')
            return
        
        # 创建自定义对话框
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QHBoxLayout, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle('确认删除 - Butter自动解压')
        dialog.setMinimumWidth(350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
                padding: 10px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #666666;
                border-radius: 3px;
                background-color: #3c3c3c;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#cancelButton {
                background-color: #6c757d;
            }
            QPushButton#cancelButton:hover {
                background-color: #5a6268;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 提示文字
        label = QLabel('确定要删除该记录吗？')
        layout.addWidget(label)
        
        # 复选框
        checkbox = QCheckBox('同时删除文件（压缩包和解压文件夹）')
        checkbox.setChecked(False)
        layout.addWidget(checkbox)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        yes_button = QPushButton('Yes')
        yes_button.clicked.connect(dialog.accept)
        button_layout.addWidget(yes_button)
        
        no_button = QPushButton('No')
        no_button.setObjectName('cancelButton')
        no_button.clicked.connect(dialog.reject)
        button_layout.addWidget(no_button)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            also_delete_file = checkbox.isChecked()
            
            try:
                success, message = self.file_deleter.delete_record(
                    record_id, 
                    also_delete_file
                )
                
                if success:
                    QMessageBox.information(self, '成功', message)
                    # 刷新文件列表
                    self.refresh_records()
                else:
                    QMessageBox.warning(self, '失败', message)
                
            except Exception as e:
                QMessageBox.critical(self, '错误', f'删除记录时出错: {e}')
    
    def on_batch_delete_files_clicked(self, record_ids: List[int]) -> None:
        """处理批量删除文件按钮点击
        
        Args:
            record_ids: 记录ID列表
        """
        if not self.file_deleter:
            QMessageBox.warning(self, '错误', '文件删除器未初始化')
            return
        
        if not record_ids:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            '确认批量删除',
            f'确定要删除选中的 {len(record_ids)} 个压缩包吗？\n\n这将只删除压缩包文件，解压文件夹将被保留。',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success_count = 0
            failed_count = 0
            
            for record_id in record_ids:
                try:
                    success, message = self.file_deleter.delete_file(record_id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        print(f"删除文件失败 (ID: {record_id}): {message}")
                except Exception as e:
                    failed_count += 1
                    print(f"删除文件时出错 (ID: {record_id}): {e}")
            
            # 显示结果
            if failed_count == 0:
                QMessageBox.information(
                    self, 
                    '批量删除完成', 
                    f'成功删除 {success_count} 个压缩包文件'
                )
            else:
                QMessageBox.warning(
                    self, 
                    '批量删除完成', 
                    f'成功删除 {success_count} 个文件，失败 {failed_count} 个文件'
                )
            
            # 刷新文件列表
            self.refresh_records()
    
    def on_batch_delete_records_clicked(self, record_ids: List[int]) -> None:
        """处理批量删除记录按钮点击
        
        Args:
            record_ids: 记录ID列表
        """
        if not self.file_deleter:
            QMessageBox.warning(self, '错误', '文件删除器未初始化')
            return
        
        if not record_ids:
            return
        
        # 创建自定义对话框（带复选框）
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QHBoxLayout, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle('确认批量删除 - Butter自动解压')
        dialog.setMinimumWidth(350)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
                padding: 10px;
            }
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #666666;
                border-radius: 3px;
                background-color: #3c3c3c;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton#cancelButton {
                background-color: #6c757d;
            }
            QPushButton#cancelButton:hover {
                background-color: #5a6268;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 提示文字
        label = QLabel(f'确定要删除选中的 {len(record_ids)} 条记录吗？')
        layout.addWidget(label)
        
        # 复选框
        checkbox = QCheckBox('同时删除文件（压缩包和解压文件夹）')
        checkbox.setChecked(False)
        layout.addWidget(checkbox)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        yes_button = QPushButton('Yes')
        yes_button.clicked.connect(dialog.accept)
        button_layout.addWidget(yes_button)
        
        no_button = QPushButton('No')
        no_button.setObjectName('cancelButton')
        no_button.clicked.connect(dialog.reject)
        button_layout.addWidget(no_button)
        
        layout.addLayout(button_layout)
        
        # 显示对话框
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            also_delete_file = checkbox.isChecked()
            
            success_count = 0
            failed_count = 0
            
            for record_id in record_ids:
                try:
                    success, message = self.file_deleter.delete_record(
                        record_id, 
                        also_delete_file
                    )
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        print(f"删除记录失败 (ID: {record_id}): {message}")
                except Exception as e:
                    failed_count += 1
                    print(f"删除记录时出错 (ID: {record_id}): {e}")
            
            # 显示结果
            if failed_count == 0:
                QMessageBox.information(
                    self, 
                    '批量删除完成', 
                    f'成功删除 {success_count} 条记录'
                )
            else:
                QMessageBox.warning(
                    self, 
                    '批量删除完成', 
                    f'成功删除 {success_count} 条记录，失败 {failed_count} 条记录'
                )
            
            # 刷新文件列表
            self.refresh_records()
    
    def on_config_clicked(self) -> None:
        """打开配置对话框"""
        # 创建配置对话框
        dialog = ConfigDialog(self.config, self)
        
        # 显示对话框
        if dialog.exec_() == QDialog.Accepted:
            # 获取新配置
            new_config = dialog.get_config()
            
            # 验证配置
            is_valid, error_msg = self.config_manager.validate(new_config)
            
            if not is_valid:
                QMessageBox.warning(
                    self,
                    '配置错误',
                    f'配置无效: {error_msg}'
                )
                return
            
            # 保存配置
            try:
                self.config_manager.save(new_config)
                self.config = new_config
                
                QMessageBox.information(
                    self,
                    '成功',
                    '配置已保存。\n\n某些更改可能需要重启监控才能生效。'
                )
                
                # 如果监控正在运行，提示用户重启
                if self.is_monitoring:
                    reply = QMessageBox.question(
                        self,
                        '重启监控',
                        '配置已更改，是否重启监控以应用新配置？',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.stop_monitoring()
                        # 重新初始化业务组件
                        self._reinit_business_components()
                        self.start_monitoring()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    '错误',
                    f'保存配置失败: {e}'
                )
    
    def _reinit_business_components(self) -> None:
        """重新初始化业务逻辑组件"""
        # 停止现有的文件检查器
        if self.file_checker:
            self.file_checker.stop_periodic_check()
        
        # 根据配置选择首选解压软件
        preferred = getattr(self.config, 'preferred_extractor', 'bandizip')
        use_bandizip = (preferred == 'bandizip')
        
        # 重新初始化Extractor
        extractor = Extractor(use_bandizip=use_bandizip)
        
        # 重新初始化FileProcessor
        if self.config.unpack_folder:
            self.file_processor = FileProcessor(
                self.config.unpack_folder,
                extractor,
                self.db,
                self.config,
                status_callback=self._on_processing_status  # 添加状态回调
            )
        else:
            self.file_processor = None
        
        # 重新初始化FileMonitor
        if self.config.target_folder and self.file_processor:
            self.file_monitor = FileMonitor(
                self.config.target_folder,
                self._on_new_file_in_target_folder
            )
        else:
            self.file_monitor = None
        
        # 不再重新初始化解压文件夹监控器（已移除）
        self.unpack_monitor = None
        
        # 重新初始化FileChecker
        if self.config.unpack_folder:
            self.file_checker = FileChecker(self.db, self.config.unpack_folder)
            self.file_checker.check_all_files()
            self.file_checker.start_periodic_check()
        else:
            self.file_checker = None
        
        # 重新初始化FileDeleter
        if self.config.unpack_folder:
            self.file_deleter = FileDeleter(self.db, self.config.unpack_folder)
        else:
            self.file_deleter = None
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 停止自动刷新定时器
        if self.refresh_timer:
            self.refresh_timer.stop()
        
        # 停止监控
        if self.is_monitoring:
            self.stop_monitoring()
        
        # 等待所有工作线程完成
        for worker in self.processing_workers:
            if worker.isRunning():
                worker.terminate()
                worker.wait(3000)  # 等待3秒
        
        # 停止文件检查器
        if self.file_checker:
            self.file_checker.stop_periodic_check()
        
        # 清理所有残留的7z进程
        self._cleanup_7z_processes()
        
        # 清理所有残留的Bandizip进程
        self._cleanup_bandizip_processes()
        
        event.accept()
    
    def _cleanup_7z_processes(self):
        """清理所有7z进程"""
        try:
            import subprocess
            # 查找所有7za.exe进程
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq 7za.exe', '/FO', 'CSV', '/NH'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if '7za.exe' in result.stdout:
                print("检测到残留的7z进程，正在清理...")
                # 强制终止所有7za.exe进程
                subprocess.run(
                    ['taskkill', '/F', '/IM', '7za.exe'],
                    capture_output=True,
                    timeout=5
                )
                print("7z进程已清理")
        except Exception as e:
            print(f"清理7z进程时出错: {e}")
    
    def _cleanup_bandizip_processes(self):
        """清理所有Bandizip进程"""
        try:
            import subprocess
            # 查找所有bz.exe进程
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq bz.exe', '/FO', 'CSV', '/NH'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'bz.exe' in result.stdout:
                print("检测到残留的Bandizip进程，正在清理...")
                # 强制终止所有bz.exe进程
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'bz.exe'],
                    capture_output=True,
                    timeout=5
                )
                print("Bandizip进程已清理")
        except Exception as e:
            print(f"清理Bandizip进程时出错: {e}")
