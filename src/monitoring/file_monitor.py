"""文件监控服务模块

使用watchdog库监控目标文件夹中的新文件出现事件
支持检测复制、移动、创建等各种方式出现的新文件
"""
import os
import time
from typing import Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from ..log_manager import get_logger, log_system_event


class FileMonitor:
    """文件监控器
    
    监控指定文件夹，检测新文件出现事件并通过回调函数通知处理器
    支持检测复制、移动、创建等各种方式出现的新文件
    """
    
    def __init__(self, target_folder: str, callback: Callable[[str], None]):
        """初始化文件监控器
        
        Args:
            target_folder: 要监控的目标文件夹路径
            callback: 文件出现时的回调函数，接收文件路径作为参数
        """
        self.target_folder = target_folder
        self.callback = callback
        self.observer = None
        self._event_handler = None
        self.logger = get_logger()
        
        # 记录已存在的文件，避免重复处理
        self._existing_files: Set[str] = set()
        self._initialize_existing_files()
        
        self.logger.info(f"文件监控器初始化 - 目标文件夹: {target_folder}")
        self.logger.info(f"已存在文件数量: {len(self._existing_files)}")
    
    def _initialize_existing_files(self):
        """初始化已存在文件列表"""
        try:
            if os.path.exists(self.target_folder) and os.path.isdir(self.target_folder):
                for filename in os.listdir(self.target_folder):
                    file_path = os.path.join(self.target_folder, filename)
                    if os.path.isfile(file_path):
                        self._existing_files.add(file_path)
                        self.logger.debug(f"记录已存在文件: {file_path}")
        except Exception as e:
            self.logger.error(f"初始化已存在文件列表时发生错误: {e}")
    
    def start(self) -> None:
        """启动文件监控
        
        开始监控目标文件夹，检测新文件出现事件
        """
        if self.observer is not None:
            raise RuntimeError("监控器已经在运行中")
        
        if not os.path.exists(self.target_folder):
            raise ValueError(f"目标文件夹不存在: {self.target_folder}")
        
        if not os.path.isdir(self.target_folder):
            raise ValueError(f"目标路径不是文件夹: {self.target_folder}")
        
        # 创建事件处理器
        self._event_handler = _FileEventHandler(
            self.callback, 
            self.logger, 
            self._existing_files,
            self.target_folder
        )
        
        # 创建观察者并开始监控
        self.observer = Observer()
        self.observer.schedule(self._event_handler, self.target_folder, recursive=False)
        self.observer.start()
        
        self.logger.info(f"文件监控已启动 - 监控目录: {self.target_folder}")
        log_system_event("文件监控启动", f"目录: {self.target_folder}")
    
    def stop(self) -> None:
        """停止文件监控
        
        停止监控目标文件夹
        """
        if self.observer is None:
            return
        
        self.observer.stop()
        self.observer.join()
        self.observer = None
        self._event_handler = None
        
        self.logger.info("文件监控已停止")
        log_system_event("文件监控停止")


class _FileEventHandler(FileSystemEventHandler):
    """内部文件系统事件处理器
    
    响应文件创建和移动事件，检测所有新出现的文件
    """
    
    def __init__(self, callback: Callable[[str], None], logger, existing_files: Set[str], target_folder: str):
        """初始化事件处理器
        
        Args:
            callback: 文件出现时的回调函数
            logger: 日志记录器
            existing_files: 已存在文件集合
            target_folder: 监控的目标文件夹
        """
        super().__init__()
        self.callback = callback
        self.logger = logger
        self.existing_files = existing_files
        self.target_folder = target_folder
    
    def on_created(self, event):
        """处理文件创建事件
        
        Args:
            event: 文件系统事件对象
        """
        # 忽略目录创建事件，只处理文件创建
        if event.is_directory:
            return
        
        file_path = event.src_path
        self._handle_new_file(file_path, "创建")
    
    def on_moved(self, event):
        """处理文件移动事件
        
        Args:
            event: 文件系统事件对象
        """
        # 忽略目录移动事件，只处理文件移动
        if event.is_directory:
            return
        
        # 检查是否是移动到监控目录
        dest_path = event.dest_path
        if os.path.dirname(dest_path) == self.target_folder:
            self._handle_new_file(dest_path, "移动")
    
    def _handle_new_file(self, file_path: str, event_type: str):
        """处理新出现的文件
        
        Args:
            file_path: 文件路径
            event_type: 事件类型（创建、移动等）
        """
        # 检查文件是否真实存在
        if not os.path.exists(file_path):
            self.logger.debug(f"文件不存在，跳过处理: {file_path}")
            return
        
        # 检查是否为新文件（不在已存在文件列表中）
        if file_path in self.existing_files:
            self.logger.debug(f"文件已存在，跳过处理: {file_path}")
            return
        
        # 添加到已存在文件列表
        self.existing_files.add(file_path)
        
        self.logger.info(f"检测到新文件({event_type}): {file_path}")
        log_system_event(f"文件{event_type}检测", file_path)
        
        # 等待文件完全写入完成（对于大文件复制）
        self._wait_for_file_complete(file_path)
        
        # 调用回调函数处理新文件
        try:
            self.callback(file_path)
        except Exception as e:
            self.logger.error(f"处理新文件时发生错误: {file_path}", exc_info=True)
    
    def _wait_for_file_complete(self, file_path: str, max_wait: int = 5):
        """等待文件完全写入完成
        
        对于大文件的复制操作，需要等待文件完全写入完成后再处理
        
        Args:
            file_path: 文件路径
            max_wait: 最大等待时间（秒）
        """
        try:
            last_size = -1
            wait_count = 0
            
            while wait_count < max_wait:
                if not os.path.exists(file_path):
                    break
                
                current_size = os.path.getsize(file_path)
                
                # 如果文件大小没有变化，认为写入完成
                if current_size == last_size and current_size > 0:
                    break
                
                last_size = current_size
                time.sleep(1)
                wait_count += 1
                
                self.logger.debug(f"等待文件写入完成: {file_path} (大小: {current_size})")
            
            if wait_count >= max_wait:
                self.logger.warning(f"文件写入等待超时: {file_path}")
                # 如果文件大小为0且超时，跳过处理
                if current_size == 0:
                    self.logger.info(f"跳过大小为0的文件: {file_path}")
                    return
            else:
                self.logger.debug(f"文件写入完成: {file_path}")
                
        except Exception as e:
            self.logger.error(f"等待文件写入完成时发生错误: {file_path} - {e}")
