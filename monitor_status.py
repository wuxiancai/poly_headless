#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无头模式状态监控脚本
用于查看crypto_trader.py在无头模式下的运行状态
"""

import os
import time
import subprocess
from datetime import datetime

def check_process_status():
    """检查crypto_trader.py进程是否在运行"""
    try:
        result = subprocess.run(['pgrep', '-f', 'crypto_trader.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return True, pids
        else:
            return False, []
    except Exception as e:
        return False, []

def read_latest_logs():
    """读取最新的日志信息"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        return "日志目录不存在"
    
    try:
        # 获取最新的日志文件
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        if not log_files:
            return "没有找到日志文件"
        
        latest_log = max(log_files, key=lambda x: os.path.getctime(os.path.join(log_dir, x)))
        log_path = os.path.join(log_dir, latest_log)
        
        # 读取最后20行日志
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return ''.join(lines[-20:]) if lines else "日志文件为空"
    except Exception as e:
        return f"读取日志失败: {e}"

def main():
    print("=" * 60)
    print("🔍 Crypto Trader 无头模式状态监控")
    print("=" * 60)
    
    while True:
        try:
            # 清屏
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print(f"📅 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 60)
            
            # 检查进程状态
            is_running, pids = check_process_status()
            if is_running:
                print(f"✅ 程序正在运行 (PID: {', '.join(pids)})")
            else:
                print("❌ 程序未运行")
            
            print("-" * 60)
            print("📋 最新日志信息:")
            print("-" * 60)
            
            # 显示最新日志
            logs = read_latest_logs()
            print(logs)
            
            print("-" * 60)
            print("💡 提示: 按 Ctrl+C 退出监控")
            print("🔄 自动刷新中...")
            
            # 等待5秒后刷新
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n👋 监控已停止")
            break
        except Exception as e:
            print(f"❌ 监控出错: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()