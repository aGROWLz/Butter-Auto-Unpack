#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ConfigDialog - 配置对话框类
提供配置编辑界面
"""

import os
from typing import Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QListWidget, QLabel,
    QFileDialog, QMessageBox, QGroupBox, QDialogButtonBox,
    QCheckBox
)
from PyQt5.QtCore import Qt

from ..config.config import Config


class ConfigDialog(QDialog):
    """配置对话框类
    
    提供配置编辑界面，允许用户设置：
    - 目标文件夹路径
    - Unpack文件夹路径
    - 密码列表
    - 图片文件的压缩格式后缀
    """
    
    def __init__(self, config: Config, parent=None):
        """初始化配置对话框
        
        Args:
            config: 当前配置对象
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 保存配置副本
        self.config = config
        
        # 初始化UI
        self._init_ui()
        
        # 加载当前配置到UI
        self._load_config_to_ui()
    
    def _init_ui(self) -> None:
        """初始化UI组件"""
        # 设置对话框标题和大小
        self.setWindowTitle('⚙️ 配置 - Configuration')
        self.resize(650, 550)
        
        # 设置黑暗模式样式
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #4CAF50;
                font-size: 14px;
            }
            
            QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            
            QLineEdit {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                font-size: 13px;
                min-height: 20px;
            }
            
            QLineEdit:focus {
                border-color: #4CAF50;
            }
            
            QListWidget {
                background-color: #3c3c3c;
                border: 2px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                font-size: 13px;
                padding: 4px;
            }
            
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #555555;
            }
            
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            
            QListWidget::item:hover {
                background-color: #484848;
            }
            
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                font-size: 13px;
                border-radius: 4px;
                font-weight: bold;
                min-height: 20px;
            }
            
            QPushButton:hover {
                background-color: #45a049;
            }
            
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            
            QDialogButtonBox QPushButton {
                min-width: 80px;
                padding: 8px 20px;
            }
            
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555555;
                border-radius: 3px;
                background-color: #3c3c3c;
            }
            
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            
            QCheckBox::indicator:hover {
                border-color: #4CAF50;
            }
            
            QCheckBox::indicator:checked:hover {
                background-color: #45a049;
            }
        """)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建文件夹配置组
        folder_group = self._create_folder_group()
        main_layout.addWidget(folder_group)
        
        # 创建密码列表配置组
        password_group = self._create_password_group()
        main_layout.addWidget(password_group)
        
        # 创建其他配置组
        other_group = self._create_other_group()
        main_layout.addWidget(other_group)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 创建按钮栏
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_ok_clicked)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
    
    def _create_folder_group(self) -> QGroupBox:
        """创建文件夹配置组
        
        Returns:
            QGroupBox: 文件夹配置组
        """
        group = QGroupBox('文件夹配置')
        layout = QFormLayout()
        
        # 目标文件夹
        target_layout = QHBoxLayout()
        self.target_folder_edit = QLineEdit()
        self.target_folder_edit.setPlaceholderText('选择要监控的目标文件夹')
        target_layout.addWidget(self.target_folder_edit)
        
        target_browse_btn = QPushButton('浏览...')
        target_browse_btn.clicked.connect(self._browse_target_folder)
        target_layout.addWidget(target_browse_btn)
        
        layout.addRow('目标文件夹:', target_layout)
        
        # Unpack文件夹
        unpack_layout = QHBoxLayout()
        self.unpack_folder_edit = QLineEdit()
        self.unpack_folder_edit.setPlaceholderText('选择解压文件的目标文件夹')
        unpack_layout.addWidget(self.unpack_folder_edit)
        
        unpack_browse_btn = QPushButton('浏览...')
        unpack_browse_btn.clicked.connect(self._browse_unpack_folder)
        unpack_layout.addWidget(unpack_browse_btn)
        
        layout.addRow('Unpack文件夹:', unpack_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_password_group(self) -> QGroupBox:
        """创建密码列表配置组
        
        Returns:
            QGroupBox: 密码列表配置组
        """
        group = QGroupBox('密码列表')
        layout = QVBoxLayout()
        
        # 说明标签
        info_label = QLabel('解压时将按顺序尝试以下密码：')
        layout.addWidget(info_label)
        
        # 密码列表
        self.password_list = QListWidget()
        self.password_list.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.password_list)
        
        # 密码输入和按钮
        password_input_layout = QHBoxLayout()
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('输入新密码')
        self.password_input.returnPressed.connect(self._add_password)
        password_input_layout.addWidget(self.password_input)
        
        add_btn = QPushButton('添加')
        add_btn.clicked.connect(self._add_password)
        password_input_layout.addWidget(add_btn)
        
        remove_btn = QPushButton('删除')
        remove_btn.clicked.connect(self._remove_password)
        password_input_layout.addWidget(remove_btn)
        
        move_up_btn = QPushButton('上移')
        move_up_btn.clicked.connect(self._move_password_up)
        password_input_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton('下移')
        move_down_btn.clicked.connect(self._move_password_down)
        password_input_layout.addWidget(move_down_btn)
        
        layout.addLayout(password_input_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_other_group(self) -> QGroupBox:
        """创建其他配置组
        
        Returns:
            QGroupBox: 其他配置组
        """
        group = QGroupBox('其他配置')
        layout = QFormLayout()
        
        # 图片压缩后缀
        self.image_suffix_edit = QLineEdit()
        self.image_suffix_edit.setPlaceholderText('例如: .zip')
        layout.addRow('图片压缩后缀:', self.image_suffix_edit)
        
        # 媒体文件验证开关
        self.verify_media_checkbox = QCheckBox('验证图片和视频文件是否为伪装压缩包')
        self.verify_media_checkbox.setToolTip(
            '开启时：会检测图片/视频文件是否为伪装的压缩包，只处理真正的压缩包\n'
            '关闭时：将所有图片/视频文件都当作伪装压缩包处理（适用于加密压缩包）'
        )
        layout.addRow('', self.verify_media_checkbox)
        
        # 密码测试开关
        self.test_passwords_checkbox = QCheckBox('7z测试时尝试使用密码库')
        self.test_passwords_checkbox.setToolTip(
            '开启时：7z测试文件时会尝试使用密码库中的密码，可以识别加密的伪装压缩包\n'
            '关闭时：7z测试时不使用密码，只能识别无密码的伪装压缩包（速度更快）'
        )
        layout.addRow('', self.test_passwords_checkbox)
        
        # 7z路径
        seven_zip_layout = QHBoxLayout()
        self.seven_zip_path_edit = QLineEdit()
        self.seven_zip_path_edit.setPlaceholderText('7z可执行文件路径')
        seven_zip_layout.addWidget(self.seven_zip_path_edit)
        
        seven_zip_browse_btn = QPushButton('浏览...')
        seven_zip_browse_btn.clicked.connect(self._browse_seven_zip)
        seven_zip_layout.addWidget(seven_zip_browse_btn)
        
        layout.addRow('7z路径:', seven_zip_layout)
        
        group.setLayout(layout)
        return group
    
    def _load_config_to_ui(self) -> None:
        """加载当前配置到UI"""
        # 加载文件夹路径
        self.target_folder_edit.setText(self.config.target_folder)
        self.unpack_folder_edit.setText(self.config.unpack_folder)
        
        # 加载密码列表
        self.password_list.clear()
        for password in self.config.passwords:
            self.password_list.addItem(password)
        
        # 加载其他配置
        self.image_suffix_edit.setText(self.config.image_archive_suffix)
        self.seven_zip_path_edit.setText(self.config.seven_zip_path)
        self.verify_media_checkbox.setChecked(self.config.verify_media_files)
        self.test_passwords_checkbox.setChecked(self.config.test_with_passwords)
    
    def _browse_target_folder(self) -> None:
        """浏览选择目标文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            '选择目标文件夹',
            self.target_folder_edit.text() or os.path.expanduser('~')
        )
        
        if folder:
            self.target_folder_edit.setText(folder)
    
    def _browse_unpack_folder(self) -> None:
        """浏览选择Unpack文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            '选择Unpack文件夹',
            self.unpack_folder_edit.text() or os.path.expanduser('~')
        )
        
        if folder:
            self.unpack_folder_edit.setText(folder)
    
    def _browse_seven_zip(self) -> None:
        """浏览选择7z可执行文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择7z可执行文件',
            self.seven_zip_path_edit.text() or os.path.expanduser('~'),
            '可执行文件 (*.exe);;所有文件 (*.*)'
        )
        
        if file_path:
            self.seven_zip_path_edit.setText(file_path)
    
    def _add_password(self) -> None:
        """添加密码到列表"""
        password = self.password_input.text().strip()
        
        if not password:
            QMessageBox.warning(self, '警告', '密码不能为空')
            return
        
        # 检查密码是否已存在
        for i in range(self.password_list.count()):
            if self.password_list.item(i).text() == password:
                QMessageBox.warning(self, '警告', '该密码已存在')
                return
        
        # 添加密码
        self.password_list.addItem(password)
        self.password_input.clear()
    
    def _remove_password(self) -> None:
        """从列表中删除选中的密码"""
        current_item = self.password_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(self, '警告', '请先选择要删除的密码')
            return
        
        # 删除选中的密码
        row = self.password_list.row(current_item)
        self.password_list.takeItem(row)
    
    def _move_password_up(self) -> None:
        """将选中的密码上移"""
        current_row = self.password_list.currentRow()
        
        if current_row <= 0:
            return
        
        # 获取当前项
        current_item = self.password_list.takeItem(current_row)
        
        # 插入到上一行
        self.password_list.insertItem(current_row - 1, current_item)
        self.password_list.setCurrentRow(current_row - 1)
    
    def _move_password_down(self) -> None:
        """将选中的密码下移"""
        current_row = self.password_list.currentRow()
        
        if current_row < 0 or current_row >= self.password_list.count() - 1:
            return
        
        # 获取当前项
        current_item = self.password_list.takeItem(current_row)
        
        # 插入到下一行
        self.password_list.insertItem(current_row + 1, current_item)
        self.password_list.setCurrentRow(current_row + 1)
    
    def _on_ok_clicked(self) -> None:
        """处理确定按钮点击"""
        # 验证配置
        is_valid, error_msg = self.validate_config()
        
        if not is_valid:
            QMessageBox.warning(self, '配置错误', error_msg)
            return
        
        # 接受对话框
        self.accept()
    
    def validate_config(self) -> Tuple[bool, str]:
        """验证配置有效性
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        # 获取UI中的配置
        target_folder = self.target_folder_edit.text().strip()
        unpack_folder = self.unpack_folder_edit.text().strip()
        image_suffix = self.image_suffix_edit.text().strip()
        seven_zip_path = self.seven_zip_path_edit.text().strip()
        
        # 验证目标文件夹
        if not target_folder:
            return False, "目标文件夹不能为空"
        
        if not os.path.isabs(target_folder):
            return False, "目标文件夹必须是绝对路径"
        
        # 验证Unpack文件夹
        if not unpack_folder:
            return False, "Unpack文件夹不能为空"
        
        if not os.path.isabs(unpack_folder):
            return False, "Unpack文件夹必须是绝对路径"
        
        # 验证两个文件夹不能相同
        if os.path.normpath(target_folder) == os.path.normpath(unpack_folder):
            return False, "目标文件夹和Unpack文件夹不能相同"
        
        # 验证图片后缀
        if not image_suffix:
            return False, "图片压缩后缀不能为空"
        
        if not image_suffix.startswith('.'):
            return False, "图片压缩后缀必须以点(.)开头"
        
        # 验证7z路径
        if not seven_zip_path:
            return False, "7z路径不能为空"
        
        return True, ""
    
    def get_config(self) -> Config:
        """获取用户编辑后的配置
        
        Returns:
            Config: 新的配置对象
        """
        # 获取密码列表
        passwords = []
        for i in range(self.password_list.count()):
            passwords.append(self.password_list.item(i).text())
        
        # 创建新的配置对象
        return Config(
            target_folder=self.target_folder_edit.text().strip(),
            unpack_folder=self.unpack_folder_edit.text().strip(),
            passwords=passwords,
            image_archive_suffix=self.image_suffix_edit.text().strip(),
            seven_zip_path=self.seven_zip_path_edit.text().strip(),
            verify_media_files=self.verify_media_checkbox.isChecked(),
            test_with_passwords=self.test_passwords_checkbox.isChecked()
        )
