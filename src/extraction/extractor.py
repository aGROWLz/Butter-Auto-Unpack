#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extractor - 解压引擎
使用7z命令行工具进行解压操作，支持密码尝试和分卷压缩包
"""

import os
import sys
import subprocess
from dataclasses import dataclass
from typing import List, Tuple, Optional

from ..log_manager import get_logger, log_file_operation, log_exception


@dataclass
class ExtractionResult:
    """解压结果数据类
    
    Attributes:
        success: 解压是否成功
        error_type: 错误类型 ('none', 'password', 'corrupted', 'incomplete_volume', 'other')
        error_message: 错误信息
        used_password: 使用的成功密码（可选）
    """
    success: bool
    error_type: str
    error_message: str
    used_password: Optional[str] = None


class Extractor:
    """解压引擎类
    
    使用打包的7z工具执行解压操作，支持密码尝试和分卷压缩包处理
    """
    
    def __init__(self, seven_zip_path: str = None):
        """初始化解压引擎
        
        Args:
            seven_zip_path: 7z可执行文件路径，如果为None则使用打包的7z
        """
        self.seven_zip_path = seven_zip_path or self.get_bundled_7z_path()
        self.logger = get_logger()
        self.logger.info(f"解压引擎初始化 - 7z路径: {self.seven_zip_path}")
    
    def get_bundled_7z_path(self) -> str:
        """获取打包的7za.exe路径
        
        Returns:
            7za.exe的完整路径
        """
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            base_path = sys._MEIPASS
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        return os.path.join(base_path, 'resources', '7za.exe')
    
    def check_7z_available(self) -> bool:
        """检查7z是否可用
        
        Returns:
            True如果7z可用，否则False
        """
        try:
            result = subprocess.run(
                [self.seven_zip_path],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            # 7z在没有参数时会返回非0，但会输出帮助信息
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False
    
    def test_archive(self, archive_path: str, passwords: List[str] = None) -> ExtractionResult:
        """测试文件是否为有效的压缩包（不实际解压）
        
        Args:
            archive_path: 压缩包路径
            passwords: 密码列表（可选）
        
        Returns:
            ExtractionResult: 测试结果
        """
        self.logger.debug(f"测试文件是否为压缩包: {archive_path}")
        
        try:
            # 首先尝试无密码测试
            cmd = [self.seven_zip_path, 't', archive_path, '-y']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                self.logger.debug(f"文件测试成功（无密码），确认为压缩包: {archive_path}")
                return ExtractionResult(
                    success=True,
                    error_type='none',
                    error_message=''
                )
            
            # 如果无密码测试失败，且提供了密码列表，则尝试使用密码
            if passwords and len(passwords) > 0:
                self.logger.debug(f"无密码测试失败，尝试使用密码测试: {archive_path}")
                
                for password in passwords:
                    cmd_with_password = [self.seven_zip_path, 't', archive_path, f'-p{password}', '-y']
                    
                    result = subprocess.run(
                        cmd_with_password,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    
                    if result.returncode == 0:
                        self.logger.debug(f"文件测试成功（密码: {password}），确认为压缩包: {archive_path}")
                        return ExtractionResult(
                            success=True,
                            error_type='none',
                            error_message=''
                        )
                
                self.logger.debug(f"所有密码测试失败，可能不是压缩包或密码错误: {archive_path}")
            else:
                self.logger.debug(f"文件测试失败，不是有效压缩包: {archive_path}")
            
            return ExtractionResult(
                success=False,
                error_type='not_archive',
                error_message=f"不是有效的压缩包或密码错误: {result.stderr}"
            )
        
        except subprocess.TimeoutExpired:
            return ExtractionResult(
                success=False,
                error_type='timeout',
                error_message='测试超时'
            )
        except Exception as e:
            return ExtractionResult(
                success=False,
                error_type='other',
                error_message=f'测试时发生错误: {str(e)}'
            )
    
    def extract(self, archive_path: str, output_dir: str, 
                passwords: List[str] = None) -> ExtractionResult:
        """解压文件，支持密码尝试和分卷压缩包
        
        Args:
            archive_path: 压缩包路径（对于分卷压缩包，应为起始卷路径）
            output_dir: 解压输出目录
            passwords: 密码列表（可选）
        
        Returns:
            ExtractionResult: 解压结果
        """
        self.logger.info(f"开始解压: {archive_path} -> {output_dir}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 首先尝试无密码解压
        self.logger.debug("尝试无密码解压")
        success, error_msg = self._try_extract_with_password(archive_path, output_dir, None)
        
        if success:
            self.logger.info(f"无密码解压成功: {archive_path}")
            log_file_operation("解压", archive_path, "成功", "无密码")
            return ExtractionResult(
                success=True,
                error_type='none',
                error_message='',
                used_password=None
            )
        
        # 检查是否需要密码
        if self._is_password_error(error_msg):
            self.logger.info("检测到需要密码，开始尝试密码列表")
            # 如果提供了密码列表，依次尝试
            if passwords:
                for i, password in enumerate(passwords, 1):
                    self.logger.debug(f"尝试密码 {i}/{len(passwords)}: {'*' * len(password)}")
                    success, error_msg = self._try_extract_with_password(
                        archive_path, output_dir, password
                    )
                    if success:
                        self.logger.info(f"密码解压成功: {archive_path} (密码: {'*' * len(password)})")
                        log_file_operation("解压", archive_path, "成功", f"使用密码: {'*' * len(password)}")
                        return ExtractionResult(
                            success=True,
                            error_type='none',
                            error_message='',
                            used_password=password
                        )
                
                # 所有密码都失败
                return ExtractionResult(
                    success=False,
                    error_type='password',
                    error_message='所有密码尝试失败',
                    used_password=None
                )
            else:
                # 需要密码但没有提供密码列表
                return ExtractionResult(
                    success=False,
                    error_type='password',
                    error_message='需要密码但未提供密码列表',
                    used_password=None
                )
        
        # 解析其他错误类型
        error_type = self._parse_error(error_msg)
        return ExtractionResult(
            success=False,
            error_type=error_type,
            error_message=error_msg,
            used_password=None
        )
    
    def _try_extract_with_password(self, archive_path: str, 
                                   output_dir: str, password: str = None) -> Tuple[bool, str]:
        """尝试使用指定密码解压
        
        Args:
            archive_path: 压缩包路径
            output_dir: 输出目录
            password: 密码（可选）
        
        Returns:
            (是否成功, 错误信息)
        """
        # 构建7z命令
        cmd = [
            self.seven_zip_path,
            'x',  # 解压命令
            archive_path,
            f'-o{output_dir}',  # 输出目录
            '-y'  # 自动确认所有提示
        ]
        
        # 总是添加密码参数，即使是空密码，避免7z等待输入
        if password:
            cmd.append(f'-p{password}')
        else:
            cmd.append('-p')  # 空密码
        
        process = None
        try:
            self.logger.info(f"准备执行7z命令: {' '.join(cmd[:4])} -p*** -y")  # 不记录密码
            self.logger.info(f"creationflags: {subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0}")
            
            # 使用 Popen 以便更好地控制进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,  # 提供 stdin 避免等待输入
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # 关闭 stdin，确保不会等待输入
            if process.stdin:
                process.stdin.close()
            
            # 等待进程完成，设置超时
            try:
                stdout, stderr = process.communicate(timeout=300)
                returncode = process.returncode
                
                self.logger.info(f"7z命令执行完成，返回码: {returncode}")
                
                # 7z返回0表示成功
                if returncode == 0:
                    return True, ''
                else:
                    # 返回stderr和stdout的组合
                    error_msg = stderr + stdout
                    return False, error_msg
                    
            except subprocess.TimeoutExpired:
                self.logger.error("7z进程超时，强制终止")
                # 超时，强制终止进程
                process.kill()
                process.wait()  # 等待进程真正终止
                return False, '解压超时'
                
        except Exception as e:
            self.logger.error(f"7z进程异常: {e}", exc_info=True)
            # 确保进程被终止
            if process and process.poll() is None:
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
            return False, f'解压异常: {str(e)}'
        
        finally:
            # 确保进程被清理
            if process and process.poll() is None:
                try:
                    self.logger.warning("7z进程仍在运行，强制终止")
                    process.kill()
                    process.wait()
                except Exception as e:
                    self.logger.error(f"无法终止7z进程: {e}")
    
    def _is_password_error(self, error_msg: str) -> bool:
        """判断错误信息是否表示需要密码
        
        Args:
            error_msg: 错误信息
        
        Returns:
            True如果是密码错误
        """
        password_keywords = [
            'wrong password',
            'encrypted',
            'password',
            'can not open encrypted archive',
            'wrong password'
        ]
        
        error_lower = error_msg.lower()
        return any(keyword in error_lower for keyword in password_keywords)
    
    def _parse_error(self, stderr: str) -> str:
        """解析7z错误信息，判断错误类型
        
        Args:
            stderr: 7z的错误输出
        
        Returns:
            错误类型: 'password', 'corrupted', 'incomplete_volume', 'other'
        """
        stderr_lower = stderr.lower()
        
        # 检查密码错误
        if self._is_password_error(stderr):
            return 'password'
        
        # 检查文件损坏
        corrupted_keywords = [
            'crc failed',
            'data error',
            'unexpected end of archive',
            'headers error',
            'is not archive'
        ]
        if any(keyword in stderr_lower for keyword in corrupted_keywords):
            return 'corrupted'
        
        # 检查分卷不完整
        volume_keywords = [
            'can not open',
            'missing volume',
            'cannot find volume',
            'next volume'
        ]
        if any(keyword in stderr_lower for keyword in volume_keywords):
            return 'incomplete_volume'
        
        # 其他错误
        return 'other'
    
    def verify_volume_completeness(self, leader_path: str) -> Tuple[bool, List[str]]:
        """验证分卷文件完整性
        
        Args:
            leader_path: 起始卷路径
        
        Returns:
            (是否完整, 缺失的分卷列表)
        """
        missing_volumes = []
        
        # 获取文件目录和基础名称
        directory = os.path.dirname(leader_path)
        filename = os.path.basename(leader_path)
        
        # 检测分卷类型
        if '.7z.001' in filename:
            # 7z分卷格式: file.7z.001, file.7z.002, ...
            base_name = filename.replace('.001', '')
            volume_num = 2
            while True:
                volume_path = os.path.join(directory, f'{base_name}.{volume_num:03d}')
                if os.path.exists(volume_path):
                    volume_num += 1
                else:
                    # 检查是否还有更多分卷（可能中间缺失）
                    # 尝试检查接下来的5个分卷
                    found_more = False
                    for i in range(volume_num + 1, volume_num + 6):
                        test_path = os.path.join(directory, f'{base_name}.{i:03d}')
                        if os.path.exists(test_path):
                            # 发现缺失的分卷
                            missing_volumes.append(f'{base_name}.{volume_num:03d}')
                            found_more = True
                            break
                    if not found_more:
                        break
                    volume_num += 1
        
        elif '.zip.001' in filename:
            # Zip编号分卷格式: file.zip.001, file.zip.002, ...
            base_name = filename.replace('.001', '')
            volume_num = 2
            while True:
                volume_path = os.path.join(directory, f'{base_name}.{volume_num:03d}')
                if os.path.exists(volume_path):
                    volume_num += 1
                else:
                    # 检查是否还有更多分卷（可能中间缺失）
                    found_more = False
                    for i in range(volume_num + 1, volume_num + 6):
                        test_path = os.path.join(directory, f'{base_name}.{i:03d}')
                        if os.path.exists(test_path):
                            missing_volumes.append(f'{base_name}.{volume_num:03d}')
                            found_more = True
                            break
                    if not found_more:
                        break
                    volume_num += 1
        
        elif 'part1.rar' in filename.lower() or 'part01.rar' in filename.lower():
            # RAR分卷格式: file.part1.rar, file.part2.rar, ...
            if 'part01.rar' in filename.lower():
                base_name = filename.lower().replace('part01.rar', '')
                format_str = 'part{:02d}.rar'
            else:
                base_name = filename.lower().replace('part1.rar', '')
                format_str = 'part{}.rar'
            
            volume_num = 2
            while True:
                volume_name = base_name + format_str.format(volume_num)
                volume_path = os.path.join(directory, volume_name)
                if os.path.exists(volume_path):
                    volume_num += 1
                else:
                    # 检查是否还有更多分卷
                    found_more = False
                    for i in range(volume_num + 1, volume_num + 6):
                        test_name = base_name + format_str.format(i)
                        test_path = os.path.join(directory, test_name)
                        if os.path.exists(test_path):
                            missing_volumes.append(volume_name)
                            found_more = True
                            break
                    if not found_more:
                        break
                    volume_num += 1
        
        elif filename.endswith('.zip'):
            # Zip分卷格式: file.zip, file.z01, file.z02, ...
            base_name = filename[:-4]  # 移除.zip
            volume_num = 1
            while True:
                volume_path = os.path.join(directory, f'{base_name}.z{volume_num:02d}')
                if os.path.exists(volume_path):
                    volume_num += 1
                else:
                    # 检查是否还有更多分卷
                    found_more = False
                    for i in range(volume_num + 1, volume_num + 6):
                        test_path = os.path.join(directory, f'{base_name}.z{i:02d}')
                        if os.path.exists(test_path):
                            missing_volumes.append(f'{base_name}.z{volume_num:02d}')
                            found_more = True
                            break
                    if not found_more:
                        break
                    volume_num += 1
        
        # 如果有缺失的分卷，返回False
        is_complete = len(missing_volumes) == 0
        return is_complete, missing_volumes
