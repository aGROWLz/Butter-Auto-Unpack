#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LZ4 Extractor - LZ4解压引擎
使用lz4.exe命令行工具解压.lz4文件
"""

import os
import sys
import subprocess
import shutil
from typing import Tuple

from ..log_manager import get_logger


class LZ4Extractor:
    """LZ4解压引擎类
    
    使用lz4.exe执行解压操作，特点：
    - 只支持.lz4格式
    - 不需要密码
    - 直接解压内容到输出目录（不创建子文件夹）
    """
    
    def __init__(self, lz4_path: str = None):
        """初始化LZ4解压引擎
        
        Args:
            lz4_path: lz4.exe可执行文件路径，如果为None则使用打包的lz4
        """
        self.lz4_path = lz4_path or self.get_bundled_lz4_path()
        self.logger = get_logger()
        self.logger.info(f"LZ4解压引擎初始化 - 路径: {self.lz4_path}")
    
    def get_bundled_lz4_path(self) -> str:
        """获取打包的lz4.exe路径
        
        Returns:
            lz4.exe的完整路径
        """
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            base_path = sys._MEIPASS
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        return os.path.join(base_path, 'resources', 'lz4', 'lz4.exe')
    
    def check_lz4_available(self) -> bool:
        """检查lz4是否可用
        
        Returns:
            True如果lz4可用，否则False
        """
        try:
            result = subprocess.run(
                [self.lz4_path, '--version'],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.returncode == 0 or b'LZ4' in result.stdout or b'LZ4' in result.stderr
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False
    
    def is_lz4_file(self, file_path: str) -> bool:
        """检查文件是否为.lz4格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为.lz4文件
        """
        return file_path.lower().endswith('.lz4')
    
    def extract(self, archive_path: str, output_dir: str) -> Tuple[bool, str]:
        """解压LZ4文件
        
        LZ4解压特点：
        - 直接解压内容到输出目录，不创建子文件夹
        - 不需要密码
        - 输出文件名默认去掉.lz4后缀
        
        Args:
            archive_path: LZ4文件路径
            output_dir: 输出目录
            
        Returns:
            (是否成功, 错误信息)
        """
        if not self.is_lz4_file(archive_path):
            return False, '不是LZ4文件'
        
        if not os.path.exists(self.lz4_path):
            return False, f'LZ4工具不存在: {self.lz4_path}'
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取输出文件名（去掉.lz4后缀）
        base_name = os.path.basename(archive_path)
        if base_name.lower().endswith('.lz4'):
            output_name = base_name[:-4]  # 去掉.lz4
        else:
            output_name = base_name + '.out'
        
        output_path = os.path.join(output_dir, output_name)
        
        self.logger.info(f"开始解压LZ4文件: {archive_path} -> {output_path}")
        
        try:
            # 构建命令: lz4 -d input.lz4 output
            # -d 表示解压模式
            cmd = [
                self.lz4_path,
                '-d',  # 解压模式
                archive_path,
                output_path
            ]
            
            self.logger.info(f"执行LZ4命令: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            stdout, stderr = process.communicate(timeout=300)
            
            # 解码输出
            stdout_str = stdout.decode('utf-8', errors='ignore') if stdout else ''
            stderr_str = stderr.decode('utf-8', errors='ignore') if stderr else ''
            
            self.logger.info(f"LZ4返回码: {process.returncode}")
            if stdout_str:
                self.logger.info(f"LZ4 stdout: {stdout_str}")
            if stderr_str:
                self.logger.info(f"LZ4 stderr: {stderr_str}")
            
            # LZ4返回0表示成功
            if process.returncode == 0:
                # 检查输出文件是否创建成功
                if os.path.exists(output_path):
                    self.logger.info(f"LZ4解压成功: {output_path}")
                    return True, ''
                else:
                    return False, '解压后输出文件不存在'
            else:
                error_msg = stderr_str.strip() or stdout_str.strip() or f'返回码: {process.returncode}'
                return False, f'LZ4解压失败: {error_msg}'
                
        except subprocess.TimeoutExpired:
            self.logger.error("LZ4解压超时")
            if process.poll() is None:
                process.kill()
            return False, '解压超时'
        except Exception as e:
            self.logger.error(f"LZ4解压异常: {e}", exc_info=True)
            return False, f'解压异常: {str(e)}'
    
    def extract_with_fallback(self, archive_path: str, output_dir: str, 
                              passwords: list = None) -> Tuple[bool, str, str]:
        """解压LZ4文件（兼容接口，忽略密码参数）
        
        Args:
            archive_path: LZ4文件路径
            output_dir: 输出目录
            passwords: 密码列表（LZ4不需要，忽略此参数）
            
        Returns:
            (是否成功, 错误类型, 错误信息)
        """
        success, error_msg = self.extract(archive_path, output_dir)
        
        if success:
            return True, 'none', ''
        else:
            return False, 'other', error_msg
