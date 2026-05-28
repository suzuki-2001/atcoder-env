#!/usr/bin/env python3
"""AtCoder local helper: contests / tasks / ac / todo / problem / whoami."""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import shutil
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ATCODER_BASE = "https://atcoder.jp"
PROBLEMS_BASE = "https://kenkoooo.com/atcoder"

# oj / aclogin write LWP-Cookies-2.0 format.
COOKIE_PATH = Path.home() / ".local/share/online-judge-tools/cookie.jar"

CACHE_DIR = Path.home() / ".cache/atcoder-cli-build"
CACHE_TTL = 24 * 3600


def _load_jar():
    if not COOKIE_PATH.exists():
        return None
    jar = http.cookiejar.LWPCookieJar(str(COOKIE_PATH))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar
    except Exception as e:
        print(f"warning: failed to load cookie jar: {e}", file=sys.stderr)
        return None


def make_session():
    s = requests.Session()
    s.headers["User-Agent"] = "atcoder-cli-build"
    jar = _load_jar()
    if jar is not None:
        s.cookies = jar
    return s


def cached_json(s, url, name, ttl=CACHE_TTL):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{name}.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < ttl:
        return json.loads(cache.read_text())
    r = s.get(url, timeout=60)
    r.raise_for_status()
    data = r.json()
    cache.write_text(json.dumps(data))
    return data


def _revel_session_value():
    jar = _load_jar()
    if jar is None:
        return None
    for c in jar:
        if c.name == "REVEL_SESSION":
            return c.value
    return None


def _handle_from_revel(raw):
    # REVEL_SESSION value: '<hmac>-<urlencoded payload>'; payload is
    # null-separated 'key:value' pairs after URL decoding.
    idx = raw.find("-")
    if idx < 0:
        return None
    try:
        payload = urllib.parse.unquote(raw[idx + 1 :])
    except Exception:
        return None
    for chunk in payload.split("\x00"):
        if chunk.startswith("UserScreenName:"):
            return chunk[len("UserScreenName:") :]
    return None


def require_user():
    user = os.environ.get("ATCODER_USER", "").strip()
    if user:
        return user
    raw = _revel_session_value()
    if raw:
        h = _handle_from_revel(raw)
        if h:
            return h
    print(
        "Could not determine your handle.\n"
        "Run `make login`, or set ATCODER_USER in .env.",
        file=sys.stderr,
    )
    sys.exit(2)


def cmd_whoami(args):
    raw = _revel_session_value()
    if not raw:
        print("NOT signed in. REVEL_SESSION cookie not found.")
        print("Run `make login` first.")
        return 1
    handle = _handle_from_revel(raw)
    s = make_session()
    r = s.get(
        f"{ATCODER_BASE}/contests/agc001/submit",
        timeout=15,
        allow_redirects=False,
    )
    if r.status_code in (301, 302) and "/login" in r.headers.get("Location", ""):
        print(f"EXPIRED: cookie for '{handle or '?'}' is no longer valid.")
        print("Run `make login` to refresh.")
        return 1
    if r.status_code != 200:
        print(f"WARN: unexpected status {r.status_code} from auth check")
        return 1
    print(f"OK: signed in as {handle}" if handle else "OK: session valid")
    return 0


def cmd_contests(args):
    s = make_session()
    contests = cached_json(s, f"{PROBLEMS_BASE}/resources/contests.json", "contests")
    now = datetime.now(timezone.utc).timestamp()
    started = sorted(
        (c for c in contests if c["start_epoch_second"] <= now),
        key=lambda c: c["start_epoch_second"],
        reverse=True,
    )
    print(f"{'ID':<18} {'Start':<17} {'Dur':>5} Title")
    print("-" * 80)
    for c in started[: args.limit]:
        start = datetime.fromtimestamp(c["start_epoch_second"], timezone.utc).strftime("%Y-%m-%d %H:%M")
        dur = f"{c['duration_second'] // 60}m"
        print(f"{c['id']:<18} {start:<17} {dur:>5} {c['title']}")
    return 0


def _user_submissions(s, user):
    return cached_json(
        s,
        f"{PROBLEMS_BASE}/atcoder-api/v3/user/submissions?user={user}&from_second=0",
        f"submissions_{user}",
        ttl=3600,
    )


def _user_acs(s, user):
    return {sub["problem_id"] for sub in _user_submissions(s, user) if sub.get("result") == "AC"}


def cmd_tasks(args):
    contest = args.contest
    s = make_session()
    r = s.get(f"{ATCODER_BASE}/contests/{contest}/tasks", timeout=30)
    if r.status_code == 404:
        print(f"contest not found: {contest}", file=sys.stderr)
        return 1
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    rows = soup.select("table tbody tr")
    if not rows:
        print(f"no tasks parsed for {contest}", file=sys.stderr)
        return 1

    ac_set = set()
    user = os.environ.get("ATCODER_USER", "").strip()
    if user:
        try:
            ac_set = _user_acs(s, user)
        except Exception as e:
            print(f"warning: AC fetch failed: {e}", file=sys.stderr)

    print(f"{'#':<3} {'St':<3} {'ID':<22} {'TL':>7} {'ML':>9}  Title")
    print("-" * 90)
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        letter = cells[0].get_text(strip=True)
        link = cells[1].find("a")
        title = link.get_text(strip=True) if link else cells[1].get_text(strip=True)
        href = link.get("href", "") if link else ""
        pid = href.rsplit("/", 1)[-1] if "/tasks/" in href else ""
        tl = cells[2].get_text(strip=True)
        ml = cells[3].get_text(strip=True)
        mark = "AC" if pid in ac_set else "·"
        print(f"{letter:<3} {mark:<3} {pid:<22} {tl:>7} {ml:>9}  {title}")
    return 0


def _fetch_rating(s, user):
    r = s.get(f"{ATCODER_BASE}/users/{user}", timeout=15)
    if r.status_code != 200:
        return "?"
    soup = BeautifulSoup(r.text, "lxml")
    for th in soup.find_all("th"):
        if "Rating" in th.get_text():
            td = th.find_next("td")
            if td:
                txt = td.get_text(strip=True).split()[0]
                if txt.isdigit():
                    return txt
    return "?"


def cmd_ac(args):
    user = require_user()
    s = make_session()
    subs = _user_submissions(s, user)
    ac_subs = [sub for sub in subs if sub.get("result") == "AC"]
    unique = {sub["problem_id"] for sub in ac_subs}
    latest = sorted(ac_subs, key=lambda x: x["epoch_second"], reverse=True)[: args.recent]
    print(f"User:     {user}")
    print(f"Rating:   {_fetch_rating(s, user)}")
    print(f"AC count: {len(unique)} unique problems  ({len(ac_subs)} submissions)")
    print()
    print(f"Last {args.recent} ACs:")
    for sub in latest:
        when = datetime.fromtimestamp(sub["epoch_second"], timezone.utc).strftime("%Y-%m-%d")
        print(f"  {when}  {sub['problem_id']:<25} ({sub['language']})")
    return 0


def cmd_todo(args):
    user = require_user()
    s = make_session()
    ac_set = _user_acs(s, user)
    problems = {p["id"]: p for p in cached_json(s, f"{PROBLEMS_BASE}/resources/problems.json", "problems")}
    models = cached_json(s, f"{PROBLEMS_BASE}/resources/problem-models.json", "problem-models")
    candidates = []
    for pid, prob in problems.items():
        if pid in ac_set:
            continue
        m = models.get(pid)
        if not m:
            continue
        diff_val = m.get("difficulty")
        if diff_val is None:
            continue
        diff = int(diff_val)
        if not (args.min <= diff <= args.max):
            continue
        candidates.append((diff, pid, prob))
    candidates.sort(key=lambda x: x[0])
    print(f"Unsolved, difficulty {args.min}-{args.max}:")
    print(f"{'Diff':>5}  {'ID':<25} Title")
    print("-" * 70)
    for diff, pid, prob in candidates[: args.limit]:
        print(f"{diff:>5}  {pid:<25} {prob['title']}")
    return 0


def cmd_problem(args):
    contest = args.contest
    task = args.task
    out_dir = Path(args.out_dir) if args.out_dir else Path(f"/work/contests/{contest}/{task}")
    s = make_session()
    url = f"{ATCODER_BASE}/contests/{contest}/tasks/{contest}_{task}"
    r = s.get(url, timeout=30)
    if r.status_code == 404:
        print(f"404: {url}", file=sys.stderr)
        return 1
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    head = soup.find("head")
    if head:
        head.insert(0, soup.new_tag("base", href=ATCODER_BASE + "/"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "problem.html"
    out.write_text(str(soup))
    print(f"saved: {out}")
    return 0


def _find_revel_cookie():
    jar = _load_jar()
    if jar is None:
        return None, None
    for c in jar:
        if c.name == "REVEL_SESSION":
            return jar, c
    return jar, None


def cmd_precheck(args):
    """Fast offline check before `new` / `submit`. No network calls."""
    _, c = _find_revel_cookie()
    if c is None:
        print("ERROR: not signed in. Run `make login` first.", file=sys.stderr)
        return 1
    if c.is_expired():
        print("ERROR: REVEL_SESSION cookie expired. Run `make login`.", file=sys.stderr)
        return 1
    return 0


def cmd_doctor(args):
    ok = True

    def check(label, passed, detail=""):
        nonlocal ok
        mark = "✓" if passed else "✗"
        print(f"  {mark} {label}{(' — ' + detail) if detail else ''}")
        if not passed:
            ok = False

    for tool in ("acc", "oj", "aclogin", "g++", "python3"):
        path = shutil.which(tool)
        check(f"{tool} on PATH", path is not None, path or "missing")

    try:
        import onlinejudge.service.atcoder as mod
        src = Path(mod.__file__).read_text()
        check("MiB patch applied", "MiB" in src and "KiB" in src, mod.__file__)
    except ImportError:
        check("onlinejudge importable", False, "ImportError")

    acl = Path("/opt/ac-library/atcoder/all")
    check("AC Library at /opt/ac-library", acl.exists())

    _, c = _find_revel_cookie()
    if c is None:
        check("REVEL_SESSION cookie", False, "not found — run `make login`")
    elif c.is_expired():
        check("REVEL_SESSION cookie", False, "expired — run `make login`")
    else:
        handle = _handle_from_revel(c.value) or "?"
        exp = datetime.fromtimestamp(c.expires, tz=timezone.utc).strftime("%Y-%m-%d") if c.expires else "?"
        check("REVEL_SESSION cookie", True, f"{handle} (expires {exp})")

        try:
            s = make_session()
            r = s.get(f"{ATCODER_BASE}/contests/agc001/submit", timeout=10, allow_redirects=False)
            if r.status_code in (301, 302) and "/login" in r.headers.get("Location", ""):
                check("AtCoder accepts session", False, "redirected to /login — run `make login`")
            else:
                check("AtCoder accepts session", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            check("AtCoder accepts session", False, f"network error: {e}")

    print()
    print("doctor: all green ✓" if ok else "doctor: issues found ✗")
    return 0 if ok else 1


def cmd_cache(args):
    if not CACHE_DIR.exists():
        print("no cache")
        return 0
    if args.clear:
        for f in CACHE_DIR.iterdir():
            f.unlink()
        print(f"cleared: {CACHE_DIR}")
        return 0
    print(f"cache dir: {CACHE_DIR}")
    for f in sorted(CACHE_DIR.iterdir()):
        age = int(time.time() - f.stat().st_mtime)
        size = f.stat().st_size
        print(f"  {f.name:<30} {size:>10} B   {age // 60:>5} min old")
    return 0


def main():
    p = argparse.ArgumentParser(description="AtCoder local helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("whoami", help="check session validity & show handle")
    sp.set_defaults(func=cmd_whoami)

    sp = sub.add_parser("contests", help="list recent contests")
    sp.add_argument("--limit", type=int, default=30)
    sp.set_defaults(func=cmd_contests)

    sp = sub.add_parser("tasks", help="list tasks in a contest")
    sp.add_argument("contest")
    sp.set_defaults(func=cmd_tasks)

    sp = sub.add_parser("ac", help="show AC stats")
    sp.add_argument("--recent", type=int, default=10)
    sp.set_defaults(func=cmd_ac)

    sp = sub.add_parser("todo", help="recommend unsolved problems by difficulty")
    sp.add_argument("--min", type=int, default=0)
    sp.add_argument("--max", type=int, default=3000)
    sp.add_argument("--limit", type=int, default=30)
    sp.set_defaults(func=cmd_todo)

    sp = sub.add_parser("problem", help="download problem statement HTML")
    sp.add_argument("contest")
    sp.add_argument("task")
    sp.add_argument("--out-dir")
    sp.set_defaults(func=cmd_problem)

    sp = sub.add_parser("cache", help="show or clear local API cache")
    sp.add_argument("--clear", action="store_true")
    sp.set_defaults(func=cmd_cache)

    sp = sub.add_parser("precheck", help="quick offline cookie check (used internally)")
    sp.set_defaults(func=cmd_precheck)

    sp = sub.add_parser("doctor", help="full diagnostics (tools, patch, cookie, session)")
    sp.set_defaults(func=cmd_doctor)

    args = p.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
