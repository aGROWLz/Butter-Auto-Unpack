#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LogWidget - 日志显示控件
提供简洁的日志显示功能，支持文本复制
"""

from typing import List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QLabel, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class LogWidget(QWidget):
    """日志显示控件
    
    提供简洁的日志显示功能，支持文本复制
    
    Signals:
        log_cleared: 日志清空信号
    """
    
    log_cleared = pyqtSignal()
    
    def __init__(self, parent=None):
        """初始化日志控件
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        
        # 日志条目列表（用于限制数量）
        self._log_entries: List[str] = []
        self._max_entries = 500  # 最大保留日志条数
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self) -> None:
        """初始化UI组件"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建标题栏
        title_layout = QHBoxLayout()
        
        # 标题
        self.title_label = QLabel('📋 运行日志')
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        self.title_label.setFont(title_font)
        title_layout.addWidget(self.title_label)
        
        # 日志计数
        self.count_label = QLabel('(0 条)')
        title_layout.addWidget(self.count_label)
        
        # 弹性空间
        title_layout.addStretch()
        
        # 复制按钮
        self.copy_button = QPushButton('📋 复制全部')
        self.copy_button.setMinimumWidth(100)
        self.copy_button.clicked.connect(self._copy_all_logs)
        title_layout.addWidget(self.copy_button)
        
        # 清空按钮
        self.clear_button = QPushButton('🗑️ 清空')
        self.clear_button.setMinimumWidth(80)
        self.clear_button.clicked.connect(self._clear_logs)
        title_layout.addWidget(self.clear_button)
        
        main_layout.addLayout(title_layout)
        
        # 创建日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setLineWrapMode(QTextEdit.WidgetWidth)
        
        # 设置字体
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.Monospace)
        self.log_text.setFont(font)
        
        # 设置样式 - 黑暗模式
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 10px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
        """)
        
        main_layout.addWidget(self.log_text, 1)
        
        # 设置整体样式
        self.setStyleSheet("""
            LogWidget {
                background-color: #2d2d2d;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #666666;
                border-radius: 4px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #777777;
            }
        """)
    
    def add_log(self, message: str) -> None:
        """添加日志条目
        
        Args:
            message: 日志消息
        """
        # 简化日志格式 - 只保留时间和核心信息
        simplified_message = self._simplify_log(message)
        
        # 添加到列表
        self._log_entries.append(simplified_message)
        
        # 限制日志数量
        if len(self._log_entries) > self._max_entries:
            self._log_entries = self._log_entries[-self._max_entries:]
        
        # 更新显示
        self._update_display()
    
    def _simplify_log(self, message: str) -> str:
        """简化日志消息
        
        Args:
            message: 原始日志消息
            
        Returns:
            简化后的日志消息
        """
        # 如果消息包含时间戳，提取时间和核心内容
        if ' - ' in message and ':' in message[:20]:
            # 尝试提取时间部分
            parts = message.split(' - ', 2)
            if len(parts) >= 2:
                time_part = parts[0].strip()
                # 提取 HH:MM:SS 格式的时间
                if ' ' in time_part:
                    time_str = time_part.split(' ')[-1]
                else:
                    time_str = time_part
                
                # 提取核心信息（去掉文件名等冗长信息）
                core_message = parts[-1].strip()
                
                # 进一步简化常见消息
                core_message = self._simplify_common_messages(core_message)
                
                return f"[{time_str}] {core_message}"
        
        # 无法解析，返回简化后的原消息
        return self._simplify_common_messages(message)
    
    def _simplify_common_messages(self, message: str) -> str:
        """简化常见日志消息
        
        Args:
            message: 原始消息
            
        Returns:
            简化后的消息
        """
        # 简化文件路径 - 只保留文件名
        import re
        
        # 替换完整路径为文件名
        message = re.sub(r'[A-Za-z]:/[^/\s]+/([^/\s]+)', r'\1', message)
        message = re.sub(r'[A-Za-z]:\\[^\\\s]+\\([^\\\s]+)', r'\1', message)
        
        # 简化常见消息
        simplifications = {
            'Bandizip进程已启动': '开始解压',
            'Bandizip命令执行完成，返回码': '解压完成，返回码',
            '准备执行Bandizip命令（无密码）': '尝试无密码解压',
            '准备执行Bandizip命令（使用密码）': '尝试密码解压',
            '返回码为': '返回码:',
            '且无错误输出，推测需要密码': '→ 需要密码',
            '错误输出中包含密码关键词，推测需要密码': '→ 需要密码',
            '检测到需要密码': '需要密码',
            '密码解压成功': '✓ 解压成功',
            '解压成功': '✓ 解压成功',
            '解压失败': '✗ 解压失败',
            '文件操作 - 移动': '→ 移动',
            '文件操作 - 解压': '→ 解压',
            '文件已移动到': '已移动',
            '递归处理器返回': '递归完成',
            '状态已更新为': '状态:',
            '准备更新状态为': '更新状态:',
            '文件处理完成': '处理完成',
            '开始处理文件': '开始处理',
            '文件已在数据库中标记为已处理，跳过': '已处理，跳过',
            '文件已处理过，跳过': '已处理，跳过',
        }
        
        for old, new in simplifications.items():
            if old in message:
                message = message.replace(old, new)
                break
        
        return message
    
    def _update_display(self) -> None:
        """更新日志显示"""
        # 合并所有日志条目
        log_text = '\n'.join(self._log_entries)
        
        # 更新文本框
        self.log_text.setPlainText(log_text)
        
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # 更新计数
        self.count_label.setText(f'({len(self._log_entries)} 条)')
    
    def _copy_all_logs(self) -> None:
        """复制所有日志到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_text.toPlainText())
        
        # 临时显示提示
        original_text = self.copy_button.text()
        self.copy_button.setText('✓ 已复制')
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.copy_button.setText(original_text))
    
    def _clear_logs(self) -> None:
        """清空日志"""
        self._log_entries.clear()
        self.log_text.clear()
        self.count_label.setText('(0 条)')
        self.log_cleared.emit()
    
    def get_logs(self) -> str:
        """获取所有日志文本
        
        Returns:
            所有日志文本
        """
        return self.log_text.toPlainText()
