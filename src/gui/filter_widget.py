#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FilterWidget - 筛选控件
提供状态筛选功能
"""

from typing import Dict, List, Optional
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QLabel, QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class FilterWidget(QWidget):
    """筛选控件
    
    提供状态筛选功能，支持单标签和多标签筛选
    
    Signals:
        filter_changed: 筛选条件变化信号 (selected_statuses: List[str])
        log_button_clicked: 日志按钮点击信号 (is_active: bool)
    """
    
    # 定义信号 - 传递选中的状态列表
    filter_changed = pyqtSignal(list)
    log_button_clicked = pyqtSignal(bool)  # 日志按钮点击信号，传递是否选中
    
    # 状态定义
    STATUS_ALL = 'all'
    STATUS_MOVED = 'moved'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_PASSWORD_ERROR = 'password_error'
    STATUS_CORRUPTED = 'corrupted'
    STATUS_DELETED = 'deleted'
    STATUS_LOG = 'log'  # 日志按钮状态
    
    # 状态显示文本映射
    STATUS_TEXT_MAP = {
        STATUS_ALL: '全部',
        STATUS_MOVED: '已移动',
        STATUS_SUCCESS: '解压成功',
        STATUS_FAILED: '解压失败',
        STATUS_PASSWORD_ERROR: '密码错误',
        STATUS_CORRUPTED: '文件损坏',
        STATUS_DELETED: '已删除'
    }
    
    def __init__(self, parent=None):
        """初始化筛选控件
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        
        # 状态按钮字典 {status: button}
        self._status_buttons = {}
        
        # 状态计数字典 {status: count}
        self._status_counts = {}
        
        # 选中的状态集合
        self._selected_statuses = {self.STATUS_ALL}
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self) -> None:
        """初始化UI组件"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建标题
        title_label = QLabel('筛选条件')
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # 创建状态按钮
        statuses = [
            self.STATUS_ALL,
            self.STATUS_MOVED,
            self.STATUS_SUCCESS,
            self.STATUS_FAILED,
            self.STATUS_PASSWORD_ERROR,
            self.STATUS_CORRUPTED,
            self.STATUS_DELETED
        ]
        
        for status in statuses:
            button = self._create_status_button(status)
            self._status_buttons[status] = button
            button_layout.addWidget(button)
        
        # 添加分隔线
        button_layout.addSpacing(20)
        
        # 创建日志按钮
        self.log_button = QPushButton('📋 日志')
        self.log_button.setCheckable(True)
        self.log_button.setMinimumWidth(80)
        self.log_button.setMinimumHeight(30)
        self.log_button.clicked.connect(self._on_log_button_clicked)
        self._update_log_button_style()
        button_layout.addWidget(self.log_button)
        
        # 添加弹性空间
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # 设置背景色 - 黑暗模式
        self.setStyleSheet("""
            FilterWidget {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            
            QLabel {
                color: #ffffff;
                font-weight: bold;
            }
        """)
    
    def _create_status_button(self, status: str) -> QPushButton:
        """创建状态标签按钮
        
        Args:
            status: 状态代码
            
        Returns:
            状态按钮
        """
        # 获取显示文本
        text = self.STATUS_TEXT_MAP.get(status, status)
        
        # 创建按钮
        button = QPushButton(text)
        button.setCheckable(True)  # 可切换状态
        
        # 默认选中"全部"
        if status == self.STATUS_ALL:
            button.setChecked(True)
        
        # 设置按钮样式
        button.setMinimumWidth(80)
        button.setMinimumHeight(30)
        
        # 连接点击事件
        button.clicked.connect(lambda: self._on_button_clicked(status))
        
        # 更新按钮样式
        self._update_button_style(button, status)
        
        return button
    
    def _on_button_clicked(self, status: str) -> None:
        """处理按钮点击事件
        
        Args:
            status: 被点击的状态
        """
        button = self._status_buttons.get(status)
        if not button:
            return
        
        # 如果点击的是"全部"
        if status == self.STATUS_ALL:
            if button.isChecked():
                # 选中"全部"，取消其他所有选择
                self._selected_statuses = {self.STATUS_ALL}
                for s, btn in self._status_buttons.items():
                    if s != self.STATUS_ALL:
                        btn.setChecked(False)
                        self._update_button_style(btn, s)
            else:
                # 不允许取消"全部"如果没有其他选择
                if not any(self._status_buttons[s].isChecked() 
                          for s in self._status_buttons if s != self.STATUS_ALL):
                    button.setChecked(True)
                    return
        else:
            # 点击的是具体状态
            if button.isChecked():
                # 选中具体状态，取消"全部"
                self._selected_statuses.discard(self.STATUS_ALL)
                self._selected_statuses.add(status)
                
                all_button = self._status_buttons.get(self.STATUS_ALL)
                if all_button:
                    all_button.setChecked(False)
                    self._update_button_style(all_button, self.STATUS_ALL)
            else:
                # 取消选中具体状态
                self._selected_statuses.discard(status)
                
                # 如果没有任何选择，自动选中"全部"
                if not self._selected_statuses:
                    self._selected_statuses = {self.STATUS_ALL}
                    all_button = self._status_buttons.get(self.STATUS_ALL)
                    if all_button:
                        all_button.setChecked(True)
                        self._update_button_style(all_button, self.STATUS_ALL)
        
        # 更新按钮样式
        self._update_button_style(button, status)
        
        # 发送筛选变化信号
        self._emit_filter_changed()
    
    def _on_log_button_clicked(self) -> None:
        """处理日志按钮点击事件"""
        is_checked = self.log_button.isChecked()
        
        # 如果选中日志按钮，取消其他所有筛选按钮
        if is_checked:
            for status, button in self._status_buttons.items():
                button.setChecked(False)
                self._update_button_style(button, status)
            self._selected_statuses.clear()
        
        # 更新日志按钮样式
        self._update_log_button_style()
        
        # 发送日志按钮点击信号
        self.log_button_clicked.emit(is_checked)
    
    def _update_log_button_style(self) -> None:
        """更新日志按钮样式"""
        if self.log_button.isChecked():
            # 选中状态 - 蓝色
            self.log_button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    border: 2px solid #4CAF50;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    color: #ffffff;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #42A5F5;
                }
            """)
        else:
            # 未选中状态
            self.log_button.setStyleSheet("""
                QPushButton {
                    background-color: #404040;
                    border: 1px solid #666666;
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: #cccccc;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border: 1px solid #777777;
                    color: #ffffff;
                }
            """)
    
    def uncheck_log_button(self) -> None:
        """取消日志按钮的选中状态"""
        self.log_button.setChecked(False)
        self._update_log_button_style()
    
    def _update_button_style(self, button: QPushButton, status: str) -> None:
        """更新按钮样式（黑暗模式适配）
        
        Args:
            button: 按钮
            status: 状态代码
        """
        # 获取计数
        count = self._status_counts.get(status, 0)
        
        # 更新按钮文本（包含计数）
        text = self.STATUS_TEXT_MAP.get(status, status)
        button.setText(f"{text} ({count})")
        
        # 根据选中状态设置样式
        if button.isChecked():
            # 选中状态的样式 - 黑暗模式
            color = self._get_status_color(status)
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    border: 2px solid #4CAF50;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-weight: bold;
                    color: #ffffff;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {self._lighten_color(color)};
                }}
            """)
        else:
            # 未选中状态的样式 - 黑暗模式
            button.setStyleSheet("""
                QPushButton {
                    background-color: #404040;
                    border: 1px solid #666666;
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: #cccccc;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                    border: 1px solid #777777;
                    color: #ffffff;
                }
            """)
    
    def _get_status_color(self, status: str) -> str:
        """获取状态颜色（黑暗模式适配）
        
        Args:
            status: 状态代码
            
        Returns:
            颜色代码
        """
        color_map = {
            self.STATUS_ALL: '#4a4a4a',
            self.STATUS_MOVED: '#1e3c72',      # 深蓝色
            self.STATUS_SUCCESS: '#2d5016',    # 深绿色
            self.STATUS_FAILED: '#5c1e1e',     # 深红色
            self.STATUS_PASSWORD_ERROR: '#5c3a1e', # 深橙色
            self.STATUS_CORRUPTED: '#6b1e1e',  # 更深红色
            self.STATUS_DELETED: '#3c3c3c'     # 深灰色
        }
        return color_map.get(status, '#4a4a4a')
    
    def _lighten_color(self, color: str) -> str:
        """使颜色变亮（黑暗模式适配）
        
        Args:
            color: 颜色代码
            
        Returns:
            变亮后的颜色代码
        """
        # 简单实现：将RGB值增加30（黑暗模式下需要更明显的变化）
        if color.startswith('#') and len(color) == 7:
            r = min(255, int(color[1:3], 16) + 30)
            g = min(255, int(color[3:5], 16) + 30)
            b = min(255, int(color[5:7], 16) + 30)
            return f'#{r:02x}{g:02x}{b:02x}'
        return color
    
    def _emit_filter_changed(self) -> None:
        """发送筛选变化信号"""
        # 获取选中的状态列表
        selected = list(self._selected_statuses)
        
        # 发送信号
        self.filter_changed.emit(selected)
    
    def set_status_counts(self, counts: Dict[str, int]) -> None:
        """设置各状态的文件数量
        
        Args:
            counts: 状态计数字典 {status: count}
        """
        # 更新计数
        self._status_counts = counts.copy()
        
        # 计算总数
        total = sum(counts.values())
        self._status_counts[self.STATUS_ALL] = total
        
        # 更新所有按钮的显示
        for status, button in self._status_buttons.items():
            self._update_button_style(button, status)
    
    def get_selected_statuses(self) -> List[str]:
        """获取当前选中的状态列表
        
        Returns:
            选中的状态列表
        """
        return list(self._selected_statuses)
    
    def reset_filter(self) -> None:
        """重置筛选条件为"全部" """
        # 取消所有选择
        for status, button in self._status_buttons.items():
            if status != self.STATUS_ALL:
                button.setChecked(False)
                self._update_button_style(button, status)
        
        # 选中"全部"
        all_button = self._status_buttons.get(self.STATUS_ALL)
        if all_button:
            all_button.setChecked(True)
            self._update_button_style(all_button, self.STATUS_ALL)
        
        self._selected_statuses = {self.STATUS_ALL}
        
        # 发送筛选变化信号
        self._emit_filter_changed()
