# WPS Office 磁盘清理工具

清理 WPS Office 在 Windows 上产生的各种缓存、备份和临时文件，释放磁盘空间。

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-brightgreen)
[![Build Windows App](https://github.com/bjdeng/wps_cleanup/actions/workflows/build.yml/badge.svg)](https://github.com/bjdeng/wps_cleanup/actions/workflows/build.yml)

## 功能

- **扫描** WPS 的所有缓存目录，展示文件数量和占用空间
- **按类别展示**：插件缓存 / 本地备份 / 云文档缓存 / 功能缓存
- **安全等级标注**：✅ 可安全删除 / ⚠️ 谨慎清理
- **选择性清理**：勾选需要清理的项目
- **回收站支持**：默认移入回收站，可追溯
- **WPS 进程检测**：检测到 WPS 正在运行时警告用户
- **清理报告**：清理后展示详细报告，支持搜索文件列表和导出
- **命令行模式**：支持脚本化批量操作

## 清理目录详情

| 类别 | 目录 | 安全等级 |
|------|------|----------|
| 插件缓存 | `%AppData%\Kingsoft\wps\addons\pool\win-i386` | ✅ 安全 |
| 插件缓存 | `C:\Program Files\WPS Office\Cache / Temp / UpdateBackup` | ✅ 安全 |
| 本地备份 | `%AppData%\Kingsoft\office6\backup` | ⚠️ 谨慎 |
| 本地备份 | `%LocalAppData%\Kingsoft\WPS Office\{version}\office6\backup` | ⚠️ 谨慎 |
| 本地备份 | `%Temp%\WPS Office\AutoSave` | ✅ 安全 |
| 云文档缓存 | `%LocalAppData%\Kingsoft\WPS Cloud Files\userdata\qing\filecache` | ⚠️ 谨慎 |
| 云文档备份 | `%UserProfile%\Documents\WPS Cloud Files\Backup` | ⚠️ 谨慎 |
| 功能缓存 | `%AppData%\WPS 灵犀\paste` | ✅ 安全 |
| 通用缓存 | `%LocalAppData%\Kingsoft\WPS Office\cache` | ✅ 安全 |
| 备份中心 | `%LocalAppData%\Kingsoft\WPS Office\backupcenter` | ⚠️ 谨慎 |

---

## 📥 下载与安装

从 [Releases 页面](https://github.com/bjdeng/wps_cleanup/releases) 下载最新版本：

| 文件 | 说明 |
|------|------|
| `WPS-Cleanup.exe` | 单文件版，下载后直接运行 |
| `WPS-Cleanup-Portable.zip` | 便携版，解压到任意目录即可使用 |
| `WPS-Cleanup-Setup.exe` | 安装版，带开始菜单和卸载程序 |

---

## 🚀 使用方法

### 图形界面（推荐）

```bash
python main.py            # 源码运行
# 或直接双击 WPS-Cleanup.exe
```

### 命令行模式

```bash
# 扫描所有目录
python -m wps_cleanup.cli scan

# 清理所有可安全删除的项目
python -m wps_cleanup.cli clean --safe-only -y

# 模拟运行，预览将清理的内容
python -m wps_cleanup.cli clean --dry-run

# 强制清理（即使 WPS 正在运行）
python -m wps_cleanup.cli clean --force -y

# 仅清理安全项目，永久删除（不入回收站）
python -m wps_cleanup.cli clean --safe-only --permanent
```

---

## 🔨 构建 Windows 应用

### 方案 A：GitHub Actions 自动构建（推荐）

推送标签即可自动触发构建和发布：

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions 会自动：
1. 在 `windows-latest` 环境用 PyInstaller 打包为 `.exe`
2. 构建安装包（Inno Setup）
3. 创建 GitHub Release 并上传产物

查看 [Actions 页面](https://github.com/bjdeng/wps_cleanup/actions) 的进度。

### 方案 B：本地构建

在 Windows 上运行：

```batch
scripts\build_local.bat
```

或手动操作：

```bash
pip install pyinstaller
python scripts/generate_icon.py
pyinstaller --onefile --windowed --name "WPS-Cleanup" --icon assets/icon.ico --add-data "wps_cleanup;wps_cleanup" --noconfirm --clean main.py
```

输出文件在 `dist/WPS-Cleanup.exe`。

---

## 🧪 运行测试

```bash
python -m pytest tests/ -v
```

---

## 项目结构

```
wps_cleanup/
├── main.py                       # 入口（GUI 模式）
├── pyproject.toml                # 项目元数据
├── requirements.txt
├── README.md
│
├── .github/workflows/
│   └── build.yml                 # GitHub Actions 构建流水线
│
├── scripts/
│   ├── build_local.bat           # 本地构建批处理
│   ├── generate_icon.py          # 图标生成
│   └── setup.iss                 # Inno Setup 安装脚本
│
├── assets/
│   └── icon.ico                  # 应用图标
│
├── tests/
│   ├── conftest.py               # 共享 fixtures
│   ├── test_config.py
│   ├── test_scanner.py
│   ├── test_cleaner.py
│   ├── test_report.py
│   └── test_utils.py
│
└── wps_cleanup/
    ├── __init__.py
    ├── app.py                    # Tkinter GUI（左右分栏）
    ├── cli.py                    # 命令行入口
    ├── cleaner.py                # 清理逻辑 + 文件明细记录
    ├── config.py                 # 目录配置
    ├── report.py                 # 清理报告构建/格式化
    ├── report_dialog.py          # 报告弹窗
    ├── scanner.py                # 扫描逻辑
    └── utils.py                  # 工具函数
```

## 要求

- Python 3.8+
- Windows 操作系统（部分功能如回收站、进程检测依赖 Windows API）
- 无需第三方依赖，仅使用标准库

## 注意事项

1. 清理前请确保重要文档已保存或上传云端
2. 建议关闭所有 WPS 进程后再执行清理
3. 本地备份类项目建议通过 WPS 自带的「备份中心」管理
