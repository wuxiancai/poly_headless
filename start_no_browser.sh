#!/bin/bash

# Polymarket 自动交易系统 - 无浏览器模式启动脚本
# 显示GUI界面，但Chrome浏览器在后台运行

echo "🖥️ 启动 Polymarket 自动交易系统 (无浏览器模式)"
echo "==============================================="
echo "📋 模式说明:"
echo "   ✅ GUI界面正常显示"
echo "   ✅ 可实时监控价格变化"
echo "   ✅ 可修改交易参数和本金设置"
echo "   🔧 Chrome浏览器在后台运行（节省资源）"
echo "==============================================="

# 检查是否有现有进程在运行
if pgrep -f "crypto_trader.py" > /dev/null; then
    echo "⚠️ 检测到程序正在运行，正在停止现有进程..."
    pkill -f "crypto_trader.py"
    sleep 2
fi

# 启动无浏览器模式程序
echo "🔧 启动无浏览器模式程序..."
python3 crypto_trader.py --no-browser &
PID=$!

echo "✅ 程序已启动 (PID: $PID)"
echo "📊 GUI界面已显示，可进行实时监控和参数调整"
echo ""
echo "💡 功能说明:"
echo "   📈 实时价格监控: 在GUI界面查看币安价格变化"
echo "   💰 本金设置: 可在界面中修改初始本金和交易金额"
echo "   🎯 交易价格: 可实时调整买入和卖出价格"
echo "   📝 日志查看: 程序运行日志实时显示在控制台"
echo ""
echo "🎯 程序已成功启动，GUI界面可用于监控和调整参数"