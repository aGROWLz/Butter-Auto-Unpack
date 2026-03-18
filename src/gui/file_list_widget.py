#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FileListWidget - 文件列表控件
显示文件记录列表，支持排序和操作按钮
"""

from typing import List, Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QWidget, 
    QHBoxLayout, QPushButton, QHeaderView, QLabel, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QIcon, QFont

from ..database.models import FileRecord


class FileListWidget(QTableWidget):
    """文件列表控件
    
    显示文件记录列表，支持排序和操作按钮，支持多选和批量操作
    
    Signals:
        delete_file_clicked: 删除文件按钮点击信号 (record_id: int)
        delete_record_clicked: 删除记录按钮点击信号 (record_id: int)
        batch_delete_files_clicked: 批量删除文件信号 (record_ids: List[int])
        batch_delete_records_clicked: 批量删除记录信号 (record_ids: List[int])
    """
    
    # 定义信号
    delete_file_clicked = pyqtSignal(int)
    delete_record_clicked = pyqtSignal(int)
    batch_delete_files_clicked = pyqtSignal(list)
    batch_delete_records_clicked = pyqtSignal(list)
    
    # 列索引常量
    COL_CHECKBOX = 0
    COL_FILENAME = 1
    COL_ORIGINAL_PATH = 2
    COL_MOVED_TIME = 3
    COL_STATUS = 4
    COL_ACTIONS = 5
    
    def __init__(self, parent=None):
        """初始化文件列表控件
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        
        # 存储记录ID映射（行号 -> 记录ID）
        self._record_id_map = {}
        
        # 批量操作按钮
        self._batch_buttons_widget = None
        
        # 初始化表格
        self._init_table()
        
        # 不再需要连接itemSelectionChanged信号，因为我们使用复选框
    
    def _init_table(self) -> None:
        """初始化表格结构"""
        # 设置列数
        self.setColumnCount(6)
        
        # 设置表头
        self.setHorizontalHeaderLabels([
            '选择',
            '文件名',
            '原始路径',
            '移动时间',
            '状态',
            '操作'
        ])
        
        # 设置表格属性
        self.setSelectionBehavior(QTableWidget.SelectRows)  # 选择整行
        self.setSelectionMode(QTableWidget.SingleSelection)  # 单选模式
        self.setEditTriggers(QTableWidget.NoEditTriggers)  # 不可编辑
        self.setAlternatingRowColors(True)  # 交替行颜色
        
        # 设置列宽模式
        header = self.horizontalHeader()
        header.setSectionResizeMode(self.COL_CHECKBOX, QHeaderView.Fixed)
        header.setSectionResizeMode(self.COL_FILENAME, QHeaderView.Interactive)
        header.setSectionResizeMode(self.COL_ORIGINAL_PATH, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_MOVED_TIME, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_ACTIONS, QHeaderView.Fixed)
        
        # 设置默认列宽
        self.setColumnWidth(self.COL_CHECKBOX, 60)
        self.setColumnWidth(self.COL_FILENAME, 200)
        self.setColumnWidth(self.COL_ACTIONS, 220)  # 为两个按钮预留足够空间
        
        # 启用排序
        self.setSortingEnabled(True)
        
        # 设置行高
        self.verticalHeader().setDefaultSectionSize(40)  # 设置默认行高
        self.verticalHeader().setVisible(False)  # 隐藏行号
    
    def set_records(self, records: List[FileRecord]) -> None:
        """设置要显示的文件记录
        
        Args:
            records: 文件记录列表
        """
        # 保存当前选中的记录ID
        selected_record_ids = self.get_selected_record_ids()
        
        # 禁用排序以提高性能
        self.setSortingEnabled(False)
        
        # 清空现有内容
        self.setRowCount(0)
        self._record_id_map.clear()
        
        # 添加所有记录
        for record in records:
            self.add_record(record)
        
        # 恢复选中状态
        self._restore_checkbox_states(selected_record_ids)
        
        # 重新启用排序
        self.setSortingEnabled(True)
    
    def add_record(self, record: FileRecord) -> None:
        """添加单条记录
        
        Args:
            record: 文件记录
        """
        # 插入新行
        row = self.rowCount()
        self.insertRow(row)
        
        # 存储记录ID映射
        self._record_id_map[row] = record.id
        
        # 复选框
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setAlignment(Qt.AlignCenter)
        
        checkbox = QCheckBox()
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #666666;
                border-radius: 3px;
                background-color: #3c3c3c;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #666666;
                background-color: #3c3c3c;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #4CAF50;
                background-color: #4CAF50;
                border-radius: 3px;
                image: none;
            }
            QCheckBox::indicator:hover {
                border-color: #4CAF50;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #45a049;
                border-color: #45a049;
            }
        """)
        checkbox.stateChanged.connect(self._on_checkbox_changed)
        checkbox_layout.addWidget(checkbox)
        
        self.setCellWidget(row, self.COL_CHECKBOX, checkbox_widget)
        
        # 文件名
        filename_item = QTableWidgetItem(record.filename)
        filename_item.setData(Qt.UserRole, record.id)  # 存储记录ID
        self.setItem(row, self.COL_FILENAME, filename_item)
        
        # 原始路径
        path_item = QTableWidgetItem(record.original_path)
        path_item.setToolTip(record.original_path)  # 设置工具提示显示完整路径
        self.setItem(row, self.COL_ORIGINAL_PATH, path_item)
        
        # 移动时间
        time_str = self._format_datetime(record.moved_time)
        time_item = QTableWidgetItem(time_str)
        time_item.setData(Qt.UserRole, record.moved_time)  # 存储原始时间用于排序
        self.setItem(row, self.COL_MOVED_TIME, time_item)
        
        # 状态
        status_text = self._get_status_text(record.status)
        status_item = QTableWidgetItem(status_text)
        status_item.setData(Qt.UserRole, record.status)  # 存储原始状态
        
        # 设置状态颜色
        status_color = self._get_status_color(record.status)
        if status_color:
            status_item.setBackground(QBrush(status_color))
        
        # 设置状态图标
        status_icon = self._get_status_icon(record.status)
        if status_icon:
            status_item.setIcon(status_icon)
        
        # 为已删除状态设置特殊样式
        if record.status == 'deleted':
            font = status_item.font()
            font.setStrikeOut(True)  # 删除线
            font.setItalic(True)  # 斜体
            status_item.setFont(font)
            status_item.setForeground(QBrush(QColor(160, 160, 160)))  # 浅灰色文字（黑暗模式适配）
        
        # 如果有错误信息，添加到工具提示
        if record.error_message:
            status_item.setToolTip(f"{status_text}\n错误: {record.error_message}")
        
        self.setItem(row, self.COL_STATUS, status_item)
        
        # 操作按钮
        action_widget = self._create_action_buttons(record.id)
        self.setCellWidget(row, self.COL_ACTIONS, action_widget)
    
    def update_record(self, record: FileRecord) -> None:
        """更新记录显示
        
        Args:
            record: 文件记录
        """
        # 查找记录所在行
        row = self._find_record_row(record.id)
        
        if row is None:
            # 记录不存在，添加新记录
            self.add_record(record)
            return
        
        # 更新文件名
        filename_item = self.item(row, self.COL_FILENAME)
        if filename_item:
            filename_item.setText(record.filename)
        
        # 更新原始路径
        path_item = self.item(row, self.COL_ORIGINAL_PATH)
        if path_item:
            path_item.setText(record.original_path)
            path_item.setToolTip(record.original_path)
        
        # 更新移动时间
        time_str = self._format_datetime(record.moved_time)
        time_item = self.item(row, self.COL_MOVED_TIME)
        if time_item:
            time_item.setText(time_str)
            time_item.setData(Qt.UserRole, record.moved_time)
        
        # 更新状态
        status_text = self._get_status_text(record.status)
        status_item = self.item(row, self.COL_STATUS)
        if status_item:
            status_item.setText(status_text)
            status_item.setData(Qt.UserRole, record.status)
            
            # 更新状态颜色
            status_color = self._get_status_color(record.status)
            if status_color:
                status_item.setBackground(QBrush(status_color))
            else:
                status_item.setBackground(QBrush())  # 清除背景色
            
            # 更新状态图标
            status_icon = self._get_status_icon(record.status)
            if status_icon:
                status_item.setIcon(status_icon)
            else:
                status_item.setIcon(QIcon())  # 清除图标
            
            # 为已删除状态设置特殊样式
            if record.status == 'deleted':
                font = status_item.font()
                font.setStrikeOut(True)  # 删除线
                font.setItalic(True)  # 斜体
                status_item.setFont(font)
                status_item.setForeground(QBrush(QColor(160, 160, 160)))  # 浅灰色文字（黑暗模式适配）
            else:
                # 清除特殊样式
                font = status_item.font()
                font.setStrikeOut(False)
                font.setItalic(False)
                status_item.setFont(font)
                status_item.setForeground(QBrush())  # 清除前景色
            
            # 更新工具提示
            if record.error_message:
                status_item.setToolTip(f"{status_text}\n错误: {record.error_message}")
            else:
                status_item.setToolTip(status_text)
    
    def _find_record_row(self, record_id: int) -> Optional[int]:
        """查找记录所在行
        
        Args:
            record_id: 记录ID
            
        Returns:
            行号，如果未找到返回None
        """
        for row in range(self.rowCount()):
            item = self.item(row, self.COL_FILENAME)
            if item and item.data(Qt.UserRole) == record_id:
                return row
        return None
    
    def _create_action_buttons(self, record_id: int) -> QWidget:
        """创建操作按钮（删除文件、删除记录）
        
        Args:
            record_id: 记录ID
            
        Returns:
            包含操作按钮的控件
        """
        # 创建容器控件
        widget = QWidget()
        widget.setStyleSheet("background-color: transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 2, 10, 2)  # 减少上下边距
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter)  # 垂直居中对齐
        
        # 删除文件按钮 - 简化文字
        delete_file_btn = QPushButton('删除文件')
        delete_file_btn.setMinimumSize(90, 30)  # 稍微减少高度
        delete_file_btn.setMaximumSize(90, 30)
        delete_file_btn.setToolTip('删除压缩包文件和解压文件夹')
        delete_file_btn.setCursor(Qt.PointingHandCursor)
        delete_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                border: none;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        delete_file_btn.clicked.connect(
            lambda: self.delete_file_clicked.emit(record_id)
        )
        layout.addWidget(delete_file_btn)
        
        # 删除记录按钮 - 简化文字
        delete_record_btn = QPushButton('删除记录')
        delete_record_btn.setMinimumSize(90, 30)  # 稍微减少高度
        delete_record_btn.setMaximumSize(90, 30)
        delete_record_btn.setToolTip('仅删除数据库记录，保留文件')
        delete_record_btn.setCursor(Qt.PointingHandCursor)
        delete_record_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                border: none;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        delete_record_btn.clicked.connect(
            lambda: self.delete_record_clicked.emit(record_id)
        )
        layout.addWidget(delete_record_btn)
        
        layout.addStretch()
        
        return widget
    
    def _format_datetime(self, dt: datetime) -> str:
        """格式化日期时间
        
        Args:
            dt: 日期时间对象
            
        Returns:
            格式化后的字符串
        """
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(dt, str):
            # 如果已经是字符串，尝试解析后重新格式化
            try:
                parsed_dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                return parsed_dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return dt
        return str(dt)
    
    def _get_status_text(self, status: str) -> str:
        """获取状态显示文本
        
        Args:
            status: 状态代码
            
        Returns:
            状态显示文本
        """
        status_map = {
            'moved': '已移动',
            'extracting': '解压中',
            'success': '解压成功',
            'failed': '解压失败',
            'password_error': '密码错误',
            'corrupted': '文件损坏',
            'recursive_processing': '递归处理中',
            'deleted': '已删除'
        }
        return status_map.get(status, status)
    
    def _get_status_color(self, status: str) -> Optional[QColor]:
        """获取状态颜色（黑暗模式适配）
        
        Args:
            status: 状态代码
            
        Returns:
            状态颜色，如果没有特殊颜色返回None
        """
        color_map = {
            'moved': QColor(30, 60, 90),      # 深蓝色
            'extracting': QColor(80, 70, 30), # 深黄色
            'success': QColor(30, 80, 30),    # 深绿色
            'failed': QColor(80, 30, 30),     # 深红色
            'password_error': QColor(90, 60, 30), # 深橙色
            'corrupted': QColor(90, 30, 30),  # 更深红色
            'recursive_processing': QColor(60, 50, 90), # 深紫色
            'deleted': QColor(60, 60, 60)     # 深灰色
        }
        return color_map.get(status)
    
    def _get_status_icon(self, status: str) -> Optional[QIcon]:
        """获取状态图标
        
        Args:
            status: 状态代码
            
        Returns:
            状态图标，如果没有图标返回None
        """
        # 使用Qt标准图标
        from PyQt5.QtWidgets import QStyle
        
        style = self.style()
        if not style:
            return None
        
        icon_map = {
            'moved': QStyle.SP_FileDialogDetailedView,
            'extracting': QStyle.SP_BrowserReload,
            'success': QStyle.SP_DialogApplyButton,
            'failed': QStyle.SP_DialogCancelButton,
            'password_error': QStyle.SP_MessageBoxWarning,
            'corrupted': QStyle.SP_MessageBoxCritical,
            'recursive_processing': QStyle.SP_ArrowForward,
            'deleted': QStyle.SP_TrashIcon
        }
        
        icon_type = icon_map.get(status)
        if icon_type:
            return style.standardIcon(icon_type)
        
        return None
    def _on_selection_changed(self) -> None:
        """处理选择变化事件"""
        checked_count = self.get_checked_count()
        
        # 如果有多行选中，显示批量操作按钮
        if checked_count > 1:
            self._show_batch_buttons()
        else:
            self._hide_batch_buttons()
    
    def _on_checkbox_changed(self) -> None:
        """处理复选框状态变化"""
        checked_count = self.get_checked_count()
        
        # 如果有多行选中，显示批量操作按钮
        if checked_count > 1:
            self._show_batch_buttons()
        else:
            self._hide_batch_buttons()
    
    def get_checked_count(self) -> int:
        """获取选中的复选框数量
        
        Returns:
            选中的复选框数量
        """
        count = 0
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, self.COL_CHECKBOX)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    count += 1
        return count
    
    def get_selected_rows(self) -> List[int]:
        """获取选中的行号列表
        
        Returns:
            选中的行号列表
        """
        selected_rows = []
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, self.COL_CHECKBOX)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_rows.append(row)
        return selected_rows
    
    def get_selected_record_ids(self) -> List[int]:
        """获取选中记录的ID列表
        
        Returns:
            选中记录的ID列表
        """
        record_ids = []
        selected_rows = self.get_selected_rows()
        
        for row in selected_rows:
            item = self.item(row, self.COL_FILENAME)
            if item:
                record_id = item.data(Qt.UserRole)
                if record_id:
                    record_ids.append(record_id)
        
        return record_ids
    
    def _restore_checkbox_states(self, selected_record_ids: List[int]) -> None:
        """恢复复选框的选中状态
        
        Args:
            selected_record_ids: 之前选中的记录ID列表
        """
        if not selected_record_ids:
            return
        
        for row in range(self.rowCount()):
            item = self.item(row, self.COL_FILENAME)
            if item:
                record_id = item.data(Qt.UserRole)
                if record_id in selected_record_ids:
                    # 恢复选中状态
                    checkbox_widget = self.cellWidget(row, self.COL_CHECKBOX)
                    if checkbox_widget:
                        checkbox = checkbox_widget.findChild(QCheckBox)
                        if checkbox:
                            checkbox.setChecked(True)
        
        # 检查是否需要显示批量操作按钮
        checked_count = self.get_checked_count()
        if checked_count > 1:
            self._show_batch_buttons()
        else:
            self._hide_batch_buttons()
    
    def _show_batch_buttons(self) -> None:
        """显示批量操作按钮"""
        if self._batch_buttons_widget:
            self._update_selected_count()
            return
        
        # 创建批量操作按钮容器
        self._batch_buttons_widget = QWidget(self)
        self._batch_buttons_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(60, 60, 60, 240);
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 5px;
            }
        """)
        
        layout = QHBoxLayout(self._batch_buttons_widget)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # 选中数量标签
        self._selected_count_label = QLabel()
        self._selected_count_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self._selected_count_label)
        
        layout.addStretch()
        
        # 批量删除文件按钮
        batch_delete_files_btn = QPushButton('批量删除文件')
        batch_delete_files_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                border: none;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        batch_delete_files_btn.clicked.connect(self._on_batch_delete_files)
        layout.addWidget(batch_delete_files_btn)
        
        # 批量删除记录按钮
        batch_delete_records_btn = QPushButton('批量删除记录')
        batch_delete_records_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                border: none;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        batch_delete_records_btn.clicked.connect(self._on_batch_delete_records)
        layout.addWidget(batch_delete_records_btn)
        
        # 取消选择按钮
        cancel_btn = QPushButton('取消选择')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                border: none;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        cancel_btn.clicked.connect(self.clear_all_checkboxes)
        layout.addWidget(cancel_btn)
        
        # 更新选中数量
        self._update_selected_count()
        
        # 显示批量操作按钮
        self._batch_buttons_widget.show()
        self._position_batch_buttons()
    
    def _hide_batch_buttons(self) -> None:
        """隐藏批量操作按钮"""
        if self._batch_buttons_widget:
            self._batch_buttons_widget.hide()
            self._batch_buttons_widget.deleteLater()
            self._batch_buttons_widget = None
    
    def _position_batch_buttons(self) -> None:
        """定位批量操作按钮"""
        if not self._batch_buttons_widget:
            return
        
        # 将按钮定位在表格底部中央
        table_rect = self.rect()
        button_width = 600
        button_height = 50
        
        x = (table_rect.width() - button_width) // 2
        y = table_rect.height() - button_height - 20
        
        self._batch_buttons_widget.setGeometry(x, y, button_width, button_height)
    
    def _update_selected_count(self) -> None:
        """更新选中数量显示"""
        if not self._batch_buttons_widget or not hasattr(self, '_selected_count_label'):
            return
        
        selected_count = self.get_checked_count()
        self._selected_count_label.setText(f"已选择 {selected_count} 项")
    
    def _on_batch_delete_files(self) -> None:
        """处理批量删除文件"""
        record_ids = self.get_selected_record_ids()
        if record_ids:
            self.batch_delete_files_clicked.emit(record_ids)
    
    def _on_batch_delete_records(self) -> None:
        """处理批量删除记录"""
        record_ids = self.get_selected_record_ids()
        if record_ids:
            self.batch_delete_records_clicked.emit(record_ids)
    
    def clear_all_checkboxes(self) -> None:
        """清除所有复选框选择"""
        for row in range(self.rowCount()):
            checkbox_widget = self.cellWidget(row, self.COL_CHECKBOX)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
        self._hide_batch_buttons()
    
    def resizeEvent(self, event):
        """重写resize事件，重新定位批量操作按钮"""
        super().resizeEvent(event)
        if self._batch_buttons_widget and self._batch_buttons_widget.isVisible():
            self._position_batch_buttons()
    
    def clearSelection(self):
        """重写清除选择方法"""
        super().clearSelection()
        # 不需要隐藏批量按钮，因为复选框状态没有改变