#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Butter Auto Unpack - Main Entry Point
Butter自动解压 - 主入口文件
"""

import sys
import os
import argparse
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from src.log_manager import setup_logging, get_logger, log_exception, log_system_event
from src.gui.main_window import MainWindow


def get_7z_path() -> str:
    """获取打包的7za.exe路径
    
    处理开发环境和打包环境的路径差异
    
    Returns:
        7za.exe的完整路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的exe环境
        # PyInstaller会将文件解压到临时目录sys._MEIPASS
        base_path = sys._MEIPASS
    else:
        # 开发环境
        # 获取当前脚本所在目录（项目根目录）
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    # 返回resources目录下的7za.exe路径
    return os.path.join(base_path, 'resources', '7za.exe')


def parse_arguments():
    """解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description='Butter自动解压 - Butter Auto Unpack',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 启动GUI应用程序
  %(prog)s --config config.json  # 使用指定的配置文件
  %(prog)s --version          # 显示版本信息
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='配置文件路径 (默认: config.json)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Butter Auto Unpack v1.0.0'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式'
    )
    
    return parser.parse_args()


def main():
    """主应用程序入口点
    
    创建QApplication实例，初始化主窗口，启动事件循环
    
    Returns:
        int: 应用程序退出码
    """
    # 解析命令行参数
    args = parse_arguments()
    
    # 初始化日志系统
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(log_level)
    logger = get_logger()
    
    # 记录启动参数
    logger.info(f"命令行参数: {vars(args)}")
    logger.info(f"7z路径: {get_7z_path()}")
    
    # 设置调试模式
    if args.debug:
        print("调试模式已启用")
        print(f"7z路径: {get_7z_path()}")
        print(f"配置文件: {args.config}")
        logger.debug("调试模式已启用")
    
    # 创建QApplication实例
    # 在Windows上启用高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # 尝试注册自定义元类型以避免PyQt5警告（如果可用）
    try:
        from PyQt5.QtCore import qRegisterMetaType
        qRegisterMetaType('QVector<int>')
    except ImportError:
        # 如果qRegisterMetaType不可用，忽略注册
        pass
    
    # 设置应用程序信息
    app.setApplicationName('Butter Auto Unpack')
    app.setApplicationDisplayName('Butter-Auto-Unpack')
    app.setOrganizationName('Butter')
    app.setOrganizationDomain('butter.local')
    
    log_system_event("应用程序初始化", "QApplication已创建")
    
    # 设置应用程序样式（可选）
    # app.setStyle('Fusion')
    
    try:
        # 初始化主窗口
        logger.info("正在初始化主窗口...")
        main_window = MainWindow()
        
        # 显示主窗口
        main_window.show()
        logger.info("主窗口已显示")
        
        # 如果是调试模式，打印窗口信息
        if args.debug:
            print(f"主窗口已显示")
            print(f"窗口大小: {main_window.size()}")
            logger.debug(f"窗口大小: {main_window.size()}")
        
        log_system_event("应用程序启动完成", "进入事件循环")
        
        # 启动Qt事件循环
        exit_code = app.exec_()
        
        log_system_event("应用程序退出", f"退出码: {exit_code}")
        logger.info("应用程序正常退出")
        
        return exit_code
        
    except Exception as e:
        # 捕获并显示任何初始化错误
        error_msg = f"应用程序启动失败: {e}"
        print(f"错误: {error_msg}")
        log_exception(e, "应用程序启动")
        
        # 尝试显示错误对话框
        try:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                '启动错误',
                f'应用程序启动失败:\n\n{e}\n\n请检查配置文件和7z工具是否正确安装。'
            )
        except Exception as dialog_error:
            logger.error(f"无法显示错误对话框: {dialog_error}")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
