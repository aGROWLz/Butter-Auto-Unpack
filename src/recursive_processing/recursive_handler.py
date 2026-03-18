#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RecursiveHandler - 递归处理器
处理解压后的嵌套压缩包和单图片文件夹
"""

import os
from typing import List, Tuple, Optional, Callable
from ..extraction.extractor import Extractor
from ..file_processing.file_type_detector import FileTypeDetector
from ..config.config import Config


class RecursiveHandler:
    """递归处理器类
    
    处理解压后文件夹中的嵌套压缩包和单图片文件夹
    """
    
    MAX_RECURSION_DEPTH = 10  # 最大递归深度限制
    
    def __init__(self, extractor: Extractor, config: Config, status_callback: Optional[Callable[[str], None]] = None, db=None):
        """初始化递归处理器
        
        Args:
            extractor: 解压引擎实例
            config: 配置对象
            status_callback: 状态回调函数
            db: 数据库实例
        """
        self.extractor = extractor
        self.config = config
        self.status_callback = status_callback
        self.db = db
        self.processed_files = set()  # 跟踪已处理的文件，避免重复处理
    
    def _send_status(self, message: str) -> None:
        """发送状态消息
        
        Args:
            message: 状态消息
        """
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)
    
    def process_extracted_folder(self, folder_path: str, 
                                 passwords: List[str], 
                                 current_depth: int = 0) -> None:
        """递归处理解压后的文件夹
        
        Args:
            folder_path: 要处理的文件夹路径
            passwords: 密码列表
            current_depth: 当前递归深度（默认为0）
        """
        # 检查递归深度限制
        if current_depth >= self.MAX_RECURSION_DEPTH:
            self._send_status(f"达到最大递归深度 {self.MAX_RECURSION_DEPTH}，停止递归处理: {folder_path}")
            return
        
        # 如果是第一层递归，清空已处理文件集合
        if current_depth == 0:
            self.processed_files.clear()
        
        # 首先检查是否为单图片文件夹
        is_single_image, image_path = self._is_single_image_folder(folder_path)
        if is_single_image:
            # 处理单图片文件
            self._handle_single_image(image_path, passwords, current_depth)
            # 处理完单图片后，再次检查文件夹（可能解压出了新内容）
            self.process_extracted_folder(folder_path, passwords, current_depth + 1)
            return
        
        # 检查文件夹内容类型
        content_analysis = self._analyze_folder_content(folder_path)
        
        # 如果文件夹中有非压缩包文件，停止递归处理
        if content_analysis['has_other_files']:
            self._send_status(f"文件夹包含非压缩包文件，停止递归处理: {folder_path}")
            self._send_status(f"压缩包文件: {len(content_analysis['archives'])}, 其他文件: {len(content_analysis['other_files'])}")
            return
        
        # 如果只有压缩包文件，继续处理
        archives = content_analysis['archives']
        
        # 如果没有找到压缩包，递归处理完成
        if not archives:
            return
        
        self._send_status(f"文件夹只包含压缩包文件，继续递归处理: {folder_path} (共{len(archives)}个压缩包)")
        
        # 处理每个找到的压缩包，直接在当前文件夹解压
        for archive_path in archives:
            # 检查是否已经处理过这个文件
            if archive_path in self.processed_files:
                self._send_status(f"文件已在本次递归中处理过，跳过: {archive_path}")
                continue
            
            # 检查文件类型
            file_type = FileTypeDetector.get_file_type(archive_path)
            
            # 如果是分卷文件的非起始卷，跳过
            if file_type == 'volume_part':
                self._send_status(f"跳过分卷非起始卷: {archive_path}")
                continue
            
            # 标记为已处理
            self.processed_files.add(archive_path)
            
            # 为递归解压的文件创建数据库记录
            filename = os.path.basename(archive_path)
            record_id = None
            if self.db:
                # 检查数据库中是否已有记录
                existing_record = self.db.get_record_by_filename(filename)
                if existing_record and existing_record.status in ['success']:
                    self._send_status(f"文件已在数据库中标记为已处理，跳过: {archive_path}")
                    continue
                
                record_id = self.db.create_record(filename, archive_path)
                self.db.update_status(record_id, 'extracting')
            
            # 根据文件类型选择处理方式
            if file_type == 'multi_volume':
                # 分卷压缩包需要特殊处理
                result = self._handle_volume_extraction(archive_path, folder_path, passwords)
            elif file_type in ['image', 'video']:
                # 伪装的压缩包需要先重命名
                result = self._handle_disguised_archive(archive_path, folder_path, passwords, record_id)
                
                # 对于伪装压缩包，结果处理逻辑稍有不同
                if result.success:
                    self._send_status(f"成功处理伪装压缩包: {archive_path}")
                    
                    # 更新数据库状态为成功
                    if self.db and record_id:
                        self.db.update_status(record_id, 'success')
                    
                    self._send_status(f"已标记伪装压缩包为已处理: {archive_path}")
                else:
                    self._send_status(f"处理伪装压缩包失败: {archive_path}, 错误: {result.error_message}")
                    
                    # 更新数据库状态
                    if self.db and record_id:
                        if result.error_type == 'password':
                            self.db.update_status(record_id, 'password_error', result.error_message)
                        elif result.error_type == 'corrupted':
                            self.db.update_status(record_id, 'corrupted', result.error_message)
                        else:
                            self.db.update_status(record_id, 'failed', result.error_message)
                
                # 跳过通用的结果处理逻辑
                continue
            else:
                # 普通压缩包直接解压
                result = self.extractor.extract(archive_path, folder_path, passwords)
            
            if result.success:
                self._send_status(f"成功解压嵌套压缩包到当前文件夹: {archive_path}")
                
                # 更新数据库状态为成功，不删除文件
                if self.db and record_id:
                    self.db.update_status(record_id, 'success')
                
                self._send_status(f"已标记文件为已处理: {archive_path}")
            else:
                self._send_status(f"解压嵌套压缩包失败: {archive_path}, 错误: {result.error_message}")
                
                # 更新数据库状态
                if self.db and record_id:
                    if result.error_type == 'password':
                        self.db.update_status(record_id, 'password_error', result.error_message)
                    elif result.error_type == 'corrupted':
                        self.db.update_status(record_id, 'corrupted', result.error_message)
                    else:
                        self.db.update_status(record_id, 'failed', result.error_message)
        
        # 递归处理当前文件夹（可能解压出了新的压缩包）
        self.process_extracted_folder(folder_path, passwords, current_depth + 1)
    
    def _find_archives(self, folder_path: str) -> List[str]:
        """查找文件夹中的所有压缩包
        
        Args:
            folder_path: 文件夹路径
        
        Returns:
            压缩包文件路径列表
        """
        archives = []
        
        try:
            # 遍历文件夹中的所有文件
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                
                # 只处理文件，不处理子目录
                if os.path.isfile(item_path):
                    # 检查是否为压缩包
                    if FileTypeDetector.is_archive(item_path):
                        archives.append(item_path)
        
        except (OSError, PermissionError) as e:
            self._send_status(f"无法访问文件夹 {folder_path}: {e}")
        
        return archives
    
    def _analyze_folder_content(self, folder_path: str) -> dict:
        """分析文件夹内容类型
        
        Args:
            folder_path: 文件夹路径
        
        Returns:
            包含分析结果的字典:
            {
                'archives': [压缩包文件路径列表],
                'other_files': [其他文件路径列表],
                'has_other_files': bool,
                'total_files': int
            }
        """
        result = {
            'archives': [],
            'other_files': [],
            'has_other_files': False,
            'total_files': 0
        }
        
        try:
            # 遍历文件夹中的所有文件
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                
                # 只处理文件，不处理子目录
                if os.path.isfile(item_path):
                    result['total_files'] += 1
                    
                    # 检查文件类型
                    file_type = FileTypeDetector.get_file_type(item_path)
                    
                    self._send_status(f"递归分析文件: {item} -> 类型: {file_type}")
                    
                    if file_type in ['archive', 'multi_volume']:
                        # 检查是否已经处理过
                        if self.db:
                            existing_record = self.db.get_record_by_filename(item)
                            if existing_record and existing_record.status in ['success']:
                                self._send_status(f"文件已处理过，跳过: {item}")
                                continue  # 跳过已处理的文件
                        
                        # 压缩包文件
                        result['archives'].append(item_path)
                        self._send_status(f"添加到处理列表: {item}")
                    elif file_type in ['image', 'video']:
                        # 图片或视频文件 - 需要检查是否为伪装的压缩包
                        if self.config.verify_media_files:
                            # 验证是否真的是压缩包
                            if self._is_disguised_archive(item_path):
                                self._send_status(f"检测到伪装压缩包: {item}")
                                should_add = True
                            else:
                                # 真正的图片/视频文件
                                result['other_files'].append(item_path)
                                result['has_other_files'] = True
                                self._send_status(f"真实媒体文件: {item}")
                                should_add = False
                        else:
                            # 不验证，直接当作伪装压缩包处理
                            self._send_status(f"跳过验证，检测到媒体文件: {item}")
                            should_add = True
                        
                        if should_add:
                            # 检查重命名后的文件是否已处理过
                            new_filename = item + self.config.image_archive_suffix
                            if self.db:
                                existing_record = self.db.get_record_by_filename(new_filename)
                                if existing_record and existing_record.status in ['success']:
                                    self._send_status(f"伪装压缩包已处理过，跳过: {item}")
                                    continue
                            
                            # 添加到处理列表（作为需要重命名的伪装压缩包）
                            result['archives'].append(item_path)
                            self._send_status(f"添加伪装压缩包到处理列表: {item}")
                    elif file_type == 'volume_part':
                        # 分卷文件的非起始卷 - 不算作其他文件，但也不需要处理
                        self._send_status(f"分卷非起始卷，忽略: {item}")
                        # 不添加到 other_files，也不设置 has_other_files = True
                    else:
                        # 其他类型文件
                        result['other_files'].append(item_path)
                        result['has_other_files'] = True
                        self._send_status(f"其他文件: {item}")
        
        except (OSError, PermissionError) as e:
            self._send_status(f"无法访问文件夹 {folder_path}: {e}")
        
        self._send_status(f"文件夹分析完成: 总文件{result['total_files']}, 压缩包{len(result['archives'])}, 其他{len(result['other_files'])}")
        
        return result
    
    def _is_single_image_folder(self, folder_path: str) -> Tuple[bool, str]:
        """检查是否为只包含单个图片的文件夹
        
        Args:
            folder_path: 文件夹路径
        
        Returns:
            (是否为单图片文件夹, 图片文件路径)
        """
        try:
            # 获取文件夹中的所有项目
            items = os.listdir(folder_path)
            
            # 过滤出文件（排除子目录）
            files = [item for item in items 
                    if os.path.isfile(os.path.join(folder_path, item))]
            
            # 检查是否只有一个文件
            if len(files) == 1:
                file_path = os.path.join(folder_path, files[0])
                # 检查该文件是否为图片
                if FileTypeDetector.is_image(file_path):
                    return True, file_path
        
        except (OSError, PermissionError) as e:
            self._send_status(f"无法访问文件夹 {folder_path}: {e}")
        
        return False, ''
    
    def _handle_single_image(self, image_path: str, 
                            passwords: List[str],
                            current_depth: int) -> None:
        """处理单图片文件（添加后缀并解压）
        
        Args:
            image_path: 图片文件路径
            passwords: 密码列表
            current_depth: 当前递归深度
        """
        # 为图片添加配置的压缩格式后缀
        new_path = image_path + self.config.image_archive_suffix
        
        try:
            # 检查是否已经处理过这个文件
            if image_path in self.processed_files:
                self._send_status(f"单图片文件已在本次递归中处理过，跳过: {image_path}")
                return
            
            # 标记为已处理
            self.processed_files.add(image_path)
            
            # 为递归处理的单图片创建数据库记录
            filename = os.path.basename(image_path)
            record_id = None
            if self.db:
                # 检查数据库中是否已有记录
                existing_record = self.db.get_record_by_filename(filename)
                if existing_record and existing_record.status in ['success']:
                    self._send_status(f"单图片文件已在数据库中标记为已处理，跳过: {image_path}")
                    return
                
                record_id = self.db.create_record(filename, image_path)
            
            # 重命名文件（添加后缀）
            os.rename(image_path, new_path)
            self._send_status(f"为单图片添加后缀: {image_path} -> {new_path}")
            
            # 更新数据库记录
            if self.db and record_id:
                new_filename = os.path.basename(new_path)
                self.db.update_filename(record_id, new_filename)
                self.db.update_original_path(record_id, new_path)
                self.db.update_status(record_id, 'extracting')
            
            # 创建解压目录（与图片同名，不含扩展名）
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            extract_dir = os.path.join(os.path.dirname(image_path), image_name)
            
            # 尝试解压
            result = self.extractor.extract(new_path, extract_dir, passwords)
            
            if result.success:
                self._send_status(f"成功解压单图片文件: {new_path}")
                
                # 更新数据库状态
                if self.db and record_id:
                    self.db.update_status(record_id, 'success')
                
                # 递归处理解压后的文件夹
                self.process_extracted_folder(extract_dir, passwords, current_depth + 1)
            else:
                self._send_status(f"解压单图片文件失败: {new_path}, 错误: {result.error_message}")
                
                # 更新数据库状态
                if self.db and record_id:
                    if result.error_type == 'password':
                        self.db.update_status(record_id, 'password_error', result.error_message)
                    elif result.error_type == 'corrupted':
                        self.db.update_status(record_id, 'corrupted', result.error_message)
                    else:
                        self.db.update_status(record_id, 'failed', result.error_message)
                
                # 如果解压失败，恢复原文件名
                try:
                    os.rename(new_path, image_path)
                    self._send_status(f"解压失败，恢复原文件名: {new_path} -> {image_path}")
                except OSError as e:
                    self._send_status(f"无法恢复文件名: {e}")
        
        except OSError as e:
            self._send_status(f"处理单图片文件时出错: {e}")
    
    def _handle_volume_extraction(self, leader_path: str, extract_dir: str, passwords: List[str]):
        """处理分卷压缩包解压
        
        Args:
            leader_path: 起始卷路径
            extract_dir: 解压目录
            passwords: 密码列表
        
        Returns:
            ExtractionResult: 解压结果
        """
        # 查找所有分卷文件
        volume_files = self._find_all_volumes(leader_path)
        
        if not volume_files:
            self._send_status(f"未找到分卷文件: {leader_path}")
            from ..extraction.extractor import ExtractionResult
            return ExtractionResult(
                success=False,
                error_type='incomplete_volume',
                error_message='未找到分卷文件'
            )
        
        # 验证分卷完整性
        is_complete, missing_volumes = self.extractor.verify_volume_completeness(leader_path)
        
        if not is_complete:
            error_msg = f"分卷不完整，缺失: {', '.join(missing_volumes)}"
            self._send_status(f"分卷不完整: {leader_path}, 缺失: {missing_volumes}")
            from ..extraction.extractor import ExtractionResult
            return ExtractionResult(
                success=False,
                error_type='incomplete_volume',
                error_message=error_msg
            )
        
        # 标记所有分卷文件为已处理，避免重复处理
        for volume_file in volume_files:
            self.processed_files.add(volume_file)
        
        # 使用起始卷解压（7z会自动处理所有分卷）
        self._send_status(f"开始解压分卷压缩包: {leader_path} (共{len(volume_files)}个分卷)")
        result = self.extractor.extract(leader_path, extract_dir, passwords)
        
        if result.success:
            self._send_status(f"分卷压缩包解压成功: {leader_path}")
        else:
            self._send_status(f"分卷压缩包解压失败: {leader_path}, 错误: {result.error_message}")
        
        return result
    
    def _handle_disguised_archive(self, archive_path: str, extract_dir: str, passwords: List[str], record_id: int):
        """处理伪装的压缩包（图片/视频文件）
        
        Args:
            archive_path: 伪装压缩包路径
            extract_dir: 解压目录
            passwords: 密码列表
            record_id: 数据库记录ID
        
        Returns:
            ExtractionResult: 解压结果
        """
        # 为伪装文件添加压缩后缀
        new_path = archive_path + self.config.image_archive_suffix
        
        try:
            # 检查重命名后的文件是否已存在
            if os.path.exists(new_path):
                self._send_status(f"重命名后的文件已存在，跳过重命名: {new_path}")
                # 删除原文件
                try:
                    os.remove(archive_path)
                    self._send_status(f"删除原文件: {archive_path}")
                except OSError as e:
                    self._send_status(f"无法删除原文件: {archive_path}, 错误: {e}")
            else:
                # 重命名文件（添加后缀）
                os.rename(archive_path, new_path)
                self._send_status(f"为伪装压缩包添加后缀: {archive_path} -> {new_path}")
            
            # 更新数据库记录
            if self.db and record_id:
                new_filename = os.path.basename(new_path)
                self.db.update_filename(record_id, new_filename)
                self.db.update_original_path(record_id, new_path)
            
            # 标记重命名后的文件为已处理，避免重复处理
            self.processed_files.add(new_path)
            
            # 解压重命名后的文件
            result = self.extractor.extract(new_path, extract_dir, passwords)
            
            if result.success:
                self._send_status(f"成功解压伪装压缩包: {new_path}")
            else:
                self._send_status(f"解压伪装压缩包失败: {new_path}, 错误: {result.error_message}")
            
            return result
        
        except OSError as e:
            self._send_status(f"处理伪装压缩包时出错: {archive_path}, 错误: {e}")
            from ..extraction.extractor import ExtractionResult
            return ExtractionResult(
                success=False,
                error_type='file_error',
                error_message=f'文件操作失败: {str(e)}'
            )

    def _is_disguised_archive(self, file_path: str) -> bool:
        """检查图片/视频文件是否是伪装的压缩包
        
        Args:
            file_path: 文件路径
        
        Returns:
            True如果是伪装的压缩包，否则False
        """
        try:
            # 根据配置决定是否使用密码测试
            passwords = None
            if self.config.verify_media_files and self.config.passwords:
                passwords = self.config.passwords
                self._send_status(f"使用密码库测试文件: {os.path.basename(file_path)}")
            else:
                self._send_status(f"不使用密码测试文件: {os.path.basename(file_path)}")
            
            # 使用7z工具测试文件是否为有效的压缩包
            result = self.extractor.test_archive(file_path, passwords)
            return result.success
        except Exception as e:
            self._send_status(f"测试文件是否为压缩包时出错: {file_path}, 错误: {e}")
            return False

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
            if 'part01.rar' in filename.lower():
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
