"""
系统通知管理器 — 跨平台通知 + 去重

使用 plyer 实现跨平台系统气泡通知。
同类通知 60 秒内不重复推送。
"""

from __future__ import annotations

import time
from typing import Literal

NotifyLevel = Literal["info", "warning", "error"]

# 通知去重间隔（秒）
_DEDUP_INTERVAL = 60

# 上次通知时间缓存 {类型: 时间戳}
_last_notified: dict[str, float] = {}


def notify(
    title: str,
    message: str,
    level: NotifyLevel = "info",
    category: str = "",
) -> bool:
    """
    发送系统通知。

    Args:
        title: 通知标题
        message: 通知内容
        level: 通知级别（影响图标/声音，部分平台支持）
        category: 去重类别，同类别 60 秒内不重复

    Returns:
        是否成功发送
    """
    # 去重检查
    if category:
        now = time.time()
        last = _last_notified.get(category, 0)
        if now - last < _DEDUP_INTERVAL:
            return False
        _last_notified[category] = now

    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="LarkSync",
            timeout=8,
        )
        return True
    except ImportError:
        # plyer 未安装，尝试 Windows toast 或静默
        return _fallback_notify(title, message)
    except Exception:
        return False


def _fallback_notify(title: str, message: str) -> bool:
    """fallback 通知方式。"""
    import sys

    if sys.platform == "win32":
        try:
            # Windows 10+ toast 通知（通过 PowerShell）
            import subprocess

            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName('text')
            $textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('LarkSync').Show($toast)
            """
            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return True
        except Exception:
            pass

    # 最终 fallback：打印到 stderr
    import sys as _sys
    print(f"[LarkSync] {title}: {message}", file=_sys.stderr)
    return False


def notify_sync_complete(file_count: int) -> bool:
    """通知同步完成。"""
    return notify(
        "同步完成",
        f"{file_count} 个文件已同步。",
        level="info",
        category="sync_complete",
    )


def notify_conflict(file_path: str) -> bool:
    """通知发现冲突。"""
    return notify(
        "发现文件冲突",
        f"文件 {file_path} 存在冲突，请打开管理面板处理。",
        level="warning",
        category=f"conflict:{file_path}",
    )


def notify_error(error_msg: str) -> bool:
    """通知严重错误。"""
    return notify(
        "同步错误",
        error_msg,
        level="error",
        category="sync_error",
    )


def notify_backend_crash() -> bool:
    """通知后端崩溃。"""
    return notify(
        "LarkSync 后端异常",
        "后端服务多次重启失败，请检查日志。",
        level="error",
        category="backend_crash",
    )
