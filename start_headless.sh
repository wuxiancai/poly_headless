#!/bin/bash

# Polymarket 无头模式启动脚本

echo "🚀 启动 Polymarket 自动交易系统 (无头模式)"
echo "=" | tr -d '\n' | head -c 50; echo

# 检查是否已有程序在运行
if pgrep -f "crypto_trader.py" > /dev/null; then
    echo "⚠️  检测到程序已在运行"
    echo "📋 当前运行的进程:"
    ps aux | grep "crypto_trader.py" | grep -v grep
    echo
    read -p "是否要停止现有进程并重新启动? (y/N): " choice
    if [[ $choice =~ ^[Yy]$ ]]; then
        echo "🛑 停止现有进程..."
        pkill -f "crypto_trader.py"
        sleep 2
    else
        echo "❌ 取消启动"
        exit 1
    fi
fi

echo "🔧 启动无头模式程序..."
# 在后台启动程序
nohup python3 crypto_trader.py --headless > crypto_trader_headless.log 2>&1 &
PID=$!

echo "✅ 程序已在后台启动 (PID: $PID)"
echo "📝 日志文件: crypto_trader_headless.log"
echo "📊 监控命令: python3 monitor_status.py"
echo
echo "💡 常用命令:"
echo "   查看实时日志: tail -f crypto_trader_headless.log"
echo "   查看程序状态: python3 monitor_status.py"
echo "   停止程序: pkill -f crypto_trader.py"
echo
echo "🎯 程序已成功启动，可以关闭终端窗口"