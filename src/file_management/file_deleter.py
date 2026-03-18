"""文件删除器模块"""
import os
import shutil
from typing import Tuple
from pathlib import Path

from ..database.database import Database


class FileDeleter:
    """文件删除器
    
    负责处理用户的文件删除和记录删除请求
    """
    
    def __init__(self, db: Database, unpack_folder: str):
        """初始化文件删除器
        
        Args:
            db: 数据库实例
            unpack_folder: Unpack文件夹路径
        """
        self.db = db
        self.unpack_folder = unpack_folder
    
    def delete_file(self, record_id: int) -> Tuple[bool, str]:
        """删除文件（压缩包和解压文件夹）
        
        Args:
            record_id: 记录ID
            
        Returns:
            (成功状态, 消息)
        """
        # 获取文件名
        filename = self.db.get_file_path(record_id)
        if filename is None:
            return False, "记录不存在"
        
        # 删除压缩包和解压文件夹
        success = self._delete_archive_and_folder(filename)
        
        if success:
            # 标记记录为已删除
            self.db.update_status(record_id, 'deleted', '文件已被删除')
            return True, "文件删除成功"
        else:
            return False, "文件删除失败或文件不存在"
    
    def delete_record(self, record_id: int, also_delete_file: bool = False) -> Tuple[bool, str]:
        """删除记录，可选同时删除文件
        
        Args:
            record_id: 记录ID
            also_delete_file: 是否同时删除文件
            
        Returns:
            (成功状态, 消息)
        """
        # 如果需要同时删除文件
        if also_delete_file:
            filename = self.db.get_file_path(record_id)
            if filename:
                self._delete_archive_and_folder(filename)
        
        # 从数据库删除记录
        try:
            self.db.delete_record(record_id)
            return True, "记录删除成功"
        except Exception as e:
            return False, f"记录删除失败: {str(e)}"
    
    def _delete_archive_and_folder(self, filename: str) -> bool:
        """删除压缩包文件和对应的解压文件夹
        
        Args:
            filename: 文件名
            
        Returns:
            是否成功删除
        """
        unpack_path = Path(self.unpack_folder)
        archive_path = unpack_path / filename
        
        # 获取不带扩展名的文件名作为文件夹名
        folder_name = Path(filename).stem
        folder_path = unpack_path / folder_name
        
        deleted_something = False
        
        # 删除压缩包文件
        if archive_path.exists():
            try:
                if archive_path.is_file():
                    archive_path.unlink()
                    deleted_something = True
            except Exception as e:
                print(f"删除压缩包失败: {e}")
        
        # 删除解压文件夹
        if folder_path.exists():
            try:
                if folder_path.is_dir():
                    shutil.rmtree(folder_path)
                    deleted_something = True
            except Exception as e:
                print(f"删除解压文件夹失败: {e}")
        
        return deleted_something
