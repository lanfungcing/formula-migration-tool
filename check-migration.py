#!/usr/bin/env python3
import requests, json, sys

UPSTREAM_API = "https://formulae.brew.sh/api/formula.jws.json"
DOWNSTREAM_API = "https://harmonybrew.atomgit.com/api/formula.jws.json"

# 全局缓存
UPSTREAM_MAP = {}
DOWNSTREAM_NAMES = set()
VISITED = set()


def fetch_api(url):
    try:
        print(f"[*] downloading: {url}")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        payload = json.loads(resp.json().get("payload", "[]"))
        return {item["name"]: item for item in payload}
    except Exception as e:
        print(f"[!] error: {e}")
        return {}


def get_linux_deps(formula_info):
    """精准提取通用 + ARM64 Linux + 构建依赖"""
    deps = set(formula_info.get("dependencies", []) + formula_info.get("build_dependencies", []))

    # 合并 ARM64 Linux 变体逻辑
    arm_linux = formula_info.get("variations", {}).get("arm64_linux", {})
    deps.update(arm_linux.get("dependencies", []))
    deps.update(arm_linux.get("build_dependencies", []))

    # 合并 uses_from_macos (在 Linux 上通常是必需的)
    for item in formula_info.get("uses_from_macos", []):
        deps.add(item if isinstance(item, str) else list(item.keys())[0])

    return sorted([d for d in deps if d])


def analyze_deps(name, prefix="", is_last=True):
    connector = "└── " if is_last else "├── "
    in_up = name in UPSTREAM_MAP
    status = ("✅ [MIGRATED]" if name in DOWNSTREAM_NAMES else "❌ [NOT_MIGRATED]") if in_up else "⚠️  [NOT_FOUND]"

    print(f"{prefix}{connector}{name:<25} {status}")

    if not in_up or name in VISITED:
        return
    VISITED.add(name)

    deps = get_linux_deps(UPSTREAM_MAP[name])
    new_prefix = prefix + ("    " if is_last else "│   ")
    for i, dep in enumerate(deps):
        analyze_deps(dep, new_prefix, i == len(deps) - 1)


def main():
    global UPSTREAM_MAP, DOWNSTREAM_NAMES
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 script.py <package>")

    UPSTREAM_MAP = fetch_api(UPSTREAM_API)
    DOWNSTREAM_NAMES = set(fetch_api(DOWNSTREAM_API).keys())

    if not UPSTREAM_MAP:
        return
    print("\nresult:\n" + "-" * 50)
    analyze_deps(sys.argv[1])
    print("-" * 50)


if __name__ == "__main__":
    main()
