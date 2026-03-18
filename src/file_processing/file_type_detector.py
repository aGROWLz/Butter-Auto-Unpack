"""
文件类型识别器模块
用于识别压缩包、图片和分卷压缩包文件
"""
import os
import re
from typing import Tuple


class FileTypeDetector:
    """文件类型识别器"""
    
    ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    
    @staticmethod
    def is_archive(file_path: str) -> bool:
        """
        判断是否为压缩包
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为压缩包
        """
        _, ext = os.path.splitext(file_path.lower())
        return ext in FileTypeDetector.ARCHIVE_EXTENSIONS
    
    @staticmethod
    def is_image(file_path: str) -> bool:
        """
        判断是否为图片
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为图片
        """
        _, ext = os.path.splitext(file_path.lower())
        return ext in FileTypeDetector.IMAGE_EXTENSIONS
    
    @staticmethod
    def is_video(file_path: str) -> bool:
        """
        判断是否为视频文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为视频文件
        """
        _, ext = os.path.splitext(file_path.lower())
        return ext in FileTypeDetector.VIDEO_EXTENSIONS
    
    @staticmethod
    def get_file_type(file_path: str) -> str:
        """
        获取文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件类型 ('archive', 'image', 'video', 'multi_volume', 'volume_part', 'unknown')
        """
        # 首先检查是否为分卷压缩包
        if FileTypeDetector.is_leader_volume(file_path):
            return 'multi_volume'
        
        if FileTypeDetector.is_volume_part(file_path):
            return 'volume_part'
        
        # 检查普通压缩包
        if FileTypeDetector.is_archive(file_path):
            return 'archive'
        
        # 检查图片
        if FileTypeDetector.is_image(file_path):
            return 'image'
        
        # 检查视频
        if FileTypeDetector.is_video(file_path):
            return 'video'
        
        return 'unknown'
    
    @staticmethod
    def is_leader_volume(file_path: str) -> bool:
        """
        判断是否为分卷压缩包的起始卷
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为起始卷
        """
        volume_type = FileTypeDetector.detect_volume_type(file_path)
        return volume_type != 'none'
    
    @staticmethod
    def is_volume_part(file_path: str) -> bool:
        """
        判断是否为分卷压缩包的非起始卷
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为非起始卷
        """
        file_lower = file_path.lower()
        
        # 检查7z非起始卷 (.002, .003, ...)
        if re.search(r'\.00[2-9]$', file_lower) or re.search(r'\.0[1-9][0-9]$', file_lower):
            return True
        
        # 检查zip编号分卷非起始卷 (.zip.002, .zip.003, ...)
        if re.search(r'\.zip\.00[2-9]$', file_lower) or re.search(r'\.zip\.0[1-9][0-9]$', file_lower):
            return True
        
        # 检查RAR非起始卷 (part2.rar, part02.rar, .part2.rar)
        if re.search(r'(part0?[2-9]|part[1-9][0-9])\.rar$', file_lower):
            return True
        
        # 检查Zip非起始卷 (.z01, .z02, .z03, ...)
        if re.search(r'\.z0[1-9]$', file_lower) or re.search(r'\.z[1-9][0-9]$', file_lower):
            return True
        
        # 检查伪装非起始卷 (.002.xxx, .003.xxx, ...)
        # 排除常见的非压缩文件扩展名
        excluded_extensions = {'.dll', '.exe', '.sys', '.drv'}
        match = re.search(r'\.00[2-9]\.(\w+)$', file_lower) or re.search(r'\.0[1-9][0-9]\.(\w+)$', file_lower)
        if match:
            ext = '.' + match.group(1)
            if ext not in excluded_extensions:
                return True
        
        return False
    
    @staticmethod
    def detect_volume_type(file_path: str) -> str:
        """
        检测分卷类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 分卷类型 ('7z', 'rar', 'zip', 'zip_numbered', 'disguised', 'none')
        """
        file_lower = file_path.lower()
        
        # 检查伪装分卷 (.001.xxx) - 优先检查，因为它可能包含.001
        # 排除常见的非压缩文件扩展名
        excluded_extensions = {'.dll', '.exe', '.sys', '.drv'}
        if re.search(r'\.001\.[^.]+$', file_lower):
            # 获取伪装后的扩展名
            match = re.search(r'\.001\.(\w+)$', file_lower)
            if match:
                ext = '.' + match.group(1)
                if ext not in excluded_extensions:
                    return 'disguised'
            else:
                return 'disguised'
        
        # 检查zip编号分卷 (.zip.001)
        if re.search(r'\.zip\.001$', file_lower):
            return 'zip_numbered'
        
        # 检查7z分卷 (.001)
        if file_lower.endswith('.001'):
            return '7z'
        
        # 检查RAR分卷 (part1.rar, part01.rar, .part1.rar)
        if re.search(r'(part0?1|part1)\.rar$', file_lower):
            return 'rar'
        
        # 检查Zip分卷 (.zip且同目录存在.z01)
        if file_lower.endswith('.zip'):
            # 检查同目录是否存在.z01文件
            dir_path = os.path.dirname(file_path)
            base_name = os.path.splitext(file_path)[0]
            z01_path = base_name + '.z01'
            
            if os.path.exists(z01_path):
                return 'zip'
        
        return 'none'
