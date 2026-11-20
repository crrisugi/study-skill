"""study 跨宿主低打扰更新探测与按来源分流升级工具（纯 Python 标准库）"""
from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_SLUG = "crrisugi/study-skill"
RELEASES_LATEST_URL = f"https://github.com/{REPO_SLUG}/releases/latest"
RELEASES_PAGE_URL = f"https://github.com/{REPO_SLUG}/releases"
ARCHIVE_URL_TMPL = f"https://github.com/{REPO_SLUG}/archive/refs/tags/{{tag}}.tar.gz"

SUCCESS_TTL_SECONDS = 72 * 3600
FAILURE_TTL_SECONDS = 6 * 3600
REFRESH_DEBOUNCE_SECONDS = 60
HTTP_TIMEOUT_SECONDS = 2.5
UPGRADE_TIMEOUT_SECONDS = 20.0

OPT_OUT_ENV_VARS = ("STUDY_NO_UPDATE_CHECK", "NO_UPDATE_NOTIFIER", "CI", "GITHUB_ACTIONS")
SEMVER_RE = re.compile(r"^[vV]?(\d+)\.(\d+)(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
TAG_PATH_RE = re.compile(r"/releases/tag/([^/?#]+)")


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_env_disabled() -> bool:
    return any(_env_truthy(var) for var in OPT_OUT_ENV_VARS)


def parse_semver(ver: str) -> tuple[int, int, int, tuple[tuple[int, int | str], ...]] | None:
    m = SEMVER_RE.match(ver.strip())
    if not m:
        return None
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    pre_raw = m.group(4) or ""
    if not pre_raw:
        return (major, minor, patch, ())
    parts: list[tuple[int, int | str]] = []
    for item in pre_raw.split("."):
        parts.append((0, int(item)) if item.isdigit() else (1, item))
    return (major, minor, patch, tuple(parts))


def normalize_version(ver: str) -> str:
    return ver.strip().lstrip("vV")


def is_strictly_newer(candidate: str, current: str) -> bool:
    cand_p = parse_semver(candidate)
    curr_p = parse_semver(current)
    if cand_p is None or curr_p is None:
        return False
    if cand_p[:3] != curr_p[:3]:
        return cand_p[:3] > curr_p[:3]
    c_pre, cur_pre = cand_p[3], curr_p[3]
    if not cur_pre:
        return False
    if not c_pre:
        return True
    return c_pre > cur_pre


def read_local_version(skill_dir: pathlib.Path | None = None) -> str:
    base = skill_dir or pathlib.Path(__file__).resolve().parents[1]
    ver_file = base / "VERSION"
    if not ver_file.exists():
        return "0.0.0"
    return ver_file.read_text(encoding="utf-8").strip() or "0.0.0"


def get_cache_path() -> pathlib.Path:
    if override := os.environ.get("STUDY_UPDATE_CACHE_PATH", "").strip():
        return pathlib.Path(override)
    if sys.platform == "win32":
        base = pathlib.Path(os.environ.get("LOCALAPPDATA") or (pathlib.Path.home() / "AppData" / "Local"))
    else:
        base = pathlib.Path(os.environ.get("XDG_CACHE_HOME") or (pathlib.Path.home() / ".cache"))
    return base / "study-skill" / "update-check.json"


def load_cache(cache_path: pathlib.Path) -> dict:
    try:
        if cache_path.exists():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, ValueError):
        pass
    return {}


def save_cache(cache_path: pathlib.Path, data: dict) -> None:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        fd, tmp_name = tempfile.mkstemp(prefix="study-upd-", suffix=".tmp", dir=str(cache_path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_name, cache_path)
        except OSError:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
    except OSError:
        pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def extract_tag_from_location(location: str) -> str | None:
    if not location:
        return None
    m = TAG_PATH_RE.search(location.strip())
    if not m:
        return None
    tag = m.group(1).strip()
    return tag if parse_semver(tag) is not None else None


def fetch_latest_release(timeout: float = HTTP_TIMEOUT_SECONDS) -> tuple[str | None, str | None]:
    opener = urllib.request.build_opener(_NoRedirectHandler())
    headers = {"User-Agent": "study-skill-update-check/1.0"}
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(RELEASES_LATEST_URL, method=method, headers=headers)
        try:
            with opener.open(req, timeout=timeout) as resp:
                loc = resp.headers.get("Location", "")
                if tag := extract_tag_from_location(loc):
                    return normalize_version(tag), tag
                return None, None
        except urllib.error.HTTPError as err:
            if err.code in (301, 302, 303, 307, 308):
                loc = err.headers.get("Location", "") if err.headers else ""
                if tag := extract_tag_from_location(loc):
                    return normalize_version(tag), tag
                return None, None
            if err.code == 405 and method == "HEAD":
                continue
            return None, None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return None, None
    return None, None


def _read_lock_has_skill(lock_path: pathlib.Path, skill_names: tuple[str, ...] = ("study",)) -> bool:
    try:
        if not lock_path.is_file():
            return False
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        skills = data.get("skills") if isinstance(data, dict) else None
        if not isinstance(skills, dict):
            return False
        for key, entry in skills.items():
            if key in skill_names:
                return True
            if isinstance(entry, dict) and entry.get("skillName") in skill_names:
                return True
    except (OSError, ValueError):
        pass
    return False


def _find_git_root(path: pathlib.Path) -> pathlib.Path | None:
    for parent in (path, *path.parents):
        if (parent / ".git").exists():
            return parent
    return None


def _is_subpath(child: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def detect_install_channel(
    skill_dir: pathlib.Path | None = None,
    cwd: pathlib.Path | None = None,
    home_dir: pathlib.Path | None = None,
) -> dict[str, str]:
    raw_dir = skill_dir or pathlib.Path(__file__).resolve().parents[1]
    try:
        resolved_dir = raw_dir.resolve()
    except OSError:
        resolved_dir = raw_dir
    work_cwd = cwd or pathlib.Path.cwd()
    user_home = home_dir or pathlib.Path.home()

    plugin_markers = (
        (".claude/plugins", "claude", "claude plugin update study@study-skill"),
        (".gemini/config/plugins", "antigravity", "在 Antigravity 插件管理页更新 study 插件"),
        (".gemini/extensions", "gemini-cli", "gemini extensions update study"),
        (".codex/plugins", "codex", "在 Codex 插件管理界面更新 study 插件"),
        ("dsh-plugin-study", "dsh", "在 DeepSeek Harness 插件页更新 dsh-plugin-study"),
        ("node_modules", "npm", "通过项目包管理器更新依赖"),
    )
    for candidate in (raw_dir, resolved_dir):
        norm = candidate.as_posix().lower()
        for marker, host, cmd in plugin_markers:
            if marker in norm:
                return {"channel": "plugin-managed", "host": host, "upgrade_cmd": cmd}

    for candidate_root in (raw_dir, work_cwd):
        for base in (candidate_root, *candidate_root.parents):
            proj_lock = base / "skills-lock.json"
            if _read_lock_has_skill(proj_lock) and (_is_subpath(raw_dir, base) or _is_subpath(resolved_dir, base)):
                return {
                    "channel": "npx-skills",
                    "scope": "project",
                    "upgrade_cmd": "npx skills update study",
                    "check_cmd": "npx skills check",
                }
            if (base / ".git").exists():
                break

    for candidate in (resolved_dir, raw_dir):
        if git_root := _find_git_root(candidate):
            if candidate == git_root or candidate == (git_root / "skills" / "study"):
                return {
                    "channel": "git-clone",
                    "repo_root": str(git_root),
                    "upgrade_cmd": f'git -C "{git_root}" pull --ff-only',
                }

    xdg_state = os.environ.get("XDG_STATE_HOME", "").strip()
    global_locks = [user_home / ".agents" / ".skill-lock.json"]
    if xdg_state:
        global_locks.insert(0, pathlib.Path(xdg_state) / "skills" / ".skill-lock.json")
    if _is_subpath(raw_dir, user_home) or _is_subpath(resolved_dir, user_home):
        for g_lock in global_locks:
            if _read_lock_has_skill(g_lock):
                return {
                    "channel": "npx-skills",
                    "scope": "global",
                    "upgrade_cmd": "npx skills update study -g",
                    "check_cmd": "npx skills check -g",
                }

    script_self = raw_dir / "scripts" / "check_update.py"
    return {
        "channel": "manual-copy",
        "upgrade_cmd": "npx skills add crrisugi/study-skill",
        "alt_upgrade_cmd": f'uv run "{script_self}" --upgrade',
    }


def _refresh_cache_now(skill_dir: pathlib.Path | None = None) -> dict:
    cache_path = get_cache_path()
    cache = load_cache(cache_path)
    now = time.time()
    latest_ver, latest_tag = fetch_latest_release()
    cache["last_checked_at"] = now
    cache["current_version"] = read_local_version(skill_dir)
    if latest_ver and latest_tag:
        cache["last_status"] = "ok"
        cache["latest_version"] = latest_ver
        cache["latest_tag"] = latest_tag
    else:
        cache["last_status"] = "error"
    save_cache(cache_path, cache)
    return cache


def _spawn_background_refresh(cache_path: pathlib.Path, cache: dict) -> None:
    now = time.time()
    started = float(cache.get("refresh_started_at") or 0)
    if now - started < REFRESH_DEBOUNCE_SECONDS:
        return
    cache["refresh_started_at"] = now
    save_cache(cache_path, cache)
    cmd = [sys.executable, str(pathlib.Path(__file__).resolve()), "--refresh-cache"]
    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        kwargs["creationflags"] = flags
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def _format_upgrade_hint(info: dict[str, str]) -> str:
    if info["channel"] == "manual-copy":
        return f"运行 {info['upgrade_cmd']}（或 {info['alt_upgrade_cmd']}）"
    return f"运行 {info['upgrade_cmd']}"


def _should_suppress_notice(cache: dict, latest_ver: str, current_ver: str, now: float) -> bool:
    if cache.get("disabled"):
        return True
    if not latest_ver or not is_strictly_newer(latest_ver, current_ver):
        return True
    if cache.get("ignored_version") == latest_ver:
        return True
    if float(cache.get("snooze_until") or 0) > now:
        return True
    return False


def maybe_notify(skill_dir: pathlib.Path | None = None) -> None:
    try:
        if is_env_disabled():
            return
        cache_path = get_cache_path()
        cache = load_cache(cache_path)
        if cache.get("disabled"):
            return
        now = time.time()
        last_checked = float(cache.get("last_checked_at") or 0)
        ttl = SUCCESS_TTL_SECONDS if cache.get("last_status") == "ok" else FAILURE_TTL_SECONDS
        if last_checked == 0 or (now - last_checked) >= ttl:
            _spawn_background_refresh(cache_path, cache)

        current_ver = read_local_version(skill_dir)
        latest_ver = str(cache.get("latest_version") or "")
        if _should_suppress_notice(cache, latest_ver, current_ver, now):
            return
        channel_info = detect_install_channel(skill_dir)
        hint = _format_upgrade_hint(channel_info)
        print(
            f"[study] 发现新版 v{latest_ver}（当前 v{current_ver}）· {hint} · 更新说明：{RELEASES_PAGE_URL}",
            file=sys.stderr,
        )
    except Exception:
        pass


def _extract_changelog_section(changelog_text: str, version: str) -> str:
    lines = changelog_text.splitlines()
    collecting = False
    collected: list[str] = []
    ver_pat = re.compile(rf"^##\s+\[?v?{re.escape(version)}\]?(?:\s|$)")
    for line in lines:
        if line.startswith("## "):
            if collecting:
                break
            if ver_pat.match(line.strip()):
                collecting = True
                collected.append(line)
                continue
        elif collecting:
            collected.append(line)
    return "\n".join(collected).strip()


def _safe_extract_tar_gz(tar_bytes: bytes, dest_dir: pathlib.Path) -> pathlib.Path:
    dest_resolved = dest_dir.resolve()
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
        members = tf.getmembers()
        if not members:
            raise ValueError("压缩包为空")
        for member in members:
            if member.issym() or member.islnk():
                raise ValueError(f"拒绝含符号/硬链接的归档条目: {member.name}")
            m_path = pathlib.PurePosixPath(member.name)
            if m_path.is_absolute() or ".." in m_path.parts:
                raise ValueError(f"拒绝越界归档路径: {member.name}")
            target = (dest_resolved / pathlib.Path(*m_path.parts)).resolve()
            if target != dest_resolved and dest_resolved not in target.parents:
                raise ValueError(f"归档路径逸出目标目录: {member.name}")
        tf.extractall(dest_resolved)
    roots = [p for p in dest_resolved.iterdir() if p.is_dir()]
    if len(roots) != 1:
        raise ValueError("归档根目录结构异常")
    return roots[0]


def _sync_skill_tree(src_dir: pathlib.Path, dst_dir: pathlib.Path, preserve_names: set[str]) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    incoming_top = {p.name for p in src_dir.iterdir()}
    for existing in list(dst_dir.iterdir()):
        if existing.name in preserve_names:
            continue
        if existing.name not in incoming_top:
            if existing.is_dir():
                shutil.rmtree(existing)
            else:
                existing.unlink()
    for item in src_dir.iterdir():
        if item.name in preserve_names:
            continue
        target = dst_dir / item.name
        if item.is_dir():
            if item.name == "scripts":
                _sync_skill_tree(item, target, {".venv", "__pycache__"})
            else:
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def run_upgrade(skill_dir: pathlib.Path, yes: bool = False) -> int:
    channel_info = detect_install_channel(skill_dir)
    if channel_info["channel"] != "manual-copy":
        print(
            f"[study] 当前为 {channel_info['channel']} 托管安装，拒绝自动覆盖本地目录；"
            f"请改用：{_format_upgrade_hint(channel_info)}",
            file=sys.stderr,
        )
        return 1

    current_ver = read_local_version(skill_dir)
    latest_ver, latest_tag = fetch_latest_release(timeout=10.0)
    if not latest_ver or not latest_tag:
        print("[study] 无法获取 GitHub 最新发布版本，请检查网络或访问：" + RELEASES_PAGE_URL, file=sys.stderr)
        return 1
    if not is_strictly_newer(latest_ver, current_ver):
        print(f"[study] 当前已是最新版本 v{current_ver}（远端 {latest_tag}）。")
        return 0

    archive_url = ARCHIVE_URL_TMPL.format(tag=latest_tag)
    req = urllib.request.Request(archive_url, headers={"User-Agent": "study-skill-upgrader/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=UPGRADE_TIMEOUT_SECONDS) as resp:
            tar_bytes = resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        print(f"[study] 下载发布包失败: {err}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="study-upg-") as tmp_str:
        tmp_root = pathlib.Path(tmp_str)
        extract_dir = tmp_root / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        try:
            repo_root = _safe_extract_tar_gz(tar_bytes, extract_dir)
        except (tarfile.TarError, ValueError, OSError) as err:
            print(f"[study] 解压校验失败: {err}", file=sys.stderr)
            return 1

        new_study = repo_root / "skills" / "study"
        if not (new_study / "SKILL.md").is_file() or not (new_study / "VERSION").is_file():
            print("[study] 发布包内缺失 skills/study 核心文件，已中止升级。", file=sys.stderr)
            return 1

        changelog_file = repo_root / "CHANGELOG.md"
        excerpt = ""
        if changelog_file.is_file():
            excerpt = _extract_changelog_section(changelog_file.read_text(encoding="utf-8"), latest_ver)

        print(f"准备升级 study：v{current_ver} -> v{latest_ver}")
        if excerpt:
            print(f"\n{excerpt}\n")
        else:
            print(f"更新说明：{RELEASES_PAGE_URL}/tag/{latest_tag}\n")

        if not yes:
            if not sys.stdin.isatty():
                print("[study] 非交互终端请加 --yes 确认执行升级。", file=sys.stderr)
                return 1
            ans = input("确认替换当前手动复制的 study 技能目录吗？[y/N]: ").strip().lower()
            if ans not in {"y", "yes"}:
                print("[study] 已取消升级。")
                return 0

        backup_dir = pathlib.Path(tempfile.mkdtemp(prefix="study-skill-bak-"))
        shutil.copytree(skill_dir, backup_dir / "study", ignore=shutil.ignore_patterns(".venv", "__pycache__"))
        sibling_fb = skill_dir.parent / "study-feedback"
        new_fb = repo_root / "skills" / "study-feedback"
        has_fb = sibling_fb.is_dir() and (sibling_fb / "SKILL.md").is_file() and new_fb.is_dir()
        if has_fb:
            shutil.copytree(
                sibling_fb,
                backup_dir / "study-feedback",
                ignore=shutil.ignore_patterns(".venv", "__pycache__", "local_config.json"),
            )
        try:
            _sync_skill_tree(new_study, skill_dir, {".venv", "__pycache__"})
            if has_fb:
                _sync_skill_tree(new_fb, sibling_fb, {".venv", "__pycache__", "local_config.json"})
        except OSError as err:
            print(f"[study] 写入更新失败，正在从备份还原 ({backup_dir}): {err}", file=sys.stderr)
            _sync_skill_tree(backup_dir / "study", skill_dir, {".venv", "__pycache__"})
            return 1

        _refresh_cache_now(skill_dir)
        print(f"[study] 已升级至 v{read_local_version(skill_dir)}（原文件已备份于 {backup_dir}）。")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="study 伴学技能跨宿主更新探测与手动升级工具")
    ap.add_argument("--passive", action="store_true", help="仅读取缓存，过期时后台刷新，有新版则轻量提示")
    ap.add_argument("--refresh-cache", action="store_true", help="后台刷新本地版本缓存")
    ap.add_argument("--check", action="store_true", help="立即联网检查最新版本并输出当前安装来源")
    ap.add_argument("--json", action="store_true", help="配合 --check 以 JSON 格式输出")
    ap.add_argument("--upgrade", action="store_true", help="仅限手动复制安装：拉取对应 Release Tag 并安全替换")
    ap.add_argument("--yes", "-y", action="store_true", help="跳过 --upgrade 交互确认")
    ap.add_argument("--snooze", type=int, metavar="DAYS", help="暂停更新提醒指定天数")
    ap.add_argument("--ignore-version", metavar="VER", help="永久跳过指定版本号的提醒")
    ap.add_argument("--disable", action="store_true", help="永久关闭自动更新提醒")
    ap.add_argument("--enable", action="store_true", help="重新开启自动更新提醒并清除静音")
    args = ap.parse_args(argv)

    skill_dir = pathlib.Path(__file__).resolve().parents[1]
    cache_path = get_cache_path()

    if args.disable:
        cache = load_cache(cache_path)
        cache["disabled"] = True
        save_cache(cache_path, cache)
        print("[study] 已关闭更新提醒。")
        return 0

    if args.enable:
        cache = load_cache(cache_path)
        cache.pop("disabled", None)
        cache.pop("snooze_until", None)
        cache.pop("ignored_version", None)
        save_cache(cache_path, cache)
        print("[study] 已重新开启更新提醒。")
        return 0

    if args.snooze is not None:
        days = max(1, args.snooze)
        cache = load_cache(cache_path)
        cache["snooze_until"] = time.time() + days * 86400
        save_cache(cache_path, cache)
        print(f"[study] 已暂停更新提醒 {days} 天。")
        return 0

    if args.ignore_version:
        cache = load_cache(cache_path)
        cache["ignored_version"] = normalize_version(args.ignore_version)
        save_cache(cache_path, cache)
        print(f"[study] 已忽略版本 v{cache['ignored_version']} 的提醒。")
        return 0

    if args.refresh_cache:
        if not is_env_disabled():
            _refresh_cache_now(skill_dir)
        return 0

    if args.passive:
        maybe_notify(skill_dir)
        return 0

    if args.upgrade:
        return run_upgrade(skill_dir, yes=args.yes)

    current_ver = read_local_version(skill_dir)
    cache = _refresh_cache_now(skill_dir)
    latest_ver = str(cache.get("latest_version") or "")
    has_update = bool(latest_ver and is_strictly_newer(latest_ver, current_ver))
    channel_info = detect_install_channel(skill_dir)

    if args.json:
        payload = {
            "current_version": current_ver,
            "latest_version": latest_ver or None,
            "update_available": has_update,
            "status": cache.get("last_status"),
            "channel": channel_info,
            "releases_url": RELEASES_PAGE_URL,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if cache.get("last_status") != "ok":
        print(f"[study] 当前版本 v{current_ver}（安装来源：{channel_info['channel']}）；暂未连上 GitHub Releases。")
        return 0
    if has_update:
        print(
            f"[study] 发现新版 v{latest_ver}（当前 v{current_ver}，安装来源：{channel_info['channel']}）\n"
            f"- 升级方式：{_format_upgrade_hint(channel_info)}\n"
            f"- 发布页：{RELEASES_PAGE_URL}"
        )
    else:
        print(f"[study] 当前已是最新版本 v{current_ver}（安装来源：{channel_info['channel']}）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
