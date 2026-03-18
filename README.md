# Butter Auto Unpack

<div align="center">

**一个智能的文件自动解压工具**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

[English](#english) | [中文](#中文)

</div>

---

## 中文

### 📖 简介

Butter Auto Unpack 是一个智能的文件自动解压工具，用于监控指定文件夹中的新文件，自动识别压缩包和图片文件，将它们移动到指定文件夹并进行解压处理。

### ✨ 功能特性

- 🔍 **自动监控** - 实时监控目标文件夹中的新文件
- 📦 **多格式支持** - 支持 .zip, .rar, .7z, .tar, .gz, .bz2 等压缩格式
- 🖼️ **图片处理** - 支持 .jpg, .jpeg, .png, .gif, .bmp, .webp 等图片格式
- 🔐 **密码解压** - 自动尝试密码列表进行解压
- 🔄 **递归解压** - 自动解压嵌套的压缩包
- 📂 **智能处理** - 自动处理单图片文件夹
- 💾 **分卷支持** - 完整支持分卷压缩包
- 🎨 **GUI界面** - 友好的图形界面，方便管理和筛选
- 📊 **状态跟踪** - 完整的文件处理状态跟踪
- 📝 **日志系统** - 详细记录所有操作和错误信息

### 🚀 快速开始

#### 下载使用（推荐）

1. 前往 [Releases](../../releases) 页面下载最新版本的 `Butter-Auto-Unpack.exe`
2. 双击运行程序
3. 点击"配置"按钮设置监控文件夹和解压文件夹
4. 添加常用的解压密码
5. 点击"开始监控"

#### 从源码运行

```bash
# 克隆仓库
git clone https://github.com/yourusername/Butter-Auto-Unpack.git
cd Butter-Auto-Unpack

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

### 📋 系统要求

- **操作系统**: Windows 7/8/10/11
- **Python**: 3.8+ (仅源码运行需要)
- **内存**: 至少 100MB 可用内存
- **磁盘**: 至少 50MB 可用空间

### ⚙️ 配置说明

首次运行时，程序会创建 `config.json` 配置文件：

```json
{
    "target_folder": "C:/Downloads",
    "unpack_folder": "C:/Unpack",
    "passwords": ["password1", "password2"],
    "image_archive_suffix": ".zip",
    "seven_zip_path": "7z"
}
```

| 配置项 | 说明 |
|--------|------|
| `target_folder` | 监控的目标文件夹路径 |
| `unpack_folder` | 解压输出文件夹路径 |
| `passwords` | 解压密码列表 |
| `image_archive_suffix` | 图片打包后缀 |
| `seven_zip_path` | 7z工具路径 |

### 💻 命令行参数

```bash
# 正常运行
Butter-Auto-Unpack.exe

# 调试模式（显示详细日志）
Butter-Auto-Unpack.exe --debug

# 查看版本信息
Butter-Auto-Unpack.exe --version

# 指定配置文件
Butter-Auto-Unpack.exe --config custom_config.json
```

### 📁 项目结构

```
Butter-Auto-Unpack/
├── src/                     # 源代码
│   ├── config/              # 配置管理
│   ├── database/            # 数据库管理
│   ├── extraction/          # 解压引擎
│   ├── file_management/     # 文件管理
│   ├── file_processing/     # 文件处理
│   ├── gui/                 # GUI界面
│   ├── log_manager/         # 日志管理
│   ├── monitoring/          # 文件监控
│   └── recursive_processing/ # 递归处理
├── resources/               # 资源文件（7z工具）
├── release/                 # 发布版本
├── config.template.json     # 配置文件模板
├── requirements.txt         # Python依赖
├── Butter-Auto-Unpack.spec  # PyInstaller配置
├── main.py                  # 主入口文件
└── README.md               # 项目说明
```

### 🔧 开发指南

#### 环境设置

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试（如果有）
python -m pytest tests/

# 打包为可执行文件
pyinstaller Butter-Auto-Unpack.spec
```

#### 技术栈

- **GUI框架**: PyQt5
- **文件监控**: watchdog
- **解压工具**: 7-Zip
- **数据库**: SQLite3
- **打包工具**: PyInstaller

### 📝 日志系统

程序运行时会在 `logs/` 文件夹中生成日志文件：

- `auto_unpack_manager.log` - 主日志文件
- `error.log` - 错误日志文件

使用 `--debug` 参数可以获得更详细的日志输出。

### ❓ 常见问题

<details>
<summary><b>程序无法启动？</b></summary>

- 检查是否被防病毒软件阻止
- 尝试以管理员身份运行
- 查看 `logs/error.log` 文件了解错误信息
</details>

<details>
<summary><b>解压失败？</b></summary>

- 检查是否添加了正确的解压密码
- 确保目标文件夹和解压文件夹路径正确
- 查看日志文件了解详细错误信息
</details>

<details>
<summary><b>文件未被监控？</b></summary>

- 确认已点击"开始监控"按钮
- 检查目标文件夹路径是否正确
- 确认文件格式在支持列表中
</details>

### 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

### 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

### 📧 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](../../issues)
- 发送邮件至: [your-email@example.com](mailto:your-email@example.com)

### 🙏 致谢

- [7-Zip](https://www.7-zip.org/) - 强大的压缩工具
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - 优秀的GUI框架
- [watchdog](https://github.com/gorakhargosh/watchdog) - 文件系统监控库

---

## English

### 📖 Introduction

Butter Auto Unpack is an intelligent automatic file extraction tool that monitors specified folders for new files, automatically identifies compressed files and images, moves them to designated folders, and performs extraction.

### ✨ Features

- 🔍 **Auto Monitoring** - Real-time monitoring of target folders
- 📦 **Multi-format Support** - Supports .zip, .rar, .7z, .tar, .gz, .bz2, etc.
- 🖼️ **Image Processing** - Supports .jpg, .jpeg, .png, .gif, .bmp, .webp, etc.
- 🔐 **Password Extraction** - Automatically tries password list for extraction
- 🔄 **Recursive Extraction** - Automatically extracts nested archives
- 📂 **Smart Processing** - Automatically handles single-image folders
- 💾 **Multi-volume Support** - Full support for split archives
- 🎨 **GUI Interface** - User-friendly graphical interface
- 📊 **Status Tracking** - Complete file processing status tracking
- 📝 **Logging System** - Detailed logging of all operations and errors

### 🚀 Quick Start

#### Download and Use (Recommended)

1. Go to [Releases](../../releases) page and download the latest `Butter-Auto-Unpack.exe`
2. Double-click to run the program
3. Click "Configure" to set monitoring and extraction folders
4. Add common extraction passwords
5. Click "Start Monitoring"

#### Run from Source

```bash
# Clone repository
git clone https://github.com/yourusername/Butter-Auto-Unpack.git
cd Butter-Auto-Unpack

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run program
python main.py
```

### 📋 System Requirements

- **OS**: Windows 7/8/10/11
- **Python**: 3.8+ (only for running from source)
- **Memory**: At least 100MB available
- **Disk**: At least 50MB available

### 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

### 📧 Contact

For questions or suggestions:

- Submit an [Issue](../../issues)
- Email: [your-email@example.com](mailto:your-email@example.com)

---

<div align="center">

Made with ❤️ by Butter Team

</div>
