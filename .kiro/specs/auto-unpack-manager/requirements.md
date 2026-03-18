# 需求文档

## 介绍

自动解压管理器是一个文件处理工具，用于监控指定文件夹中的新文件，自动识别压缩包和图片文件，将它们移动到Unpack文件夹并进行解压处理。系统支持多密码尝试、处理状态跟踪，并提供前端界面进行文件管理和筛选。

## 术语表

- **System**: 自动解压管理系统
- **Target_Folder**: 被监控的源文件夹
- **Unpack_Folder**: 存放和解压文件的目标文件夹
- **Archive_File**: 压缩包文件（如.zip, .rar, .7z等格式）
- **Image_File**: 图片文件（如.jpg, .png等格式）
- **Password_List**: 预设的解压密码列表
- **File_Record**: 文件处理记录，包含状态信息
- **Processing_Status**: 文件处理状态（已移动、解压中、解压成功、解压失败、密码错误、文件损坏、递归处理中等）
- **Nested_Archive**: 嵌套在已解压文件夹中的压缩包
- **Single_Image_Folder**: 只包含一个图片文件的文件夹
- **Deleted_Status**: 文件已被手动删除的状态标记
- **Multi_Volume_Archive**: 分卷压缩包，被分割成多个文件的压缩包
- **Leader_Volume**: 分卷压缩包的起始卷（第一个分卷文件）

## 需求

### 需求 1: 文件监控与识别

**用户故事:** 作为用户，我希望系统能自动监控目标文件夹中的新文件，以便我不需要手动处理每个文件。

#### 验收标准

1. WHEN 目标文件夹中出现新文件，THEN THE System SHALL 检测到该文件
2. WHEN 检测到新文件，THEN THE System SHALL 识别文件类型（压缩包或图片）
3. THE System SHALL 支持多种压缩包格式（.zip, .rar, .7z, .tar, .gz, .bz2）
4. THE System SHALL 支持多种图片格式（.jpg, .jpeg, .png, .gif, .bmp, .webp）

### 需求 2: 压缩包处理

**用户故事:** 作为用户，我希望系统能自动处理压缩包文件，将其移动到Unpack文件夹并解压到对应的子文件夹中。

#### 验收标准

1. WHEN 检测到压缩包文件，THEN THE System SHALL 将文件移动到Unpack_Folder
2. WHEN 压缩包被移动到Unpack_Folder，THEN THE System SHALL 使用7z工具进行解压
3. WHEN 解压压缩包，THEN THE System SHALL 创建与压缩包同名的子文件夹（不含扩展名）
4. WHEN 压缩包名为"bigmod.zip"，THEN THE System SHALL 解压到"Unpack/bigmod/"文件夹
5. THE System SHALL 保留原始压缩包文件在Unpack_Folder中

### 需求 3: 图片文件处理

**用户故事:** 作为用户，我希望系统能将图片文件转换为压缩包格式并自动解压，以便统一处理流程。

#### 验收标准

1. WHEN 检测到图片文件，THEN THE System SHALL 在文件名后添加可配置的压缩格式后缀（默认.zip）
2. WHEN 图片文件添加压缩后缀后，THEN THE System SHALL 将文件移动到Unpack_Folder
3. WHEN 图片文件移动到Unpack_Folder，THEN THE System SHALL 尝试解压该文件
4. THE System SHALL 允许用户在前端配置图片文件的压缩格式后缀

### 需求 4: 密码尝试解压

**用户故事:** 作为用户，我希望系统能使用预设的密码列表自动尝试解压加密的压缩包，以便无需手动输入密码。

#### 验收标准

1. THE System SHALL 维护一个可配置的密码列表
2. WHEN 解压失败提示需要密码，THEN THE System SHALL 依次尝试Password_List中的每个密码
3. WHEN 某个密码解压成功，THEN THE System SHALL 停止尝试其他密码并记录成功的密码
4. WHEN 所有密码都尝试失败，THEN THE System SHALL 标记文件为"密码错误"状态
5. THE System SHALL 首先尝试无密码解压，然后再尝试密码列表

### 需求 5: 文件处理记录

**用户故事:** 作为用户，我希望系统能记录每个文件的处理状态，以便我了解哪些文件已成功处理，哪些需要关注。

#### 验收标准

1. WHEN 文件被处理，THEN THE System SHALL 创建File_Record记录
2. THE File_Record SHALL 包含文件名、原始路径、移动时间、处理状态
3. THE System SHALL 支持以下处理状态：已移动、解压中、解压成功、解压失败、密码错误、文件损坏、已删除
4. WHEN 文件状态变化，THEN THE System SHALL 更新File_Record中的状态和时间戳
5. THE System SHALL 持久化存储所有File_Record到数据库或文件

### 需求 6: 错误识别与分类

**用户故事:** 作为用户，我希望系统能准确识别解压失败的原因，以便我采取相应的处理措施。

#### 验收标准

1. WHEN 解压失败，THEN THE System SHALL 分析错误信息
2. WHEN 错误信息表明文件损坏，THEN THE System SHALL 标记状态为"文件损坏"
3. WHEN 错误信息表明密码错误且所有密码已尝试，THEN THE System SHALL 标记状态为"密码错误"
4. WHEN 解压过程中发生其他错误，THEN THE System SHALL 标记状态为"解压失败"并记录错误详情
5. THE System SHALL 在File_Record中保存详细的错误信息

### 需求 7: GUI界面 - 文件列表显示

**用户故事:** 作为用户，我希望在GUI界面看到所有处理过的文件及其状态，以便我管理和监控文件处理情况。

#### 验收标准

1. THE System SHALL 提供桌面GUI界面（使用PyQt5）
2. WHEN 用户打开应用程序，THEN THE System SHALL 显示所有File_Record的列表
3. THE 文件列表 SHALL 显示文件名、原始路径、移动时间、当前状态
4. WHEN 文件状态更新，THEN THE GUI界面 SHALL 自动刷新显示最新状态
5. THE System SHALL 为不同状态使用不同的视觉标识（颜色、图标）

### 需求 8: GUI界面 - 标签筛选功能

**用户故事:** 作为用户，我希望能通过标签筛选文件，以便快速找到特定状态的文件。

#### 验收标准

1. THE GUI界面 SHALL 提供状态标签筛选功能
2. THE System SHALL 支持按以下标签筛选：全部、已移动、解压成功、解压失败、密码错误、文件损坏、已删除
3. WHEN 用户选择标签，THEN THE System SHALL 只显示匹配该状态的文件
4. THE System SHALL 支持多标签同时筛选
5. THE System SHALL 在每个标签上显示对应状态的文件数量

### 需求 9: GUI界面 - 配置管理

**用户故事:** 作为用户，我希望能在GUI界面配置系统参数，以便根据需要调整系统行为。

#### 验收标准

1. THE GUI界面 SHALL 提供配置对话框或设置页面
2. THE 配置界面 SHALL 允许用户设置Target_Folder路径
3. THE 配置界面 SHALL 允许用户设置Unpack_Folder路径
4. THE 配置界面 SHALL 允许用户管理Password_List（添加、删除、排序密码）
5. THE 配置界面 SHALL 允许用户设置图片文件的压缩格式后缀
6. WHEN 用户保存配置，THEN THE System SHALL 验证配置有效性并应用新配置

### 需求 10: 递归解压嵌套压缩包

**用户故事:** 作为用户，我希望系统能自动处理解压后仍包含压缩包的情况，以便完全解压所有嵌套的压缩包。

#### 验收标准

1. WHEN 解压完成后，THEN THE System SHALL 扫描解压目录中的所有文件
2. WHEN 解压目录中发现压缩包文件，THEN THE System SHALL 在当前位置继续解压该压缩包
3. WHEN 嵌套压缩包解压完成，THEN THE System SHALL 递归检查新解压的内容
4. THE System SHALL 继续递归解压直到目录中不再包含压缩包文件
5. THE System SHALL 对嵌套压缩包应用相同的密码尝试策略

### 需求 11: 递归处理单图片文件夹

**用户故事:** 作为用户，我希望系统能自动处理解压后只包含单个图片文件的文件夹，以便继续解压这些伪装成图片的压缩包。

#### 验收标准

1. WHEN 解压完成后，THEN THE System SHALL 检查解压目录的内容
2. WHEN 解压目录中有且只有一个文件，THEN THE System SHALL 检查该文件是否为图片文件
3. WHEN 该唯一文件是图片文件，THEN THE System SHALL 为该图片添加配置的压缩格式后缀
4. WHEN 图片添加后缀后，THEN THE System SHALL 在当前位置尝试解压该文件
5. THE System SHALL 递归处理，直到文件夹中不再只包含单个图片文件
6. THE System SHALL 对这些图片文件应用相同的密码尝试策略

### 需求 12: 7z工具集成

**用户故事:** 作为系统，我需要使用7z命令行工具进行解压操作，以便支持多种压缩格式。

#### 验收标准

1. THE System SHALL 将7z可执行文件（7z.exe和7z.dll）打包到应用程序中
2. THE System SHALL 在启动时检测打包的7z工具是否可用
3. THE System SHALL 使用打包的7z命令行进行所有解压操作
4. WHEN 使用密码解压，THEN THE System SHALL 通过7z的密码参数传递密码
5. THE System SHALL 捕获7z的输出和错误信息用于状态判断

### 需求 13: 文件删除状态检测

**用户故事:** 作为用户，我希望系统能检测到我手动删除的文件，并在界面上标记为已删除状态，以便我了解哪些文件已不存在。

#### 验收标准

1. THE System SHALL 定期检查已记录文件的存在性
2. WHEN 已记录的压缩包文件被手动删除，THEN THE System SHALL 标记该记录为"已删除"状态
3. THE System SHALL 在前端界面中以特殊样式显示已删除状态的文件
4. WHEN 文件被标记为已删除，THEN THE System SHALL 保留该文件的历史记录
5. THE System SHALL 在启动时检查所有已记录文件的存在性

### 需求 14: GUI界面 - 文件删除功能

**用户故事:** 作为用户，我希望能在GUI界面删除文件或删除记录，以便管理不需要的文件和记录。

#### 验收标准

1. THE GUI界面 SHALL 为每个文件记录提供"删除文件"按钮
2. THE GUI界面 SHALL 为每个文件记录提供"删除记录"按钮
3. WHEN 用户点击"删除文件"，THEN THE System SHALL 显示确认对话框
4. WHEN 用户点击"删除记录"，THEN THE System SHALL 显示确认对话框
5. THE "删除记录"确认对话框 SHALL 包含"同时删除文件"的可选项
6. WHEN 用户确认删除文件，THEN THE System SHALL 删除Unpack文件夹中的压缩包文件和解压文件夹
7. WHEN 用户确认删除记录，THEN THE System SHALL 从数据库中删除该文件记录
8. WHEN 用户选择"同时删除文件"并确认，THEN THE System SHALL 删除文件和记录

### 需求 15: 可执行文件打包

**用户故事:** 作为用户，我希望系统能打包成独立的exe可执行文件，以便在Windows系统上直接运行而无需安装Python环境。

#### 验收标准

1. THE System SHALL 支持打包为Windows可执行文件（.exe）
2. THE 可执行文件 SHALL 包含所有必要的依赖库
3. THE 可执行文件 SHALL 在首次运行时创建默认配置文件
4. WHEN 配置文件不存在，THEN THE System SHALL 使用默认配置并创建配置文件
5. THE System SHALL 将配置文件存储在可执行文件同目录或用户数据目录

### 需求 16: 配置文件持久化

**用户故事:** 作为用户，我希望系统使用配置文件保存设置，以便在程序重启后保留我的配置，防止数据丢失。

#### 验收标准

1. THE System SHALL 在启动时加载配置文件
2. WHEN 配置文件不存在，THEN THE System SHALL 创建默认配置文件
3. WHEN 用户修改配置，THEN THE System SHALL 立即保存到配置文件
4. THE 配置文件 SHALL 使用JSON格式存储
5. THE System SHALL 在配置文件损坏时使用默认配置并备份损坏的文件
6. THE 数据库文件 SHALL 与配置文件存储在同一目录


### 需求 17: 分卷压缩包处理

**用户故事:** 作为用户，我希望系统能自动识别和处理分卷压缩包，以便解压被分割成多个文件的大型压缩包。

#### 验收标准

1. THE System SHALL 识别7z分卷压缩包（后缀为.001，如game.7z.001）
2. THE System SHALL 识别RAR分卷压缩包（后缀为part1.rar或part01.rar）
3. THE System SHALL 识别Zip分卷压缩包（后缀为.zip且同级存在.z01文件）
4. THE System SHALL 识别伪装分卷压缩包（包含.001.的路径，如game.7z.001.pdf）
5. WHEN 检测到分卷压缩包的起始卷，THEN THE System SHALL 仅将起始卷路径传递给解压引擎
6. WHEN 检测到非起始卷（如.002, .003），THEN THE System SHALL 忽略这些文件不单独处理
7. THE System SHALL 验证后续分卷文件与起始卷在同一目录下
8. WHEN 分卷文件不完整，THEN THE System SHALL 标记为解压失败并记录缺失的分卷
