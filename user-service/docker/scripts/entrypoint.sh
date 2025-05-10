#!/bin/bash
set -e

# 環境変数からポートを取得（デフォルト値を設定）
PORT=${USER_SERVICE_INTERNAL_PORT:-"8080"}

# 直接uvicornを実行（すべてのインターフェースでリッスン）
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2