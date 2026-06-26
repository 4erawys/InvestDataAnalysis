"""启动 Streamlit 应用，自动选择一个空闲端口。

Streamlit 默认固定使用 8501，端口被占用时会直接报错退出，不会自动换端口。
本脚本先让操作系统分配一个空闲端口，再把它传给 `streamlit run app.py`，
因此无需手动指定 `--server.port`。额外的命令行参数会原样透传给 streamlit。

用法：
    conda run -n invest python run_app.py
    conda run -n invest python run_app.py --server.headless true
"""

from __future__ import annotations

import socket
import subprocess
import sys


def find_free_port() -> int:
    """绑定到端口 0，由操作系统分配一个当前空闲的端口后返回。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


def main() -> None:
    port = find_free_port()
    print(f"自动选择空闲端口：{port}  ->  http://localhost:{port}")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            str(port),
            *sys.argv[1:],
        ]
    )


if __name__ == "__main__":
    main()
