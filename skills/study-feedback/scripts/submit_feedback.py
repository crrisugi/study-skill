"""study-feedback 外部反馈探测与脱敏提交工具（纯 Python 标准库，零外部依赖）

用法：
  python submit_feedback.py --probe
  python submit_feedback.py --channel email --title "<问题标题>" --body-file "<临时文件路径>" [--delete-body-file]
  python submit_feedback.py --channel github --title "<问题标题>" --body-file "<临时文件路径>" [--delete-body-file]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_SLUG = "crrisugi/study-skill"
FORMSPREE_URL = "https://formspree.io/f/xrpqkvwl"
HTTP_TIMEOUT_SECONDS = 15.0


def probe_gh(timeout: float = 10.0) -> dict:
    try:
        proc = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"gh_available": False, "gh_authenticated": False, "detail": "未检测到 gh 命令"}
    except subprocess.TimeoutExpired:
        return {"gh_available": True, "gh_authenticated": False, "detail": "gh auth status 超时"}

    if proc.returncode == 0:
        return {"gh_available": True, "gh_authenticated": True, "detail": "gh 已安装且已登录"}
    msg = (proc.stderr or proc.stdout or "gh 未登录").strip().splitlines()
    return {"gh_available": True, "gh_authenticated": False, "detail": msg[0] if msg else "gh 未登录"}


def build_email_payload(title: str, report: str) -> dict[str, str]:
    clean_title = title.strip()
    return {
        "_subject": f"[study-feedback] {clean_title}",
        "source": "study-skill",
        "title": clean_title,
        "report": report,
    }


def is_email_response_ok(status_code: int, raw_body: str) -> bool:
    if not (200 <= status_code < 300):
        return False
    try:
        data = json.loads(raw_body)
    except ValueError:
        return False
    return isinstance(data, dict) and data.get("ok") is True


def send_email(
    title: str,
    report: str,
    url: str = FORMSPREE_URL,
    timeout: float = HTTP_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    payload = build_email_payload(title, report)
    body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body_bytes,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "study-feedback-submitter/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            raw_resp = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace") if err.fp else ""
        return False, f"邮箱接口返回 HTTP {err.code}: {err_body[:160] or err.reason}"
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        return False, f"邮箱接口请求失败: {err}"

    if is_email_response_ok(status, raw_resp):
        return True, "邮箱反馈提交成功"
    return False, f"邮箱接口未返回 ok=true (HTTP {status}): {raw_resp[:160]}"


def build_gh_issue_cmd(title: str, body_file: pathlib.Path, repo: str = REPO_SLUG) -> list[str]:
    return [
        "gh",
        "issue",
        "create",
        "-R",
        repo,
        "--title",
        title.strip(),
        "--body-file",
        str(body_file),
    ]


def send_github_issue(
    title: str,
    body_file: pathlib.Path,
    repo: str = REPO_SLUG,
    timeout: float = 30.0,
) -> tuple[bool, str]:
    cmd = build_gh_issue_cmd(title, body_file, repo=repo)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError:
        return False, "未检测到 gh 命令"
    except subprocess.TimeoutExpired:
        return False, "gh issue create 超时"

    if proc.returncode == 0:
        out = (proc.stdout or "").strip()
        return True, out or "GitHub Issue 创建成功"
    err_msg = (proc.stderr or proc.stdout or f"gh 退出码 {proc.returncode}").strip()
    return False, err_msg


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="study-feedback 外部反馈探测与脱敏提交工具")
    ap.add_argument("--probe", action="store_true", help="只读探测 gh 命令与登录状态")
    ap.add_argument("--channel", choices=("email", "github"), help="外发通道：email 或 github")
    ap.add_argument("--title", help="一句话问题标题")
    ap.add_argument("--body-file", type=pathlib.Path, help="脱敏诊断单正文文件路径")
    ap.add_argument("--delete-body-file", action="store_true", help="发送成功后删除临时正文文件")
    args = ap.parse_args(argv)

    if args.probe:
        print(json.dumps(probe_gh(), ensure_ascii=False, indent=2))
        return 0

    if not args.channel or not args.title or not args.body_file:
        ap.error("非 --probe 模式下必须同时提供 --channel、--title 与 --body-file")

    body_path: pathlib.Path = args.body_file
    if not body_path.is_file():
        print(f"[FAIL] 诊断单文件不存在: {body_path}", file=sys.stderr)
        return 1

    try:
        report = body_path.read_text(encoding="utf-8")
    except OSError as err:
        print(f"[FAIL] 读取诊断单文件失败: {err}", file=sys.stderr)
        return 1

    if not report.strip():
        print("[FAIL] 诊断单正文为空，已中止外发", file=sys.stderr)
        return 1

    if args.channel == "email":
        ok, detail = send_email(args.title, report)
    else:
        ok, detail = send_github_issue(args.title, body_path)

    if not ok:
        print(f"[FAIL] {detail}", file=sys.stderr)
        return 1

    if args.delete_body_file:
        try:
            body_path.unlink(missing_ok=True)
        except OSError:
            pass

    print(f"[OK] {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
