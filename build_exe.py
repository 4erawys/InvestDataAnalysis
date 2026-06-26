"""把 Streamlit 应用打包成 Windows 桌面程序（基于 streamlit-desktop-app）。

streamlit-desktop-app 用 PyInstaller 把整个 app 连同一个 pywebview 原生窗口
打包：双击启动、关窗口即自动结束后台 streamlit 进程，无浏览器标签、
无残留控制台进程。底层仍是 PyInstaller，`--pyinstaller-options` 原样透传。

采用 onedir（目录）模式而非 onefile（单文件）：产物是一个文件夹
`dist/InvestBacktest/`，内含 `InvestBacktest.exe` + `_internal/`（Python 运行时、
DLL、数据等）。相比单文件，onedir **没有每次启动解压到临时目录的开销，启动快很多**；
分发时把整个文件夹 zip 打包即可。

本脚本固定好这些「必须传对」的参数：
  --paths src                把 src/ 加进导入搜索路径，否则 invest_analysis 收不进去
                             （库默认只加了 `--paths .`）。
  --collect-submodules ...   兜底收全 invest_analysis 整包。
  --add-data 数据            把 data/processed 打进产物；运行时 data_loader.py 用
                             sys._MEIPASS 作为根目录定位它（见 _resolve_repo_root）。
                             onedir 下 _MEIPASS 指向 _internal/，解析同样成立。
  --collect-all plotly       plotly 需要其包内数据文件，否则图表运行时报错。
  --onedir / --noconfirm / --clean   目录模式、不交互、清构建缓存。

用法（务必在 invest 环境、仓库根目录下运行）：
    conda run -n invest python build_exe.py

产物：dist/InvestBacktest/（文件夹，约数百 MB）。整个文件夹 zip 后分发。
build/ 与 dist/ 均已在 .gitignore 中，不入库。
"""

from __future__ import annotations

import os
from pathlib import Path

from streamlit_desktop_app.build import build_executable

HERE = Path(__file__).resolve().parent
APP_NAME = "InvestBacktest"
ENTRY_SCRIPT = "app.py"


def main() -> None:
    # PyInstaller 的 --add-data / --paths 均相对 CWD 解析，固定到仓库根最稳。
    os.chdir(HERE)

    pyinstaller_options = [
        "--onedir",
        "--noconfirm",
        "--clean",
        # 让 PyInstaller 能找到 src/ 下的 invest_analysis（库默认只有 `--paths .`）。
        "--paths", "src",
        "--collect-submodules", "invest_analysis",
        # 处理后的年度数据，运行时经 sys._MEIPASS 定位（onedir 下指向 _internal/）。
        # Windows 上 PyInstaller 6.x 同样接受 ':' 作为 SRC:DEST 分隔符（与库内部一致）。
        "--add-data", "data/processed:data/processed",
        # plotly 依赖其包内 JSON/模板数据，必须整包收集。
        "--collect-all", "plotly",
    ]

    print(f"开始打包：{ENTRY_SCRIPT}  ->  dist/{APP_NAME}/（onedir 目录模式）")
    build_executable(
        script_path=ENTRY_SCRIPT,
        name=APP_NAME,
        pyinstaller_options=pyinstaller_options,
    )
    print(f"完成：dist/{APP_NAME}/  —— 分发时将整个文件夹打包成 zip")


if __name__ == "__main__":
    main()
