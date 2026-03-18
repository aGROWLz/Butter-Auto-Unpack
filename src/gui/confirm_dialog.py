#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ConfirmDialog - 确认对话框类
提供删除文件和删除记录的确认对话框
"""

from typing import Tuple
from PyQt5.QtWidgets import QMessageBox, QCheckBox, QVBoxLayout, QLabel, QWidget
from PyQt5.QtCore import Qt


class ConfirmDialog:
    """确认对话框类
    
    提供静态方法用于显示确认对话框：
    - 删除文件确认
    - 删除记录确认（带"同时删除文件"选项）
    """
    
    @staticmethod
    def confirm_delete_file(filename: str, parent=None) -> bool:
        """确认删除文件
        
        显示确认对话框，询问用户是否删除文件（包括压缩包和解压文件夹）
        
        Args:
            filename: 要删除的文件名
            parent: 父窗口
            
        Returns:
            bool: 用户是否确认删除
        """
        # 创建消息框
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle('确认删除文件')
        msg_box.setIcon(QMessageBox.Warning)
        
        # 设置消息文本
        msg_box.setText(f'确定要删除文件吗？')
        msg_box.setInformativeText(
            f'文件名: {filename}\n\n'
            f'此操作将删除：\n'
            f'• Unpack文件夹中的压缩包文件\n'
            f'• 对应的解压文件夹及其所有内容\n\n'
            f'此操作不可撤销！'
        )
        
        # 设置按钮
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        # 设置按钮文本
        yes_button = msg_box.button(QMessageBox.Yes)
        yes_button.setText('删除')
        no_button = msg_box.button(QMessageBox.No)
        no_button.setText('取消')
        
        # 显示对话框并返回结果
        result = msg_box.exec_()
        return result == QMessageBox.Yes
    
    @staticmethod
    def confirm_delete_record(filename: str, parent=None) -> Tuple[bool, bool]:
        """确认删除记录
        
        显示确认对话框，询问用户是否删除记录，并提供"同时删除文件"选项
        
        Args:
            filename: 要删除记录的文件名
            parent: 父窗口
            
        Returns:
            Tuple[bool, bool]: (用户是否确认删除, 是否同时删除文件)
        """
        # 创建消息框
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle('确认删除记录')
        msg_box.setIcon(QMessageBox.Question)
        
        # 设置消息文本
        msg_box.setText(f'确定要删除记录吗？')
        msg_box.setInformativeText(
            f'文件名: {filename}\n\n'
            f'此操作将从数据库中删除该文件的处理记录。'
        )
        
        # 创建"同时删除文件"复选框
        checkbox = QCheckBox('同时删除文件（包括压缩包和解压文件夹）')
        checkbox.setChecked(False)
        
        # 将复选框添加到消息框
        msg_box.setCheckBox(checkbox)
        
        # 设置按钮
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        # 设置按钮文本
        yes_button = msg_box.button(QMessageBox.Yes)
        yes_button.setText('删除')
        no_button = msg_box.button(QMessageBox.No)
        no_button.setText('取消')
        
        # 显示对话框
        result = msg_box.exec_()
        
        # 返回结果
        confirmed = result == QMessageBox.Yes
        # 使用msg_box.checkBox()获取复选框状态
        also_delete_file = msg_box.checkBox().isChecked() if confirmed else False
        
        return confirmed, also_delete_file
