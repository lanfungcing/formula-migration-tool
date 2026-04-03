#!/usr/bin/env python3
import requests, json, sys

UPSTREAM_API = "https://formulae.brew.sh/api/formula.jws.json"
DOWNSTREAM_API = "https://harmonybrew.atomgit.com/api/formula.jws.json"

# 全局数据
UPSTREAM_MAP = {}    # 真实名称 -> 详细信息
ALIAS_MAP = {}       # 别名 -> 真实名称
DOWNSTREAM_NAMES = set()
FULLY_EXPANDED = set()

def fetch_api(url):
    try:
        print(f"[*] downloading: {url}")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        # 处理 JWS 格式中的 payload
        data = resp.json()
        payload_str = data.get("payload", "[]")
        payload = json.loads(payload_str)
        return payload
    except Exception as e:
        print(f"[!] error: {e}")
        return []

def build_maps():
    global UPSTREAM_MAP, ALIAS_MAP, DOWNSTREAM_NAMES

    # 获取上游数据并构建别名映射
    upstream_data = fetch_api(UPSTREAM_API)
    for item in upstream_data:
        real_name = item["name"]
        UPSTREAM_MAP[real_name] = item
        # 记录所有别名指向 real_name
        for alias in item.get("aliases", []):
            ALIAS_MAP[alias] = real_name

    # 获取下游数据
    downstream_data = fetch_api(DOWNSTREAM_API)
    DOWNSTREAM_NAMES = {item["name"] for item in downstream_data}

def resolve_name(name):
    """将别名转换为真实名称，如果不是别名则返回原名"""
    return ALIAS_MAP.get(name, name)

def get_linux_deps(formula_info):
    deps = set()
    deps.update(formula_info.get("dependencies", []))
    deps.update(formula_info.get("build_dependencies", []))

    variations = formula_info.get("variations", {})
    # 优先检查 linux 变体
    linux_var = variations.get("arm64_linux") or variations.get("x86_64_linux")
    if linux_var:
        deps.update(linux_var.get("dependencies", []))
        deps.update(linux_var.get("build_dependencies", []))

    for item in formula_info.get("uses_from_macos", []):
        deps.add(item if isinstance(item, str) else list(item.keys())[0])

    return sorted([d for d in deps if d])

def analyze_deps(display_name, prefix="", is_last=True, current_path=None):
    if current_path is None:
        current_path = set()

    # 核心逻辑：立即解析真实名称
    real_name = resolve_name(display_name)
    connector = "└── " if is_last else "├── "
    
    # 判定状态
    in_up = real_name in UPSTREAM_MAP
    if not in_up:
        status = "⚠️  [NOT_FOUND]"
    else:
        status = "✅ [MIGRATED]" if real_name in DOWNSTREAM_NAMES else "❌ [NOT_MIGRATED]"

    # 构造显示字符串（如果是别名，显示 alias -> real_name）
    label = display_name
    if display_name != real_name:
        label = f"{display_name} -> {real_name}"

    # 检查循环依赖
    if real_name in current_path:
        print(f"{prefix}{connector}{label:<30} {status} (🔄 Cycle)")
        return

    # 检查是否已展示过
    if real_name in FULLY_EXPANDED:
        print(f"{prefix}{connector}{label:<30} {status} (Already shown above)")
        return

    print(f"{prefix}{connector}{label:<30} {status}")

    if not in_up:
        return

    FULLY_EXPANDED.add(real_name)
    current_path.add(real_name)

    formula_info = UPSTREAM_MAP[real_name]
    deps = get_linux_deps(formula_info)
    
    new_prefix = prefix + ("    " if is_last else "│   ")
    for i, dep in enumerate(deps):
        analyze_deps(dep, new_prefix, i == len(deps) - 1, current_path.copy())

def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 script.py <package>")

    build_maps()

    if not UPSTREAM_MAP:
        print("[!] Failed to fetch upstream data.")
        return
    
    target = sys.argv[1]
    real_target = resolve_name(target)

    print("\nResult Dependency Tree:\n" + "-" * 70)
    if real_target not in UPSTREAM_MAP:
        print(f"[!] Target '{target}' not found in upstream (even as an alias).")
    else:
        analyze_deps(target)
    print("-" * 70)

if __name__ == "__main__":
    main()
