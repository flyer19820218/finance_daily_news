#!/bin/bash
# 總體經濟資料庫 — 一鍵同步 GitHub 腳本
cd "$(dirname "$0")"

echo "=========================================="
echo "🚀 準備同步總體經濟資料庫至 GitHub..."
echo "=========================================="

# 檢查是否有遠端倉庫關聯
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "⚠️ 尚未設定 GitHub 遠端儲存庫 (origin)！"
    echo "請先執行: git remote add origin https://github.com/<您的帳號>/<儲存庫名稱>.git"
    exit 1
fi

# 加入所有變更與新增檔案
git add .

# 檢查是否有變更需要提交
if git diff --staged --quiet; then
    echo "ℹ️ 目前沒有任何檔案變更需要上傳。"
    exit 0
fi

# 產生附帶時間的 commit 訊息
COMMIT_TIME=$(date '+%Y-%m-%d %H:%M:%S')
git commit -m "更新總經報告與數據 ($COMMIT_TIME)"

# 推送至 main 分支
echo "📤 正在推送至 GitHub (main 分支)..."
git push origin main

echo "=========================================="
echo "✅ 同步成功！網頁與檔案已更新至 GitHub。"
echo "=========================================="
