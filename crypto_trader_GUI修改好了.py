# -*- coding: utf-8 -*-
# polymarket_v1
import platform
import tkinter as tk
from tkinter import E, ttk, messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import json
import threading
import time
import os
import subprocess
from screeninfo import get_monitors
import logging
from datetime import datetime, timezone, timedelta
import re
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import pyautogui
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import socket
import sys
import logging
from xpath_config import XPathConfig
from threading import Thread
import random
import requests
import websocket


class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 如果logger已经有处理器，则不再添加新的处理器
        if not self.logger.handlers:
            # 创建logs目录（如果不存在）
            if not os.path.exists('logs'):
                os.makedirs('logs')
                
            # 设置日志文件名（使用当前日期）
            log_filename = f"logs/{datetime.now().strftime('%Y%m%d')}.log"
            
            # 创建文件处理器
            file_handler = logging.FileHandler(log_filename, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # 创建控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            
            # 创建格式器
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加处理器到logger
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def critical(self, message):
        self.logger.critical(message)

class CryptoTrader:
    def __init__(self):
        super().__init__()
        self.logger = Logger('poly')
        self.driver = None
        self.running = False
        self.trading = False
        self.login_running = False
        # 添加交易状态
        self.start_login_monitoring_running = False
        self.url_monitoring_running = False
        self.refresh_page_running = False

        # 添加重试次数和间隔
        self.retry_count = 3
        self.retry_interval = 5

        # 添加交易次数计数器
        self.trade_count = 0
        self.sell_count = 0 
        self.reset_trade_count = 0 
        
        # 添加定时器
        self.refresh_page_timer = None  # 用于存储定时器ID
        self.url_check_timer = None
        # 添加登录状态监控定时器
        self.login_check_timer = None
        self.monitor_xpath_timer = None
        self.get_zero_time_cash_timer = None
        self.get_binance_zero_time_price_timer = None
        self.get_binance_price_websocket_timer = None
        self.comparison_binance_price_timer = None
        self.schedule_auto_find_coin_timer = None

        # 添加URL and refresh_page监控锁
        self.url_monitoring_lock = threading.Lock()
        self.refresh_page_lock = threading.Lock()
        self.login_attempt_lock = threading.Lock()
        self.restart_lock = threading.Lock()  # 添加重启锁
        self.is_restarting = False  # 重启状态标志

        # 初始化本金
        self.initial_amount = 2.5
        self.first_rebound = 220
        self.n_rebound = 120
        self.profit_rate = 2.2
        self.doubling_weeks = 30

        # 默认买价
        self.default_target_price = 52 # 不修改
        # 默认反水卖价
        self.default_sell_price_backwater = 47 # 不修改
        # 默认卖价
        self.default_sell_price = 1 # 不修改

        # 默认卖价
        self.default_normal_sell_price = 99 # 不修改

        # 买入价格冗余
        self.price_premium = 3 # 不修改

        # 买入触发条件之一:最少成交数量SHARES
        self.asks_shares = 100 # 不修改
        self.bids_shares = 100# 不修改
        
        # 按钮区域按键 WIDTH
        self.button_width = 8 # 不修改
        # 停止事件
        self.stop_event = threading.Event()
        # 初始化金额为 0
        for i in range(1, 4):  # 1到4
            setattr(self, f'yes{i}_amount', 0)
            setattr(self, f'no{i}_amount', 0)
        # 初始化 UI 界面
        try:
            self.config = self.load_config()
            self.setup_gui()
            # 注释掉固定窗口大小的设置，让后面的自适应代码处理
            # self.root.update_idletasks()  # 确保窗口尺寸已计算
            # window_width = self.root.winfo_width()
            # screen_height = self.root.winfo_screenheight()
            # 设置窗口位置在屏幕最左边
            # self.root.geometry(f"{window_width}x{screen_height}+0+0")
        except Exception as e:
            self.logger.error(f"初始化失败: {str(e)}")
            messagebox.showerror("错误", "程序初始化失败，请检查日志文件")
            sys.exit(1)

        # 打印启动参数
        self.logger.info(f"✅ 初始化成功: {sys.argv}")
      
    def load_config(self):
        """加载配置文件，保持默认格式"""
        try:
            # 默认配置
            default_config = {
                'website': {'url': ''},
                'trading': {
                    'Up1': {'target_price': 0, 'amount': 0},
                    'Up2': {'target_price': 0, 'amount': 0},
                    'Up3': {'target_price': 0, 'amount': 0},
                    'Up4': {'target_price': 0, 'amount': 0},
                    'Up5': {'target_price': 0, 'amount': 0},

                    'Down1': {'target_price': 0, 'amount': 0},
                    'Down2': {'target_price': 0, 'amount': 0},
                    'Down3': {'target_price': 0, 'amount': 0},
                    'Down4': {'target_price': 0, 'amount': 0},
                    'Down5': {'target_price': 0, 'amount': 0}
                },
                'url_history': []
            }
            
            try:
                # 尝试读取现有配置
                with open('config.json', 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.logger.info("✅ 成功加载配置文件")
                    
                    # 合并配置
                    for key in default_config:
                        if key not in saved_config:
                            saved_config[key] = default_config[key]
                        elif isinstance(default_config[key], dict):
                            for sub_key in default_config[key]:
                                if sub_key not in saved_config[key]:
                                    saved_config[key][sub_key] = default_config[key][sub_key]
                    return saved_config
            except FileNotFoundError:
                self.logger.warning("配置文件不存在，创建默认配置")
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
            except json.JSONDecodeError:
                self.logger.error("配置文件格式错误，使用默认配置")
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4, ensure_ascii=False)
                return default_config
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            raise
    
    def save_config(self):
        """保存配置到文件,保持JSON格式化"""
        try:
            for position, frame in [('Yes', self.yes_frame), ('No', self.no_frame)]:
                # 精确获取目标价格和金额的输入框
                entries = [
                    w for w in frame.winfo_children() 
                    if isinstance(w, ttk.Entry) and "price" in str(w).lower()
                ]
                amount_entries = [
                    w for w in frame.winfo_children()
                    if isinstance(w, ttk.Entry) and "amount" in str(w).lower()
                ]

                # 添加类型转换保护
                try:
                    target_price = float(entries[0].get().strip() or '0') if entries else 0
                except ValueError as e:
                    self.logger.error(f"价格转换失败: {e}, 使用默认值0")
                    target_price = 0

                try:
                    amount = float(amount_entries[0].get().strip() or '0') if amount_entries else 0
                except ValueError as e:
                    self.logger.error(f"金额转换失败: {e}, 使用默认值0")
                    amount = 0

                # 使用正确的配置键格式
                config_key = f"{position}1"  # 改为Yes1/No1
                self.config['trading'][config_key]['target_price'] = target_price
                self.config['trading'][config_key]['amount'] = amount

            # 处理网站地址历史记录
            current_url = self.url_entry.get().strip()
            if current_url:
                if 'url_history' not in self.config:
                    self.config['url_history'] = []
                
                # 清空历史记录
                self.config['url_history'].clear()
                # 只保留当前URL
                self.config['url_history'].insert(0, current_url)
                # 确保最多保留1条
                self.config['url_history'] = self.config['url_history'][:1]
                self.url_entry['values'] = self.config['url_history']
            
            # 保存配置到文件，使用indent=4确保格式化
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f)
                
        except Exception as e:
            self.logger.error(f"保存配置失败: {str(e)}")
            raise

    """从这里开始设置 GUI 直到 771 行"""
    def setup_gui(self):
        """优化后的GUI界面设置"""
        self.root = tk.Tk()
        self.root.title("Polymarket Automatic Trading System Power by @wuxiancai")
        
        # 创建主滚动框架
        main_canvas = tk.Canvas(self.root, bg='#f8f9fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        
        # 创建内容Frame，放在Canvas里
        scrollable_frame = ttk.Frame(main_canvas)
        
        # 让Frame成为Canvas的一个window
        canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # 让scrollable_frame宽度始终和canvas一致
        def _on_canvas_configure(event):
            main_canvas.itemconfig(canvas_window, width=event.width)
        main_canvas.bind('<Configure>', _on_canvas_configure)

        # 让canvas的scrollregion始终覆盖全部内容
        def _on_frame_configure(event):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        scrollable_frame.bind('<Configure>', _on_frame_configure)

        # pack布局，保证canvas和scrollbar都能自适应
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 优化的滚动事件处理
        def _on_mousewheel(event):
            try:
                system = platform.system()
                if system == 'Linux':
                    delta = -1 if event.num == 4 else 1 if event.num == 5 else 0
                elif system == 'Darwin':
                    delta = -int(event.delta)
                else:  # Windows
                    delta = -int(event.delta/120)
                if delta:
                    main_canvas.yview_scroll(delta, "units")
            except Exception as e:
                self.logger.error(f"滚动事件处理错误: {str(e)}")
        
        def _on_arrow_key(event):
            try:
                delta = -1 if event.keysym == 'Up' else 1 if event.keysym == 'Down' else 0
                if delta:
                    main_canvas.yview_scroll(delta, "units")
            except Exception as e:
                self.logger.error(f"键盘滚动事件处理错误: {str(e)}")
        
        # 绑定滚动事件
        if platform.system() == 'Linux':
            main_canvas.bind_all("<Button-4>", _on_mousewheel)
            main_canvas.bind_all("<Button-5>", _on_mousewheel)
        else:
            main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_canvas.bind_all("<Up>", _on_arrow_key)
        main_canvas.bind_all("<Down>", _on_arrow_key)
        
        # 创建统一的样式配置
        style = ttk.Style()
        
        # 根据系统设置字体
        if platform.system() == 'Darwin':
            small_font = ('SF Pro Display', 10, 'normal')
            base_font = ('SF Pro Display', 12, 'normal')
            bold_font = ('SF Pro Display', 12, 'bold')
            large_font = ('SF Pro Display', 14, 'normal')
            title_font = ('SF Pro Display', 14, 'bold')
        else:  # Linux and others
            small_font = ('DejaVu Sans', 10, 'normal')
            base_font = ('DejaVu Sans', 11, 'normal')
            bold_font = ('DejaVu Sans', 11, 'bold')
            large_font = ('DejaVu Sans', 13, 'normal')
            title_font = ('DejaVu Sans', 14, 'bold')
        
        # 配置样式
        styles_config = {
            'Red.TButton': {'foreground': '#dc3545', 'font': bold_font},
            'Black.TButton': {'foreground': '#212529', 'font': base_font},
            'Blue.TButton': {'foreground': '#0d6efd', 'font': base_font},
            'Red.TEntry': {'foreground': '#dc3545', 'font': base_font},
            'Blue.TLabel': {'foreground': '#0d6efd', 'font': large_font},
            'Red.TLabel': {'foreground': '#dc3545', 'font': large_font},
            'Black.TLabel': {'foreground': '#212529', 'font': base_font},
            'Top.TLabel': {'foreground': '#212529', 'font': base_font},
            'Warning.TLabelframe': {'font': title_font, 'foreground': '#FF0000', 'anchor': 'center'},
            'LeftAligned.TButton': {'anchor': 'w', 'foreground': '#212529', 'padding': (1, 1)},
            'Red.TLabelframe.Label': {'foreground': '#dc3545'},
            'LeftBlack.TButton': {'foreground': '#212529', 'font': base_font},
            'Black.TLabelframe': {'font': small_font, 'foreground': '#212529', 'anchor': 'center'}
        }
        
        for style_name, config in styles_config.items():
            style.configure(style_name, **config)
        
        # 金额设置框架
        amount_settings_frame = ttk.LabelFrame(scrollable_frame, text="⚠️ 娟娟细流,终入大海! 宁静致远,财富自由!", 
                                             padding=(10, 8), style='Warning.TLabelframe')
        amount_settings_frame.pack(fill="x", padx=8, pady=6)

        # 创建主要设置容器
        settings_container = ttk.Frame(amount_settings_frame)
        settings_container.pack(fill=tk.X, pady=5)
        
        # 金额设置区域
        amount_frame = ttk.Frame(settings_container)
        amount_frame.pack(fill=tk.X, pady=2)

        # 设置金额配置
        settings_items = [
            ("Initial", "initial_amount_entry", self.initial_amount, 3),
            ("Turn-1", "first_rebound_entry", self.first_rebound, 3),
            ("Turn-N", "n_rebound_entry", self.n_rebound, 3),
            ("Margin", "profit_rate_entry", f"{self.profit_rate}%", 4)
        ]
        
        for i, (label_text, entry_attr, default_value, width) in enumerate(settings_items):
            item_frame = ttk.Frame(amount_frame)
            item_frame.pack(side=tk.LEFT, padx=2)
            
            ttk.Label(item_frame, text=label_text, style='Top.TLabel').pack(side=tk.LEFT, padx=(0, 2))
            entry = ttk.Entry(item_frame, width=width, font=base_font)
            entry.pack(side=tk.LEFT)
            entry.insert(0, str(default_value))
            setattr(self, entry_attr, entry)

        # 翻倍天数设置
        double_frame = ttk.Frame(amount_frame)
        double_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(double_frame, text="DB", style='Top.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.doubling_weeks_entry = ttk.Entry(double_frame, width=3)
        self.doubling_weeks_entry.pack(side=tk.LEFT)
        self.doubling_weeks_entry.insert(0, str(self.doubling_weeks))
        
        # 监控网站配置
        url_frame = ttk.LabelFrame(scrollable_frame, text="🌐 Website Monitoring", padding=(8, 5))
        url_frame.pack(fill="x", padx=8, pady=6)
        
        url_container = ttk.Frame(url_frame)
        url_container.pack(fill="x", pady=2)
        
        ttk.Label(url_container, text="URL:", style='Black.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry = ttk.Combobox(url_container, font=base_font, width=40)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 从配置文件加载历史记录
        if 'url_history' not in self.config:
            self.config['url_history'] = []
        self.url_entry['values'] = self.config['url_history']
        
        # 如果有当前URL，设置为默认值
        current_url = self.config.get('website', {}).get('url', '')
        if current_url:
            self.url_entry.set(current_url)
        
        # 控制按钮区域
        control_frame = ttk.LabelFrame(scrollable_frame, text="🎮 Control Panel", padding=(8, 5))
        control_frame.pack(fill="x", padx=8, pady=6)
        
        # 主控制按钮行
        main_controls = ttk.Frame(control_frame)
        main_controls.pack(fill="x", pady=2)
        
        # 开始按钮
        self.start_button = ttk.Button(main_controls, text="▶ Start", 
                                      command=self.start_monitoring, width=5,
                                      style='Blue.TButton')
        self.start_button.pack(side=tk.LEFT, padx=3)
        
        # 设置金额按钮
        self.set_amount_button = ttk.Button(main_controls, text="Set 💰", width=5,
                                           command=self.set_yes_no_cash, style='LeftAligned.TButton')
        self.set_amount_button.pack(side=tk.LEFT, padx=3)
        self.set_amount_button['state'] = 'disabled'

        # 币种选择
        ttk.Label(main_controls, text="Coin:", style='Black.TLabel').pack(side=tk.LEFT, padx=(10, 2))
        self.coin_combobox = ttk.Combobox(main_controls, values=['BTC', 'ETH', 'SOL', 'XRP'], width=3)
        self.coin_combobox.pack(side=tk.LEFT, padx=2)
        self.coin_combobox.set('BTC')
        
        # CASH 显示
        ttk.Label(main_controls, text="Cash:", style='Black.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.zero_time_cash_label = ttk.Label(main_controls, text="0", style='Red.TLabel')
        self.zero_time_cash_label.pack(side=tk.LEFT)

         # 重启次数显示
        ttk.Label(main_controls, text="Reset:", style='Black.TLabel').pack(side=tk.LEFT, padx=(10, 2))
        self.reset_count_label = ttk.Label(main_controls, text="0", style='Red.TLabel')
        self.reset_count_label.pack(side=tk.LEFT, padx=(0, 15))

        # 交易信息显示区域
        trading_info_frame = ttk.LabelFrame(scrollable_frame, text="📊 Trading Information", padding=(8, 5))
        trading_info_frame.pack(fill="x", padx=8, pady=6)

        # 交易币对显示
        pair_container = ttk.Frame(trading_info_frame)
        pair_container.pack(fill="x", pady=2)
        
        ttk.Label(pair_container, text="Trading Pair:", style='Black.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        self.trading_pair_label = ttk.Label(pair_container, text="Trader-type", style='Black.TLabel')
        self.trading_pair_label.pack(side=tk.LEFT)

        # 币安价格信息
        binance_container = ttk.Frame(trading_info_frame)
        binance_container.pack(fill="x", pady=2)
        
        # 价格信息网格布局
        price_info_items = [
            ("🌙Midnight:", "binance_zero_price_label", "0"),
            ("⚡Now:", "binance_now_price_label", "0"),
            ("📈:", "binance_rate_display", "0%")
        ]
        
        for i, (label_text, attr_name, default_value) in enumerate(price_info_items):
            item_frame = ttk.Frame(binance_container)
            item_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            ttk.Label(item_frame, text=label_text, style='Black.TLabel').pack(side=tk.LEFT)
            
            if attr_name == "binance_rate_display":
                # 创建涨跌显示容器
                rate_frame = ttk.Frame(item_frame)
                rate_frame.pack(side=tk.LEFT, padx=(2, 0))
                
                self.binance_rate_label = ttk.Label(rate_frame, text="0", style='Black.TLabel')
                self.binance_rate_label.pack(side=tk.LEFT)
                
                self.binance_rate_symbol_label = ttk.Label(rate_frame, text="%", style='Black.TLabel')
                self.binance_rate_symbol_label.pack(side=tk.LEFT)
            else:
                label = ttk.Label(item_frame, text=default_value, font=large_font, foreground='blue')
                label.pack(side=tk.LEFT, padx=(2, 0))
                setattr(self, attr_name, label)
        
        # 实时价格显示区域
        price_frame = ttk.LabelFrame(scrollable_frame, text="💰 Live Prices", padding=(8, 5))
        price_frame.pack(fill="x", padx=8, pady=6)
        
        # 价格显示容器
        prices_container = ttk.Frame(price_frame)
        prices_container.pack(fill="x", pady=2)
        
        # Up/Down 价格和份额显示
        price_items = [
            ("📈 Up:", "yes_price_label", "Up: waiting..."),
            ("📉 Down:", "no_price_label", "Down: waiting...")
        ]
        
        for i, (icon_text, attr_name, default_text) in enumerate(price_items):
            item_container = ttk.Frame(prices_container)
            item_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # 价格显示
            price_frame_item = ttk.Frame(item_container)
            price_frame_item.pack(fill="x", pady=1)
            
            price_label = ttk.Label(price_frame_item, text=default_text, 
                                   font=(base_font[0], 16, 'bold'), foreground='#9370DB')
            price_label.pack()
            setattr(self, attr_name, price_label)
            
            # 份额显示
            shares_frame_item = ttk.Frame(item_container)
            shares_frame_item.pack(fill="x", pady=1)
            
            shares_attr = "up_shares_label" if "yes_price_label" == attr_name else "down_shares_label"
            shares_label = ttk.Label(shares_frame_item, text="Shares: waiting...",
                                   font=(base_font[0], 14, 'normal'), foreground='#9370DB')
            shares_label.pack()
            setattr(self, shares_attr, shares_label)

        # 资金显示区域
        balance_frame = ttk.LabelFrame(scrollable_frame, text="💳 Account Balance", padding=(8, 5))
        balance_frame.pack(fill="x", padx=8, pady=6)
        
        balance_container = ttk.Frame(balance_frame)
        balance_container.pack(fill="x", pady=2)
        
        # Portfolio 和 Cash 显示
        balance_items = [
            ("📊 Portfolio:", "portfolio_label", "Portfolio: waiting..."),
            ("💵 Cash:", "cash_label", "Cash: waiting...")
        ]
        
        for i, (label_text, attr_name, default_text) in enumerate(balance_items):
            item_frame = ttk.Frame(balance_container)
            item_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
            
            balance_label = ttk.Label(item_frame, text=default_text, 
                                     font=(base_font[0], 16, 'bold'), foreground='#16A34A')
            balance_label.pack()
            setattr(self, attr_name, balance_label)
        
        # Yes/No 交易配置区域
        trading_config_frame = ttk.LabelFrame(scrollable_frame, text="⚙️ Trading Configuration", padding=(8, 5))
        trading_config_frame.pack(fill="x", padx=8, pady=6)
        
        # 创建左右分栏
        config_container = ttk.Frame(trading_config_frame)
        config_container.pack(fill="x", pady=2)
        
        # YES 区域配置
        self.yes_frame = ttk.LabelFrame(config_container, text="📈 YES Positions", padding=(5, 3))
        self.yes_frame.grid(row=0, column=0, padx=(0, 4), sticky="nsew")
        config_container.grid_columnconfigure(0, weight=1)

        # No 配置区域
        self.no_frame = ttk.LabelFrame(config_container, text="📉 NO Positions", padding=(5, 3))
        self.no_frame.grid(row=0, column=1, padx=(4, 0), sticky="nsew")
        config_container.grid_columnconfigure(1, weight=1)
        
        # YES 配置项
        yes_configs = [
            ("Yes1", "yes1_price_entry", "yes1_amount_entry", 
             str(self.config['trading']['Yes1']['target_price']), 
             str(self.config['trading']['Yes1']['amount'])),
            ("Yes2", "yes2_price_entry", "yes2_amount_entry", "0", "0"),
            ("Yes3", "yes3_price_entry", "yes3_amount_entry", "0", "0"),
            ("Yes4", "yes4_price_entry", "yes4_amount_entry", "0", "0"),
            ("Yes5", "yes5_price_entry", "yes5_amount_entry", "0", "0")
        ]
        
        for i, (label, price_attr, amount_attr, price_val, amount_val) in enumerate(yes_configs):
            row_base = i * 2
            
            # 价格标签和输入框
            ttk.Label(self.yes_frame, text=f"{label} Price(¢):", style='Black.TLabel').grid(
                row=row_base, column=0, padx=3, pady=2, sticky="w")
            price_entry = ttk.Entry(self.yes_frame, font=base_font)
            price_entry.insert(0, price_val)
            price_entry.grid(row=row_base, column=1, padx=3, pady=2, sticky="ew")
            setattr(self, price_attr, price_entry)
            
            # 金额标签和输入框
            ttk.Label(self.yes_frame, text=f"{label} Amount:", style='Black.TLabel').grid(
                row=row_base+1, column=0, padx=3, pady=2, sticky="w")
            amount_entry = ttk.Entry(self.yes_frame, font=base_font)
            amount_entry.insert(0, amount_val)
            amount_entry.grid(row=row_base+1, column=1, padx=3, pady=2, sticky="ew")
            setattr(self, amount_attr, amount_entry)
        
        # 配置列权重
        self.yes_frame.grid_columnconfigure(1, weight=1)

        # NO 配置项
        no_configs = [
            ("No1", "no1_price_entry", "no1_amount_entry", 
             str(self.config['trading']['No1']['target_price']), 
             str(self.config['trading']['No1']['amount'])),
            ("No2", "no2_price_entry", "no2_amount_entry", "0", "0"),
            ("No3", "no3_price_entry", "no3_amount_entry", "0", "0"),
            ("No4", "no4_price_entry", "no4_amount_entry", "0", "0"),
            ("No5", "no5_price_entry", "no5_amount_entry", "0", "0")
        ]
        
        for i, (label, price_attr, amount_attr, price_val, amount_val) in enumerate(no_configs):
            row_base = i * 2
            
            # 价格标签和输入框
            ttk.Label(self.no_frame, text=f"{label} Price(¢):", style='Black.TLabel').grid(
                row=row_base, column=0, padx=3, pady=2, sticky="w")
            price_entry = ttk.Entry(self.no_frame, font=base_font)
            price_entry.insert(0, price_val)
            price_entry.grid(row=row_base, column=1, padx=3, pady=2, sticky="ew")
            setattr(self, price_attr, price_entry)
            
            # 金额标签和输入框
            ttk.Label(self.no_frame, text=f"{label} Amount:", style='Black.TLabel').grid(
                row=row_base+1, column=0, padx=3, pady=2, sticky="w")
            amount_entry = ttk.Entry(self.no_frame, font=base_font)
            amount_entry.insert(0, amount_val)
            amount_entry.grid(row=row_base+1, column=1, padx=3, pady=2, sticky="ew")
            setattr(self, amount_attr, amount_entry)
        
        # 配置列权重
        self.no_frame.grid_columnconfigure(1, weight=1)

        # 创建按钮区域
        trade_frame = ttk.LabelFrame(scrollable_frame, text="Buttons", style='Black.TLabelframe')
        trade_frame.pack(fill="x", padx=2, pady=2)
        
        # 按钮配置
        button_configs = [
            # 第一行：主要交易按钮
            [("buy_button", "Buy", self.click_buy),
             ("buy_yes_button", "Buy-Yes", self.click_buy_yes),
             ("buy_no_button", "Buy-No", self.click_buy_no),
             ("buy_confirm_button", "Buy-conf", self.click_buy_confirm_button)],
            # 第二行：Yes金额按钮
            [("amount_yes1_button", "Amount-Y1", None),
             ("amount_yes2_button", "Amount-Y2", None),
             ("amount_yes3_button", "Amount-Y3", None),
             ("amount_yes4_button", "Amount-Y4", None)],
            # 第三行：No金额按钮
            [("amount_no1_button", "Amount-N1", None),
             ("amount_no2_button", "Amount-N2", None),
             ("amount_no3_button", "Amount-N3", None),
             ("amount_no4_button", "Amount-N4", None)],
            # 第四行：卖出按钮
            [("position_sell_yes_button", "P-Sell-Yes", self.click_position_sell_yes),
             ("position_sell_no_button", "P-Sell-No", self.click_position_sell_no),
             ("sell_confirm_button", "Sell-conf", self.click_sell_confirm_button),
             (None, None, None)]  # 占位符
        ]
        
        for row, button_row in enumerate(button_configs):
            for col, (attr_name, text, command) in enumerate(button_row):
                if attr_name:  # 跳过占位符
                    button = ttk.Button(trade_frame, text=text, width=self.button_width)
                    
                    if command:
                        button.configure(command=command)
                    else:
                        # 金额按钮使用特殊绑定
                        button.bind('<Button-1>', self.click_amount)
                    
                    button.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
                    setattr(self, attr_name, button)
        
        # 配置列权重使按钮均匀分布
        for i in range(4):
            trade_frame.grid_columnconfigure(i, weight=1)
            
        # 窗口自适应内容大小
        self.root.update_idletasks()
        
        content_height = scrollable_frame.winfo_reqheight()
        
        # 计算并设置窗口的初始大小
        final_width = 470
        # 高度自适应，但有最小和最大值
        final_height = max(400, min(content_height + 20, 800))

        self.root.geometry(f'{final_width}x{final_height}+0+0')
        self.root.minsize(470, 1050)
        
        # 最后一次更新确保布局正确
        self.root.update_idletasks()
    """以上代码从240行到 742 行是设置 GUI 界面的"""

    """以下代码从 745 行到行是程序交易逻辑"""
    def start_monitoring(self):
        """开始监控"""
        # 直接使用当前显示的网址
        target_url = self.url_entry.get()
        self.logger.info(f"\033[34m✅ 开始监控网址: {target_url}\033[0m")
        
        # 启用开始按钮，启用停止按钮
        self.start_button['state'] = 'disabled'
            
        # 将"开始监控"文字变为红色
        self.start_button.configure(style='Red.TButton')
        
        # 重置交易次数计数器
        self.trade_count = 0
            
        # 启动浏览器作线程
        threading.Thread(target=self._start_browser_monitoring, args=(target_url,), daemon=True).start()
        """到这里代码执行到了 995 行"""

        self.running = True

        # 启用设置金额按钮
        self.set_amount_button['state'] = 'normal'

        # 检查是否登录
        self.login_check_timer = self.root.after(6000, self.start_login_monitoring)

        # 启动URL监控
        self.url_check_timer = self.root.after(10000, self.start_url_monitoring)

        # 启动零点 CASH 监控
        self.get_zero_time_cash_timer = self.root.after(12000, self.get_zero_time_cash)

        # 启动币安零点时价格监控
        self.get_binance_zero_time_price_timer = self.root.after(14000, self.get_binance_zero_time_price)
        
        # 启动币安实时价格监控
        self.get_binance_price_websocket_timer = self.root.after(16000, self.get_binance_price_websocket)

        # 启动币安价格对比
        self.comparison_binance_price_timer = self.root.after(20000, self.comparison_binance_price)

        # 启动自动找币
        self.schedule_auto_find_coin_timer = self.root.after(30000, self.schedule_auto_find_coin)

        # 启动页面刷新
        self.refresh_page_timer = self.root.after(40000, self.refresh_page)
        self.logger.info("\033[34m✅ 启动页面刷新成功!\033[0m")
        
        # 启动 XPath 监控
        self.monitor_xpath_timer = self.monitor_xpath_timer = self.root.after(600000, self.monitor_xpath_elements)

    def _start_browser_monitoring(self, new_url):
        """在新线程中执行浏览器操作"""
        try:
            if not self.driver and not self.is_restarting:
                chrome_options = Options()
                chrome_options.debugger_address = "127.0.0.1:9222"
                chrome_options.add_argument('--disable-dev-shm-usage')
                
                system = platform.system()
                if system == 'Linux':
                    # 添加与启动脚本一致的所有参数
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-gpu')
                    chrome_options.add_argument('--disable-software-rasterizer')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--disable-background-networking')
                    chrome_options.add_argument('--disable-default-apps')
                    chrome_options.add_argument('--disable-extensions')
                    chrome_options.add_argument('--disable-sync')
                    chrome_options.add_argument('--metrics-recording-only')
                    chrome_options.add_argument('--no-first-run')
                    chrome_options.add_argument('--disable-translate')
                    chrome_options.add_argument('--disable-background-timer-throttling')
                    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
                    chrome_options.add_argument('--disable-renderer-backgrounding')
                    chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees,SitePerProcess,IsolateOrigins')
                    chrome_options.add_argument('--noerrdialogs')

                self.driver = webdriver.Chrome(options=chrome_options)
            try:
                # 在当前标签页打开URL
                self.driver.get(new_url)
                
                # 等待页面加载
                WebDriverWait(self.driver, 60).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                self.logger.info("\033[34m✅ 浏览器启动成功!\033[0m")
                # 保存配置
                if 'website' not in self.config:
                    self.config['website'] = {}
                self.config['website']['url'] = new_url
                self.save_config()
                
                # 更新交易币对显示
                try:
                    pair = re.search(r'event/([^?]+)', new_url)
                    if pair:
                        self.trading_pair_label.config(text=pair.group(1))
                    else:
                        self.trading_pair_label.config(text="无识别事件名称")
                except Exception:
                    self.trading_pair_label.config(text="解析失败")
                    
                #  开启监控
                self.running = True
                
                # 启动监控线程
                self.monitoring_thread = threading.Thread(target=self.monitor_prices, daemon=True)
                self.monitoring_thread.start()
                self.logger.info("\033[34m✅ 启动实时监控价格和资金线程\033[0m")
                
            except Exception as e:
                error_msg = f"加载网站失败: {str(e)}"
                self.logger.error(error_msg)
                self._show_error_and_reset(error_msg)  
        except Exception as e:
            error_msg = f"启动浏览器失败: {str(e)}"
            self.logger.error(f"启动监控失败: {str(e)}")
            self.logger.error(error_msg)
            self._show_error_and_reset(error_msg)

    def _show_error_and_reset(self, error_msg):
        """显示错误并重置按钮状态"""
        # 用after方法确保在线程中执行GUI操作
        # 在尝试显示消息框之前，检查Tkinter主窗口是否仍然存在
        if self.root and self.root.winfo_exists():
            self.root.after(0, lambda: messagebox.showerror("错误", error_msg))
            self.root.after(0, lambda: self.start_button.config(state='normal'))
        else:
            # 如果主窗口不存在，则直接记录错误到日志
            self.logger.error(f"GUI主窗口已销毁,无法显示错误消息: {error_msg}")
        self.running = False

    def monitor_prices(self):
        """检查价格变化"""
        try:
            # 确保浏览器连接
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
                
            target_url = self.url_entry.get()
            
            # 使用JavaScript创建并点击链接来打开新标签页
            js_script = """
                const a = document.createElement('a');
                a.href = arguments[0];
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            """
            self.driver.execute_script(js_script, target_url)
            
            # 等待新标签页打开
            time.sleep(1)
            
            # 切换到新打开的标签页
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
           
            # 开始监控价格
            while not self.stop_event.is_set():  # 改用事件判断
                try:
                    self.check_balance()
                    self.check_prices()
                    time.sleep(1)
                except Exception as e:
                    if not self.stop_event.is_set():  # 仅在未停止时记录错误
                        self.logger.error(f"监控失败: {str(e)}")
                    time.sleep(self.retry_interval)
        except Exception as e:
            if not self.stop_event.is_set():
                self.logger.error(f"加载页面失败: {str(e)}")
            self.stop_monitoring()
    
    def restart_browser(self,force_restart=True):
        """统一的浏览器重启/重连函数
        Args:
            force_restart: True=强制重启Chrome进程,False=尝试重连现有进程
        """
        # 检查是否已在重启中
        with self.restart_lock:
            if self.is_restarting:
                self.logger.info("浏览器正在重启中，跳过重复重启")
                return True
            self.is_restarting = True

        self._send_chrome_alert_email()
        try:
            self.logger.info(f"正在{'重启' if force_restart else '重连'}浏览器...")
            
            # 1. 清理现有连接
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
            
            # 2. 如果需要强制重启，启动新的Chrome进程
            if force_restart:
                try:
                    # 根据操作系统选择启动脚本
                    script_path = ('start_chrome_macos.sh' if platform.system() == 'Darwin' 
                                else 'start_chrome_aliyun.sh')
                    script_path = os.path.abspath(script_path)
                    
                    # 检查脚本是否存在
                    if not os.path.exists(script_path):
                        raise FileNotFoundError(f"启动脚本不存在: {script_path}")
                    
                    # 启动Chrome进程（异步）
                    process = subprocess.Popen(['bash', script_path], 
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE)
                    
                    # 等待Chrome调试端口可用
                    max_wait_time = 30
                    wait_interval = 1
                    for wait_time in range(0, max_wait_time, wait_interval):
                        time.sleep(wait_interval)
                        try:
                            # 检查调试端口是否可用
                            import requests
                            response = requests.get('http://127.0.0.1:9222/json', timeout=2)
                            if response.status_code == 200:
                                self.logger.info(f"✅ Chrome浏览器已重新启动，调试端口可用 (等待{wait_time+1}秒)")
                                break
                        except:
                            continue
                    else:
                        raise Exception("Chrome调试端口在30秒内未能启动")
                    
                except Exception as e:
                    self.logger.error(f"启动Chrome失败: {e}")
                    self.restart_browser(force_restart=True)
                    return False
            
            # 3. 重新连接浏览器（带重试机制）
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    chrome_options = Options()
                    chrome_options.debugger_address = "127.0.0.1:9222"
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    
                    # Linux特定配置
                    if platform.system() == 'Linux':
                        
                        # 添加与启动脚本一致的所有参数
                        chrome_options.add_argument('--no-sandbox')
                        chrome_options.add_argument('--disable-gpu')
                        chrome_options.add_argument('--disable-software-rasterizer')
                        chrome_options.add_argument('--disable-dev-shm-usage')
                        chrome_options.add_argument('--disable-background-networking')
                        chrome_options.add_argument('--disable-default-apps')
                        chrome_options.add_argument('--disable-extensions')
                        chrome_options.add_argument('--disable-sync')
                        chrome_options.add_argument('--metrics-recording-only')
                        chrome_options.add_argument('--no-first-run')
                        chrome_options.add_argument('--disable-translate')
                        chrome_options.add_argument('--disable-background-timer-throttling')
                        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
                        chrome_options.add_argument('--disable-renderer-backgrounding')
                        chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees,SitePerProcess,IsolateOrigins')
                        chrome_options.add_argument('--noerrdialogs')
                    self.driver = webdriver.Chrome(options=chrome_options)
                    
                    # 验证连接
                    self.driver.execute_script("return navigator.userAgent")
                    
                    # 加载目标URL
                    target_url = self.url_entry.get()
                    if target_url:
                        self.driver.get(target_url)
                        WebDriverWait(self.driver, 15).until(
                            lambda d: d.execute_script('return document.readyState') == 'complete'
                        )
                        self.logger.info(f"✅ 成功加载页面: {target_url}")
                    
                    self.logger.info("✅ 浏览器连接成功")

                    # 连接成功后，重置监控线程
                    self._restore_monitoring_state()
                    return True
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"连接失败 ({attempt+1}/{max_retries}),2秒后重试: {e}")
                        time.sleep(2)
                    else:
                        self.logger.error(f"浏览器连接最终失败: {e}")
                        return False
            return False
            
        except Exception as e:
            self.logger.error(f"浏览器重启失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"浏览器重启失败: {e}")
            return False
        finally:
            with self.restart_lock:
                self.is_restarting = False

    def _restore_monitoring_state(self):
        """恢复监控状态 - 重新同步监控逻辑，确保所有监控功能正常工作"""
        try:
            self.logger.info("🔄 恢复监控状态...")
            
            # 确保运行状态正确
            self.running = True
            
            # 重新启动各种监控功能（不是重新创建定时器，而是确保监控逻辑正常）
            
            # 1. 重新启动登录监控（如果当前没有运行）
            if hasattr(self, 'login_check_timer') and self.login_check_timer:
                self.root.after_cancel(self.login_check_timer)
            self.start_login_monitoring()
            
            # 2. 重新启动URL监控（如果当前没有运行）
            if hasattr(self, 'url_check_timer') and self.url_check_timer:
                self.root.after_cancel(self.url_check_timer) 
            self.start_url_monitoring()

            # 3. 重新启动页面刷新监控（如果当前没有运行）
            if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                self.root.after_cancel(self.refresh_page_timer)     
            self.refresh_page()

            # 4. 重新启动XPath元素监控（如果当前没有运行）
            if hasattr(self, 'monitor_xpath_timer') and self.monitor_xpath_timer:
                self.root.after_cancel(self.monitor_xpath_timer)
            self.monitor_xpath_elements()

            # 6.重新开始价格比较
            if hasattr(self,'comparison_binance_price_timer') and self.comparison_binance_price_timer:
                self.root.after_cancel(self.comparison_binance_price_timer)
            self.comparison_binance_price()

            # 7.重新启动自动找币功能
            if hasattr(self,'schedule_auto_find_coin_timer') and self.schedule_auto_find_coin_timer:
                self.root.after_cancel(self.schedule_auto_find_coin_timer)
            self.schedule_auto_find_coin()
            
            # 智能恢复时间敏感类定时器
            current_time = datetime.now()
            
            # 8. binance_zero_timer: 计算到下一个零点的时间差
            next_zero_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            if current_time >= next_zero_time:
                next_zero_time += timedelta(days=1)
            
            seconds_until_next_run = int((next_zero_time - current_time).total_seconds() * 1000)  # 转换为毫秒
            
            # 只在合理的时间范围内恢复零点价格定时器
            if seconds_until_next_run > 0:
                self.get_binance_zero_time_price_timer = self.root.after(seconds_until_next_run, self.get_binance_zero_time_price)
                self.logger.info(f"✅ 恢复零点价格定时器，{round(seconds_until_next_run / 3600000, 2)} 小时后执行")
            
            # 9. zero_cash_timer: 类似的计算逻辑
            # 现金监控可以稍微提前一点，比如在23:59:30开始
            next_cash_time = current_time.replace(hour=23, minute=59, second=30, microsecond=0)
            if current_time >= next_cash_time:
                next_cash_time += timedelta(days=1)
            
            seconds_until_cash_run = int((next_cash_time - current_time).total_seconds() * 1000)
            
            if seconds_until_cash_run > 0:
                self.get_zero_time_cash_timer = self.root.after(seconds_until_cash_run, self.get_zero_time_cash)
                self.logger.info(f"✅ 恢复零点现金定时器，{round(seconds_until_cash_run / 3600000, 2)} 小时后执行")
            
            self.logger.info("✅ 监控状态恢复完成")
            
        except Exception as e:
            self.logger.error(f"恢复监控状态失败: {e}")

    def _send_chrome_alert_email(self):
        """发送Chrome异常警报邮件"""
        try:
            hostname = socket.gethostname()
            sender = 'huacaihuijin@126.com'
            receiver = 'huacaihuijin@126.com'
            app_password = 'PUaRF5FKeKJDrYH7'
            
            # 获取交易币对信息
            full_pair = self.trading_pair_label.cget("text")
            trading_pair = full_pair.split('-')[0] if full_pair and '-' in full_pair else "未知交易币对"
            
            msg = MIMEMultipart()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            subject = f'🚨{hostname}-Chrome异常-{trading_pair}-需要手动介入'
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = sender
            msg['To'] = receiver
            
            # 获取当前状态信息
            try:
                cash_value = self.cash_label.cget("text")
                portfolio_value = self.portfolio_label.cget("text")
            except:
                cash_value = "无法获取"
                portfolio_value = "无法获取"
            
            content = f"""
    🚨 Chrome浏览器异常警报 🚨

    异常时间: {current_time}
    主机名称: {hostname}
    交易币对: {trading_pair}
    当前买入次数: {self.trade_count}
    当前卖出次数: {self.sell_count}
    重启次数: {self.reset_trade_count}
    当前 CASH 值: {cash_value}
    当前 PORTFOLIO 值: {portfolio_value}

    ⚠️  请立即手动检查并介入处理！
            """
            
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP_SSL('smtp.126.com', 465, timeout=5)
            server.set_debuglevel(0)
            
            try:
                server.login(sender, app_password)
                server.sendmail(sender, receiver, msg.as_string())
                self.logger.info(f"✅ Chrome异常警报邮件发送成功")
            except Exception as e:
                self.logger.error(f"❌ Chrome异常警报邮件发送失败: {str(e)}")
            finally:
                try:
                    server.quit()
                except Exception:
                    pass
                    
        except Exception as e:
            self.logger.error(f"发送Chrome异常警报邮件时出错: {str(e)}")

    def get_nearby_cents(self):
        """获取spread附近的价格数字"""
        # 根据规律直接获取对应位置的值
        up_price_val = None
        asks_shares_val = None
        down_price_val = None
        bids_shares_val = None

        # 定位 Spread 元素
        keyword_element = None
        try:
            keyword_element = self.driver.find_element(By.XPATH, XPathConfig.SPREAD[0])
        except NoSuchElementException:
            #self.logger.warning(f"SPREAD元素最终未找到: {keyword_element}")
            return None, None, None, None   
        # 获取container
        container = None
        try:
            container = keyword_element.find_element(By.XPATH, './ancestor::div[3]')
        except NoSuchElementException:
            #self.logger.warning(f"SPREAD元素 '{keyword_element.text}' 的ancestor::div[3] (container) 未找到")
            return None, None, None, None
        
        if not container:
            #self.logger.warning("Container for SPREAD not found (was None after trying to get ancestor).")
            return None, None, None, None         
        # 取兄弟节点
        above_element_texts = []
        below_element_texts = []
        try:
            # JavaScript to get trimmed text content of previous and next siblings in one call
            js_combined = '''
                const container = arguments[0];
                const result = { above_texts: [], below_texts: [] };

                let above_e = container;
                while (above_e = above_e.previousElementSibling) {
                    let txt = "";
                    try { txt = above_e.innerText || above_e.textContent || ""; } catch (err) {}
                    result.above_texts.push(txt.trim());
                }

                let below_e = container;
                while (below_e = below_e.nextElementSibling) {
                    let txt = "";
                    try { txt = below_e.innerText || below_e.textContent || ""; } catch (err) {}
                    result.below_texts.push(txt.trim());
                }
                return result;
            '''
            
            # Execute the combined JavaScript
            sibling_texts_result = self.driver.execute_script(js_combined, container)
            above_element_texts = sibling_texts_result.get('above_texts', [])
            below_element_texts = sibling_texts_result.get('below_texts', [])

        except StaleElementReferenceException:
            #self.logger.warning("获取兄弟节点文本时发生StaleElementReferenceException (可能由于container失效)")
            return None, None, None, None
        except Exception as e:
            #self.logger.error(f"执行JavaScript获取兄弟节点文本失败: {str(e)}")
            return None, None, None, None
        
        up_price_str = None
        asks_shares_str = None
        
        if len(above_element_texts) >= 3: # Need at least 3 elements for a block
            for i in range(len(above_element_texts) - 2): 
                total_value_candidate = above_element_texts[i]
                shares_candidate = above_element_texts[i+1]
                price_candidate = above_element_texts[i+2]

                # Check if the candidates form a valid price block
                if '$' in total_value_candidate and '¢' in price_candidate:
                    # Validate shares format
                    cleaned_shares = shares_candidate.replace(',', '')
                    if re.fullmatch(r'\d+\.?\d*', cleaned_shares) or re.fullmatch(r'\d+', cleaned_shares):
                        # Validate price format
                        price_match_obj = re.search(r'(\d+\.?\d*)¢', price_candidate)
                        if price_match_obj:
                            up_price_str = price_match_obj.group(1)
                            asks_shares_str = cleaned_shares
                            #self.logger.info(f"Found UP price (ask): {up_price_str} from '{price_candidate}', shares: {asks_shares_str} from '{shares_candidate}'")
                            break
        down_price_str = None
        bids_shares_str = None
        # For "down" (bids), the pattern is Price Cents, then Shares
        if len(below_element_texts) >= 2: # Need at least 2 elements
            for i in range(len(below_element_texts) - 1):
                current_text = below_element_texts[i] 
                next_text = below_element_texts[i+1] 
                
                if '¢' in current_text:
                    price_match_obj = re.search(r'(\d+\.?\d*)¢', current_text)
                    if price_match_obj:
                        potential_shares_cleaned = next_text.replace(',', '')
                        if re.fullmatch(r'\d+\.?\d*', potential_shares_cleaned) or re.fullmatch(r'\d+', potential_shares_cleaned):
                            down_price_str = price_match_obj.group(1)
                            # Use the cleaned shares value directly
                            bids_shares_str = potential_shares_cleaned 
                            #self.logger.info(f"Found DOWN price (bid): {down_price_str} from '{current_text}', shares: {bids_shares_str} from '{next_text}'")
                            break 
        try:  
            if up_price_str is not None: # Check for None before float conversion
                up_price_val = round(float(up_price_str), 2)
            if asks_shares_str is not None:
                asks_shares_val = float(asks_shares_str.replace(',', ''))
            
            if down_price_str is not None:
                down_price_val = round(float(down_price_str), 2)
            if bids_shares_str is not None:
                bids_shares_val = float(bids_shares_str.replace(',', ''))
            #self.logger.info(f"up_price_val: {up_price_val}, down_price_val: {down_price_val}, asks_shares_val: {asks_shares_val}, bids_shares_val: {bids_shares_val}")           
            return up_price_val, down_price_val, asks_shares_val, bids_shares_val 
             
        except ValueError as e:
            #self.logger.error(f"数值转换错误: {e}. Values: up_p='{up_price_str}', ask_s='{asks_shares_str}', down_p='{down_price_str}', bid_s='{bids_shares_str}'")
            return None, None, None, None
        except Exception as e: # Catch any other unexpected errors during conversion
            #self.logger.error(f"解析价格和股数时发生未知错误: {str(e)}")
            return None, None, None, None
        
    def check_prices(self):
        """检查价格变化"""
        # 直接检查driver是否存在，不存在就重启
        if not self.driver and not self.is_restarting:
            self.logger.warning("浏览器未初始化，尝试重启...")
            if not self.restart_browser(force_restart=True):
                self.logger.error("浏览器重启失败，跳过本次检查")
                return

        try:
            # 获取一次价格和SHARES
            up_price_val, down_price_val, asks_shares_val, bids_shares_val = self.get_nearby_cents()
            
            if up_price_val is not None and down_price_val is not None and asks_shares_val is not None and bids_shares_val is not None:
                # 将原始的 '¢' 单位价格转换为 0-100 的百分比价格用于显示和逻辑判断
                # asks_price (up_price) 是直接的 '¢' 值
                # bids_price (down_price) 需要转换为 (100 - '¢') 值
                
                gui_up_price = float(up_price_val)  # 用于GUI显示的 up price (ask price)
                gui_down_price = 100.0 - float(down_price_val) # 用于GUI显示的 down price (bid price, 100 - raw_bid)
            
                # 更新价格显示
                self.yes_price_label.config(text=f"Up: {gui_up_price:.1f}¢")
                self.no_price_label.config(text=f"Down: {gui_down_price:.1f}¢") # 使用转换后的 no_price
                self.up_shares_label.config(text=f"Up Shares: {asks_shares_val:.1f}")
                self.down_shares_label.config(text=f"Down Shares: {bids_shares_val:.1f}")
                
                # 执行所有交易检查函数
                self.First_trade(up_price_val, down_price_val, asks_shares_val, bids_shares_val)
                self.Second_trade(up_price_val, down_price_val, asks_shares_val, bids_shares_val)
                self.Third_trade(up_price_val, down_price_val, asks_shares_val, bids_shares_val)
                self.Forth_trade(up_price_val, down_price_val, asks_shares_val, bids_shares_val)
                self.Sell_yes(up_price_val, down_price_val, asks_shares_val, bids_shares_val)
                self.Sell_no(up_price_val, down_price_val, asks_shares_val, bids_shares_val)
            else:
                self.yes_price_label.config(text="Up: N/A")
                self.no_price_label.config(text="Down: N/A")
                self.up_shares_label.config(text="Up Shares: N/A")
                self.down_shares_label.config(text="Down Shares: N/A")
                
        except Exception as e:
            self.yes_price_label.config(text="Up: Fail")
            self.no_price_label.config(text="Down: Fail")
            self.up_shares_label.config(text="Up Shares: Fail")
            self.down_shares_label.config(text="Down Shares: Fail")
            time.sleep(1)
            
    def check_balance(self):
        """获取Portfolio和Cash值"""
        if not self.driver and not self.is_restarting:
            self.restart_browser(force_restart=True)

        # 等待页面完全加载
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete'
        )
        
        try:
            # 取Portfolio值和Cash值
            self.cash_value = None
            self.portfolio_value = None
            try:
                portfolio_element = self.driver.find_element(By.XPATH, XPathConfig.PORTFOLIO_VALUE[0])
                cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE[0])
                self.cash_value = cash_element.text
                self.portfolio_value = portfolio_element.text
            except NoSuchElementException:
                portfolio_element = self._find_element_with_retry(XPathConfig.PORTFOLIO_VALUE, timeout=3, silent=True)
                cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE, timeout=3, silent=True)
                self.cash_value = cash_element.text
                self.portfolio_value = portfolio_element.text
        
            # 更新Portfolio和Cash显示
            self.portfolio_label.config(text=f"Portfolio: {self.portfolio_value}")
            self.cash_label.config(text=f"Cash: {self.cash_value}")

        except Exception as e:
            self.portfolio_label.config(text="Portfolio: Fail")
            self.cash_label.config(text="Cash: Fail")
             
    """以上代码执行了监控价格和获取 CASH 的值。从这里开始程序返回到第 740 行"""  

    """以下代码是设置 YES/NO 金额的函数,直到第 1127 行"""
    def schedule_update_amount(self, retry_count=0):
        """设置金额,带重试机制"""
        try:
            if retry_count < 15:  # 最多重试15次
                # 1秒后执行
                self.root.after(1000, lambda: self.try_update_amount(retry_count))
            else:
                self.logger.warning("更新金额操作达到最大重试次数")
        except Exception as e:
            self.logger.error(f"安排更新金额操作失败: {str(e)}")

    def try_update_amount(self, current_retry=0):
        """尝试设置金额"""
        try:
            self.set_amount_button.invoke()
            self.root.after(1000, lambda: self.check_amount_and_set_price(current_retry))
        except Exception as e:
            self.logger.error(f"更新金额操作失败 (尝试 {current_retry + 1}/15): {str(e)}")
            # 如果失败，安排下一次重试
            self.schedule_update_amount(current_retry + 1)

    def check_amount_and_set_price(self, current_retry):
        """检查金额是否设置成功,成功后设置价格"""
        try:
            # 检查yes金额是否为非0值
            yes1_amount = self.yes1_amount_entry.get().strip()

            if yes1_amount and yes1_amount != '0':
                # 延迟5秒设置价格
                self.root.after(5000, lambda: self.set_yes1_no1_default_target_price())
                
            else:
                if current_retry < 15:  # 最多重试15次
                    self.logger.info("\033[31m❌ 金额未成功设置,2秒后重试\033[0m")
                    self.root.after(2000, lambda: self.check_amount_and_set_price(current_retry))
                else:
                    self.logger.warning("金额设置超时")
        except Exception as e:
            self.logger.error(f"检查金额设置状态失败: {str(e)}")

    def set_yes1_no1_default_target_price(self):
        """设置默认目标价格"""
        self.yes1_price_entry.delete(0, tk.END)
        self.yes1_price_entry.insert(0, self.default_target_price)
        self.no1_price_entry.delete(0, tk.END)
        self.no1_price_entry.insert(0, self.default_target_price)
        self.logger.info(f"\033[34m✅ 设置买入价格{self.default_target_price}成功\033[0m")
        self.close_windows()

    def set_yes_no_cash(self):
        """设置 Yes/No 各级金额"""
        try:
            #设置重试参数
            max_retry = 15
            retry_count = 0
            cash_value = 0

            while retry_count < max_retry:
                try:
                    # 获取 Cash 值
                    cash_value = float(self.zero_time_cash_value)
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retry:
                        time.sleep(2)
                    else:
                        raise ValueError("获取Cash值失败")
            if cash_value is None:
                raise ValueError("获取Cash值失败")
            
            # 获取金额设置中的百分比值
            initial_percent = float(self.initial_amount_entry.get()) / 100  # 初始金额百分比
            first_rebound_percent = float(self.first_rebound_entry.get()) / 100  # 反水一次百分比
            n_rebound_percent = float(self.n_rebound_entry.get()) / 100  # 反水N次百分比

            # 设置 Yes1 和 No1金额
            base_amount = cash_value * initial_percent
            self.yes1_entry = self.yes_frame.grid_slaves(row=1, column=1)[0]
            self.yes1_amount_entry.delete(0, tk.END)
            self.yes1_amount_entry.insert(0, f"{base_amount:.2f}")
            self.no1_entry = self.no_frame.grid_slaves(row=1, column=1)[0]
            self.no1_amount_entry.delete(0, tk.END)
            self.no1_amount_entry.insert(0, f"{base_amount:.2f}")
            
            # 计算并设置 Yes2/No2金额
            self.yes2_amount = base_amount * first_rebound_percent
            self.yes2_entry = self.yes_frame.grid_slaves(row=3, column=1)[0]
            self.yes2_entry.delete(0, tk.END)
            self.yes2_entry.insert(0, f"{self.yes2_amount:.2f}")
            self.no2_entry = self.no_frame.grid_slaves(row=3, column=1)[0]
            self.no2_entry.delete(0, tk.END)
            self.no2_entry.insert(0, f"{self.yes2_amount:.2f}")
            
            # 计算并设置 YES3/NO3 金额
            self.yes3_amount = self.yes2_amount * n_rebound_percent
            self.yes3_entry = self.yes_frame.grid_slaves(row=5, column=1)[0]
            self.yes3_entry.delete(0, tk.END)
            self.yes3_entry.insert(0, f"{self.yes3_amount:.2f}")
            self.no3_entry = self.no_frame.grid_slaves(row=5, column=1)[0]
            self.no3_entry.delete(0, tk.END)
            self.no3_entry.insert(0, f"{self.yes3_amount:.2f}")

            # 计算并设置 Yes4/No4金额
            self.yes4_amount = self.yes3_amount * n_rebound_percent
            self.yes4_entry = self.yes_frame.grid_slaves(row=7, column=1)[0]
            self.yes4_entry.delete(0, tk.END)
            self.yes4_entry.insert(0, f"{self.yes4_amount:.2f}")
            self.no4_entry = self.no_frame.grid_slaves(row=7, column=1)[0]
            self.no4_entry.delete(0, tk.END)
            self.no4_entry.insert(0, f"{self.yes4_amount:.2f}")

            # 获取当前CASH并显示,此CASH再次点击start按钮时会更新
            self.logger.info("\033[34m✅ YES/NO 金额设置完成\033[0m")
            
        except Exception as e:
            self.logger.error(f"设置金额失败: {str(e)}")
            
            self.schedule_retry_update()

    def schedule_retry_update(self):
        """安排重试更新金额"""
        if hasattr(self, 'retry_timer'):
            self.root.after_cancel(self.retry_timer)
        self.retry_timer = self.root.after(3000, self.set_yes_no_cash)  # 3秒后重试
    """以上代码执行了设置 YES/NO 金额的函数,从 1000 行到 1127 行,程序执行返回到 745 行"""

    """以下代码是启动 URL 监控和登录状态监控的函数,直到第 1426 行"""
    def start_url_monitoring(self):
        """启动URL监控"""
        with self.url_monitoring_lock:
            if getattr(self, 'is_url_monitoring', False):
                self.logger.debug("URL监控已在运行中")
                return
            
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)

            self.url_monitoring_running = True
            self.logger.info("\033[34m✅ 启动URL监控\033[0m")

            def check_url():
                if self.running and self.driver:
                    try:
                        current_page_url = self.driver.current_url # 获取当前页面URL
                        target_url = self.url_entry.get() # 获取输入框中的URL,这是最原始的URL

                        if current_page_url != target_url:
                            self.logger.warning("检测到URL变化,正在恢复")
                            self.driver.get(target_url)
                            self.logger.info(f"\033[34m✅ 已恢复到原始的监控网址: {target_url}\033[0m")

                    except Exception as e:
                        self.logger.error(f"URL监控出错: {str(e)}")
                        # 重新导航到目标URL
                        if self.driver:
                            try:
                                self.driver.get(target_url)
                                self.logger.info(f"\033[34m✅ URL监控已自动修复: {target_url}\033[0m")
                            except Exception:
                                self.restart_browser(force_restart=True)
                        else:
                            self.restart_browser(force_restart=True)
                    # 继续监控
                    if self.running:
                        self.url_check_timer = self.root.after(3000, check_url)  # 每3秒检查一次
            
            # 开始第一次检查
            self.url_check_timer = self.root.after(1000, check_url)
    def stop_url_monitoring(self):
        """停止URL监控"""
        with self.url_monitoring_lock:
            # 检查是否有正在运行的URL监控
            if not hasattr(self, 'url_monitoring_running') or not self.url_monitoring_running:
                self.logger.debug("URL监控未在运行中,无需停止")
                return
            
            # 取消定时器
            if hasattr(self, 'url_check_timer') and self.url_check_timer:
                try:
                    self.root.after_cancel(self.url_check_timer)
                    self.url_check_timer = None
                    
                except Exception as e:
                    self.logger.error(f"取消URL监控定时器时出错: {str(e)}")
            
            # 重置监控状态
            self.url_monitoring_running = False
            self.logger.info("\033[31m❌ URL监控已停止\033[0m")

    def find_login_button(self):
        """查找登录按钮"""
        login_button_element = None # 重命名以区分元素和文本
        try:
            login_button_element = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_BUTTON[0])
        except NoSuchElementException:
            login_button_element = self._find_element_with_retry(
                XPathConfig.LOGIN_BUTTON,
                timeout=3,
                silent=True
            )
        
        if login_button_element:
            try:
                if login_button_element.text == "Log In":
                    self.logger.info(f"\033[34m✅ 找到登录按钮，文本为 '{login_button_element.text}'\033[0m")
                    return login_button_element # 返回 WebElement 对象
                else:
                    return None # 文本不匹配，返回 None
            except StaleElementReferenceException:
                self.logger.warning("获取登录按钮文本时发生 StaleElementReferenceException将重试查找。")
                return None
        else: 
            return None # 未找到元素，返回 None
    
    def click_login_button(self):
        """点击登录按钮""" 
        login_button_element = self.find_login_button() # 现在返回元素或 None

        if login_button_element: # 检查是否获取到了元素   
            try:
                login_button_element.click()
                self.logger.info("\033[34m✅ 已点击 'Log In' 按钮\033[0m")

                # 使用 XPath 定位并点击 google 按钮,可以考虑使用pyautogui点击登录按钮
                google_button = None
                try:
                    google_button = self.driver.find_element(By.XPATH, XPathConfig.LOGIN_WITH_GOOGLE_BUTTON[0])
                except NoSuchElementException:
                    google_button = self._find_element_with_retry(
                        XPathConfig.LOGIN_WITH_GOOGLE_BUTTON,
                        timeout=3,
                        silent=True
                    )
                if google_button:
                    google_button.click()
                    self.logger.info("\033[34m✅ 已点击 Google 登录按钮\033[0m")

            except StaleElementReferenceException:
                self.logger.warning("点击登录按钮时发生 StaleElementReferenceException,可能需要重新查找按钮或处理页面刷新。")
            except Exception as e:
                self.logger.info(f"❌ 点击登录按钮或 Google 按钮时出错")
                self.click_login_button()
        else:
            self.logger.info("❌ 未找到 'Log In' 按钮或不符合点击条件，跳过点击。")

    def start_login_monitoring(self):
        """启动登录状态监控"""
        self.logger.info("\033[34m✅ 启动登录状态监控\033[0m")
        if not self.driver and not self.is_restarting:
            self.restart_browser(force_restart=True)
            
        def check_login_status():
            if self.running and self.driver:
                try:
                    # 使用线程执行登录检查，避免阻塞主线程
                    threading.Thread(
                        target=self._check_login_status_thread, # 执行登录检查线程,此线程完全独立于主线程
                        daemon=True
                    ).start()
                except Exception as e:
                    self.logger.error(f"登录状态检查出错: {str(e)}")
                
                # 继续监控
                if self.running:
                    self.login_check_timer = self.root.after(15000, check_login_status)  # 每15秒检查一次
        # 开始第一次检查
        self.login_check_timer = self.root.after(10000, check_login_status)

    def _check_login_status_thread(self):
        """在单独线程中执行登录检查,只检查"""
        try:
            login_button_element_found = self.find_login_button()

            if login_button_element_found:
                try:
                    self.logger.warning(f"❌ 检测到未登录状态, 执行登录操作")
                    # 在新的辅助线程中执行登录操作
                    login_thread = threading.Thread(target=self.check_and_handle_login, daemon=True)
                    login_thread.start()

                except Exception as e_thread_start:
                    self.logger.error(f"启动登录线程失败: {e_thread_start}")
                                
        except Exception as e:
            self.logger.info(f"❌ _check_login_status_thread 中发生意外错误: {e}")

    def check_and_handle_login(self):
        """执行登录操作 - 此函数由 _check_login_status_thread 在获得锁后于新线程中启动"""
        try:
            self.stop_refresh_page()
            self.stop_url_monitoring()

            self.logger.info("开始执行登录操作 (在独立线程中)...")
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True) 

            self.login_running = True

            self.click_login_button()

            # 等待10秒,等待页面跳转
            time.sleep(10)
            
            # 再次检查 "Log In" 按钮是否仍然存在
            login_button_still_present = self.find_login_button()
            
            if login_button_still_present:
                self.click_login_button()
                time.sleep(10)
            
            def check_cash():
                # 找 CASH的值, 验证是否登录成功,如果找到, 则登录成功
                try:
                    cash_value = None
                    try:
                        cash_value = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE[0])
                    except NoSuchElementException:
                        cash_value = self._find_element_with_retry(
                            XPathConfig.CASH_VALUE,
                            timeout=3,
                            silent=True
                        )

                    if cash_value:
                        return cash_value
                    else:
                        return None

                except Exception as e:
                    self.logger.warning(f"❌ 检查 CASH 值失败")
                    return None
                
            cash_value = check_cash()
            if cash_value:
                self.logger.info(f"✅ 找到\033[34mcash的值:{cash_value.text}\033[0m,登录成功")
                # 在当前标签页打开 url 网址
                url = self.url_entry.get()
                self.driver.get(url)
                time.sleep(2)

                # 执行 CLICK_ACCEPT 按钮
                self.click_accept()
                
                # 确保在主线程中调用 refresh_page
                self.root.after(2000, self.start_url_monitoring)
                self.root.after(20000, self.refresh_page)
                self.logger.info(f"✅ \033[34m启动页面刷新\033[0m")
                self.login_running = False

        except Exception as e:
            self.logger.info(f"❌ 登录流程 'check_and_handle_login' 发生错误: {e}")

    def click_accept(self):
        """点击ACCEPT按钮"""
        self.logger.info("开始执行点击ACCEPT按钮")
        #点击 AMOUNT 按钮,输入 1,然后点击 CONFIRM 按钮
        self.amount_yes1_button.event_generate('<Button-1>')
        time.sleep(0.5)
        self.buy_confirm_button.invoke()
        time.sleep(0.5)

        try:
            screen_width, screen_height = pyautogui.size()
            target_x = 0
            target_y = 0
            if platform.system() == "Linux": # 分辨率 2560x1600
                # Linux 系统下的特定坐标
                target_x = screen_width - 520
                target_y = 724    
            else:
                # 其他操作系统的默认坐标分辨率 1920x1080
                target_x = screen_width - 520
                target_y = 724
                
            # 移动鼠标到目标位置并点击
            pyautogui.moveTo(target_x, target_y, duration=0.2) # 可选，平滑移动
            pyautogui.click(target_x, target_y)
            
            self.logger.info("✅ 点击ACCEPT成功")
            self.driver.refresh()

        except Exception as e:
            self.logger.error(f"执行 click_accept 点击操作失败: {str(e)}")

    def refresh_page(self):
        """定时刷新页面"""
        # 生成随机的5-10分钟（以毫秒为单位）
        random_minutes = random.uniform(2, 6)
        self.refresh_interval = int(random_minutes * 60000)  # 转换为毫秒

        with self.refresh_page_lock:
            self.refresh_page_running = True
            try:
                # 先取消可能存在的旧定时器
                if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                    try:
                        self.root.after_cancel(self.refresh_page_timer)
                        self.refresh_page_timer = None
                    except Exception as e:
                        self.logger.error(f"取消旧定时器失败: {str(e)}")

                if self.running and self.driver and not self.trading:
                    refresh_time = self.refresh_interval / 60000
                    self.driver.refresh()
                else:
                    self.logger.info("刷新失败(else)")
                    self.logger.info(f"trading={self.trading}")
                    
            except Exception as e:
                self.logger.warning(f"页面刷新失败(except)")
                # 无论是否执行刷新都安排下一次（确保循环持续）
                if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                    try:
                        self.root.after_cancel(self.refresh_page_timer)
                    except Exception as e:
                        self.logger.error(f"取消旧定时器失败")
            finally:
                self.refresh_page_timer = self.root.after(self.refresh_interval, self.refresh_page)
                #self.logger.info(f"\033[34m{round(refresh_time, 2)} 分钟后再次刷新\033[0m")

    def stop_refresh_page(self):
        """停止页面刷新"""
        with self.refresh_page_lock:
            
            if hasattr(self, 'refresh_page_timer') and self.refresh_page_timer:
                try:
                    self.root.after_cancel(self.refresh_page_timer)
                    self.refresh_page_timer = None
                    self.logger.info("\033[31m❌ 刷新定时器已停止\033[0m")
                except Exception as e:
                    self.logger.error("取消页面刷新定时器时出错")
            # 重置监控状态
            self.refresh_page_running = False
            self.logger.info("\033[31m❌ 刷新状态已停止\033[0m")
    """以上代码执行了登录操作的函数,直到第 1315 行,程序执行返回到 748 行"""

    """以下代码是监控买卖条件及执行交易的函数,程序开始进入交易阶段,从 1468 行直到第 2224200 行"""  
    def First_trade(self, asks_price_raw, bids_price_raw, asks_shares, bids_shares):
        """第一次交易价格设置为 0.52 买入"""
        try:
            if asks_price_raw is not None and asks_price_raw > 20 and bids_price_raw is not None and bids_price_raw < 97:
                # 获取Yes1和No1的GUI界面上的价格
                yes1_price = float(self.yes1_price_entry.get())
                no1_price = float(self.no1_price_entry.get())
                self.trading = True  # 开始交易
               
                # 检查Yes1价格匹配: asks_price_raw should be close to yes1_price_gui
                if 0 <= round((asks_price_raw - yes1_price), 2) <= self.price_premium and (asks_shares > self.asks_shares):
                    while True:
                        self.logger.info(f"Up 1: {asks_price_raw}¢ 价格匹配,执行自动交易")
                        # 执行现有的交易操作
                        self.amount_yes1_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(0.5)
                        
                        time.sleep(2)
                        if self.Verify_buy_yes():
                            # 增加交易次数
                            self.buy_yes1_amount = float(self.yes1_amount_entry.get())
                            self.trade_count += 1
                            
                            # 重置Yes1和No1价格为0
                            self.yes1_price_entry.delete(0, tk.END)
                            self.yes1_price_entry.insert(0, "0")
                            self.no1_price_entry.delete(0, tk.END)
                            self.no1_price_entry.insert(0, "0")
                            
                            # 设置No2价格为默认值
                            self.no2_price_entry = self.no_frame.grid_slaves(row=2, column=1)[0]
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, str(self.default_target_price))
                            self.no2_price_entry.configure(foreground='red')  # 添加红色设置

                            # 设置 Yes5和No5价格为99
                            self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
                            self.yes5_price_entry.delete(0, tk.END)
                            self.yes5_price_entry.insert(0, str(self.default_normal_sell_price))
                            self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
                            self.no5_price_entry.delete(0, tk.END)
                            self.no5_price_entry.insert(0, str(self.default_normal_sell_price))
                            self.no5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.logger.info("\033[34m✅ First_trade执行成功\033[0m")
                            self.root.after(30000, self.driver.refresh)
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Up1",
                                price=self.buy_up_price,
                                amount=self.buy_yes1_amount,
                                trade_count=self.trade_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            break
                        else:
                            self.logger.warning("❌ 交易失败,等待1秒后重试")
                            time.sleep(1)  # 添加延时避免过于频繁的重试

                # 检查No1价格匹配: (100 - bids_price_raw) should be close to no1_price_gui
                elif 0 <= round(((100.0 - bids_price_raw) - no1_price), 2) <= self.price_premium and (bids_shares > self.bids_shares):
                     while True:
                        self.logger.info(f"Down 1: {100.0 - bids_price_raw}¢ 价格匹配,执行自动交易") 
                        # 执行现有的交易操作
                        self.buy_no_button.invoke()
                        time.sleep(0.5)
                        self.amount_no1_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(0.5)

                        time.sleep(2)
                        if self.Verify_buy_no():
                            self.buy_no1_amount = float(self.no1_amount_entry.get())
                            # 增加交易次数
                            self.trade_count += 1
                            
                            # 重置Yes1和No1价格为0
                            self.yes1_price_entry.delete(0, tk.END)
                            self.yes1_price_entry.insert(0, "0")
                            self.no1_price_entry.delete(0, tk.END)
                            self.no1_price_entry.insert(0, "0")
                            
                            
                            # 设置Yes2价格为默认值
                            self.yes2_price_entry = self.yes_frame.grid_slaves(row=2, column=1)[0]
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, str(self.default_target_price))
                            self.yes2_price_entry.configure(foreground='red')  # 添加红色设置

                            # 设置 Yes5和No5价格为0.98
                            self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
                            self.yes5_price_entry.delete(0, tk.END)
                            self.yes5_price_entry.insert(0, str(self.default_normal_sell_price))
                            self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
                            self.no5_price_entry.delete(0, tk.END)
                            self.no5_price_entry.insert(0, str(self.default_normal_sell_price))
                            self.no5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.logger.info("\033[34m✅ First_trade执行成功\033[0m")
                            self.root.after(30000, self.driver.refresh)
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Down1",
                                price=self.buy_down_price,
                                amount=self.buy_no1_amount,
                                trade_count=self.trade_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            break
                        else:
                            self.logger.warning("❌ 交易失败,等待1秒后重试")
                            time.sleep(1)  # 添加延时避免过于频繁的重试                           
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"First_trade执行失败: {str(e)}")
            
        finally:
            self.trading = False
            
    def Second_trade(self, asks_price_raw, bids_price_raw, asks_shares, bids_shares):
        """处理Yes2/No2的自动交易"""
        try:
            if asks_price_raw is not None and asks_price_raw > 20 and bids_price_raw is not None and bids_price_raw < 97:
                # 获Yes2和No2的价格输入框
                yes2_price = float(self.yes2_price_entry.get())
                no2_price = float(self.no2_price_entry.get())
                self.trading = True  # 开始交易
                
                # 检查Yes2价格匹配
                if 0 <= round((asks_price_raw - yes2_price), 2) <= self.price_premium and (asks_shares > self.asks_shares):
                    while True:
                        self.logger.info(f"Up 2: {asks_price_raw}¢ 价格匹配,执行自动交易")
                        # 执行现有的交易操作
                        self.amount_yes2_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(0.5)

                        time.sleep(2)
                        if self.Verify_buy_yes():
                            self.buy_yes2_amount = float(self.yes2_amount_entry.get())

                            # 重置Yes2和No2价格为0
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, "0")
                            self.yes2_price_entry.configure(foreground='black')
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, "0")
                            self.no2_price_entry.configure(foreground='black')
                            
                            # 设置No3价格为默认值
                            self.no3_price_entry = self.no_frame.grid_slaves(row=4, column=1)[0]
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, str(self.default_target_price))
                            self.no3_price_entry.configure(foreground='red')  # 添加红色设置
                            
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Up2",
                                price=self.buy_up_price,
                                amount=self.buy_yes2_amount,
                                trade_count=self.trade_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info("\033[34m✅ Second_trade执行成功\033[0m")
                            self.root.after(30000, self.driver.refresh)
                            break
                        else:
                            self.logger.warning("❌ 交易失败,等待1秒后重试")
                            time.sleep(1)  # 添加延时避免过于频繁的重试
                # 检查No2价格匹配
                elif 0 <= round(((100.0 - bids_price_raw) - no2_price), 2) <= self.price_premium and (bids_shares > self.bids_shares):
                    while True:
                        self.logger.info(f"Down 2: {100.0 - bids_price_raw}¢ 价格匹配,执行自动交易")
                        
                        # 执行现有的交易操作
                        self.buy_no_button.invoke()
                        time.sleep(0.5)
                        self.amount_no2_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(0.5)
                            
                        time.sleep(2)
                        if self.Verify_buy_no():
                            self.buy_no2_amount = float(self.no2_amount_entry.get())
                            # 重置Yes2和No2价格为0
                            self.yes2_price_entry.delete(0, tk.END)
                            self.yes2_price_entry.insert(0, "0")
                            self.yes2_price_entry.configure(foreground='black')
                            self.no2_price_entry.delete(0, tk.END)
                            self.no2_price_entry.insert(0, "0")
                            self.no2_price_entry.configure(foreground='black')
                            
                            # 设置Yes3价格为默认值
                            self.yes3_price_entry = self.yes_frame.grid_slaves(row=4, column=1)[0]
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, str(self.default_target_price))
                            self.yes3_price_entry.configure(foreground='red')  # 添加红色设置
                            
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Down2",
                                price=self.buy_down_price,
                                amount=self.buy_no2_amount,
                                trade_count=self.trade_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info("\033[34m✅ Second_trade执行成功\033[0m")
                            self.root.after(30000, self.driver.refresh)
                            break
                        else:
                            self.logger.warning("交易失败,等待1秒后重试")
                            time.sleep(1)  # 添加延时避免过于频繁的重试
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Second_trade执行失败: {str(e)}")
            
        finally:
            self.trading = False
            
    def Third_trade(self, asks_price_raw, bids_price_raw, asks_shares, bids_shares):
        """处理Yes3/No3的自动交易"""
        try:
            if asks_price_raw is not None and asks_price_raw > 20 and bids_price_raw is not None and bids_price_raw < 97:                
                # 获取Yes3和No3的价格输入框
                yes3_price = float(self.yes3_price_entry.get())
                no3_price = float(self.no3_price_entry.get())
                self.trading = True  # 开始交易
            
                # 检查Yes3价格匹配
                if 0 <= round((asks_price_raw - yes3_price), 2) <= self.price_premium and (asks_shares > self.asks_shares):
                    while True:
                        self.logger.info(f"Up 3: {asks_price_raw}¢ 价格匹配,执行自动交易")
                        # 执行交易操作
                        self.amount_yes3_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(0.5)

                        time.sleep(2)
                        if self.Verify_buy_yes():
                            # 获取 YES3 的金额
                            self.buy_yes3_amount = float(self.yes3_amount_entry.get())
                            
                            # 重置Yes3和No3价格为0
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, "0")
                            self.yes3_price_entry.configure(foreground='black')
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, "0")
                            self.no3_price_entry.configure(foreground='black')
                            
                            # 设置No4价格为默认值
                            self.no4_price_entry = self.no_frame.grid_slaves(row=6, column=1)[0]
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, str(self.default_target_price))
                            self.no4_price_entry.configure(foreground='red')  # 添加红色设置

                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Up3",
                                price=self.buy_up_price,
                                amount=self.buy_yes3_amount,
                                trade_count=self.trade_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )   
                            self.logger.info("\033[34m✅ Third_trade执行成功\033[0m")
                            self.root.after(30000, self.driver.refresh)
                            break
                        else:
                            self.logger.warning("❌ 交易失败,等待1秒后重试")
                            time.sleep(1)  # 添加延时避免过于频繁的重试
                # 检查No3价格匹配
                elif 0 <= round(((100.0 - bids_price_raw) - no3_price), 2) <= self.price_premium and (bids_shares > self.bids_shares):
                    while True:
                        self.logger.info(f"Down 3: {100.0 - bids_price_raw}¢ 价格匹配,执行自动交易")
                        # 执行交易操作
                        self.buy_no_button.invoke()
                        time.sleep(0.5)
                        self.amount_no3_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        time.sleep(0.5)
                    
                        time.sleep(2)
                        if self.Verify_buy_no():
                            self.buy_no3_amount = float(self.no3_amount_entry.get())
                            
                            # 重置Yes3和No3价格为0
                            self.yes3_price_entry.delete(0, tk.END)
                            self.yes3_price_entry.insert(0, "0")
                            self.yes3_price_entry.configure(foreground='black')
                            self.no3_price_entry.delete(0, tk.END)
                            self.no3_price_entry.insert(0, "0")
                            self.no3_price_entry.configure(foreground='black')
                            
                            # 设置Yes4价格为默认值
                            self.yes4_price_entry = self.yes_frame.grid_slaves(row=6, column=1)[0]
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, str(self.default_target_price))
                            self.yes4_price_entry.configure(foreground='red')  # 添加红色设置
                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Down3",
                                price=self.buy_down_price,
                                amount=self.buy_no3_amount,
                                trade_count=self.trade_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info("\033[34m✅ Third_trade执行成功\033[0m")
                            self.root.after(30000, self.driver.refresh)
                            break
                        else:
                            self.logger.warning("❌ 交易失败,等待1秒后重试")
                            time.sleep(1)  # 添加延时避免过于频繁的重试
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Third_trade执行失败: {str(e)}")    
        finally:
            self.trading = False
            
    def Forth_trade(self, asks_price_raw, bids_price_raw, asks_shares, bids_shares):
        """处理Yes4/No4的自动交易"""
        try:
            if asks_price_raw is not None and asks_price_raw > 20 and bids_price_raw is not None and bids_price_raw < 97:  
                # 获取Yes4和No4的价格输入框
                yes4_price = float(self.yes4_price_entry.get())
                no4_price = float(self.no4_price_entry.get())
                self.trading = True  # 开始交易
            
                # 检查Yes4价格匹配
                if 0 <= round((asks_price_raw - yes4_price), 2) <= self.price_premium and (asks_shares > self.asks_shares):
                    while True:
                        self.logger.info(f"Up 4: {asks_price_raw}¢ 价格匹配,执行自动交易")
                        # 执行交易操作
                        self.amount_yes4_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()
                        
                        time.sleep(2)
                        if self.Verify_buy_yes():
                            self.buy_yes4_amount = float(self.yes4_amount_entry.get())
                            
                            # 重置Yes4和No4价格为0
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, "0")
                            self.yes4_price_entry.configure(foreground='black')
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, "0")
                            self.no4_price_entry.configure(foreground='black')

                            """当买了 4次后预防第 5 次反水，所以价格到了 51 时就平仓，然后再自动开"""
                            # 设置 Yes5和No5价格为0.85
                            self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
                            self.yes5_price_entry.delete(0, tk.END)
                            self.yes5_price_entry.insert(0, str(self.default_sell_price_backwater))
                            self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
                            self.no5_price_entry.delete(0, tk.END)
                            self.no5_price_entry.insert(0, str(self.default_sell_price))
                            self.no5_price_entry.configure(foreground='red')  # 添加红色设置

                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Up4",
                                price=self.buy_up_price,
                                amount=self.buy_yes4_amount,
                                trade_count=self.trade_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info("\033[34m✅ Forth_trade执行成功\033[0m")
                            self.root.after(30000, self.driver.refresh)
                            break
                        else:
                            self.logger.warning("❌ 交易失败,等待2秒后重试")
                            time.sleep(2)  # 添加延时避免过于频繁的重试
                # 检查No4价格匹配
                elif 0 <= round(((100.0 - bids_price_raw) - no4_price), 2) <= self.price_premium and (bids_shares > self.bids_shares):
                    while True:
                        self.logger.info(f"Down 4: {100.0 - bids_price_raw}¢ 价格匹配,执行自动交易")
                        # 执行交易操作
                        self.buy_no_button.invoke()
                        time.sleep(0.5)
                        self.amount_no4_button.event_generate('<Button-1>')
                        time.sleep(0.5)
                        self.buy_confirm_button.invoke()

                        time.sleep(2)
                        if self.Verify_buy_no():
                            # 重置Yes4和No4价格为0
                            self.yes4_price_entry.delete(0, tk.END)
                            self.yes4_price_entry.insert(0, "0")
                            self.yes4_price_entry.configure(foreground='black')
                            self.no4_price_entry.delete(0, tk.END)
                            self.no4_price_entry.insert(0, "0")
                            self.no4_price_entry.configure(foreground='black')

                            """当买了 4次后预防第 5 次反水，所以价格到了 47 时就平仓，然后再自动开"""
                            # 设置 Yes5和No5价格为0.98
                            self.yes5_price_entry = self.yes_frame.grid_slaves(row=8, column=1)[0]
                            self.yes5_price_entry.delete(0, tk.END)
                            self.yes5_price_entry.insert(0, str(self.default_sell_price))
                            self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.no5_price_entry = self.no_frame.grid_slaves(row=8, column=1)[0]
                            self.no5_price_entry.delete(0, tk.END)
                            self.no5_price_entry.insert(0, str(self.default_sell_price_backwater))
                            self.no5_price_entry.configure(foreground='red')  # 添加红色设置
                            self.buy_no4_amount = float(self.no4_amount_entry.get())

                            # 增加交易次数
                            self.trade_count += 1
                            # 发送交易邮件
                            self.send_trade_email(
                                trade_type="Buy Down4",
                                price=self.buy_down_price,
                                amount=self.buy_no4_amount,
                                trade_count=self.trade_count,
                                cash_value=self.cash_value,
                                portfolio_value=self.portfolio_value
                            )
                            self.logger.info("\033[34m✅ Forth_trade执行成功\033[0m")
                            self.root.after(30000, self.driver.refresh)
                            break
                        else:
                            self.logger.warning("❌ 交易失败,等待1秒后重试")
                            time.sleep(1)  # 添加延时避免过于频繁的重试
        except ValueError as e:
            self.logger.error(f"价格转换错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"Forth_trade执行失败: {str(e)}")  
        finally:
            self.trading = False
            
    def Sell_yes(self, asks_price_raw, bids_price_raw, asks_shares, bids_shares):
        """当YES5价格等于实时Yes价格时自动卖出"""
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
              
            if asks_price_raw is not None and bids_price_raw is not None and (bids_price_raw > 10):
                
                # 获取Yes5价格
                yes5_price = float(self.yes5_price_entry.get())
                self.trading = True  # 开始交易
                price_diff = round(bids_price_raw - yes5_price, 2) # 47-47=0;;46-47=-1;

                # 检查Yes5价格匹配
                if (44 <=yes5_price <= 47) and (-2 <= price_diff <= 1) and (bids_shares > self.bids_shares):
                    self.logger.info(f"Up 5: {bids_price_raw}¢ 价格匹配,执行自动卖出")
                    
                    self.yes5_target_price = yes5_price
                            
                    while True:
                        # 先卖 Down
                        self.only_sell_yes()
                        self.logger.info(f"卖完 Up 后，再卖 Down 3 SHARES")
                        
                        self.only_sell_no3()

                        # 设置 YES5/NO5 价格为 99
                        self.yes5_price_entry.delete(0, tk.END)
                        self.yes5_price_entry.insert(0, str(self.default_normal_sell_price))
                        self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                        self.no5_price_entry.delete(0, tk.END)
                        self.no5_price_entry.insert(0, str(self.default_normal_sell_price))
                        self.no5_price_entry.configure(foreground='red')  # 添加红色设置

                        # 重置交易次数
                        self.reset_trade_count += 1
                        self.reset_count_label.config(text=str(self.reset_trade_count))
                        #self.logger.info(f"重置交易次数: {self.reset_trade_count}")
                        self.sell_count = 0
                        self.trade_count = 0

                        # 重置YES2 价格为默认值
                        self.yes2_price_entry.delete(0, tk.END)
                        self.yes2_price_entry.insert(0, str(self.default_target_price))
                        self.yes2_price_entry.configure(foreground='black') 
                        break
                    
                elif yes5_price >= 60 and 0 <= price_diff <= 1.1 and (bids_shares > self.bids_shares):
                    self.logger.info(f"Up 5: {asks_price_raw}¢ 价格匹配,执行自动卖出")
                    
                    self.yes5_target_price = yes5_price
                            
                    while True:
                        # 执行卖出YES操作
                        self.only_sell_yes()
                        
                        time.sleep(1)
                        self.driver.refresh()

                        self.logger.info("卖完 Up 后，再卖 Down")
                        # 卖 Down 之前先检查是否有 Down 标签
                        if self.find_position_label_no():
                            self.only_sell_no()
                        
                        # 重置所有价格
                        for i in range(1,5):  # 1-4
                            yes_entry = getattr(self, f'yes{i}_price_entry', None)
                            no_entry = getattr(self, f'no{i}_price_entry', None)

                            if yes_entry:
                                yes_entry.delete(0, tk.END)
                                yes_entry.insert(0, "0")
                                yes_entry.configure(foreground='black')
                            if no_entry:
                                no_entry.delete(0, tk.END)
                                no_entry.insert(0, "0")
                                no_entry.configure(foreground='black')
                        # 在所有操作完成后,重置交易
                        self.root.after(0, self.reset_trade)
                        break
                    
        except Exception as e:
            self.logger.error(f"❌ Sell_yes执行失败: {str(e)}")
            
        finally:
            self.trading = False
            
    def Sell_no(self, asks_price_raw, bids_price_raw, asks_shares, bids_shares):
        """当NO4价格等于实时No价格时自动卖出"""
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
            
            if asks_price_raw is not None and (0 < asks_price_raw < 90) and bids_price_raw is not None:
                # 获取No5价格
                no5_price = float(self.no5_price_entry.get())
                self.trading = True  # 开始交易
                price_diff = round(100 - asks_price_raw - no5_price, 2)
            
                # 检查No5价格匹配,反水卖出同方向
                if (40 <=no5_price <= 47) and (-2 <= price_diff <= 1) and (bids_shares > self.bids_shares):
                    self.logger.info(f"Down 5: {100 - asks_price_raw}¢ 价格匹配,执行自动卖出")

                    while True:
                        # 先卖全部 Down
                        self.only_sell_no()
                        self.logger.info(f"卖完 Down 后，再卖 Up3 SHARES")
                        
                        self.only_sell_yes3()

                        # 设置 YES5/NO5 价格为 99
                        self.yes5_price_entry.delete(0, tk.END)
                        self.yes5_price_entry.insert(0, str(self.default_normal_sell_price))
                        self.yes5_price_entry.configure(foreground='red')  # 添加红色设置
                        self.no5_price_entry.delete(0, tk.END)
                        self.no5_price_entry.insert(0, str(self.default_normal_sell_price))
                        self.no5_price_entry.configure(foreground='red')  # 添加红色设置

                        # 重置交易
                        self.reset_trade_count += 1
                        self.reset_count_label.config(text=str(self.reset_trade_count))
                        self.logger.info(f"重置交易次数: {self.reset_trade_count}")
                        
                        self.sell_count = 0
                        self.trade_count = 0

                        # 重置NO2 价格为默认值
                        self.no2_price_entry.delete(0, tk.END)
                        self.no2_price_entry.insert(0, str(self.default_target_price))
                        self.no2_price_entry.configure(foreground='black')  

                        break
                    
                elif no5_price >= 60 and (0 <= price_diff <= 1.1) and (bids_shares > self.bids_shares):
                    self.logger.info(f"Down 5: {100 - asks_price_raw}¢ 价格匹配,执行自动卖出")

                    self.no5_target_price = no5_price
                    
                    while True:
                        # 卖完 Down 后，自动再卖 Up                      
                        self.only_sell_no()
                        self.logger.info("卖完 Down 后，再卖 Up")
                        time.sleep(2)
                        self.driver.refresh()
                        if self.find_position_label_yes():
                            self.only_sell_yes()

                        # 重置所有价格
                        for i in range(1,5):  # 1-4
                            yes_entry = getattr(self, f'yes{i}_price_entry', None)
                            no_entry = getattr(self, f'no{i}_price_entry', None)
                            if yes_entry:
                                yes_entry.delete(0, tk.END)
                                yes_entry.insert(0, "0")
                                yes_entry.configure(foreground='black')
                            if no_entry:
                                no_entry.delete(0, tk.END)
                                no_entry.insert(0, "0")
                                no_entry.configure(foreground='black')
                        # 在所有操作完成后,重置交易
                        self.root.after(0, self.reset_trade)
                        break
                
        except Exception as e:
            self.logger.error(f"❌ Sell_no执行失败: {str(e)}")
            
        finally:
            self.trading = False

    def reset_trade(self):
        """重置交易"""
        # 在所有操作完成后,重置交易
        time.sleep(1)
        
        # 检查属性是否存在，如果不存在则使用默认值
        yes5_price = getattr(self, 'yes5_target_price', 0)
        no5_price = getattr(self, 'no5_target_price', 0)

        if (yes5_price > 90) or (no5_price > 90):
            self.reset_trade_count = 0
        else:
            self.reset_trade_count += 1
        
        self.sell_count = 0
        self.trade_count = 0

        # 设置 YES5/NO5 价格为 0
        self.yes5_price_entry.delete(0, tk.END)
        self.yes5_price_entry.insert(0, "0")
        self.yes5_price_entry.configure(foreground='black')
        self.no5_price_entry.delete(0, tk.END)
        self.no5_price_entry.insert(0, "0")
        self.no5_price_entry.configure(foreground='black')
        
        # 重置Yes1和No1价格为默认值
        self.set_yes1_no1_default_target_price()
        # 重置交易次数
        self.reset_count_label.config(text=str(self.reset_trade_count))
        self.logger.info(f"第\033[32m{self.reset_trade_count}\033[0m次重置交易")

    def only_sell_yes(self):
        """只卖出YES"""
        self.logger.info("执行only_sell_yes")

        self.position_sell_yes_button.invoke()
        time.sleep(0.5)
        self.sell_confirm_button.invoke()
        time.sleep(0.5)
        
        time.sleep(2)
        if self.Verify_sold_yes():
             # 增加卖出计数
            self.sell_count += 1
            # 发送交易邮件 - 卖出YES
            self.send_trade_email(
                trade_type="Sell Up",
                price=self.sell_up_price,
                amount=self.position_yes_cash(),  # 卖出时金额为总持仓
                trade_count=self.sell_count,
                cash_value=self.cash_value,
                portfolio_value=self.portfolio_value
            )
            
        else:
            self.logger.warning("❌ 卖出only_sell_yes验证失败,重试")
            self.only_sell_yes()        
       
    def only_sell_no(self):
        """只卖出Down"""
        self.logger.info("执行only_sell_no")
        self.position_sell_no_button.invoke()
        time.sleep(0.5)
        self.sell_confirm_button.invoke()
        time.sleep(1)

        time.sleep(2)
        if self.Verify_sold_no():
            # 增加卖出计数
            self.sell_count += 1
            
            # 发送交易邮件 - 卖出NO
            self.send_trade_email(
                trade_type="Sell Down",
                price=self.sell_down_price,
                amount=self.position_no_cash(),  # 卖出时金额为总持仓
                trade_count=self.sell_count,
                cash_value=self.cash_value,
                portfolio_value=self.portfolio_value
            )
            
        else:
            self.logger.warning("❌ 卖出only_sell_no验证失败,重试")
            self.only_sell_no()

    def only_sell_yes3(self):
        """只卖出YES 3 SHARES"""
        try:
            self.logger.info("执行only_sell_yes3")
            # 获取 YES3 的金额
            yes3_shares = self.buy_yes3_amount / (self.default_target_price / 100)
            
            # 再卖 UP ,但是只卖 YES3 的金额对应的 SHARES
            self.position_sell_yes_button.invoke()
            time.sleep(0.5)

            # 找到SHARES输入框(与 AMOUNT_INPUT 相同)
            try:
                shares_input = self.driver.find_element(By.XPATH, XPathConfig.AMOUNT_INPUT[0])
            except NoSuchElementException:
                shares_input = self._find_element_with_retry(
                    XPathConfig.AMOUNT_INPUT,
                    timeout=3,
                    silent=True
                )                   

            # 清除 SHARES 输入为 0,然后再插入需要卖的 SHARES
            shares_input.clear()
            time.sleep(0.5)
            shares_input.send_keys(str(yes3_shares))
            time.sleep(0.5)
            self.sell_confirm_button.invoke()
            time.sleep(0.5)

            # 验证是否卖出成功
            if self.Verify_sold_yes():
                self.logger.info(f"卖 Up 3 SHARES 成功")

            # 增加卖出计数
            self.sell_count += 1
            # 发送交易邮件 - 卖出YES
            self.send_trade_email(
                trade_type="Sell Up",
                price=self.sell_up_price,
                amount=self.position_yes_cash(),  # 卖出时金额为总持仓
                trade_count=self.sell_count,
                cash_value=self.cash_value,
                portfolio_value=self.portfolio_value
            )
            self.logger.info(f"卖出 Up 3 SHARES: {yes3_shares} 成功")     
        except Exception as e:
            self.logger.info(f"❌ only_sell_yes3执行失败,重试")
            self.only_sell_yes3()
            
    def only_sell_no3(self):
        """只卖出Down 3 SHARES"""
        try:
            self.logger.info("执行only_sell_no3")
            # 获取 NO3 的SHARES
            no3_shares = self.buy_no3_amount / (self.default_target_price / 100)
            
            # 再卖 down ,但是只卖 no3 的金额对应的 SHARES
            self.position_sell_no_button.invoke()
            time.sleep(0.5)
            
            # 找到输入框
            try:
                shares_input = self.driver.find_element(By.XPATH, XPathConfig.AMOUNT_INPUT[0])
            except NoSuchElementException:
                shares_input = self._find_element_with_retry(
                    XPathConfig.AMOUNT_INPUT,
                    timeout=3,
                    silent=True
                )
            
            # 设置 SHARES_input 为 0,然后再插入需要卖的 SHARES                       
            shares_input.clear()

            time.sleep(0.5)
            shares_input.send_keys(str(no3_shares))
            time.sleep(0.5)
            self.sell_confirm_button.invoke()
            time.sleep(0.5)

            if self.Verify_sold_no():
                self.logger.info(f"卖 Down 3 SHARES 成功")

            # 增加卖出计数
            self.sell_count += 1
            
            # 发送交易邮件 - 卖出NO
            self.send_trade_email(
                trade_type="Sell Down",
                price=self.sell_down_price,
                amount=self.position_no_cash(),  # 卖出时金额为总持仓
                trade_count=self.sell_count,
                cash_value=self.cash_value,
                portfolio_value=self.portfolio_value
            )
            self.logger.info(f"卖出 Down 3 SHARES: {no3_shares} 成功")
        except Exception as e:
            self.logger.info(f"❌ only_sell_no3执行失败,重试")
            self.only_sell_no3()
            
    def Verify_buy_yes(self):
        """
        验证交易是否成功完成Returns:bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
            
            time.sleep(1)
            try:
                yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY[0])
            except NoSuchElementException:
                yes_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = yes_element.text
            trade_type = re.search(r'\b(Bought)\b', text)  # 匹配单词 Bought
            yes_match = re.search(r'\b(Up)\b', text)  # 匹配单词 Up
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
            price_match = re.search(r'(\d+)¢', text)  # 匹配 数字¢ 格式

            # 添加空值检查
            if not all([trade_type, yes_match]):
                #self.logger.warning(f"正则匹配失败,text内容: {text}")
                return False

            if trade_type.group(1) == "Bought" and yes_match.group(1) == "Up":
                self.trade_type = trade_type.group(1)  # 获取 "Bought"
                self.buy_yes_value = yes_match.group(1)  # 获取 "Up"
                self.buy_yes_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.buy_up_price = float(price_match.group(1))# 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_yes_value}-${self.buy_yes_amount}")
                return True, self.buy_yes_amount 
            return False       
        except Exception as e:
            self.logger.warning(f"❌ Verify_buy_yes执行失败: {str(e)}")
            return False
        finally:
            self.driver.refresh()
        
    def Verify_buy_no(self):
        """
        验证交易是否成功完成
        Returns:
        bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
            
            time.sleep(1)
            # 等待并检查是否存在 No 标签
            try:
                no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY[0])
            except NoSuchElementException:
                no_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = no_element.text

            trade_type = re.search(r'\b(Bought)\b', text)  # 匹配单词 Bought
            no_match = re.search(r'\b(Down)\b', text)  # 匹配单词 Down
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
            price_match = re.search(r'(\d+)¢', text)  # 匹配 数字¢ 格式

            if not all([trade_type, no_match]):
                self.logger.warning(f"正则匹配失败,text内容: {text}")
                return False

            if trade_type.group(1) == "Bought" and no_match.group(1) == "Down":
                self.trade_type = trade_type.group(1)  # 获取 "Bought"
                self.buy_no_value = no_match.group(1)  # 获取 "Down"
                self.buy_no_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.buy_down_price = float(price_match.group(1)) # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_no_value}-${self.buy_no_amount}")
                return True, self.buy_no_amount
            return False        
        except Exception as e:
            self.logger.warning(f"❌ Verify_buy_no执行失败: {str(e)}")
            return False
        finally:
            self.driver.refresh()
    
    def Verify_sold_yes(self):
        """
        验证交易是否成功完成Returns:bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)  

            time.sleep(2)
            try:
                yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY[0])
            except NoSuchElementException:
                yes_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = yes_element.text
            trade_type = re.search(r'\b(Sold)\b', text)  # 匹配单词 Sold
            yes_match = re.search(r'\b(Up)\b', text)  # 匹配单词 Up
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
            price_match = re.search(r'(\d+)¢', text)  # 匹配 数字¢ 格式

            if not all([trade_type, yes_match]):
                self.logger.warning(f"正则匹配失败,text内容: {text}")
                return False

            if trade_type.group(1) == "Sold" and yes_match.group(1) == "Up":
                self.trade_type = trade_type.group(1)  # 获取 "Sold"
                self.buy_yes_value = yes_match.group(1)  # 获取 "Up"
                self.sell_yes_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.sell_up_price = float(price_match.group(1)) # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_yes_value}-${self.sell_yes_amount}")
                return True, self.sell_yes_amount
            return False       
        except Exception as e:
            self.logger.warning(f"❌ Verify_sold_yes执行失败: {str(e)}")   
            return False
        finally:
            self.driver.refresh()
        
    def Verify_sold_no(self):
        """
        验证交易是否成功完成
        Returns:
        bool: 交易是否成功
        """
        try:
            # 首先验证浏览器状态
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)

            time.sleep(2)
            try:
                no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY[0])
            except NoSuchElementException:
                no_element = self._find_element_with_retry(
                    XPathConfig.HISTORY,
                    timeout=3,
                    silent=True
                )
            text = no_element.text

            trade_type = re.search(r'\b(Sold)\b', text)  # 匹配单词 Sold
            no_match = re.search(r'\b(Down)\b', text)  # 匹配单词 Down
            amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
            price_match = re.search(r'(\d+)¢', text)  # 匹配 数字¢ 格式

            if not all([trade_type, no_match]):
                self.logger.warning(f"正则匹配失败,text内容: {text}")
                return False

            if trade_type.group(1) == "Sold" and no_match.group(1) == "Down":
                self.trade_type = trade_type.group(1)  # 获取 "Sold"
                self.buy_no_value = no_match.group(1)  # 获取 "Down"
                self.sell_no_amount = float(amount_match.group(1))  # 获取数字部分并转为浮点数
                self.sell_down_price = float(price_match.group(1)) # 获取数字部分并转为浮点数
                self.logger.info(f"交易验证成功: {self.trade_type}-{self.buy_no_value}-${self.sell_no_amount}")
                return True, self.sell_no_amount
            return False        
        except Exception as e:
            self.logger.info(f"❌ Verify_sold_no执行失败: {str(e)}")
            return False
        finally:
            self.driver.refresh()
    """以上代码是交易主体函数 1-4,从第 1370 行到第 2418行"""

    """以下代码是交易过程中的各种点击方法函数，涉及到按钮的点击，从第 2419 行到第 2528 行"""
    def click_buy_confirm_button(self):
        try:
            buy_confirm_button = self.driver.find_element(By.XPATH, XPathConfig.BUY_CONFIRM_BUTTON[0])
            buy_confirm_button.click()
        except NoSuchElementException:
            
            buy_confirm_button = self._find_element_with_retry(
                XPathConfig.BUY_CONFIRM_BUTTON,
                timeout=3,
                silent=True
            )
            buy_confirm_button.click()
    
    def click_position_sell_no(self):
        """点击 Positions-Sell-No 按钮"""
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)

            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            position_value = self.find_position_label_yes()
            # position_value 的值是true 或 false
            # 根据position_value的值决定点击哪个按钮
            if position_value:
                # 如果第一行是Up，点击第二的按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_NO_BUTTON[0])
                except NoSuchElementException:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_NO_BUTTON,
                        timeout=3,
                        silent=True
                    )
            else:
                # 如果第一行不存在或不是Up，使用默认的第一行按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON[0])
                except NoSuchElementException:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_BUTTON,
                        timeout=3,
                        silent=True
                    )
            # 执行点击
            self.driver.execute_script("arguments[0].click();", button)
            
        except Exception as e:
            error_msg = f"点击 Positions-Sell-No 按钮失败: {str(e)}"
            self.logger.error(error_msg)
            

    def click_position_sell_yes(self):
        """点击 Positions-Sell-Yes 按钮"""
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)

            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            position_value = self.find_position_label_no()
            
            # 根据position_value的值决定点击哪个按钮
            
            if position_value:
                # 如果第二行是No，点击第一行YES 的 SELL的按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_YES_BUTTON[0])
                except NoSuchElementException:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_YES_BUTTON,
                        timeout=3,
                        silent=True
                    )
            else:
                # 如果第二行不存在或不是No，使用默认的第一行按钮
                try:
                    button = self.driver.find_element(By.XPATH, XPathConfig.POSITION_SELL_BUTTON[0])
                except NoSuchElementException:
                    button = self._find_element_with_retry(
                        XPathConfig.POSITION_SELL_BUTTON,
                        timeout=3,
                        silent=True
                    )
            # 执行点击
            self.driver.execute_script("arguments[0].click();", button)
             
        except Exception as e:
            error_msg = f"点击 Positions-Sell-Yes 按钮失败: {str(e)}"
            self.logger.error(error_msg)
            

    def click_sell_confirm_button(self):
        """点击sell-卖出按钮"""
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
            # 点击Sell-卖出按钮
            try:
                sell_confirm_button = self.driver.find_element(By.XPATH, XPathConfig.SELL_CONFIRM_BUTTON[0])
            except NoSuchElementException:
                sell_confirm_button = self._find_element_with_retry(
                    XPathConfig.SELL_CONFIRM_BUTTON,
                    timeout=3,
                    silent=True
                )
            sell_confirm_button.click()
            
        except Exception as e:
            error_msg = f"卖出操作失败: {str(e)}"
            self.logger.error(error_msg)

    def click_buy(self):
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_BUTTON[0])
            except NoSuchElementException:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            
        except Exception as e:
            self.logger.error(f"点击 Buy 按钮失败: {str(e)}")

    def click_buy_yes(self):
        """点击 Buy-Yes 按钮"""
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
            
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_YES_BUTTON[0])
            except NoSuchElementException:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_YES_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            
        except Exception as e:
            self.logger.error(f"点击 Buy-Yes 按钮失败: {str(e)}")

    def click_buy_no(self):
        """点击 Buy-No 按钮"""
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
            try:
                button = self.driver.find_element(By.XPATH, XPathConfig.BUY_NO_BUTTON[0])
            except NoSuchElementException:
                button = self._find_element_with_retry(
                    XPathConfig.BUY_NO_BUTTON,
                    timeout=3,
                    silent=True
                )
            button.click()
            
        except Exception as e:
            self.logger.error(f"点击 Buy-No 按钮失败: {str(e)}")

    def click_amount(self, event=None):
        """点击 Amount 按钮并输入数量"""
        try:
            if not self.driver and not self.is_restarting:
                self.restart_browser(force_restart=True)
            
            # 获取触发事件的按钮
            button = event.widget if event else self.amount_button
            button_text = button.cget("text")

            # 找到输入框
            try:
                amount_input = self.driver.find_element(By.XPATH, XPathConfig.AMOUNT_INPUT[0])
            except NoSuchElementException:
                amount_input = self._find_element_with_retry(
                    XPathConfig.AMOUNT_INPUT,
                    timeout=3,
                    silent=True
                )

            # 清空输入框
            amount_input.clear()
            # 根据按钮文本获取对应的金额
            if button_text == "Amount-Y1":
                amount = self.yes1_amount_entry.get()
            elif button_text == "Amount-Y2":
                yes2_amount_entry = self.yes_frame.grid_slaves(row=3, column=1)[0]
                amount = yes2_amount_entry.get()
            elif button_text == "Amount-Y3":
                yes3_amount_entry = self.yes_frame.grid_slaves(row=5, column=1)[0]
                amount = yes3_amount_entry.get()
            elif button_text == "Amount-Y4":
                yes4_amount_entry = self.yes_frame.grid_slaves(row=7, column=1)[0]
                amount = yes4_amount_entry.get()
            
            # No 按钮
            elif button_text == "Amount-N1":
                no1_amount_entry = self.no_frame.grid_slaves(row=1, column=1)[0]
                amount = no1_amount_entry.get()
            elif button_text == "Amount-N2":

                no2_amount_entry = self.no_frame.grid_slaves(row=3, column=1)[0]
                amount = no2_amount_entry.get()
            elif button_text == "Amount-N3":
                no3_amount_entry = self.no_frame.grid_slaves(row=5, column=1)[0]
                amount = no3_amount_entry.get()
            elif button_text == "Amount-N4":
                no4_amount_entry = self.no_frame.grid_slaves(row=7, column=1)[0]
                amount = no4_amount_entry.get()
            else:
                amount = "0"
            # 输入金额
            amount_input.send_keys(str(amount))
              
        except Exception as e:
            self.logger.error(f"Amount操作失败: {str(e)}")
    """以下代码是交易过程中的功能性函数,买卖及确认买卖成功,从第 2529 行到第 2703 行"""
    def position_yes_cash(self):
        """获取当前持仓YES的金额"""
        try:
            yes_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY[0])
        except NoSuchElementException:
            yes_element = self._find_element_with_retry(
                XPathConfig.HISTORY,
                timeout=3,
                silent=True
            )
        text = yes_element.text
        amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
        yes_value = float(amount_match.group(1))
        self.logger.info(f"当前持仓YES的金额: {yes_value}")
        return yes_value
    
    def position_no_cash(self):
        """获取当前持仓NO的金额"""
        try:
            no_element = self.driver.find_element(By.XPATH, XPathConfig.HISTORY[0])
        except NoSuchElementException:
            no_element = self._find_element_with_retry(
                XPathConfig.HISTORY,
                timeout=3,
                silent=True
            )
        text = no_element.text
        amount_match = re.search(r'\$(\d+\.?\d*)', text)  # 匹配 $数字 格式
        no_value = float(amount_match.group(1))
        self.logger.info(f"当前持仓NO的金额: {no_value}")
        return no_value

    def close_windows(self):
        """关闭多余窗口"""
        # 检查并关闭多余的窗口，只保留一个
        all_handles = self.driver.window_handles
        
        if len(all_handles) > 1:
            #self.logger.info(f"当前窗口数: {len(all_handles)}，准备关闭多余窗口")
            # 保留最后一个窗口，关闭其他所有窗口
            current_handle = all_handles[-1]  # 使用最后一个窗口
            
            # 关闭除了最后一个窗口外的所有窗口
            for handle in all_handles[:-1]:
                self.driver.switch_to.window(handle)
                self.driver.close()
            
            # 切换到保留的窗口
            self.driver.switch_to.window(current_handle)
            
        else:
            self.logger.warning("❗ 当前窗口数不足2个,无需切换")

    def set_default_price(self, price):
        """设置默认目标价格"""
        try:
            self.default_target_price = float(price)
            self.yes1_price_entry.delete(0, tk.END)
            self.yes1_price_entry.insert(0, str(self.default_target_price))
            self.no1_price_entry.delete(0, tk.END)
            self.no1_price_entry.insert(0, str(self.default_target_price))
            self.logger.info(f"默认目标价格已更新为: {price}")
        except ValueError:
            self.logger.error("价格设置无效，请输入有效数字")

    def send_trade_email(self, trade_type, price, amount, trade_count,
                         cash_value, portfolio_value):
        """发送交易邮件"""
        max_retries = 2
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                hostname = socket.gethostname()
                sender = 'huacaihuijin@126.com'
                receiver = 'huacaihuijin@126.com'
                app_password = 'PUaRF5FKeKJDrYH7'  # 有效期 180 天，请及时更新，下次到期日 2025-11-29
                
                # 获取交易币对信息
                full_pair = self.trading_pair_label.cget("text")
                trading_pair = full_pair.split('-')[0]
                if not trading_pair or trading_pair == "--":
                    trading_pair = "未知交易币对"
                
                # 根据交易类型选择显示的计数
                count_in_subject = self.sell_count if "Sell" in trade_type else trade_count
                
                msg = MIMEMultipart()
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                subject = f'{hostname}重启{self.reset_trade_count}次第{count_in_subject}次{trade_type}-{trading_pair}'
                msg['Subject'] = Header(subject, 'utf-8')
                msg['From'] = sender
                msg['To'] = receiver

                # 修复格式化字符串问题，确保cash_value和portfolio_value是字符串
                str_cash_value = str(cash_value)
                str_portfolio_value = str(portfolio_value)
                
                content = f"""
                交易价格: {price:.2f}¢
                交易金额: ${amount:.2f}
                当前买入次数: {self.trade_count}
                当前卖出次数: {self.sell_count}
                当前 CASH 值: {str_cash_value}
                当前 PORTFOLIO 值: {str_portfolio_value}
                交易时间: {current_time}
                """
                msg.attach(MIMEText(content, 'plain', 'utf-8'))
                
                # 使用126.com的SMTP服务器
                server = smtplib.SMTP_SSL('smtp.126.com', 465, timeout=5)  # 使用SSL连接
                server.set_debuglevel(0)
                
                try:
                    server.login(sender, app_password)
                    server.sendmail(sender, receiver, msg.as_string())
                    self.logger.info(f"✅ \033[34m邮件发送成功: {trade_type}\033[0m")
                    return  # 发送成功,退出重试循环
                except Exception as e:
                    self.logger.error(f"❌ SMTP操作失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                finally:
                    try:
                        server.quit()
                    except Exception:
                        pass          
            except Exception as e:
                self.logger.error(f"❌ 邮件准备失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)     
        # 所有重试都失败
        error_msg = f"发送邮件失败,已重试{max_retries}次"
        self.logger.error(error_msg)

    def stop_monitoring(self):
        """停止监控"""
        try:
            self.running = False
            self.stop_event.set()  # 设置停止事件
            # 取消所有定时器
            for timer in [self.url_check_timer, self.login_check_timer, self.refresh_timer]:
                if timer:
                    self.root.after_cancel(timer)
            # 停止URL监控
            if self.url_check_timer:
                self.root.after_cancel(self.url_check_timer)
                self.url_check_timer = None
            # 停止登录状态监控
            if self.login_check_timer:
                self.root.after_cancel(self.login_check_timer)
                self.login_check_timer = None
            
            self.start_button['state'] = 'normal'
            
            self.set_amount_button['state'] = 'disabled'  # 禁用更新金额按钮
            
            # 恢复"开始监控"文字为蓝色
            self.start_button.configure(style='Black.TButton')
            if self.driver:
                self.driver.quit()
                self.driver = None
            # 记录最终交易次数
            final_trade_count = self.trade_count
            self.logger.info(f"本次监控共执行 {final_trade_count} 次交易")

            # 取消页面刷新定时器
            if self.refresh_timer:
                self.root.after_cancel(self.refresh_timer)
                self.refresh_timer = None

            if hasattr(self, 'monitor_prices_timer'):
                self.root.after_cancel(self.monitor_prices_timer)  # 取消定时器
                self.monitor_prices_timer = None

        except Exception as e:
            self.logger.error(f"停止监控失败: {str(e)}")

    def retry_operation(self, operation, *args, **kwargs):
        """通用重试机制"""
        for attempt in range(self.retry_count):
            try:
                return operation(*args, **kwargs)
            except Exception as e:
                self.logger.warning(f"{operation.__name__} 失败，尝试 {attempt + 1}/{self.retry_count}: {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_interval)
                else:
                    raise

    """以下代码是自动找币功能,从第 2981 行到第 35320 行"""
    # 自动找币第一步:判断是否持仓,是否到了找币时间
    def find_position_label_yes(self):
        """查找Yes持仓标签"""
        max_retries = 2
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if not self.driver and not self.is_restarting:
                    self.restart_browser(force_restart=True)
                    
                # 等待页面加载完成
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 尝试获取Up标签
                try:
                    position_label_up = None
                    position_label_up = self.driver.find_element(By.XPATH, XPathConfig.POSITION_UP_LABEL[0])
                    if position_label_up is not None and position_label_up:
                        self.logger.info(f"找到了Up持仓标签: {position_label_up.text}")
                        return True
                    else:
                        self.logger.info("USE FIND-element,未找到Up持仓标签")
                        return False
                except NoSuchElementException:
                    position_label_up = self._find_element_with_retry(XPathConfig.POSITION_UP_LABEL, timeout=3, silent=True)
                    if position_label_up is not None and position_label_up:
                        self.logger.info(f"找到了Up持仓标签: {position_label_up.text}")
                        return True
                    else:
                        self.logger.info("use with-retry,未找到Up持仓标签")
                        return False
                         
            except TimeoutException:
                self.logger.debug(f"第{attempt + 1}次尝试未找到UP标签,正常情况!")
            
            if attempt < max_retries - 1:
                self.logger.info(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                self.driver.refresh()
        return False
        
    def find_position_label_no(self):
        """查找Down持仓标签"""
        max_retries = 2
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if not self.driver and not self.is_restarting:
                    self.restart_browser(force_restart=True)
                    
                # 等待页面加载完成
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                
                # 尝试获取Down标签
                try:
                    position_label_down = None
                    position_label_down = self.driver.find_element(By.XPATH, XPathConfig.POSITION_DOWN_LABEL[0])
                    if position_label_down is not None and position_label_down:
                        self.logger.info(f"use find-element,找到了Down持仓标签: {position_label_down.text}")
                        return True
                    else:
                        self.logger.info("use find-element,未找到Down持仓标签")
                        return False
                except NoSuchElementException:
                    position_label_down = self._find_element_with_retry(XPathConfig.POSITION_DOWN_LABEL, timeout=3, silent=True)
                    if position_label_down is not None and position_label_down:
                        self.logger.info(f"use with-retry,找到了Down持仓标签: {position_label_down.text}")
                        return True
                    else:
                        self.logger.info("use with-retry,未找到Down持仓标签")
                        return False
                               
            except TimeoutException:
                self.logger.warning(f"第{attempt + 1}次尝试未找到Down标签")
                
            if attempt < max_retries - 1:
                self.logger.info(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                self.driver.refresh()
        return False
      
    def _find_element_with_retry(self, xpaths, timeout=3, silent=False):
        """优化版XPATH元素查找(增强空值处理)"""
        try:
            for i, xpath in enumerate(xpaths, 1):
                try:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    return element
                except TimeoutException:
                    if not silent:
                        self.logger.warning(f"第{i}个XPATH定位超时: {xpath}")
                    continue
        except Exception as e:
            if not silent:
                raise
        return None
    
    def switch_to_frame_containing_element(self, xpath, timeout=10):
        """
        自动切换到包含指定xpath元素的iframe。
        - xpath: 你要找的元素的xpath,比如 '(//span[@class="c-ggujGL"])[2]'
        """
        self.driver.switch_to.default_content()  # 先回到主文档
        frames = self.driver.find_elements(By.TAG_NAME, "iframe")  # 找到所有 iframe

        for i, frame in enumerate(frames):
            self.driver.switch_to.frame(frame)
            try:
                WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
                self.logger.info(f"成功切换到第 {i} 个 iframe")
                return True
            except:
                self.driver.switch_to.default_content()  # 如果没找到，切回主文档，继续下一个
                continue

        self.logger.info("没有找到包含元素的 iframe")
        return False

    def monitor_xpath_elements(self):
        """使用当前浏览器实例监控 XPath 元素"""
        if not self.driver and not self.is_restarting:
            self.logger.warning("浏览器未启动，无法监控 XPath")
            return
            
        try:
            # 获取 XPathConfig 中的所有属性
            xpath_config = XPathConfig()
            # 定义要排除的 XPath 属性
            excluded_attrs = ['ACCEPT_BUTTON', 'LOGIN_BUTTON', 'LOGIN_WITH_GOOGLE_BUTTON','HISTORY',
                              'POSITION_SELL_BUTTON', 'POSITION_SELL_YES_BUTTON', 'POSITION_SELL_NO_BUTTON',
                              'POSITION_UP_LABEL', 'POSITION_DOWN_LABEL', 'POSITION_YES_VALUE', 'POSITION_NO_VALUE',
                              'SEARCH_CONFIRM_BUTTON','SEARCH_INPUT','SPREAD'
                              ]
            # 获取所有 XPath 属性，排除指定的属性
            xpath_attrs = [attr for attr in dir(xpath_config) 
                        if not attr.startswith('__') 
                        and isinstance(getattr(xpath_config, attr), list)
                        and attr not in excluded_attrs]
            failed_xpaths = []
            
            # 只检查每个 XPath 列表的第一个元素
            for attr in xpath_attrs:
                xpath_list = getattr(xpath_config, attr)
                if xpath_list:  # 确保列表不为空
                    first_xpath = xpath_list[0]  # 只获取第一个 XPath
                    try:
                        # 尝试定位元素，设置超时时间为 5 秒
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, first_xpath))
                        )
                    except (TimeoutException, NoSuchElementException):
                        self.logger.warning(f"❌ {attr} 定位失败: {first_xpath}")
                        failed_xpaths.append((attr, first_xpath))
            
            # 如果有失败的 XPath，发送邮件
            if failed_xpaths:
                subject = f"⚠️ XPath 监控警告: {len(failed_xpaths)} 个 XPath 定位失败"
                body = "以下 XPath 无法正常定位到元素:\n\n"
                
                for name, xpath in failed_xpaths:
                    body += f"{name}: {xpath}\n"
                
                body += "\n请尽快检查并更新 xpath_config.py 文件。"
                

                # 使用 send_trade_email 方法发送邮件
                self.send_trade_email(
                                trade_type="XPATH检查",
                                price=0,
                                amount=0,
                                trade_count=0,
                                cash_value=subject,
                                portfolio_value=body
                            )
                
                self.logger.warning(f"❌ 发现 {len(failed_xpaths)} 个 XPath 定位失败，已发送邮件通知")
            
        except Exception as e:
            self.logger.error(f"❌  监控 XPath 元素时发生错误: {str(e)}")
        finally:
            # 每隔 1 小时检查一次,先关闭之前的定时器
            self.root.after_cancel(self.monitor_xpath_timer)
            self.root.after(3600000, self.monitor_xpath_elements)

    def schedule_auto_find_coin(self):
        """安排每天3点30分执行自动找币"""
        now = datetime.now()
        # 计算下一个3点2分的时间
        next_run = now.replace(hour=3, minute=30, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        
        # 计算等待时间(毫秒)
        wait_time = (next_run - now).total_seconds() * 1000
        wait_time_hours = wait_time / 3600000
        
        # 设置定时器
        selected_coin = self.coin_combobox.get()
        self.root.after(int(wait_time), lambda: self.find_54_coin(selected_coin))
        self.logger.info(f"✅ \033[34m{round(wait_time_hours,2)}\033[0m小时后,开始自动找币")

    def find_54_coin(self,coin_type):
        """自动找币"""
        self.logger.info("✅ 开始自动找币")
        try:
            self.stop_url_monitoring()
            self.stop_refresh_page()
            # 保存原始窗口句柄，确保在整个过程中有一个稳定的引用
            self.original_window = self.driver.current_window_handle
            
            # 设置搜索关键词
            coins = [coin_type]
            for coin in coins:
                try:  # 为每个币种添加单独的异常处理 
                    new_url = self.find_new_weekly_url(coin)

                    def save_new_url(new_url):
                        if new_url:
                            self.driver.get(new_url)
                            # 保存当前 URL 到 config
                            self.config['website']['url'] = new_url
                            self.save_config()
                            
                            # 清除url_entry中的url
                            self.url_entry.delete(0, tk.END)
                            # 把保存到config的url放到self.url_entry中
                            self.url_entry.insert(0, new_url)

                            # 获取trader_pair,用于显示在主界面上
                            pair = re.search(r'event/([^?]+)', new_url)
                            self.trading_pair_label.config(text=pair.group(1))
                            self.logger.info(f"\033[34m✅ 新URL已插入到主界面上: {new_url} \033[0m")
                    save_new_url(new_url)

                except Exception as e:
                    self.logger.error(f"处理{coin}时出错: {str(e)}")
                    save_new_url(new_url)

            self.start_url_monitoring()
            self.refresh_page()
            
        except Exception as e:
            self.logger.error(f"自动找币异常: {str(e)}")
            self.find_54_coin(coin_type)

    def find_new_weekly_url(self, coin):
        """在Polymarket市场搜索指定币种的周合约地址,只返回URL"""
        try:
            if self.trading:
                return

            # 保存当前窗口句柄作为局部变量，用于本方法内部使用
            original_tab = self.driver.current_window_handle
            
            base_url = "https://polymarket.com/markets/crypto?_s=start_date%3Adesc"
            self.driver.switch_to.new_window('tab')
            self.driver.get(base_url)

            # 定义search_tab变量，保存搜索标签页的句柄
            search_tab = self.driver.current_window_handle

            # 等待页面加载完成
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # 等待页面渲染完成
            
            # 设置搜索关键词
            if coin == 'BTC':
                search_text = 'Bitcoin Up or Down on'
            elif coin == 'ETH':
                search_text = 'Ethereum Up or Down on'
            elif coin == 'SOL':
                search_text = 'Solana Up or Down on'
            elif coin == 'XRP':
                search_text = 'XRP Up or Down on'
            
            try:
                # 使用确定的XPath查找搜索框
                try:
                    search_box = self.driver.find_element(By.XPATH, XPathConfig.SEARCH_INPUT[0])
                except NoSuchElementException:
                    search_box = self._find_element_with_retry(
                        XPathConfig.SEARCH_INPUT,
                        timeout=3,
                        silent=True
                    )
                
                # 创建ActionChains对象
                actions = ActionChains(self.driver)
                
                # 清除搜索框并输入搜索词
                search_box.clear()
                search_box.send_keys(search_text)
                time.sleep(0.5)
                # 把搜索词保存到self.search_text
                self.search_text = search_text
                # 按ENTER键开始搜索
                actions.send_keys(Keys.RETURN).perform()
                time.sleep(2)  # 等待搜索结果加载
                
                self.click_today_card()
                
                # 切换到新标签页获取完整URL
                time.sleep(2)  
        
                # 获取所有窗口句柄
                all_handles = self.driver.window_handles
                
                # 切换到最新打开的标签页
                if len(all_handles) > 2:  # 原始窗口 + 搜索标签页 + coin标签页
                    
                    self.driver.switch_to.window(all_handles[-1])
                    WebDriverWait(self.driver, 20).until(EC.url_contains('/event/'))
                    
                    # 获取当前URL
                    new_url = self.driver.current_url
                    time.sleep(5)

                    # 这里如果价格是 52,那么会触发自动交易
                    if self.trading == True:
                        time.sleep(50)
                        
                        # 保存当前 URL 到 config
                        self.config['website']['url'] = new_url
                        self.save_config()
                        self.logger.info(f"✅ {coin}:符合要求, 正在交易,已保存到 config")
                        
                        # 把保存到config的url放到self.url_entry中
                        # 保存前,先删除现有的url
                        self.url_entry.delete(0, tk.END)
                        self.url_entry.insert(0, new_url)
                        
                        pair = re.search(r'event/([^?]+)', new_url)
                        self.trading_pair_label.config(text=pair.group(1))
                        self.logger.info(f"✅ {new_url}:已插入到主界面上")

                        target_url_window = self.driver.current_window_handle
                        time.sleep(2)

                        # 关闭原始和搜索窗口
                        self.driver.switch_to.window(search_tab)
                        self.driver.close()
                        self.driver.switch_to.window(original_tab)
                        self.driver.close()
                        self.driver.switch_to.window(target_url_window)

                        self.start_url_monitoring()
                        self.refresh_page()

                    else:
                        # 关闭当前详情URL标签页
                        self.driver.close()
                        
                        # 切换回搜索标签页
                        self.driver.switch_to.window(search_tab)
                        
                        # 关闭搜索标签页
                        self.driver.close()
                        
                        # 切换回原始窗口
                        self.driver.switch_to.window(original_tab)
                        self.logger.info(f"✅ find_new_weekly_url return:{new_url}")
                        return new_url
                else:
                    self.logger.warning(f"❌未能打开{coin}的详情页")
                    # 关闭搜索标签页
                    self.driver.close()
                    # 切换回原始窗口
                    self.driver.switch_to.window(original_tab)
                    return None
                
            except NoSuchElementException as e:
                self.logger.warning(f"❌ 未找到{coin}链接")
                # 关闭搜索标签页
                self.driver.close()
                # 切换回原始窗口
                self.driver.switch_to.window(original_tab)
                return None
            
        except Exception as e:
            self.logger.error(f"操作失败: {str(e)}")

    def click_today_card(self):
        """使用Command/Ctrl+Click点击包含今天日期的卡片,打开新标签页"""
        try:
            # 获取当前日期字符串，比如 "April 18"
            if platform.system() == 'Darwin':  # macOS
                today_str = datetime.now().strftime("%B %-d")  # macOS格式
            else:  # Linux (Ubuntu)
                today_str = datetime.now().strftime("%B %d").replace(" 0", " ")  # Linux格式，去掉前导零
            self.logger.info(f"🔍 查找包含日期 [{today_str}] 的链接...")

            # 获取所有含 "Bitcoin Up or Down on" 的卡片元素
            try:
                cards = self.driver.find_elements(By.XPATH, XPathConfig.SEARCH_CONFIRM_BUTTON[0])
            except NoSuchElementException:
                cards = self._find_element_with_retry(
                    XPathConfig.SEARCH_CONFIRM_BUTTON,
                    timeout=3,
                    silent=True
                )

            for card in cards:
                expected_text = self.search_text + " " + today_str + "?"
                if card.text.strip() == expected_text:
                    self.logger.info(f"\033[34m✅ 找到包含日期的卡片: {card.text.strip()}\033[0m")

                    # Command 键（macOS）或 Control 键（Windows/Linux）
                    modifier_key = Keys.COMMAND if sys.platform == 'darwin' else Keys.CONTROL

                    # 使用 ActionChains 执行 Command/Ctrl + Click
                    actions = ActionChains(self.driver)
                    actions.key_down(modifier_key).click(card).key_up(modifier_key).perform()

                    self.logger.info("\033[34m🆕 成功用快捷键打开新标签页！\033[0m")
                    return True

            self.logger.warning("\033[31m❌ 没有找到包含今天日期的卡片\033[0m")
            return False

        except Exception as e:
            self.logger.error(f"查找并点击今天日期卡片失败: {str(e)}")
            self.click_today_card()

    def get_zero_time_cash(self):
        """获取币安BTC实时价格,并在中国时区00:00触发"""
        try:
            # 零点获取 CASH 的值
            try:
                cash_element = self.driver.find_element(By.XPATH, XPathConfig.CASH_VALUE[0])
                cash_value = cash_element.text
            except NoSuchElementException:
                cash_element = self._find_element_with_retry(XPathConfig.CASH_VALUE, timeout=3, silent=True)
                cash_value = cash_element.text
            
            # 使用正则表达式提取数字
            cash_match = re.search(r'\$?([\d,]+\.?\d*)', cash_value)

            if not cash_match:
                raise ValueError("❌ 无法从Cash值中提取数字")

            # 移除逗号并转换为浮点数
            self.zero_time_cash_value = round(float(cash_match.group(1).replace(',', '')), 2)
            self.zero_time_cash_label.config(text=f"{self.zero_time_cash_value}")
            self.logger.info(f"✅ 获取到原始CASH值:\033[34m${self.zero_time_cash_value}\033[0m")

            # 设置 YES/NO 金额,延迟2秒确保数据稳定
            self.root.after(2000, self.schedule_update_amount)
            self.logger.info("✅ 设置 YES/NO 金额成功!")
        except Exception as e:
            self.get_zero_time_cash()
        finally:
            # 计算下一个00:10的时间
            now = datetime.now()
            tomorrow = now.replace(hour=0, minute=10, second=0, microsecond=0) + timedelta(days=1)
            seconds_until_midnight = (tomorrow - now).total_seconds()

            # 取消已有的定时器（如果存在）
            if hasattr(self, 'get_zero_time_cash_timer') and self.get_zero_time_cash_timer:
                self.root.after_cancel(self.get_zero_time_cash_timer)

            # 设置下一次执行的定时器
            if self.running and not self.stop_event.is_set():
                self.get_zero_time_cash_timer = threading.Timer(seconds_until_midnight, self.get_zero_time_cash)
                self.get_zero_time_cash_timer.daemon = True
                self.get_zero_time_cash_timer.start()
                self.logger.info(f"✅ \033[34m{round(seconds_until_midnight / 3600,2)}\033[0m小时后再次获取 \033[34mCASH\033[0m 值")
    
    def get_binance_zero_time_price(self):
        """获取币安BTC实时价格,并在中国时区00:00触发。此方法在threading.Timer的线程中执行。"""
        api_data = None
        coin_form_websocket = ""
        max_retries = 10 # 最多重试次数
        retry_delay = 2  # 重试间隔（秒）

        for attempt in range(max_retries):
            try:
                # 1. 获取币种信息
                selected_coin = self.coin_combobox.get() 
                coin_form_websocket = selected_coin + 'USDT'

                # --- 新增 websocket 获取价格逻辑 ---
                ws_url = f"wss://stream.binance.com:9443/ws/{coin_form_websocket.lower()}@ticker"
                price_holder = {'price': None}
                ws_error = {'error': None}

                def on_message(ws, message):
                    try:
                        data = json.loads(message)
                        price = round(float(data['c']), 3)
                        price_holder['price'] = price
                        ws.close()  # 收到一次价格后立即关闭连接
                    except Exception as e:
                        ws_error['error'] = e
                        ws.close()
                def on_error(ws, error):
                    ws_error['error'] = error
                    ws.close()
                def on_close(ws, close_status_code, close_msg):
                    pass
                # 获取币安价格
                ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
                ws_thread = threading.Thread(target=ws.run_forever)
                ws_thread.start()
                
                # 等待 websocket 获取到价格或超时
                ws_thread.join(timeout=5)
                if ws_error['error']:
                    raise Exception(ws_error['error'])
                if price_holder['price'] is None:
                    raise Exception("WebSocket 未能获取到价格")
                price = price_holder['price']
                # --- websocket 获取价格逻辑结束 ---

                api_data = {"price": price, "coin": coin_form_websocket, "original_selected_coin": selected_coin}
                self.logger.info(f"✅ ({attempt + 1}/{max_retries}) 成功获取到币安 \033[34m{api_data['coin']}\033[0m 价格: \033[34m{api_data['price']}\033[0m")
                
                break # 获取成功，跳出重试循环

            except Exception as e:
                self.logger.warning(f"❌ (尝试 {attempt + 1}/{max_retries}) 获取币安 \033[34m{coin_form_websocket}\033[0m 价格时发生错误: {e}")
                if attempt < max_retries - 1: # 如果不是最后一次尝试
                    self.logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay) # 等待后重试
                else: # 最后一次尝试仍然失败
                    self.logger.error(f"❌ 获取币安 \033[34m{coin_form_websocket}\033[0m 价格失败，已达到最大重试次数 ({max_retries})。")
        
        # 3. 如果成功获取数据 (即try块没有异常且api_data不为None)，则安排GUI更新到主线程
        if api_data:
            def update_gui():
                try:
                    # 获取到币安价格,并更新到GUI
                    self.zero_time_price = api_data["price"]
                    self.binance_zero_price_label.config(text=f"{self.zero_time_price}")
                except Exception as e_gui:
                    self.logger.debug(f"❌ 更新零点价格GUI时出错: {e_gui}")
            
            self.root.after(0, update_gui)

        # 设置定时器,每天00:00获取一次币安价格
        now = datetime.now()
        next_run_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now >= next_run_time:
            next_run_time += timedelta(days=1)

        seconds_until_next_run = (next_run_time - now).total_seconds()

        if hasattr(self, 'binance_zero_price_timer_thread') and self.binance_zero_price_timer and self.binance_zero_price_timer.is_alive():
            self.binance_zero_price_timer.cancel()

        if self.running and not self.stop_event.is_set():
            coin_for_next_log = self.coin_combobox.get() + 'USDT'
            self.binance_zero_price_timer = threading.Timer(seconds_until_next_run, self.get_binance_zero_time_price)
            self.binance_zero_price_timer.daemon = True
            self.binance_zero_price_timer.start()
            self.logger.info(f"✅ \033[34m{round(seconds_until_next_run / 3600,2)}\033[0m 小时后重新获取{coin_for_next_log} 零点价格")
    
    def get_binance_price_websocket(self):
        """获取币安价格,并计算上涨或下跌幅度"""
        # 获取币种信息
        selected_coin = self.coin_combobox.get()
        coin_form_websocket = selected_coin.lower() + 'usdt'
        # 获取币安价格
        ws_url = f"wss://stream.binance.com:9443/ws/{coin_form_websocket}@ticker"

        def on_message(ws, message):
            try:
                data = json.loads(message)
                # 获取最新成交价格
                now_price = round(float(data['c']), 3)
                # 计算上涨或下跌幅度
                zero_time_price_for_calc = getattr(self, 'zero_time_price', None)
                binance_rate_text = "--"
                rate_color = "blue"

                if zero_time_price_for_calc:
                    binance_rate = ((now_price - zero_time_price_for_calc) / zero_time_price_for_calc) * 100
                    binance_rate_text = f"{binance_rate:.3f}"
                    rate_color = "#1AAD19" if binance_rate >= 0 else "red"

                def update_gui():
                    try:
                        self.binance_now_price_label.config(text=f"{now_price}")
                        self.binance_rate_label.config(
                            text=f"{binance_rate_text}",
                            foreground=rate_color,
                            font=("Arial", 18, "bold")
                        )
                    except Exception as e:
                        self.logger.debug("❌ 更新GUI时发生错误:", e)

                self.root.after(0, update_gui)
            except Exception as e:
                self.logger.warning(f"WebSocket 消息处理异常: {e}")

        def on_error(ws, error):
            self.logger.warning(f"WebSocket 错误: {error}")

        def on_close(ws, close_status_code, close_msg):
            self.logger.info("WebSocket 连接已关闭")

        def run_ws():
            while self.running and not self.stop_event.is_set():
                try:
                    ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
                    ws.run_forever()
                except Exception as e:
                    self.logger.warning(f"WebSocket 主循环异常: {e}")
                time.sleep(5)  # 出错后延迟重连

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    def _perform_price_comparison(self):
        """执行价格比较"""
        try:
            # 获取0点当天的币安价格
            zero_time_price = round(float(self.binance_zero_price_label.cget('text').replace('$', '')),2)
            # 获取当前价格
            now_price = round(float(self.binance_now_price_label.cget('text').replace('$', '')),2)
            # 计算上涨或下跌幅度
            price_change = round(((now_price - zero_time_price) / zero_time_price) * 100,3)
            # 比较价格
            if 0 <= price_change <= 0.01 or -0.01 <= price_change <= 0:
                price_change = f"{round(price_change,3)}%"
                self.logger.info(f"✅ \033[34m{self.selected_coin}USDT当前价格上涨或下跌幅度小于{price_change},请立即关注\033[0m")
                self.send_trade_email(
                                trade_type=f"{self.selected_coin}USDT当前价格上涨或下跌幅度小于{price_change}",
                                price=zero_time_price,
                                amount=now_price,
                                trade_count=price_change,
                                cash_value=0,
                                portfolio_value=0
                            )
            
        except Exception as e:
            pass
        finally:
            self.comparison_binance_price()

    def comparison_binance_price(self):
        """设置定时器以在每天23点比较币安价格和当前价格"""
        now = datetime.now()
        # 设置目标时间为当天的23点
        target_time_today = now.replace(hour=23, minute=0, second=0, microsecond=0)

        if now < target_time_today:
            # 如果当前时间早于今天的23点，则在今天的23点执行
            next_run_time = target_time_today
        else:
            # 如果当前时间晚于或等于今天的23点，则在明天的23点执行
            next_run_time = target_time_today + timedelta(days=1)

        seconds_until_next_run = (next_run_time - now).total_seconds()
            # 取消已有的定时器（如果存在）
        if hasattr(self, 'comparison_binance_pric') and self.comparison_binance_price_timer:
            self.comparison_binance_price_timer.cancel()

            # 设置下一次执行的定时器
            if self.running and not self.stop_event.is_set():
                self.comparison_binance_price_timer = threading.Timer(seconds_until_next_run, self._perform_price_comparison)
                self.comparison_binance_price_timer.daemon = True
                self.comparison_binance_price_timer.start()
                self.logger.info(f"\033[34m{round(seconds_until_next_run / 3600,2)}\033[0m小时后比较\033[34m{self.selected_coin}USDT\033[0m币安价格")

if __name__ == "__main__":
    try:
        # 打印启动参数，用于调试
        
        # 初始化日志
        logger = Logger("main")
            
        # 创建并运行主程序
        app = CryptoTrader()
        app.root.mainloop()
        
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        if 'logger' in locals():
            logger.error(f"程序启动失败: {str(e)}")
        sys.exit(1)
    
