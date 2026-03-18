#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FileProcessor - 文件处理器
协调文件移动、解压和状态更新
"""

import os
import re
import shutil
import glob
from typing import Optional, Callable

from ..config.config import Config
from ..database.database import Database
from ..extraction.extractor import Extractor
from ..recursive_processing.recursive_handler import RecursiveHandler
from ..log_manager import get_logger, log_file_operation, log_exception
from .file_type_detector import FileTypeDetector


class FileProcessor:
    """文件处理器类
    
    协调文件移动、解压和状态更新
    """
    
    def __init__(self, unpack_folder: str, extractor: Extractor, 
                 db: Database, config: Config, status_callback: Optional[Callable[[str], None]] = None):
        """初始化文件处理器
        
        Args:
            unpack_folder: Unpack文件夹路径
            extractor: 解压引擎实例
            db: 数据库实例
            config: 配置对象
            status_callback: 状态回调函数，用于向GUI发送状态消息
        """
        self.unpack_folder = unpack_folder
        self.extractor = extractor
        self.db = db
        self.config = config
        self.status_callback = status_callback
        self.recursive_handler = RecursiveHandler(extractor, config, status_callback, db)
        self.logger = get_logger()
        
        # 确保Unpack文件夹存在
        os.makedirs(unpack_folder, exist_ok=True)
        self.logger.info(f"文件处理器初始化完成 - Unpack目录: {unpack_folder}")
    
    def _send_status(self, message: str) -> None:
        """发送状态消息
        
        Args:
            message: 状态消息
        """
        if self.status_callback:
            self.status_callback(message)
        else:
            # 如果没有回调函数，直接打印（用于调试）
            print(message)
    
    def process_file(self, file_path: str, is_in_unpack_folder: bool = False) -> None:
        """处理单个文件
        
        Args:
            file_path: 文件路径
            is_in_unpack_folder: 文件是否已在解压文件夹中
        """
        self.logger.info(f"开始处理文件: {file_path} (在解压文件夹: {is_in_unpack_folder})")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            error_msg = f"文件不存在: {file_path}"
            self.logger.error(error_msg)
            self._send_status(error_msg)
            return
        
        # 检查文件大小，跳过空文件
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                self.logger.info(f"跳过空文件: {file_path}")
                self._send_status(f"跳过空文件: {file_path}")
                return
        except OSError as e:
            self.logger.error(f"无法获取文件大小: {file_path}, 错误: {e}")
            return
        
        # 检查是否应跳过该文件（如非起始分卷）
        if self._should_skip_file(file_path):
            skip_msg = f"跳过非起始分卷文件: {file_path}"
            self.logger.info(skip_msg)
            self._send_status(skip_msg)
            return
        
        # 获取文件类型
        file_type = FileTypeDetector.get_file_type(file_path)
        self.logger.info(f"文件类型识别: {file_path} -> {file_type}")
        
        try:
            # 检查是否已经处理过相同的文件
            filename = os.path.basename(file_path)
            existing_record = self.db.get_record_by_filename(filename)
            
            if existing_record and existing_record.status in ['success']:
                self._send_status(f"文件已处理过，跳过: {file_path}")
                self.logger.info(f"文件已处理过，跳过: {file_path} (记录ID: {existing_record.id})")
                return
            
            # 根据文件类型进行处理
            if file_type == 'multi_volume':
                # 分卷压缩包 - 首次解压跳过，只有递归解压才处理
                if is_in_unpack_folder:
                    self.logger.info(f"递归处理分卷压缩包: {file_path}")
                    filename = os.path.basename(file_path)
                    record_id = self.db.create_record(filename, file_path)
                    self._handle_multi_volume(file_path, is_in_unpack_folder)
                else:
                    skip_msg = f"首次解压跳过分卷压缩包，等待递归处理: {file_path}"
                    self.logger.info(skip_msg)
                    self._send_status(skip_msg)
            elif file_type == 'archive':
                # 普通压缩包
                self.logger.info(f"处理普通压缩包: {file_path}")
                if is_in_unpack_folder:
                    # 如果已在解压文件夹中，直接解压
                    filename = os.path.basename(file_path)
                    record_id = self.db.create_record(filename, file_path)
                    self._handle_archive(file_path, record_id)
                else:
                    # 如果在监控文件夹中，先移动到解压文件夹
                    filename = os.path.basename(file_path)
                    moved_path = self._move_file(file_path, os.path.join(self.unpack_folder, filename))
                    if moved_path:
                        record_id = self.db.create_record(filename, file_path)
                        self._handle_archive(moved_path, record_id)
            elif file_type == 'image':
                # 图片文件 - 需要检查是否真的是伪装的压缩包
                self.logger.info(f"检测到图片文件: {file_path}")
                
                # 根据配置决定是否验证
                if self.config.verify_media_files:
                    self.logger.info(f"开始验证图片文件是否为伪装压缩包: {file_path}")
                    # 验证是否真的是压缩包
                    if self._is_disguised_archive(file_path):
                        self.logger.info(f"确认为伪装压缩包，开始处理: {file_path}")
                        should_process = True
                    else:
                        # 真正的图片文件，跳过处理
                        self._send_status(f"跳过真正的图片文件: {file_path}")
                        self.logger.info(f"跳过真正的图片文件: {file_path}")
                        should_process = False
                else:
                    # 不验证，直接当作伪装压缩包处理
                    self.logger.info(f"跳过验证，直接处理图片文件: {file_path}")
                    should_process = True
                
                if should_process:
                    if is_in_unpack_folder:
                        # 如果已在解压文件夹中，直接处理（不为原文件创建记录）
                        self._handle_image_without_record(file_path)
                    else:
                        # 如果在监控文件夹中，先移动到解压文件夹
                        filename = os.path.basename(file_path)
                        moved_path = self._move_file(file_path, os.path.join(self.unpack_folder, filename))
                        if moved_path:
                            # 移动后处理（不为原文件创建记录）
                            self._handle_image_without_record(moved_path)
            elif file_type == 'video':
                # 视频文件 - 需要检查是否真的是伪装的压缩包
                self.logger.info(f"检测到视频文件: {file_path}")
                
                # 根据配置决定是否验证
                if self.config.verify_media_files:
                    # 验证是否真的是压缩包
                    if self._is_disguised_archive(file_path):
                        self.logger.info(f"确认为伪装压缩包，开始处理: {file_path}")
                        should_process = True
                    else:
                        # 真正的视频文件，跳过处理
                        self._send_status(f"跳过真正的视频文件: {file_path}")
                        self.logger.info(f"跳过真正的视频文件: {file_path}")
                        should_process = False
                else:
                    # 不验证，直接当作伪装压缩包处理
                    self.logger.info(f"跳过验证，直接处理视频文件: {file_path}")
                    should_process = True
                
                if should_process:
                    if is_in_unpack_folder:
                        # 如果已在解压文件夹中，直接处理（不为原文件创建记录）
                        self._handle_media_without_record(file_path)
                    else:
                        # 如果在监控文件夹中，先移动到解压文件夹
                        filename = os.path.basename(file_path)
                        moved_path = self._move_file(file_path, os.path.join(self.unpack_folder, filename))
                        if moved_path:
                            # 移动后处理（不为原文件创建记录）
                            self._handle_media_without_record(moved_path)
            else:
                unknown_msg = f"未知文件类型，忽略: {file_path}"
                self.logger.warning(unknown_msg)
                self._send_status(unknown_msg)
                
        except Exception as e:
            error_msg = f"处理文件时发生错误: {file_path}"
            self.logger.error(error_msg, exc_info=True)
            log_exception(e, f"文件处理 - {file_path}")
            self._send_status(f"错误: {error_msg} - {e}")
        
        self.logger.info(f"文件处理完成: {file_path}")
    
    def _move_file(self, source: str, destination: str) -> Optional[str]:
        """移动文件到Unpack文件夹
        
        Args:
            source: 源文件路径
            destination: 目标文件路径
        
        Returns:
            移动后的文件路径，失败返回None
        """
        try:
            self.logger.debug(f"准备移动文件: {source} -> {destination}")
            
            # 如果目标文件已存在，生成新的文件名
            if os.path.exists(destination):
                base, ext = os.path.splitext(destination)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                destination = f"{base}_{counter}{ext}"
                self.logger.info(f"目标文件已存在，使用新文件名: {destination}")
            
            # 移动文件
            shutil.move(source, destination)
            log_file_operation("移动", source, "成功", f"目标: {destination}")
            self._send_status(f"文件已移动: {source} -> {destination}")
            return destination
        
        except (OSError, shutil.Error) as e:
            error_msg = f"移动文件失败: {source} -> {destination}"
            self.logger.error(f"{error_msg}, 错误: {e}")
            log_file_operation("移动", source, "失败", str(e))
            self._send_status(f"{error_msg}, 错误: {e}")
            return None
    
    def _should_skip_file(self, file_path: str) -> bool:
        """判断是否应跳过文件（如非起始分卷）
        
        Args:
            file_path: 文件路径
        
        Returns:
            True如果应跳过，否则False
        """
        return FileTypeDetector.is_volume_part(file_path)
    
    def _is_disguised_archive(self, file_path: str) -> bool:
        """检查图片文件是否是伪装的压缩包
        
        Args:
            file_path: 图片文件路径
        
        Returns:
            True如果是伪装的压缩包，否则False
        """
        try:
            # 根据配置决定是否使用密码测试
            passwords = None
            if self.config.verify_media_files and self.config.passwords:
                passwords = self.config.passwords
                self.logger.info(f"使用密码库测试文件: {file_path}, 密码数量: {len(passwords)}")
            else:
                self.logger.info(f"不使用密码测试文件: {file_path}")
            
            # 使用7z工具测试文件是否为有效的压缩包
            self.logger.info(f"调用7z测试文件: {file_path}")
            result = self.extractor.test_archive(file_path, passwords)
            self.logger.info(f"7z测试结果: success={result.success}, error_type={result.error_type}")
            return result.success
        except Exception as e:
            self.logger.error(f"测试文件是否为压缩包时出错: {file_path}, 错误: {e}", exc_info=True)
            return False
            self.logger.debug(f"测试文件是否为压缩包时出错: {file_path}, 错误: {e}")
            return False

    def _handle_media_without_record(self, file_path: str) -> None:
        """处理媒体文件（图片/视频，添加后缀），不为原文件创建记录
        
        Args:
            file_path: 媒体文件路径
        """
        # 为媒体文件添加可配置的压缩后缀
        new_path = file_path + self.config.image_archive_suffix
        
        try:
            # 重命名文件（添加后缀）
            os.rename(file_path, new_path)
            self._send_status(f"为媒体文件添加压缩后缀: {file_path} -> {new_path}")
            
            # 为重命名后的文件创建记录
            filename = os.path.basename(new_path)
            record_id = self.db.create_record(filename, new_path)  # 使用新路径作为原始路径
            
            # 将重命名后的文件当作压缩包处理
            self._handle_archive(new_path, record_id)
        
        except OSError as e:
            error_msg = f"处理媒体文件失败: {file_path}, 错误: {e}"
            self._send_status(error_msg)
            self.logger.error(error_msg)

    def _handle_image_without_record(self, file_path: str) -> None:
        """处理图片文件（添加后缀），不为原文件创建记录
        
        Args:
            file_path: 图片文件路径
        """
        # 为图片添加可配置的压缩后缀
        new_path = file_path + self.config.image_archive_suffix
        
        try:
            # 重命名文件（添加后缀）
            os.rename(file_path, new_path)
            self._send_status(f"为图片添加压缩后缀: {file_path} -> {new_path}")
            
            # 为重命名后的文件创建记录
            filename = os.path.basename(new_path)
            record_id = self.db.create_record(filename, new_path)  # 使用新路径作为原始路径
            
            # 将重命名后的文件当作压缩包处理
            self._handle_archive(new_path, record_id)
        
        except OSError as e:
            error_msg = f"处理图片文件失败: {file_path}, 错误: {e}"
            self._send_status(error_msg)
            self.logger.error(error_msg)

    def _handle_archive(self, file_path: str, record_id: int) -> None:
        """处理压缩包文件
        
        Args:
            file_path: 压缩包文件路径
            record_id: 文件记录ID
        """
        # 更新状态为解压中
        self.db.update_status(record_id, 'extracting')
        
        # 创建与压缩包同名的解压文件夹
        # 对于分卷压缩包，需要移除所有分卷相关的扩展名
        filename = os.path.basename(file_path)
        archive_name = filename
        
        # 移除分卷扩展名
        if FileTypeDetector.detect_volume_type(file_path) == '7z':
            # 移除 .7z.001 -> 获取基础名
            archive_name = re.sub(r'\.7z\.\d{3}$', '', filename, flags=re.IGNORECASE)
        elif FileTypeDetector.detect_volume_type(file_path) == 'zip_numbered':
            # 移除 .zip.001 -> 获取基础名
            archive_name = re.sub(r'\.zip\.\d{3}$', '', filename, flags=re.IGNORECASE)
        elif FileTypeDetector.detect_volume_type(file_path) == 'rar':
            # 移除 .part1.rar -> 获取基础名
            archive_name = re.sub(r'\.part\d+\.rar$', '', filename, flags=re.IGNORECASE)
        elif FileTypeDetector.detect_volume_type(file_path) == 'zip':
            # 移除 .zip
            archive_name = os.path.splitext(filename)[0]
        elif FileTypeDetector.detect_volume_type(file_path) == 'disguised':
            # 移除 .001.xxx -> 获取基础名
            archive_name = re.sub(r'\.\d{3}\.[^.]+$', '', filename, flags=re.IGNORECASE)
        else:
            # 普通压缩包，移除扩展名
            archive_name = os.path.splitext(filename)[0]
        
        extract_dir = os.path.join(self.unpack_folder, archive_name)
        
        # 解压文件
        self.logger.info(f"调用解压引擎: {file_path} -> {extract_dir}")
        result = self.extractor.extract(file_path, extract_dir, self.config.passwords)
        self.logger.info(f"解压引擎返回: success={result.success}, error_type={result.error_type}")
        
        if result.success:
            self._send_status(f"解压成功: {file_path}")
            self.logger.info(f"解压成功，准备更新状态为递归处理中: record_id={record_id}")
            
            # 更新状态为递归处理中
            self.db.update_status(record_id, 'recursive_processing')
            self.logger.info(f"状态已更新为递归处理中: record_id={record_id}")
            
            # 递归处理解压后的文件夹
            try:
                self._send_status(f"开始递归处理解压文件夹: {extract_dir}")
                self.logger.info(f"开始调用递归处理器: {extract_dir}")
                self.recursive_handler.process_extracted_folder(
                    extract_dir, 
                    self.config.passwords
                )
                self.logger.info(f"递归处理器返回: {extract_dir}")
                
                # 递归处理完成，标记为成功
                self.logger.info(f"准备更新状态为成功: record_id={record_id}")
                self.db.update_status(record_id, 'success')
                self.logger.info(f"状态已更新为成功: record_id={record_id}")
                self._send_status(f"文件处理完成: {file_path}")
            
            except Exception as e:
                # 递归处理出错
                self.logger.error(f"递归处理异常: {file_path}, 错误: {e}", exc_info=True)
                self.db.update_status(
                    record_id, 
                    'failed', 
                    f'递归处理错误: {str(e)}'
                )
                self._send_status(f"递归处理失败: {file_path}, 错误: {e}")
                self.logger.exception(f"递归处理异常: {file_path}")
        
        else:
            # 解压失败，根据错误类型更新状态
            if result.error_type == 'password':
                self.db.update_status(record_id, 'password_error', result.error_message)
                self._send_status(f"密码错误: {file_path}")
            elif result.error_type == 'corrupted':
                self.db.update_status(record_id, 'corrupted', result.error_message)
                self._send_status(f"文件损坏: {file_path}")
            else:
                self.db.update_status(record_id, 'failed', result.error_message)
                self._send_status(f"解压失败: {file_path}, 错误: {result.error_message}")

    def _handle_image(self, file_path: str, record_id: int) -> None:
        """处理图片文件（添加后缀）
        
        Args:
            file_path: 图片文件路径
            record_id: 文件记录ID
        """
        # 为图片添加可配置的压缩后缀
        new_path = file_path + self.config.image_archive_suffix
        
        try:
            # 重命名文件（添加后缀）
            os.rename(file_path, new_path)
            self._send_status(f"为图片添加压缩后缀: {file_path} -> {new_path}")
            
            # 更新数据库中的文件名和原始路径
            filename = os.path.basename(new_path)
            self.db.update_filename(record_id, filename)
            self.db.update_original_path(record_id, new_path)  # 更新为新的路径
            
            # 将图片当作压缩包处理
            self._handle_archive(new_path, record_id)
        
        except OSError as e:
            self.db.update_status(record_id, 'failed', f'添加后缀失败: {str(e)}')
            self._send_status(f"处理图片文件失败: {file_path}, 错误: {e}")

    def _handle_multi_volume(self, file_path: str, is_in_unpack_folder: bool = False) -> None:
        """处理分卷压缩包
        
        Args:
            file_path: 起始卷文件路径
            is_in_unpack_folder: 文件是否已在解压文件夹中
        """
        filename = os.path.basename(file_path)
        
        # 查找所有分卷文件
        volume_files = self._find_all_volumes(file_path)
        
        if not volume_files:
            self._send_status(f"未找到分卷文件: {file_path}")
            return
        
        # 验证分卷完整性
        is_complete, missing_volumes = self.extractor.verify_volume_completeness(file_path)
        
        if not is_complete:
            # 分卷不完整，创建记录并标记失败
            record_id = self.db.create_record(filename, file_path)
            error_msg = f"分卷不完整，缺失: {', '.join(missing_volumes)}"
            self.db.update_status(record_id, 'failed', error_msg)
            self._send_status(f"分卷不完整: {file_path}, 缺失: {missing_volumes}")
            return
        
        if is_in_unpack_folder:
            # 如果已在解压文件夹中，直接解压
            record_id = self.db.create_record(filename, file_path)
            self._handle_archive(file_path, record_id)
        else:
            # 如果在监控文件夹中，移动所有分卷文件到Unpack文件夹
            moved_leader_path = None
            for volume_file in volume_files:
                volume_filename = os.path.basename(volume_file)
                dest_path = os.path.join(self.unpack_folder, volume_filename)
                moved_path = self._move_file(volume_file, dest_path)
                
                if moved_path and volume_file == file_path:
                    # 记录起始卷的移动后路径
                    moved_leader_path = moved_path
            
            if not moved_leader_path:
                self._send_status(f"移动起始卷失败: {file_path}")
                return
            
            # 创建文件记录（仅为起始卷创建记录）
            record_id = self.db.create_record(filename, file_path)
            
            # 使用起始卷解压
            self._handle_archive(moved_leader_path, record_id)
    
    def _find_all_volumes(self, leader_path: str) -> list:
        """查找所有分卷文件
        
        Args:
            leader_path: 起始卷路径
        
        Returns:
            所有分卷文件路径列表
        """
        volume_files = [leader_path]
        directory = os.path.dirname(leader_path)
        filename = os.path.basename(leader_path)
        file_lower = filename.lower()
        
        # 根据分卷类型查找其他分卷
        volume_type = FileTypeDetector.detect_volume_type(leader_path)
        
        if volume_type == '7z':
            # 7z分卷: file.7z.001, file.7z.002, ...
            base_name = filename.replace('.001', '')
            volume_num = 2
            while True:
                volume_path = os.path.join(directory, f'{base_name}.{volume_num:03d}')
                if os.path.exists(volume_path):
                    volume_files.append(volume_path)
                    volume_num += 1
                else:
                    break
        
        elif volume_type == 'zip_numbered':
            # Zip编号分卷: file.zip.001, file.zip.002, ...
            base_name = filename.replace('.001', '')
            volume_num = 2
            while True:
                volume_path = os.path.join(directory, f'{base_name}.{volume_num:03d}')
                if os.path.exists(volume_path):
                    volume_files.append(volume_path)
                    volume_num += 1
                else:
                    break
        
        elif volume_type == 'rar':
            # RAR分卷: file.part1.rar, file.part2.rar, ...
            if 'part01.rar' in file_lower:
                base_name = filename[:filename.lower().index('part01.rar')]
                format_str = 'part{:02d}.rar'
            else:
                base_name = filename[:filename.lower().index('part1.rar')]
                format_str = 'part{}.rar'
            
            volume_num = 2
            while True:
                volume_name = base_name + format_str.format(volume_num)
                volume_path = os.path.join(directory, volume_name)
                if os.path.exists(volume_path):
                    volume_files.append(volume_path)
                    volume_num += 1
                else:
                    break
        
        elif volume_type == 'zip':
            # Zip分卷: file.zip, file.z01, file.z02, ...
            base_name = filename[:-4]  # 移除.zip
            volume_num = 1
            while True:
                volume_path = os.path.join(directory, f'{base_name}.z{volume_num:02d}')
                if os.path.exists(volume_path):
                    volume_files.append(volume_path)
                    volume_num += 1
                else:
                    break
        
        elif volume_type == 'disguised':
            # 伪装分卷: file.7z.001.pdf, file.7z.002.pdf, ...
            # 提取基础名称和伪装扩展名
            parts = filename.split('.001.')
            if len(parts) == 2:
                base_name = parts[0]
                disguise_ext = parts[1]
                volume_num = 2
                while True:
                    volume_name = f'{base_name}.{volume_num:03d}.{disguise_ext}'
                    volume_path = os.path.join(directory, volume_name)
                    if os.path.exists(volume_path):
                        volume_files.append(volume_path)
                        volume_num += 1
                    else:
                        break
        
        return volume_files
