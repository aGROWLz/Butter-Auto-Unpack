#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ConfigManager class for managing configuration persistence
配置管理器类，用于管理配置的持久化
"""

import json
import os
import shutil
from datetime import datetime
from typing import Tuple
from .config import Config


class ConfigManager:
    """
    Configuration manager for loading, saving, and validating configuration
    配置管理器，用于加载、保存和验证配置
    """
    
    def __init__(self, config_path: str = 'config.json'):
        """
        Initialize configuration manager
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径（默认为'config.json'）
        """
        self.config_path = config_path
    
    def load(self) -> Config:
        """
        Load configuration from file
        从文件加载配置
        
        If the configuration file does not exist, creates a default configuration.
        If the configuration file is corrupted, backs it up and creates a default configuration.
        
        Returns:
            Config: 加载的配置对象
        """
        # Check if config file exists
        if not os.path.exists(self.config_path):
            # Create default configuration
            config = self._create_default_config()
            self.save(config)
            return config
        
        try:
            # Try to load configuration from file
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理新旧配置兼容性：如果存在 seven_zip_path，转换为 preferred_extractor
            preferred_extractor = data.get('preferred_extractor', 'bandizip')
            if 'seven_zip_path' in data and 'preferred_extractor' not in data:
                # 旧配置，根据 seven_zip_path 判断
                seven_zip = data.get('seven_zip_path', '7z')
                if seven_zip and seven_zip != '7z':
                    preferred_extractor = '7z'
            
            # Create Config object from loaded data
            config = Config(
                target_folder=data.get('target_folder', ''),
                unpack_folder=data.get('unpack_folder', ''),
                passwords=data.get('passwords', []),
                image_archive_suffix=data.get('image_archive_suffix', '.zip'),
                preferred_extractor=preferred_extractor,
                verify_media_files=data.get('verify_media_files', False)
            )
            
            return config
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Configuration file is corrupted
            # Backup the corrupted file
            backup_path = f"{self.config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(self.config_path, backup_path)
                print(f"Corrupted config file backed up to: {backup_path}")
            except Exception as backup_error:
                print(f"Failed to backup corrupted config: {backup_error}")
            
            # Create and save default configuration
            config = self._create_default_config()
            self.save(config)
            print(f"Created new default configuration at: {self.config_path}")
            
            return config
    
    def save(self, config: Config) -> None:
        """
        Save configuration to file
        保存配置到文件
        
        Args:
            config: 要保存的配置对象
        """
        data = {
            'target_folder': config.target_folder,
            'unpack_folder': config.unpack_folder,
            'passwords': config.passwords,
            'image_archive_suffix': config.image_archive_suffix,
            'preferred_extractor': config.preferred_extractor,
            'verify_media_files': config.verify_media_files
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def validate(self, config: Config) -> Tuple[bool, str]:
        """
        Validate configuration
        验证配置有效性
        
        Args:
            config: 要验证的配置对象
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        # Validate target_folder
        if not config.target_folder:
            return False, "Target folder cannot be empty"
        
        if not os.path.isabs(config.target_folder):
            return False, "Target folder must be an absolute path"
        
        # Validate unpack_folder
        if not config.unpack_folder:
            return False, "Unpack folder cannot be empty"
        
        if not os.path.isabs(config.unpack_folder):
            return False, "Unpack folder must be an absolute path"
        
        # Validate that target and unpack folders are different
        if os.path.normpath(config.target_folder) == os.path.normpath(config.unpack_folder):
            return False, "Target folder and unpack folder must be different"
        
        # Validate image_archive_suffix
        if not config.image_archive_suffix:
            return False, "Image archive suffix cannot be empty"
        
        if not config.image_archive_suffix.startswith('.'):
            return False, "Image archive suffix must start with a dot (.)"
        
        # Passwords can be empty list (optional)
        
        return True, ""
    
    def _create_default_config(self) -> Config:
        """
        Create default configuration
        创建默认配置
        
        Returns:
            Config: 默认配置对象
        """
        return Config(
            target_folder='',
            unpack_folder='',
            passwords=['password123', '12345678', 'admin'],
            image_archive_suffix='.zip',
            preferred_extractor='bandizip',
            verify_media_files=False
        )
