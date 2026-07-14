from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_directory_in_file_manager(path: Path) -> None:
    target = path.expanduser().resolve()
    if not target.is_dir():
        raise FileNotFoundError(f"目录不存在: {target}")
    if sys.platform == "win32":
        os.startfile(str(target))
        return
    if sys.platform == "darwin":
        subprocess.Popen(["/usr/bin/open", str(target)], close_fds=True)
        return
    subprocess.Popen(["xdg-open", str(target)], close_fds=True)
