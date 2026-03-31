#!/bin/sh
set -e

FORMULA="$1"
WORKDIR=$(pwd)

if [ -z "$FORMULA" ] || [ -z "$GITCODE_USER" ] || [ -z "$GITCODE_EMAIL" ]  || [ -z "$GITCODE_TOKEN" ]; then
    echo "Error: Missing arguments."
    exit 1
fi

echo "[*] Updating Homebrew..."
brew update

# 获取 Tap 路径
TAP_PATH="$(brew --repository harmonybrew/core)"
cd "$TAP_PATH"

# 检查是否以 "lib" 开头
case "$FORMULA" in
    lib*)
        # 显式确认：如果是 lib 开头，目录强制设为 lib
        FIRST_LETTER="lib"
        ;;
    *)
        # 其他情况按首字母
	FIRST_LETTER=$(echo "$FORMULA" | cut -c1 | tr '[:upper:]' '[:lower:]')
        ;;
esac

TARGET_DIR="Formula/$FIRST_LETTER"
echo "[*] Target directory: $TARGET_DIR"
mkdir -p "$TARGET_DIR"

echo "[*] Fetching ${FORMULA}.rb from upstream..."
UPSTREAM_URL="https://raw.githubusercontent.com/Homebrew/homebrew-core/main/Formula/$FIRST_LETTER/${FORMULA}.rb"
curl -fSLO "$UPSTREAM_URL"
mv "${FORMULA}.rb" "$TARGET_DIR/"

# 构建与测试
echo "[*] Building ${FORMULA}..."
brew install -s --include-test $FORMULA

echo "[*] Running brew test..."
brew test $FORMULA

# 提取版本号 (使用 brew info --json 获取稳定的版本字段)
VERSION=$(brew info --json=v2 "$FORMULA" | python3 -c "import sys, json; print(json.load(sys.stdin)['formulae'][0]['versions']['stable'])")

# 准备提交信息：遵循 <name> <version> (new formula)
COMMIT_MSG="${FORMULA} ${VERSION} (new formula)"

echo "[*] Pushing to GitCode with message: ${COMMIT_MSG}"
git config user.name "$GITCODE_USER"
git config user.email "$GITCODE_EMAIL"

BRANCH_NAME="migrate-${FORMULA}"
git checkout -b "$BRANCH_NAME" || git checkout "$BRANCH_NAME"
git add .
git commit -m "${COMMIT_MSG}"
git push -f "https://${GITCODE_USER}:${GITCODE_TOKEN}@gitcode.com/${GITCODE_USER}/homebrew-core.git" "$BRANCH_NAME"

# 输出变量供后续步骤使用
echo "MIGRATION_BRANCH=$BRANCH_NAME" >> $WORKDIR/output.txt
echo "MIGRATION_MSG=$COMMIT_MSG" >> $WORKDIR/output.txt
