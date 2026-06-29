"""
WPS 清理目录配置。

根据用户提供的 WPS Office 各缓存/备份目录路径，按类别和安全等级归类。
所有路径中的 {username} 和 {version} 占位符会在运行时替换为实际值。
"""

import enum
import os
from dataclasses import dataclass, field
from typing import List


class SafetyLevel(enum.Enum):
    """安全等级枚举。"""
    SAFE = "✅ 可安全删除"
    CAUTION = "⚠️ 可清理，但需谨慎"


class Category(enum.Enum):
    """清理类别枚举。"""
    PLUGIN_CACHE = "插件与组件缓存"
    LOCAL_BACKUP = "本地备份与自动恢复"
    CLOUD_CACHE = "云文档缓存"
    FEATURE_CACHE = "特定功能缓存"


@dataclass
class CleanupItem:
    """描述一个可清理的目录项。"""
    name: str
    path_template: str
    description: str
    category: Category
    safety: SafetyLevel
    note: str = ""
    # 如果为 True，表示这是一个文件夹整体可删；否则只删内部临时文件
    delete_folder_entirely: bool = True
    # 需要排除的文件扩展名（如不想删 .docx）
    exclude_extensions: List[str] = field(default_factory=list)


# =========================================================================
# 所有可清理目录定义
# =========================================================================
CLEANUP_ITEMS = [
    # ========== 插件与组件缓存 ==========
    CleanupItem(
        name="插件缓存目录 (addons/pool)",
        path_template=r"~\AppData\Roaming\Kingsoft\wps\addons\pool\win-i386",
        description="WPS 插件下载缓存，删除后 WPS 会自动重新下载。",
        category=Category.PLUGIN_CACHE,
        safety=SafetyLevel.SAFE,
    ),
    CleanupItem(
        name="安装目录 Cache",
        path_template=r"C:\Program Files\WPS Office\Cache",
        description="WPS 安装目录下的缓存文件夹。",
        category=Category.PLUGIN_CACHE,
        safety=SafetyLevel.SAFE,
    ),
    CleanupItem(
        name="安装目录 Temp",
        path_template=r"C:\Program Files\WPS Office\Temp",
        description="WPS 安装目录下的临时文件夹。",
        category=Category.PLUGIN_CACHE,
        safety=SafetyLevel.SAFE,
    ),
    CleanupItem(
        name="安装目录 UpdateBackup",
        path_template=r"C:\Program Files\WPS Office\UpdateBackup",
        description="WPS 更新备份文件夹。",
        category=Category.PLUGIN_CACHE,
        safety=SafetyLevel.SAFE,
    ),

    # ========== 本地备份与自动恢复 ==========
    CleanupItem(
        name="Roaming 备份目录 (office6/backup)",
        path_template=r"~\AppData\Roaming\Kingsoft\office6\backup",
        description="WPS 本地自动备份文件。建议通过 WPS 备份中心管理删除。",
        category=Category.LOCAL_BACKUP,
        safety=SafetyLevel.CAUTION,
        note="建议通过 WPS 自带的「备份中心」来管理删除，更安全。",
    ),
    CleanupItem(
        name="Local 备份目录 (版本号/office6/backup)",
        path_template=r"~\AppData\Local\Kingsoft\WPS Office\{version}\office6\backup",
        description="另一个本地备份路径，包含 .tmp 或 .wpsbak 后缀的临时备份文件。",
        category=Category.LOCAL_BACKUP,
        safety=SafetyLevel.CAUTION,
        note="建议通过 WPS 备份中心操作。",
    ),
    CleanupItem(
        name="临时文件 AutoSave",
        path_template=r"~\AppData\Local\Temp\WPS Office\AutoSave",
        description="自动保存的临时文件目录。",
        category=Category.LOCAL_BACKUP,
        safety=SafetyLevel.SAFE,
    ),

    # ========== 云文档缓存 ==========
    CleanupItem(
        name="云文档缓存 (filecache)",
        path_template=r"~\AppData\Local\Kingsoft\WPS Cloud Files\userdata\qing\filecache",
        description="云文档的本地缓存目录。删除本地副本不会影响已保存在云端的文件。",
        category=Category.CLOUD_CACHE,
        safety=SafetyLevel.CAUTION,
        note="清理本地副本不影响云端文件。",
    ),
    CleanupItem(
        name="云文档备份 (Documents)",
        path_template=r"~\Documents\WPS Cloud Files\Backup",
        description="云文档的备份目录。清理不影响云端文件。",
        category=Category.CLOUD_CACHE,
        safety=SafetyLevel.CAUTION,
        note="清理不影响云端文件。",
    ),

    # ========== 特定功能缓存 ==========
    CleanupItem(
        name="WPS 灵犀技能缓存 (paste)",
        path_template=r"~\AppData\Roaming\WPS 灵犀\paste",
        description="WPS 灵犀技能包临时缓存目录。上传完成后不再需要。",
        category=Category.FEATURE_CACHE,
        safety=SafetyLevel.SAFE,
    ),
    CleanupItem(
        name="通用缓存目录 (WPS Office/cache)",
        path_template=r"~\AppData\Local\Kingsoft\WPS Office\cache",
        description="WPS 通用缓存目录。",
        category=Category.FEATURE_CACHE,
        safety=SafetyLevel.SAFE,
    ),
    CleanupItem(
        name="备份中心缓存 (backupcenter)",
        path_template=r"~\AppData\Local\Kingsoft\WPS Office\backupcenter",
        description="备份中心相关的缓存目录。",
        category=Category.FEATURE_CACHE,
        safety=SafetyLevel.CAUTION,
        note="确认不需要的备份后再清理。",
    ),
]


def resolve_path(template: str, version: str = "") -> str:
    """将路径模板解析为绝对路径。

    支持：
    - ~ 开头的路径展开为 USERPROFILE
    - {version} 占位符替换为实际的 WPS 版本号
    """
    path = template
    if path.startswith("~\\") or path.startswith("~/"):
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            path = os.path.join(user_profile, path[2:])
        else:
            # fallback: expanduser
            path = os.path.expanduser(path)
    if "{version}" in path:
        detected = detect_wps_version()
        path = path.replace("{version}", detected)
    return path


def detect_wps_version() -> str:
    """尝试检测已安装的 WPS 版本号。

    通过扫描 %LocalAppData%/Kingsoft/WPS Office 下的目录来找出版本号。
    """
    base = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")),
        "Kingsoft",
        "WPS Office",
    )
    if not os.path.isdir(base):
        return "11.2.2.12345"  # 默认版本号

    for entry in os.listdir(base):
        entry_path = os.path.join(base, entry)
        if os.path.isdir(entry_path) and entry[0].isdigit():
            return entry
    return "11.2.2.12345"