#!/usr/bin/env python3
"""Build a Checkmk .mkp extension package from a cmk_addons plugin folder.

Packages every file under <plugin_dir> into cmk_addons_plugins.tar, nested
under <name>/, matching the ~/local/lib/python3/cmk_addons/plugins/<name>/
install layout Checkmk 2.3 expects. Uses only the Python standard library,
so it runs without a Checkmk site (e.g. on a plain dev machine).

Executable bits are taken from git's index (not the local filesystem), so
this produces correct permissions even when built on Windows.

Usage:
    python3 scripts/build_mkp.py special_agents/check_graph_secrets \\
        --name check_graph_secrets \\
        --version 1.0.0 \\
        --title "Microsoft Graph App Secrets" \\
        --author "Your Name <you@example.com>" \\
        --description "What the package does." \\
        --download-url "https://github.com/hivescript/checkmk/tree/main/special_agents/check_graph_secrets"
"""

import argparse
import json
import pprint
import subprocess
import sys
import tarfile
from pathlib import Path


def git_exec_bits(repo_root: Path, plugin_dir: Path) -> dict[str, bool]:
    rel = plugin_dir.relative_to(repo_root).as_posix()
    out = subprocess.run(
        ["git", "ls-files", "-s", rel],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    bits = {}
    for line in out.splitlines():
        mode, _sha, _stage, path = line.split(maxsplit=3)
        bits[path] = mode == "100755"
    return bits


def build(
    plugin_dir: Path,
    repo_root: Path,
    name: str,
    version: str,
    title: str,
    author: str,
    description: str,
    download_url: str,
    min_required: str,
    packaged: str,
    output_dir: Path,
) -> Path:
    exec_bits = git_exec_bits(repo_root, plugin_dir)
    plugin_dir_rel = plugin_dir.relative_to(repo_root).as_posix()

    exclude_dirs = {"docs"}
    files = sorted(
        p
        for p in plugin_dir.rglob("*")
        if p.is_file()
        and not exclude_dirs.intersection(p.relative_to(plugin_dir).parts[:-1])
    )
    if not files:
        raise ValueError(f"No files found under {plugin_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{name}-{version}.mkp"

    build_dir = output_dir / ".mkp-build"
    build_dir.mkdir(exist_ok=True)
    try:
        rel_files = []
        addons_tar = build_dir / "cmk_addons_plugins.tar"
        with tarfile.open(addons_tar, "w") as tar:
            for path in files:
                rel_to_plugin = path.relative_to(plugin_dir).as_posix()
                arcname = f"{name}/{rel_to_plugin}"
                rel_files.append(arcname)

                git_path = f"{plugin_dir_rel}/{rel_to_plugin}"
                tarinfo = tar.gettarinfo(str(path), arcname=arcname)
                tarinfo.mode = 0o755 if exec_bits.get(git_path) else 0o644
                tarinfo.uid = tarinfo.gid = 0
                tarinfo.uname = tarinfo.gname = ""
                tarinfo.mtime = 0
                with open(path, "rb") as f:
                    tar.addfile(tarinfo, f)

        # Empty archives for the parts this package doesn't use, so the
        # package matches the full tar-of-tars schema Checkmk expects.
        for part in ("agents", "lib", "notifications"):
            with tarfile.open(build_dir / f"{part}.tar", "w"):
                pass

        info_data = {
            "author": author,
            "description": description,
            "download_url": download_url,
            "files": {
                "agents": [],
                "cmk_addons_plugins": rel_files,
                "lib": [],
                "notifications": [],
            },
            "name": name,
            "title": title,
            "version": version,
            "version.min_required": min_required,
            "version.packaged": packaged,
            "version.usable_until": None,
        }

        with open(build_dir / "info", "w", encoding="utf-8") as f:
            pprint.pprint(info_data, stream=f, indent=4, width=80)
        with open(build_dir / "info.json", "w", encoding="utf-8") as f:
            json.dump(info_data, f, indent=2, ensure_ascii=False)

        with tarfile.open(output_file, "w:gz") as tar:
            for fname in (
                "info",
                "info.json",
                "agents.tar",
                "cmk_addons_plugins.tar",
                "lib.tar",
                "notifications.tar",
            ):
                tar.add(build_dir / fname, arcname=fname)
    finally:
        for f in build_dir.iterdir():
            f.unlink()
        build_dir.rmdir()

    return output_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "plugin_dir", type=Path, help="e.g. special_agents/check_graph_secrets"
    )
    parser.add_argument("--name", required=True, help="Package/plugin name")
    parser.add_argument("--version", required=True, help="Package version, e.g. 1.0.0")
    parser.add_argument("--title", required=True, help="Human-readable title")
    parser.add_argument("--author", required=True, help="Name <email>")
    parser.add_argument("--description", required=True)
    parser.add_argument("--download-url", default="")
    parser.add_argument(
        "--min-required", default="2.3.0", help="Minimum required Checkmk version"
    )
    parser.add_argument(
        "--packaged", default="2.3.0", help="Checkmk version used for packaging"
    )
    parser.add_argument("--output-dir", type=Path, default=Path("releases"))
    args = parser.parse_args()

    repo_root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    plugin_dir = (repo_root / args.plugin_dir).resolve()

    output_file = build(
        plugin_dir=plugin_dir,
        repo_root=repo_root,
        name=args.name,
        version=args.version,
        title=args.title,
        author=args.author,
        description=args.description,
        download_url=args.download_url,
        min_required=args.min_required,
        packaged=args.packaged,
        output_dir=(repo_root / args.output_dir),
    )
    print(f"Built {output_file} ({output_file.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
