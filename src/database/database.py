"""数据库管理模块"""
import sqlite3
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from .models import FileRecord


class Database:
    """数据库管理器
    
    负责管理文件处理记录的持久化存储
    """
    
    def __init__(self, db_path: str):
        """初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        # 注册datetime适配器和转换器以避免Python 3.12+的弃用警告
        sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
        sqlite3.register_converter("TIMESTAMP", lambda b: datetime.fromisoformat(b.decode()))
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建file_records表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_path TEXT NOT NULL,
                moved_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,
                error_message TEXT,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status 
            ON file_records(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_moved_time 
            ON file_records(moved_time DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def get_record_by_filename(self, filename: str) -> Optional[FileRecord]:
        """根据文件名获取记录
        
        Args:
            filename: 文件名
            
        Returns:
            文件记录，如果不存在返回None
        """
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, original_path, moved_time, status, error_message, updated_time
            FROM file_records 
            WHERE filename = ?
            ORDER BY moved_time DESC
            LIMIT 1
        """, (filename,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return FileRecord(
                id=row[0],
                filename=row[1],
                original_path=row[2],
                moved_time=row[3],
                status=row[4],
                error_message=row[5],
                updated_time=row[6]
            )
        return None
    
    def create_record(self, filename: str, original_path: str) -> int:
        """创建新的文件记录
        
        Args:
            filename: 文件名
            original_path: 原始路径
            
        Returns:
            新创建记录的ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO file_records (filename, original_path, status, moved_time, updated_time)
            VALUES (?, ?, 'moved', ?, ?)
        """, (filename, original_path, datetime.now(), datetime.now()))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return record_id
    
    def update_filename(self, record_id: int, new_filename: str) -> None:
        """更新文件记录的文件名
        
        Args:
            record_id: 记录ID
            new_filename: 新的文件名
        """
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE file_records 
            SET filename = ?, updated_time = ?
            WHERE id = ?
        """, (new_filename, datetime.now(), record_id))
        
        conn.commit()
        conn.close()
    
    def update_original_path(self, record_id: int, new_original_path: str) -> None:
        """更新文件记录的原始路径
        
        Args:
            record_id: 记录ID
            new_original_path: 新的原始路径
        """
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE file_records 
            SET original_path = ?, updated_time = ?
            WHERE id = ?
        """, (new_original_path, datetime.now(), record_id))
        
        conn.commit()
        conn.close()
    
    def update_status(self, record_id: int, status: str, 
                     error_message: Optional[str] = None) -> None:
        """更新文件处理状态
        
        Args:
            record_id: 记录ID
            status: 新状态
            error_message: 错误信息（可选）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE file_records 
            SET status = ?, error_message = ?, updated_time = ?
            WHERE id = ?
        """, (status, error_message, datetime.now(), record_id))
        
        conn.commit()
        conn.close()
    
    def get_all_records(self) -> List[FileRecord]:
        """获取所有文件记录
        
        Returns:
            所有文件记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, original_path, moved_time, status, 
                   error_message, updated_time
            FROM file_records
            ORDER BY moved_time DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            records.append(FileRecord(
                id=row['id'],
                filename=row['filename'],
                original_path=row['original_path'],
                moved_time=datetime.fromisoformat(row['moved_time']),
                status=row['status'],
                error_message=row['error_message'],
                updated_time=datetime.fromisoformat(row['updated_time']) if row['updated_time'] else None
            ))
        
        return records
    
    def get_record_by_id(self, record_id: int) -> Optional[FileRecord]:
        """根据ID获取单个文件记录
        
        Args:
            record_id: 记录ID
            
        Returns:
            文件记录，如果不存在则返回None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, original_path, moved_time, status, 
                   error_message, updated_time
            FROM file_records
            WHERE id = ?
        """, (record_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return FileRecord(
                id=row['id'],
                filename=row['filename'],
                original_path=row['original_path'],
                moved_time=row['moved_time'],
                status=row['status'],
                error_message=row['error_message'],
                updated_time=row['updated_time']
            )
        
        return None
    
    def get_records_by_status(self, status: str) -> List[FileRecord]:
        """按状态筛选文件记录
        
        Args:
            status: 要筛选的状态
            
        Returns:
            匹配状态的文件记录列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, filename, original_path, moved_time, status, 
                   error_message, updated_time
            FROM file_records
            WHERE status = ?
            ORDER BY moved_time DESC
        """, (status,))
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            records.append(FileRecord(
                id=row['id'],
                filename=row['filename'],
                original_path=row['original_path'],
                moved_time=datetime.fromisoformat(row['moved_time']),
                status=row['status'],
                error_message=row['error_message'],
                updated_time=datetime.fromisoformat(row['updated_time']) if row['updated_time'] else None
            ))
        
        return records
    
    def delete_record(self, record_id: int) -> None:
        """删除文件记录
        
        Args:
            record_id: 要删除的记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM file_records
            WHERE id = ?
        """, (record_id,))
        
        conn.commit()
        conn.close()
    
    def get_file_path(self, record_id: int) -> Optional[str]:
        """获取文件在Unpack文件夹中的路径
        
        Args:
            record_id: 记录ID
            
        Returns:
            文件名，如果记录不存在则返回None
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT filename
            FROM file_records
            WHERE id = ?
        """, (record_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return row['filename']
        return None
