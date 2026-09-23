"""Command-line entry point for Strava MCP."""

import sys


def _repair_stdio_from_uv_tool() -> None:
    """uv tool uvx leaves this process stdin on /dev/null and parks the real pipe on a high fd."""
    import os

    try:
        if os.path.realpath("/proc/self/fd/0") != "/dev/null":
            return
        ppid = os.getppid()
        parent_in = os.stat(f"/proc/{ppid}/fd/0").st_ino
        parent_out = os.stat(f"/proc/{ppid}/fd/1").st_ino
    except OSError:
        return
    by_ino: dict[int, int] = {}
    for fd in range(3, 32):
        try:
            by_ino.setdefault(os.stat(f"/proc/self/fd/{fd}").st_ino, fd)
        except OSError:
            continue
    if parent_in in by_ino:
        os.dup2(by_ino[parent_in], 0)
    if parent_out in by_ino:
        os.dup2(by_ino[parent_out], 1)


def main() -> None:
    """Run the MCP server or a supported subcommand."""
    _repair_stdio_from_uv_tool()
    args = sys.argv[1:]

    if args == ["auth"]:
        from .scripts.setup_auth import main as auth_main

        auth_main()
        return

    if args == ["smoke-oauth"] or args == ["smoke_oauth"]:
        from .scripts.smoke_oauth import main as smoke_main

        smoke_main()
        return

    from .server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
