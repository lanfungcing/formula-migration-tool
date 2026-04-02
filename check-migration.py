#!/usr/bin/env python3
import requests, json, sys

UPSTREAM_API = "https://formulae.brew.sh/api/formula.jws.json"
DOWNSTREAM_API = "https://harmonybrew.atomgit.com/api/formula.jws.json"

# 全局缓存
UPSTREAM_MAP = {}
DOWNSTREAM_NAMES = set()
# 全局已完全展开记录
FULLY_EXPANDED = set()

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
    deps = set()
    
    # 基础依赖
    deps.update(formula_info.get("dependencies", []))
    deps.update(formula_info.get("build_dependencies", []))

    # ARM64 Linux 特定变体依赖
    variations = formula_info.get("variations", {})
    arm_linux = variations.get("arm64_linux", {}) or variations.get("x86_64_linux", {})
    
    if arm_linux:
        deps.update(arm_linux.get("dependencies", []))
        deps.update(arm_linux.get("build_dependencies", []))

    # macOS 库在 Linux 下通常也是依赖
    for item in formula_info.get("uses_from_macos", []):
        deps.add(item if isinstance(item, str) else list(item.keys())[0])

    return sorted([d for d in deps if d])

def analyze_deps(name, prefix="", is_last=True, current_path=None):
    if current_path is None:
        current_path = set()

    connector = "└── " if is_last else "├── "
    
    # 1. 检查是否存在于上游
    in_up = name in UPSTREAM_MAP
    
    # 状态判定
    if not in_up:
        status = "⚠️  [NOT_FOUND]"
    else:
        status = "✅ [MIGRATED]" if name in DOWNSTREAM_NAMES else "❌ [NOT_MIGRATED]"

    # 2. 检查循环依赖
    if name in current_path:
        print(f"{prefix}{connector}{name:<25} {status} (🔄 Cycle)")
        return

    # 3. 检查是否已展示过
    if name in FULLY_EXPANDED:
        print(f"{prefix}{connector}{name:<25} {status} (Already shown above)")
        return

    # 打印当前节点
    print(f"{prefix}{connector}{name:<25} {status}")

    # 如果找不到这个包，或者它已经被标记过，我们就不应该去查它的依赖
    if not in_up:
        return

    # 4. 只有存在的包才标记为已展开并查询依赖
    FULLY_EXPANDED.add(name)
    current_path.add(name)

    # 安全地获取依赖
    formula_info = UPSTREAM_MAP[name]
    deps = get_linux_deps(formula_info)
    
    new_prefix = prefix + ("    " if is_last else "│   ")
    for i, dep in enumerate(deps):
        analyze_deps(dep, new_prefix, i == len(deps) - 1, current_path.copy())

def main():
    global UPSTREAM_MAP, DOWNSTREAM_NAMES
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 script.py <package>")

    UPSTREAM_MAP = fetch_api(UPSTREAM_API)
    DOWNSTREAM_NAMES = set(fetch_api(DOWNSTREAM_API).keys())

    if not UPSTREAM_MAP:
        return
    
    target = sys.argv[1]
    print("\nResult Dependency Tree:\n" + "-" * 60)
    if target not in UPSTREAM_MAP:
        print(f"[!] Target '{target}' not found in upstream.")
    else:
        # 顶层手动调用，模拟根节点
        analyze_deps(target)
    print("-" * 60)

if __name__ == "__main__":
    main()
