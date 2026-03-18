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
        """删除文件（仅删除压缩包，保留解压文件夹）
        
        Args:
            record_id: 记录ID
            
        Returns:
            (成功状态, 消息)
        """
        # 获取文件记录
        record = self.db.get_record_by_id(record_id)
        if record is None:
            return False, "记录不存在"
        
        # 删除压缩包，保留解压文件夹
        success = self._delete_archive_by_original_path(record.original_path, record.filename)
        
        if success:
            # 标记记录为已删除
            self.db.update_status(record_id, 'deleted', '压缩包已被删除，解压文件夹已保留')
            return True, "压缩包删除成功，解压文件夹已保留"
        else:
            return False, "压缩包删除失败或文件不存在"
    
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
    
    def _delete_archive_by_original_path(self, original_path: str, filename: str) -> bool:
        """使用原始路径删除压缩包文件，保留解压文件夹
        
        Args:
            original_path: 文件的原始路径
            filename: 文件名
            
        Returns:
            是否成功删除
        """
        archive_path = Path(original_path)
        
        # 检查文件是否存在
        if archive_path.exists():
            try:
                if archive_path.is_file():
                    archive_path.unlink()
                    print(f"已删除压缩包: {archive_path}")
                    return True
                else:
                    print(f"路径不是文件: {archive_path}")
                    return False
            except Exception as e:
                print(f"删除压缩包失败: {e}")
                return False
        else:
            print(f"压缩包不存在: {archive_path}")
            # 如果文件不存在，也算删除成功（可能已经被手动删除了）
            return True
    
    def _delete_archive_and_folder(self, filename: str) -> bool:
        """删除压缩包文件，保留解压文件夹
        
        Args:
            filename: 文件名
            
        Returns:
            是否成功删除
        """
        unpack_path = Path(self.unpack_folder)
        archive_path = unpack_path / filename
        
        deleted_something = False
        
        # 只删除压缩包文件，不删除解压文件夹
        if archive_path.exists():
            try:
                if archive_path.is_file():
                    archive_path.unlink()
                    deleted_something = True
                    print(f"已删除压缩包: {archive_path}")
            except Exception as e:
                print(f"删除压缩包失败: {e}")
        
        # 不再删除解压文件夹，保留解压内容
        # 获取不带扩展名的文件名作为文件夹名
        folder_name = Path(filename).stem
        folder_path = unpack_path / folder_name
        
        if folder_path.exists():
            print(f"保留解压文件夹: {folder_path}")
        
        return deleted_something
