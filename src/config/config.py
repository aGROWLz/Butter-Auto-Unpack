#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Config data class
配置数据类
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    """
    Configuration data class for the Auto Unpack Manager
    自动解压管理器的配置数据类
    
    Attributes:
        target_folder: 被监控的源文件夹路径
        unpack_folder: 存放和解压文件的目标文件夹路径
        passwords: 预设的解压密码列表
        image_archive_suffix: 图片文件添加的压缩格式后缀（默认.zip）
        seven_zip_path: 7z可执行文件路径（默认为'7z'）
        verify_media_files: 是否验证图片和视频文件是否为伪装压缩包（默认True）
        test_with_passwords: 7z测试时是否尝试使用密码库（默认False）
    """
    target_folder: str
    unpack_folder: str
    passwords: List[str] = field(default_factory=list)
    image_archive_suffix: str = '.zip'
    seven_zip_path: str = '7z'
    verify_media_files: bool = True
    test_with_passwords: bool = False
