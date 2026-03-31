#!/usr/bin/python3

import requests
import sys
import os


def create_pr(formula, head_branch):
    token = os.getenv("GITCODE_TOKEN")
    owner = "Harmonybrew"
    repo = "homebrew-core"

    # 构造请求数据
    url = f"https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pulls"
    params = {"access_token": token}
    payload = {
        "title": os.getenv("COMMIT_MSG"),
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


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 create-gitcode-pr.py <formula> <head_branch>")
        sys.exit(1)

    create_pr(sys.argv[1], sys.argv[2])
