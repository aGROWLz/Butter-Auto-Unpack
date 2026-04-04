"""文件存在性检查器模块"""
import os
import threading
import time
from typing import List
from pathlib import Path

from ..database.database import Database


class FileChecker:
    """文件存在性检查器
    
    负责定期检查已记录文件是否仍然存在，标记已删除的文件
    """
    
    def __init__(self, db: Database, unpack_folder: str):
        """初始化文件检查器
        
        Args:
            db: 数据库实例
            unpack_folder: Unpack文件夹路径
        """
        self.db = db
        self.unpack_folder = unpack_folder
        self._check_thread = None
        self._stop_event = threading.Event()
        self._check_interval = 300  # 5分钟（300秒）
    
    def start_periodic_check(self) -> None:
        """启动定期检查
        
        在后台线程中每5分钟检查一次文件存在性
        """
        if self._check_thread is not None and self._check_thread.is_alive():
            return
        
        self._stop_event.clear()
        self._check_thread = threading.Thread(target=self._periodic_check_loop, daemon=True)
        self._check_thread.start()
    
    def stop_periodic_check(self) -> None:
        """停止定期检查"""
        if self._check_thread is not None:
            self._stop_event.set()
            self._check_thread.join(timeout=5)
    
    def _periodic_check_loop(self) -> None:
        """定期检查循环（在后台线程中运行）"""
        while not self._stop_event.is_set():
            self.check_all_files()
            # 等待5分钟或直到停止事件被设置
            self._stop_event.wait(self._check_interval)
    
    def check_all_files(self) -> List[int]:
        """检查所有已记录文件的存在性
        
        逻辑：
        1. 压缩包存在，解压文件夹不存在 → 状态改为 pending（未解压）
        2. 压缩包不存在，解压文件夹存在 → 状态改为 archive_deleted（包已删除）
        3. 压缩包不存在，解压文件夹也不存在 → 标记为 deleted（已删除）
        
        Returns:
            已删除文件的ID列表
        """
        deleted_ids = []
        updated_to_pending = []
        updated_to_archive_deleted = []
        updated_to_success = []
        
        # 获取所有记录
        all_records = self.db.get_all_records()
        
        for record in all_records:
            archive_exists = self.check_file(record.id)
            folder_exists = self._check_extracted_folder_exists(record)
            
            if archive_exists and not folder_exists:
                # 压缩包存在，解压文件夹不存在 → 改为未解压（可以重新解压）
                if record.status not in ['pending', 'extracting']:
                    self.db.update_status(record.id, 'pending', '压缩包存在，等待解压')
                    updated_to_pending.append(record.id)
            elif not archive_exists and folder_exists:
                # 压缩包不存在，解压文件夹存在 → 改为包已删除
                if record.status != 'archive_deleted':
                    self.db.update_status(record.id, 'archive_deleted', '压缩包已删除，但解压文件夹存在')
                    updated_to_archive_deleted.append(record.id)
            elif not archive_exists and not folder_exists:
                # 压缩包不存在，解压文件夹也不存在 → 标记为已删除
                if record.status != 'deleted':
                    self.mark_as_deleted(record.id)
                    deleted_ids.append(record.id)
            elif archive_exists and folder_exists:
                # 压缩包存在，解压文件夹也存在 → 改为解压成功
                if record.status in ['archive_deleted', 'deleted', 'pending']:
                    self.db.update_status(record.id, 'success', '压缩包和解压文件夹都存在')
                    updated_to_success.append(record.id)
        
        if updated_to_pending:
            print(f"检测到 {len(updated_to_pending)} 个文件未解压（可以重新解压）")
        if updated_to_archive_deleted:
            print(f"检测到 {len(updated_to_archive_deleted)} 个文件包已删除（但文件夹存在）")
        if updated_to_success:
            print(f"检测到 {len(updated_to_success)} 个文件已恢复（压缩包和解压文件夹都存在）")
        
        return deleted_ids
    
    def _is_recursive_extracted_file(self, record) -> bool:
        """判断是否为递归解压的文件
        
        Args:
            record: 文件记录
            
        Returns:
            是否为递归解压的文件
        """
        # 如果原始路径包含解压文件夹路径，说明是递归解压的文件
        if self.unpack_folder in record.original_path:
            return True
        
        # 如果文件名包含多层扩展名，可能是递归处理的结果
        # 例如：file.zip.png.zip 这种嵌套的文件名
        filename_lower = record.filename.lower()
        if filename_lower.count('.zip') > 1 or filename_lower.count('.rar') > 1:
            return True
        
        return False
    
    def check_file(self, record_id: int) -> bool:
        """检查单个文件是否存在
        
        Args:
            record_id: 记录ID
            
        Returns:
            压缩包文件是否存在（不考虑解压文件夹）
        """
        record = self.db.get_record_by_id(record_id)
        if not record:
            return False
        
        # 只检查压缩包文件是否存在，不考虑解压文件夹
        # 因为我们关心的是压缩包是否被手动删除
        archive_path = Path(record.original_path)
        archive_exists = archive_path.exists()
        
        return archive_exists
    
    def _check_extracted_folder_exists(self, record) -> bool:
        """检查解压文件夹是否存在
        
        Args:
            record: 文件记录
            
        Returns:
            解压文件夹是否存在
        """
        # 根据原始路径推断解压文件夹位置
        original_path = Path(record.original_path)
        
        # 获取不带扩展名的文件名作为文件夹名
        folder_name = original_path.stem
        
        # 解压文件夹应该在原始路径的同级目录
        folder_path = original_path.parent / folder_name
        
        # 如果找不到，尝试去掉最后一层扩展名（处理类似逃少.jpg.zip的情况）
        # 此时 original_path.stem 是逃少.jpg，但 Bandizip 会解压到逃少
        if not (folder_path.exists() and folder_path.is_dir()):
            # 去掉最后一层扩展名
            folder_name_without_last_ext = Path(folder_name).stem
            if folder_name_without_last_ext != folder_name:
                folder_path_alt = original_path.parent / folder_name_without_last_ext
                if folder_path_alt.exists() and folder_path_alt.is_dir():
                    return True
        
        return folder_path.exists() and folder_path.is_dir()
    
    def mark_as_deleted(self, record_id: int) -> None:
        """标记文件为已删除状态
        
        Args:
            record_id: 记录ID
        """
        self.db.update_status(record_id, 'deleted', '压缩包已被手动删除')
