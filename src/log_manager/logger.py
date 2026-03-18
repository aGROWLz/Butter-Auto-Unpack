"""日志管理模块"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


class LogManager:
    """日志管理器
    
    负责配置和管理应用程序的日志系统
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化日志管理器"""
        if not self._initialized:
            self.logger = None
            self.log_dir = None
            self._initialized = True
    
    def setup_logging(self, log_level=logging.INFO, log_dir=None):
        """设置日志系统
        
        Args:
            log_level: 日志级别
            log_dir: 日志目录，如果为None则自动确定
        """
        # 确定日志目录
        if log_dir is None:
            log_dir = self._get_log_directory()
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建logger
        self.logger = logging.getLogger('Butter-Auto-Unpack')
        self.logger.setLevel(log_level)
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器 - 主日志文件（轮转）
        log_file = self.log_dir / 'auto_unpack_manager.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 错误日志文件处理器
        error_log_file = self.log_dir / 'error.log'
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # 控制台处理器（仅在开发环境）
        if not self._is_packaged():
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # 记录启动信息
        self.logger.info("=" * 60)
        self.logger.info("自动解压管理器启动")
        self.logger.info(f"版本: 1.0.0")
        self.logger.info(f"Python版本: {sys.version}")
        self.logger.info(f"运行环境: {'打包环境' if self._is_packaged() else '开发环境'}")
        self.logger.info(f"日志目录: {self.log_dir}")
        self.logger.info(f"日志级别: {logging.getLevelName(log_level)}")
        self.logger.info("=" * 60)
    
    def _get_log_directory(self):
        """获取日志目录路径"""
        if self._is_packaged():
            # 打包环境：使用exe同目录下的logs文件夹
            exe_dir = Path(sys.executable).parent
            return exe_dir / 'logs'
        else:
            # 开发环境：使用项目根目录下的logs文件夹
            project_root = Path(__file__).parent.parent.parent
            return project_root / 'logs'
    
    def _is_packaged(self):
        """判断是否为打包环境"""
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')
    
    def get_logger(self):
        """获取logger实例"""
        if self.logger is None:
            self.setup_logging()
        return self.logger
    
    def log_exception(self, exception, context=""):
        """记录异常信息
        
        Args:
            exception: 异常对象
            context: 异常上下文描述
        """
        if self.logger:
            self.logger.error(f"异常发生 - {context}", exc_info=exception)
    
    def log_file_operation(self, operation, file_path, result="成功", details=""):
        """记录文件操作
        
        Args:
            operation: 操作类型（移动、解压、删除等）
            file_path: 文件路径
            result: 操作结果
            details: 详细信息
        """
        if self.logger:
            message = f"文件操作 - {operation}: {file_path} - {result}"
            if details:
                message += f" - {details}"
            
            if result == "成功":
                self.logger.info(message)
            elif result == "失败":
                self.logger.error(message)
            else:
                self.logger.warning(message)
    
    def log_system_event(self, event, details=""):
        """记录系统事件
        
        Args:
            event: 事件类型
            details: 事件详情
        """
        if self.logger:
            message = f"系统事件 - {event}"
            if details:
                message += f": {details}"
            self.logger.info(message)


# 全局日志管理器实例
log_manager = LogManager()


def get_logger():
    """获取全局logger实例"""
    return log_manager.get_logger()


def setup_logging(log_level=logging.INFO, log_dir=None):
    """设置日志系统（便捷函数）"""
    log_manager.setup_logging(log_level, log_dir)


def log_exception(exception, context=""):
    """记录异常（便捷函数）"""
    log_manager.log_exception(exception, context)


def log_file_operation(operation, file_path, result="成功", details=""):
    """记录文件操作（便捷函数）"""
    log_manager.log_file_operation(operation, file_path, result, details)


def log_system_event(event, details=""):
    """记录系统事件（便捷函数）"""
    log_manager.log_system_event(event, details)