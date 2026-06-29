<div align="center">

# 🧹 WPS 磁盘清理工具

**一键清理 WPS Office 的缓存、备份和临时文件，释放磁盘空间。**

![Windows](https://img.shields.io/badge/Windows-✅-brightgreen)
![大小](https://img.shields.io/badge/大小-~12_MB-blue)
[![最新版本](https://img.shields.io/github/v/release/bjdeng/wps_cleanup)](https://github.com/bjdeng/wps_cleanup/releases)

</div>

---

## ✨ 它能做什么

WPS Office 用久了会在电脑里留下大量缓存、备份和临时文件，占用几个 GB 的磁盘空间。这个工具能帮你一键扫描并清理这些文件。

| 类别 | 可以清理什么 | 安全吗？ |
|------|-------------|---------|
| 📦 **插件缓存** | WPS 插件下载缓存、安装目录的临时文件 | ✅ 安全，WPS 会自动重新下载 |
| 💾 **本地备份** | 文档自动备份文件 (.wpsbak) | ⚠️ 请确认不需要的再清理 |
| ☁️ **云文档缓存** | 云文档的本地缓存副本 | ✅ 不影响云端文件 |
| ⚡ **功能缓存** | 灵犀技能缓存、通用缓存 | ✅ 安全 |

> **放心清理**：默认移入回收站，误删可以恢复。

---

## 📥 下载

从 [Releases 页面](https://github.com/bjdeng/wps_cleanup/releases) 下载最新版本：

| 文件 | 适合谁 | 怎么用 |
|------|--------|--------|
| `WPS-Cleanup.exe` | **大多数人** | 下载后双击打开 |
| `WPS-Cleanup-Portable.zip` | 喜欢免安装 | 解压到任意文件夹，双击运行 |
| `WPS-Cleanup-Setup.exe` | 希望有开始菜单 | 安装后可在开始菜单找到 |

> **不用装 Python**，下载直接运行。

---

## 🚀 使用步骤

**第一步**：下载上面的 `WPS-Cleanup.exe`

**第二步**：双击运行，工具会自动扫描 WPS 的所有缓存目录

**第三步**：勾选你想清理的项目，点击「开始清理」

![界面预览](docs/screenshot.png)

> *截图待补充——欢迎贡献一张实际运行的截图！*

---

## ⚠️ 注意事项

1. **清理前**，建议先打开 WPS 检查一下备份中心，确认没有需要的文档
2. **关闭 WPS 再清理**，否则部分文件可能被占用导致删不掉
3. **本地备份**（标了 ⚠️ 的）建议通过 WPS 自带的「备份中心」管理，更安全

---

<details>
<summary>🔧 给开发者看的（构建、测试、项目结构）</summary>

### 本地构建

```bash
pip install pyinstaller
python scripts/generate_icon.py
pyinstaller --onefile --windowed --name "WPS-Cleanup" --add-data "wps_cleanup;wps_cleanup" --noconfirm --clean main.py
```

输出文件在 `dist/WPS-Cleanup.exe`。

### 运行测试

```bash
python -m pytest tests/ -v
```

### 项目结构

```
wps_cleanup/
├── main.py                    # 程序入口
├── wps_cleanup/               # 核心代码
│   ├── app.py                 # 图形界面
│   ├── cli.py                 # 命令行模式
│   ├── cleaner.py             # 清理逻辑
│   ├── config.py              # 目录配置
│   ├── report.py              # 清理报告
│   └── utils.py               # 工具函数
├── tests/                     # 单元测试
├── scripts/                   # 构建脚本
└── assets/                    # 图标资源
```

### 依赖

- Python 3.8+
- 仅使用标准库，**零外部依赖**

</details>

---

<div align="center">

**如果这个工具有帮助，欢迎点个 ⭐**

遇到问题或有建议 → [提交 Issue](https://github.com/bjdeng/wps_cleanup/issues)

</div>
