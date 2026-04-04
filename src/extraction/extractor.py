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
    
    使用打包的7z工具或Bandizip执行解压操作，支持密码尝试和分卷压缩包处理
    """
    
    def __init__(self, seven_zip_path: str = None, bandizip_path: str = None, use_bandizip: bool = False):
        """初始化解压引擎
        
        Args:
            seven_zip_path: 7z可执行文件路径，如果为None则使用打包的7z
            bandizip_path: Bandizip可执行文件路径，如果为None则使用打包的bz.exe
            use_bandizip: 是否优先使用Bandizip
        """
        self.seven_zip_path = seven_zip_path or self.get_bundled_7z_path()
        self.bandizip_path = bandizip_path or self.get_bundled_bandizip_path()
        self.use_bandizip = use_bandizip
        self.logger = get_logger()
        self.logger.info(f"解压引擎初始化 - 7z路径: {self.seven_zip_path}, Bandizip路径: {self.bandizip_path}, 使用Bandizip: {use_bandizip}")
    
    def get_bundled_7z_path(self) -> str:
        """获取打包的7z.exe路径
        
        Returns:
            7z.exe的完整路径（完整版，支持RAR格式）
        """
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            base_path = sys._MEIPASS
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 优先使用完整版7z.exe（支持RAR格式），如果不存在则回退到7za.exe
        seven_z_path = os.path.join(base_path, 'resources', '7z.exe')
        if os.path.exists(seven_z_path):
            return seven_z_path
        
        # 回退到精简版7za.exe
        return os.path.join(base_path, 'resources', '7za.exe')
    
    def get_bundled_bandizip_path(self) -> str:
        """获取打包的Bandizip路径
        
        Returns:
            bz.exe的完整路径
        """
        if getattr(sys, 'frozen', False):
            # 打包后的exe环境
            base_path = sys._MEIPASS
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        return os.path.join(base_path, 'resources', 'bandizip', 'bz.exe')
    
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
    
    def check_bandizip_available(self) -> bool:
        """检查Bandizip是否可用
        
        Returns:
            True如果Bandizip可用，否则False
        """
        try:
            result = subprocess.run(
                [self.bandizip_path],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            # Bandizip在没有参数时会返回非0，但会输出帮助信息
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
        self.logger.info(f"测试文件是否为压缩包: {archive_path}")

        try:
            # 首先尝试无密码测试（使用空密码参数避免等待输入）
            cmd = [self.seven_zip_path, 't', '-t*', archive_path, '-p', '-y']

            self.logger.info(f"执行无密码测试: {' '.join(cmd[:3])} -t* -p -y")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # 限制日志输出长度，避免大输出占用内存
            max_log_length = 1000
            if result.stdout:
                stdout_preview = result.stdout[:max_log_length] + ("..." if len(result.stdout) > max_log_length else "")
                self.logger.info(f"7z stdout:\n{stdout_preview}")
            if result.stderr:
                stderr_preview = result.stderr[:max_log_length] + ("..." if len(result.stderr) > max_log_length else "")
                self.logger.info(f"7z stderr:\n{stderr_preview}")

            if result.returncode == 0:
                self.logger.info(f"文件测试成功（无密码），确认为压缩包: {archive_path}")
                return ExtractionResult(
                    success=True,
                    error_type='none',
                    error_message=''
                )

            self.logger.info(f"无密码测试失败，返回码: {result.returncode}")

            # 如果无密码测试失败，且提供了密码列表，则尝试使用密码
            if passwords and len(passwords) > 0:
                self.logger.info(f"开始尝试密码列表，共 {len(passwords)} 个密码")

                for i, password in enumerate(passwords, 1):
                    self.logger.info(f"尝试密码 {i}/{len(passwords)}: {'*' * len(password)}")
                    cmd_with_password = [self.seven_zip_path, 't', '-t*', archive_path, f'-p{password}', '-y']

                    result = subprocess.run(
                        cmd_with_password,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )

                    # 限制日志输出长度
                    if result.stdout:
                        stdout_preview = result.stdout[:max_log_length] + ("..." if len(result.stdout) > max_log_length else "")
                        self.logger.info(f"7z stdout (密码 {i}):\n{stdout_preview}")
                    if result.stderr:
                        stderr_preview = result.stderr[:max_log_length] + ("..." if len(result.stderr) > max_log_length else "")
                        self.logger.info(f"7z stderr (密码 {i}):\n{stderr_preview}")

                    if result.returncode == 0:
                        self.logger.info(f"文件测试成功（密码: {'*' * len(password)}），确认为压缩包: {archive_path}")
                        return ExtractionResult(
                            success=True,
                            error_type='none',
                            error_message=''
                        )
                    else:
                        self.logger.info(f"密码 {i} 失败，返回码: {result.returncode}")

                self.logger.info(f"所有密码测试失败: {archive_path}")
            else:
                self.logger.info(f"未提供密码列表，测试结束")

            return ExtractionResult(
                success=False,
                error_type='not_archive',
                error_message=f"不是有效的压缩包或密码错误: {result.stderr[:500] if result.stderr else '未知错误'}"
            )

        except subprocess.TimeoutExpired:
            self.logger.error(f"测试超时: {archive_path}")
            return ExtractionResult(
                success=False,
                error_type='timeout',
                error_message='测试超时'
            )
        except Exception as e:
            self.logger.error(f"测试异常: {archive_path}, 错误: {e}", exc_info=True)
            return ExtractionResult(
                success=False,
                error_type='other',
                error_message=f'测试时发生错误: {str(e)}'
            )
    
    # 常见的压缩包扩展名列表（用于自动切换尝试，只保留Windows常用格式）
    ARCHIVE_EXTENSIONS = ['.zip', '.rar', '.7z']
    
    def _try_extract_with_extensions_and_passwords(self, archive_path: str, output_dir: str, 
                                                    passwords: List[str] = None) -> Tuple[bool, str, bool]:
        """尝试使用不同的扩展名和密码组合解压
        
        逻辑：
        1. 对于每个扩展名（包括原始扩展名）：
           - 先尝试无密码
           - 如果需要密码，尝试所有密码
           - 如果都失败，切换到下一个扩展名
        
        Args:
            archive_path: 原始压缩包路径
            output_dir: 输出目录
            passwords: 密码列表（可选）
        
        Returns:
            (是否成功, 错误信息, 是否需要密码)
        """
        import shutil
        
        # 获取文件基础名（去掉最后一个扩展名）和目录
        file_dir = os.path.dirname(archive_path)
        file_name = os.path.basename(archive_path)
        base_name = os.path.splitext(file_name)[0]
        current_ext = os.path.splitext(file_name)[1].lower()
        
        # 构建要尝试的扩展名列表（原始扩展名放第一个）
        extensions_to_try = [current_ext] if current_ext else []
        for ext in self.ARCHIVE_EXTENSIONS:
            if ext.lower() != current_ext:
                extensions_to_try.append(ext)
        
        original_path = archive_path
        current_path = archive_path
        
        for ext in extensions_to_try:
            # 构建当前尝试的文件路径
            if ext == current_ext:
                # 第一次使用原始路径
                try_path = original_path
                self.logger.info(f"尝试使用原始扩展名解压: {try_path}")
            else:
                # 切换到新扩展名
                new_name = base_name + ext
                new_path = os.path.join(file_dir, new_name)
                
                # 如果目标文件已存在，跳过
                if os.path.exists(new_path):
                    self.logger.debug(f"目标文件已存在，跳过: {new_path}")
                    continue
                
                try:
                    # 重命名文件
                    shutil.move(current_path, new_path)
                    self.logger.info(f"重命名文件尝试解压: {os.path.basename(current_path)} -> {new_name}")
                    try_path = new_path
                    current_path = new_path
                except Exception as e:
                    self.logger.error(f"重命名文件时出错: {e}")
                    continue
            
            # 步骤1：尝试无密码解压
            self.logger.debug(f"尝试无密码解压: {try_path}")
            success, error_msg = self._try_extract_with_bandizip(try_path, output_dir, None)
            
            if success:
                self.logger.info(f"无密码解压成功: {try_path}")
                return True, '', False
            
            # 检查是否需要密码
            self.logger.debug(f"检查错误信息是否为密码错误: '{error_msg}'")
            if self._is_password_error(error_msg):
                self.logger.info(f"检测到需要密码: {try_path}")
                
                # 步骤2：尝试所有密码
                if passwords:
                    for i, password in enumerate(passwords, 1):
                        self.logger.debug(f"尝试密码 {i}/{len(passwords)}: {'*' * len(password)}")
                        success, error_msg = self._try_extract_with_bandizip(try_path, output_dir, password)
                        
                        if success:
                            self.logger.info(f"密码解压成功: {try_path}")
                            return True, '', False
                    
                    self.logger.info(f"所有密码都失败: {try_path}")
                else:
                    self.logger.info(f"需要密码但没有提供密码列表: {try_path}")
                    # 如果当前是原始文件，返回需要密码
                    if ext == current_ext:
                        return False, '需要密码', True
            
            # 当前扩展名失败，如果是重命名的文件，恢复原文件名
            if ext != current_ext and os.path.exists(try_path):
                try:
                    shutil.move(try_path, original_path)
                    current_path = original_path
                    self.logger.debug(f"扩展名 {ext} 失败，恢复原文件名")
                except:
                    pass
        
        # 所有扩展名都失败了
        return False, '所有扩展名和密码组合都尝试失败', False
    
    def extract(self, archive_path: str, output_dir: str, 
                passwords: List[str] = None,
                create_subfolder: bool = True) -> ExtractionResult:
        """解压文件，支持密码尝试和分卷压缩包，自动尝试多种扩展名
        
        Args:
            archive_path: 压缩包路径（对于分卷压缩包，应为起始卷路径）
            output_dir: 解压输出目录
            passwords: 密码列表（可选）
            create_subfolder: 是否创建以压缩包命名的子文件夹（默认为True，用于递归解压）
        
        Returns:
            ExtractionResult: 解压结果
        """
        # 检查是否为LZ4文件，如果是则使用LZ4解压引擎
        if archive_path.lower().endswith('.lz4'):
            return self._extract_lz4(archive_path, output_dir, create_subfolder)
        
        # 获取压缩包文件名（不含扩展名）
        archive_name = os.path.splitext(os.path.basename(archive_path))[0]
        
        # 如果启用子文件夹，则解压到以压缩包命名的子文件夹中
        if create_subfolder:
            actual_output_dir = os.path.join(output_dir, archive_name)
        else:
            actual_output_dir = output_dir
        
        self.logger.info(f"开始解压: {archive_path} -> {actual_output_dir}")
        
        # 确保输出目录存在
        os.makedirs(actual_output_dir, exist_ok=True)
        
        # 使用新的方法：自动尝试扩展名和密码组合
        self.logger.debug("开始尝试解压（自动尝试扩展名和密码组合）")
        success, error_msg, needs_password = self._try_extract_with_extensions_and_passwords(
            archive_path, actual_output_dir, passwords
        )
        
        if success:
            self.logger.info(f"解压成功: {archive_path}")
            log_file_operation("解压", archive_path, "成功", "解压完成")
            return ExtractionResult(
                success=True,
                error_type='none',
                error_message='',
                used_password=None
            )
        
        # 处理失败情况
        if needs_password and not passwords:
            # 需要密码但没有提供密码列表
            return ExtractionResult(
                success=False,
                error_type='password',
                error_message='需要密码但未提供密码列表',
                used_password=None
            )
        elif needs_password and passwords:
            # 提供了密码但所有密码都失败
            return ExtractionResult(
                success=False,
                error_type='password',
                error_message='所有密码尝试失败',
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
    
    def _extract_lz4(self, archive_path: str, output_dir: str,
                     create_subfolder: bool = True) -> ExtractionResult:
        """使用LZ4引擎解压LZ4文件
        
        LZ4特点：
        - 只支持.lz4格式
        - 不需要密码
        - 直接解压内容到输出目录（不创建子文件夹）
        
        Args:
            archive_path: LZ4文件路径
            output_dir: 解压输出目录
            create_subfolder: 是否创建子文件夹
            
        Returns:
            ExtractionResult: 解压结果
        """
        from .lz4_extractor import LZ4Extractor
        
        # 获取文件名（去掉.lz4后缀作为输出子文件夹名）
        base_name = os.path.basename(archive_path)
        if base_name.lower().endswith('.lz4'):
            folder_name = base_name[:-4]  # 去掉.lz4
        else:
            folder_name = base_name
        
        # LZ4直接解压到输出目录（不创建子文件夹）
        # 但如果是递归解压需要，可以创建子文件夹
        if create_subfolder:
            actual_output_dir = os.path.join(output_dir, folder_name)
        else:
            actual_output_dir = output_dir
        
        self.logger.info(f"使用LZ4引擎解压: {archive_path} -> {actual_output_dir}")
        
        # 创建LZ4解压器并解压
        lz4_extractor = LZ4Extractor()
        success, error_msg = lz4_extractor.extract(archive_path, actual_output_dir)
        
        if success:
            self.logger.info(f"LZ4解压成功: {archive_path}")
            return ExtractionResult(
                success=True,
                error_type='none',
                error_message='',
                used_password=None
            )
        else:
            self.logger.error(f"LZ4解压失败: {error_msg}")
            return ExtractionResult(
                success=False,
                error_type='other',
                error_message=error_msg,
                used_password=None
            )
    
    def _try_extract_with_bandizip(self, archive_path: str,
                                   output_dir: str, password: str = None) -> Tuple[bool, str]:
        """尝试使用Bandizip解压

        Args:
            archive_path: 压缩包路径
            output_dir: 输出目录
            password: 密码（可选）

        Returns:
            (是否成功, 错误信息)
        """
        # 构建Bandizip命令
        # bz x -o:"output_dir" -p:"password" archive_path
        cmd = [
            self.bandizip_path,
            'x',  # 解压命令
            f'-o:{output_dir}',  # 输出目录
        ]

        # 添加密码参数
        if password:
            cmd.append(f'-p:{password}')
            self.logger.info(f"准备执行Bandizip命令（使用密码）: {cmd[0]} x -o:{output_dir} -p:***")
        else:
            self.logger.info(f"准备执行Bandizip命令（无密码）: {cmd[0]} x -o:{output_dir}")

        # 添加压缩包路径（必须是最后一个参数）
        cmd.append(archive_path)

        process = None
        try:
            # 使用 DEVNULL 丢弃输出，避免内存占用
            # 大文件解压时输出可能非常大，会导致内存泄漏
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,  # 丢弃标准输出
                stderr=subprocess.PIPE,     # 只保留错误输出
                stdin=subprocess.DEVNULL,   # 关闭 stdin
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            self.logger.info(f"Bandizip进程已启动，PID: {process.pid}")

            # 使用 wait 等待进程完成，设置超时
            try:
                returncode = process.wait(timeout=300)

                self.logger.info(f"Bandizip命令执行完成，返回码: {returncode}")

                # 只读取错误输出（通常较小）
                stderr_output = ""
                if process.stderr:
                    try:
                        stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                        if stderr_output:
                            self.logger.info(f"Bandizip stderr:\n{stderr_output}")
                    except Exception as e:
                        self.logger.debug(f"读取 stderr 失败: {e}")

                # 检测密码提示（在错误输出中）
                if 'Enter password' in stderr_output or 'Invalid password' in stderr_output:
                    self.logger.info("检测到密码提示")
                    return False, '需要密码'

                # Bandizip返回0表示成功
                if returncode == 0:
                    return True, ''
                else:
                    # 检测密码相关错误
                    # 1. 检查错误输出中是否包含密码关键词
                    # 2. 返回码2或14通常表示需要密码
                    # 3. 其他非零返回码且没有错误输出时，也可能是需要密码
                    stderr_stripped = stderr_output.strip()
                    if stderr_stripped:
                        # 有错误输出，检查是否包含密码关键词
                        error_lower = stderr_stripped.lower()
                        password_keywords = ['password', 'encrypted', 'enter password', 'invalid password', 'wrong password']
                        if any(keyword in error_lower for keyword in password_keywords):
                            self.logger.info(f"错误输出中包含密码关键词，推测需要密码: {archive_path}")
                            return False, 'password required'
                        # 不包含密码关键词，返回原始错误
                        return False, stderr_stripped
                    else:
                        # 没有错误输出，根据返回码推测
                        self.logger.info(f"返回码为{returncode}且无错误输出，推测需要密码: {archive_path}")
                        return False, 'password required'

            except subprocess.TimeoutExpired:
                self.logger.error("Bandizip进程超时，强制终止")
                process.kill()
                process.wait()
                return False, '解压超时'

        except Exception as e:
            self.logger.error(f"Bandizip进程异常: {e}", exc_info=True)
            if process and process.poll() is None:
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
            return False, f'解压异常: {str(e)}'

        finally:
            if process and process.poll() is None:
                try:
                    self.logger.warning("Bandizip进程仍在运行，强制终止")
                    process.kill()
                    process.wait()
                except Exception as e:
                    self.logger.error(f"无法终止Bandizip进程: {e}")
    
    def _try_extract_with_password(self, archive_path: str, 
                                   output_dir: str, password: str = None) -> Tuple[bool, str]:
        """尝试使用指定密码解压（优先使用配置的解压工具）
        
        Args:
            archive_path: 压缩包路径
            output_dir: 输出目录
            password: 密码（可选）
        
        Returns:
            (是否成功, 错误信息)
        """
        # 如果配置了使用Bandizip，则优先使用
        if self.use_bandizip and os.path.exists(self.bandizip_path):
            return self._try_extract_with_bandizip(archive_path, output_dir, password)
        
        # 构建7z命令
        cmd = [
            self.seven_zip_path,
            'x',  # 解压命令
            '-t*',  # 自动检测压缩格式，不依赖文件扩展名
            archive_path,
            f'-o{output_dir}',  # 输出目录
            '-y'  # 自动确认所有提示
        ]
        
        # 总是添加密码参数，即使是空密码，避免7z等待输入
        if password:
            cmd.append(f'-p{password}')
            self.logger.info(f"准备执行7z命令（使用密码）: {' '.join(cmd[:5])} -p*** -y")
        else:
            cmd.append('-p')  # 空密码
            self.logger.info(f"准备执行7z命令（空密码）: {' '.join(cmd[:5])} -p -y")
        
        self.logger.info(f"creationflags: {subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0}")
        
        process = None
        try:
            # 使用 Popen 以便更好地控制进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,  # 提供 stdin 避免等待输入
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            self.logger.info(f"7z进程已启动，PID: {process.pid}")
            
            # 关闭 stdin，确保不会等待输入
            if process.stdin:
                process.stdin.close()
                self.logger.info("stdin 已关闭")
            
            # 等待进程完成，设置超时
            try:
                stdout, stderr = process.communicate(timeout=300)
                returncode = process.returncode
                
                self.logger.info(f"7z命令执行完成，返回码: {returncode}")
                
                # 记录 7z 输出
                if stdout:
                    self.logger.info(f"7z stdout:\n{stdout}")
                if stderr:
                    self.logger.info(f"7z stderr:\n{stderr}")
                
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
            'wrong password',
            '需要密码',  # 中文
            'enter password',
            'invalid password'
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
