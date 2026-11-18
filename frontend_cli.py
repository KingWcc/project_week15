"""Terminal frontend process.

Run this in a second terminal while a backend is running, for example:

    python frontend_cli.py --url http://127.0.0.1:8000
    python frontend_cli.py --url http://127.0.0.1:8001 --once "今天升职了！"

Only the Python standard library is used, so the frontend is independent from
the backend's framework dependencies.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _configure_console() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def _request_json(url: str, payload: dict | None = None, timeout: float = 120.0) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = body.get("detail") if isinstance(body, dict) else ""
        except Exception:
            pass
        raise RuntimeError(detail or f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法连接后端：{exc.reason}") from exc


def _print_response(payload: dict) -> None:
    sentiment = payload.get("sentiment", {})
    label = {"positive": "正向", "negative": "负向", "neutral": "中性"}.get(
        sentiment.get("label"), sentiment.get("label", "未知")
    )
    route = {"encourage": "鼓励", "comfort": "排解", "neutral": "陪伴"}.get(
        payload.get("route"), payload.get("route", "回应")
    )
    confidence = sentiment.get("confidence")
    confidence_text = f"{confidence:.0%}" if isinstance(confidence, (int, float)) else "未知"
    mode_text = " · 离线演示" if payload.get("mode") == "mock" else ""

    print()
    print(f"[进程1] 情感：{label}（置信度 {confidence_text}） → [进程2] {route}{mode_text}")
    if sentiment.get("reason"):
        print(f"         依据：{sentiment['reason']}")
    print(f"[助手] {payload.get('reply', '')}")
    elapsed = payload.get("elapsed_ms")
    if isinstance(elapsed, int):
        print(f"         耗时：{elapsed / 1000:.2f}s")
    print()


def main() -> int:
    _configure_console()

    parser = argparse.ArgumentParser(description="情感支持作业的终端前端")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="后端地址")
    parser.add_argument("--once", metavar="TEXT", help="只发送一条消息后退出")
    parser.add_argument("--timeout", type=float, default=120.0, help="请求超时秒数")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    try:
        health = _request_json(f"{base_url}/api/health", timeout=10)
        framework = health.get("framework", "unknown")
        mode = health.get("mode", "unknown")
        print(f"已连接：{framework} · {mode} · {health.get('model', '')}")
        if mode == "llm" and not health.get("api_key_configured"):
            print("警告：后端尚未配置 API Key，对话请求会失败。")
    except RuntimeError as exc:
        print(f"后端连接失败：{exc}", file=sys.stderr)
        return 1

    if args.once is not None:
        try:
            _print_response(
                _request_json(
                    f"{base_url}/api/chat",
                    {"message": args.once},
                    timeout=args.timeout,
                )
            )
        except RuntimeError as exc:
            print(f"请求失败：{exc}", file=sys.stderr)
            return 1
        return 0

    print("输入消息开始对话；输入 /quit 或按 Ctrl+C 退出。\n")
    while True:
        try:
            message = input("你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            return 0

        if not message:
            continue
        if message in {"/quit", "/exit", "/q"}:
            print("再见。")
            return 0

        try:
            payload = _request_json(
                f"{base_url}/api/chat",
                {"message": message},
                timeout=args.timeout,
            )
            _print_response(payload)
        except RuntimeError as exc:
            print(f"请求失败：{exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
