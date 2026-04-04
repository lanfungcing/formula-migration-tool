#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import requests

env_vars = ["GITCODE_USER", "GITCODE_EMAIL", "GITCODE_TOKEN"]
for var in env_vars:
    if not os.getenv(var):
        sys.exit(f"Error: Environment variable {var} is missing.")

GITCODE_USER = os.getenv("GITCODE_USER")
GITCODE_EMAIL = os.getenv("GITCODE_EMAIL")
GITCODE_TOKEN = os.getenv("GITCODE_TOKEN")
UPSTREAM_API = "https://formulae.brew.sh/api/formula.jws.json"
GITCODE_REPO = f"https://{GITCODE_USER}:{GITCODE_TOKEN}@gitcode.com/{GITCODE_USER}/homebrew-core.git"

def run_cmd(cmd, cwd=None):
    """运行 Shell 命令并返回输出"""
    print(f"[*] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[!] Error: {result.stderr}")
        sys.exit(result.returncode)
    print(result.stdout.strip())
    print(result.stderr.strip())
    return result.stdout.strip()

def fetch_aliases(formula_name):
    """从 API 获取该 Formula 的所有别名"""
    try:
        print(f"[*] Fetching aliases from {UPSTREAM_API}")
        resp = requests.get(UPSTREAM_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        payload = json.loads(data.get("payload", "[]"))
        
        for item in payload:
            if item.get("name") == formula_name:
                return item.get("aliases", [])
    except Exception as e:
        print(f"[!] Warning: Failed to fetch aliases: {e}")
    return []

def create_pr(head_branch, title):
    owner = "Harmonybrew"
    repo = "homebrew-core"

    # 构造请求数据
    url = f"https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls"
    params = {"access_token": GITCODE_TOKEN}
    payload = {
        "title": title,
        "head": head_branch,  # 格式: "username:branch"
        "base": "main",
        "body": "Automatically migrated by [formula-migration-tool](https://github.com/Harmonybrew/formula-migration-tool).",
        "prune_source_branch": True,  # 合入后删除源分支
    }

    try:
        response = requests.post(url, params=params, json=payload, timeout=30)
        response.raise_for_status()
        print(
            f"[SUCCESS] PR created: https://gitcode.com/Harmonybrew/homebrew-core/pull/{response.json().get('number')}"
        )
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to create PR: {e}")
        if response is not None:
            print(f"Response: {response.text}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 migrate.py <formula>")

    formula = sys.argv[1]
    
    # 1. 确定路径逻辑
    tap_path = run_cmd(["brew", "--repository", "harmonybrew/core"])
    os.chdir(tap_path)

    first_letter = "lib" if formula.startswith("lib") else formula[0].lower()
    target_rel_dir = f"Formula/{first_letter}"
    target_abs_dir = os.path.join(tap_path, target_rel_dir)
    os.makedirs(target_abs_dir, exist_ok=True)

    # 2. 下载 Formula 文件
    print(f"[*] Fetching {formula}.rb...")
    upstream_url = f"https://raw.githubusercontent.com/Homebrew/homebrew-core/main/Formula/{first_letter}/{formula}.rb"
    rb_path = os.path.join(target_abs_dir, f"{formula}.rb")
    
    resp = requests.get(upstream_url)
    if resp.status_code != 200:
        sys.exit(f"Error: Could not find {formula}.rb on upstream.")
    with open(rb_path, "w") as f:
        f.write(resp.text)

    # 3. 创建 Aliases 软链接
    aliases = fetch_aliases(formula)
    if aliases:
        alias_dir = os.path.join(tap_path, "Aliases")
        os.makedirs(alias_dir, exist_ok=True)
        for alias in aliases:
            alias_path = os.path.join(alias_dir, alias)
            # 计算相对路径: 从 Aliases/ 到 Formula/x/name.rb
            # 结果通常是 ../Formula/x/name.rb
            rel_link_target = os.path.join("..", target_rel_dir, f"{formula}.rb")
            if os.path.lexists(alias_path):
                os.remove(alias_path)
            os.symlink(rel_link_target, alias_path)
            print(f"[*] Created alias: {alias} -> {rel_link_target}")

    # 4. 构建与测试
    print(f"[*] Installing and testing {formula}...")
    run_cmd(["brew", "install", "-s", "--include-test", formula])
    run_cmd(["brew", "test", formula])

    # 5. 获取版本号用于提交信息
    info_json = json.loads(run_cmd(["brew", "info", "--json=v2", formula]))
    version = info_json['formulae'][0]['versions']['stable']
    commit_msg = f"{formula} {version} (new formula)"

    # 6. Git 操作
    print(f"[*] Committing and pushing to GitCode...")
    branch_name = f"migrate-{formula}"
    
    run_cmd(["git", "config", "user.name", GITCODE_USER])
    run_cmd(["git", "config", "user.email", GITCODE_EMAIL])
    
    # 切换分支
    subprocess.run(["git", "checkout", "-b", branch_name]) # 允许失败（如果分支已存在）
    
    run_cmd(["git", "add", rb_path])
    for alias in aliases:
        run_cmd(["git", "add", os.path.join("Aliases", alias)])
    
    run_cmd(["git", "commit", "-m", commit_msg])
    run_cmd(["git", "push", "-f", GITCODE_REPO, branch_name])

    # 7. 生成 PR
    create_pr(f"{GITCODE_USER}:{branch_name}", commit_msg)

    print(f"\n[OK] Successfully migrated {formula}!")

if __name__ == "__main__":
    main()
