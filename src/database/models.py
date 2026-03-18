"""数据模型定义"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FileRecord:
    """文件处理记录数据类
    
    Attributes:
        id: 记录ID
        filename: 文件名
        original_path: 原始路径
        moved_time: 移动时间
        status: 处理状态 ('moved', 'extracting', 'success', 'failed', 
                        'password_error', 'corrupted', 'recursive_processing', 'deleted')
        error_message: 错误信息（可选）
        updated_time: 更新时间（可选）
    """
    id: int
    filename: str
    original_path: str
    moved_time: datetime
    status: str
    error_message: Optional[str] = None
    updated_time: Optional[datetime] = None
