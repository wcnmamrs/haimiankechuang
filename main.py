#!/usr/bin/env python3
"""
海绵科创综合脚本
代码:deepseek模型制作
逆向:QQ3245987504
版本:v3.3
"""

import os
import sys
import time
import json
import logging
import threading
import schedule
import re
import base64
import platform
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import requests

# ============ 配置文件 ============
CONFIG_FILE = "config.json"  # 修改为单个配置文件
COOKIE_FILE = "yunmc_cookie.json"
LOG_FILE = "rz.txt"

# 默认配置 - 整合到一个文件
DEFAULT_CONFIG = {
    "account": {
        "username": "",
        "password": ""
    },
    "settings": {
        "auto_task_enabled": True,
        "auto_login_enabled": True,
        "auto_exchange_enabled": True,
        "auto_signin_enabled": True,
        "login_time": "11:00",
        "exchange_time": "12:00",
        "signin_time": "11:30",
        "close_browser_after_login": True,  # 修改为默认开启自动关闭浏览器
        "browser_default_mode": "headless",
        "screenshot_enabled": False,  # 截图总开关
        "screenshot_auto_enabled": False,  # 自动截屏开关
        "screenshot_manual_enabled": False,  # 手动截屏开关
        "burst_enabled": False,  # 连发功能开关
        "burst_count": 10,  # 连发次数
        "burst_interval": 1,  # 连发间隔（秒）
    },
    "gifts": {
        "selected_gifts": [20],  # 默认选择2h4g Minecraft服务器
        "gift_list": {  # 所有可选的礼品
            "20": {"name": "2H4G服务器(Minecraft)", "server": "我的世界区", "spec": "2h4g", "points": 1200},
            "19": {"name": "4H8G服务器(Minecraft)", "server": "我的世界区", "spec": "4h8g", "points": 2400},
            "18": {"name": "8H16G服务器(Minecraft)", "server": "我的世界区", "spec": "8h16g", "points": 4800},
            "17": {"name": "4H8G服务器(Palworld)", "server": "Palworld区", "spec": "4h8g", "points": 2400},
            "16": {"name": "6H12G服务器(Palworld)", "server": "Palworld区", "spec": "6h12g", "points": 3600},
            "15": {"name": "8H16G服务器(Palworld)", "server": "Palworld区", "spec": "8h16g", "points": 4800}
        }
    }
}

# ============ 工具函数 ============
class LogWriter:
    """日志写入器，捕获所有输出到日志文件"""
    def __init__(self, filename):
        self.log_file = open(filename, 'a', encoding='utf-8')
        self.terminal = sys.stdout
        
    def write(self, message):
        # 写入到终端
        self.terminal.write(message)
        # 写入到日志文件
        if message.strip():  # 只写入非空行
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 为日志添加时间戳
            for line in message.split('\n'):
                if line.strip():
                    self.log_file.write(f"[{timestamp}] {line}\n")
            self.log_file.flush()
            
    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

# 设置输出重定向
sys.stdout = LogWriter(LOG_FILE)
sys.stderr = sys.stdout

def print_with_time(message):
    """带时间戳打印 - 自动记录到日志文件"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

# ============ 配置验证函数 ============
def validate_config(config):
    """验证配置文件的有效性"""
    errors = []
    warnings = []
    
    # 1. 验证账号密码
    if not config["account"]["username"] or not config["account"]["password"]:
        errors.append("账号或密码未配置")
    
    # 2. 验证时间格式
    time_fields = ["login_time", "exchange_time", "signin_time"]
    for field in time_fields:
        if field in config["settings"]:
            time_value = config["settings"][field]
            if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_value):
                errors.append(f"时间格式错误: {field} = '{time_value}'，应为 HH:MM 或 HH:MM:SS 格式")
            else:
                # 验证时间值是否有效
                parts = time_value.split(':')
                hour = int(parts[0])
                minute = int(parts[1])
                second = int(parts[2]) if len(parts) > 2 else 0
                
                if hour < 0 or hour > 23:
                    errors.append(f"小时值无效: {field} = '{time_value}'，小时应在0-23之间")
                if minute < 0 or minute > 59:
                    errors.append(f"分钟值无效: {field} = '{time_value}'，分钟应在0-59之间")
                if second < 0 or second > 59:
                    errors.append(f"秒值无效: {field} = '{time_value}'，秒应在0-59之间")
    
    # 3. 验证礼品ID有效性
    gift_list = config["gifts"]["gift_list"]
    for gift_id in config["gifts"]["selected_gifts"]:
        if str(gift_id) not in gift_list:
            warnings.append(f"选择的礼品ID {gift_id} 不在可用礼品列表中，将自动移除")
    
    # 4. 验证数值范围
    burst_count = config["settings"].get("burst_count", 10)
    if burst_count < 1 or burst_count > 100:
        warnings.append(f"连发次数 {burst_count} 超出合理范围1-100，已调整为默认值10")
        config["settings"]["burst_count"] = 10
    
    burst_interval = config["settings"].get("burst_interval", 1)
    if burst_interval < 0.1 or burst_interval > 10:
        warnings.append(f"连发间隔 {burst_interval} 超出合理范围0.1-10，已调整为默认值1")
        config["settings"]["burst_interval"] = 1
    
    # 5. 验证浏览器模式
    browser_mode = config["settings"].get("browser_default_mode", "headless")
    if browser_mode not in ["headless", "gui"]:
        warnings.append(f"浏览器模式 '{browser_mode}' 无效，已调整为'headless'")
        config["settings"]["browser_default_mode"] = "headless"
    
    return config, errors, warnings

# ============ 配置加载函数 ============
def load_config():
    """从配置文件加载所有配置"""
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                # 深度合并配置
                if "account" in user_config:
                    config["account"].update(user_config["account"])
                if "settings" in user_config:
                    config["settings"].update(user_config["settings"])
                if "gifts" in user_config:
                    config["gifts"].update(user_config["gifts"])
            
            # 验证配置
            config, errors, warnings = validate_config(config)
            
            # 显示警告
            for warning in warnings:
                print_with_time(f"配置警告: {warning}")
            
            # 显示错误
            if errors:
                print_with_time("配置错误:")
                for error in errors:
                    print_with_time(f"  - {error}")
                print_with_time("请使用 'config' 命令重新配置或手动编辑配置文件")
                
                # 对于严重错误，使用默认值
                if "账号或密码未配置" in errors:
                    print_with_time("检测到账号密码未配置，将使用默认值")
                    
        except json.JSONDecodeError as e:
            print_with_time(f"配置文件格式错误: {e}")
            print_with_time("将使用默认配置，建议删除错误的配置文件后重新运行")
        except Exception as e:
            print_with_time(f"加载配置文件失败: {e}")
    else:
        # 配置文件不存在，返回默认配置
        print_with_time(f"配置文件 {CONFIG_FILE} 不存在，将使用默认配置")
    
    return config

def save_config(config):
    """保存所有配置到文件"""
    try:
        # 保存前验证配置
        config, errors, warnings = validate_config(config)
        
        if errors:
            print_with_time("保存配置前发现错误:")
            for error in errors:
                print_with_time(f"  - {error}")
            print_with_time("配置可能存在问题，但将继续保存")
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print_with_time(f"配置文件已保存: {os.path.abspath(CONFIG_FILE)}")
        return True
    except Exception as e:
        print_with_time(f"保存配置失败: {e}")
        return False

# ============ 首次运行向导 ============
def first_run_wizard():
    """首次运行配置向导"""
    print("\n" + "="*60)
    print("海绵科创综合脚本 - 首次运行配置向导")
    print("="*60)
    print("欢迎使用海绵科创综合脚本！")
    print("我们将引导您完成初始配置。")
    print("="*60)
    
    config = DEFAULT_CONFIG.copy()
    
    # 步骤1: 账号密码配置
    print("\n[步骤1/4] 账号密码配置-无账号请访问(https://www.yunmc.vip/login)注册")
    print("-" * 40)
    
    while True:
        username = input("请输入账号: ").strip()
        if username:
            config["account"]["username"] = username
            break
        else:
            print("账号不能为空，请重新输入")
    
    while True:
        password = input("请输入密码: ").strip()
        if password:
            config["account"]["password"] = password
            break
        else:
            print("密码不能为空，请重新输入")
    
    # 步骤2: 礼品选择
    print("\n[步骤2/4] 礼品选择")
    print("-" * 40)
    print("请选择要兑换的礼品（可多选）：")
    
    gifts = config["gifts"]["gift_list"]
    selected_gifts = []
    
    # 显示礼品列表
    print("\n可选礼品:")
    print("ID\t规格\t\t名称\t\t\t\t消耗积分")
    print("-" * 60)
    
    for gift_id, gift_info in gifts.items():
        print(f"{gift_id:2}\t{gift_info['spec']:8}\t{gift_info['name']:30}\t{gift_info['points']}")
    
    print("\n默认选择: ID 20 (2H4G Minecraft服务器)")
    
    while True:
        choice = input("\n请输入要选择的礼品ID（多个用逗号分隔，直接回车使用默认）: ").strip()
        
        if not choice:  # 使用默认
            selected_gifts = [20]
            print("已选择默认礼品: ID 20")
            break
        
        # 解析输入的ID
        gift_ids = [gid.strip() for gid in choice.split(',') if gid.strip()]
        valid_ids = []
        invalid_ids = []
        
        for gid in gift_ids:
            if gid in gifts:
                valid_ids.append(int(gid))
            else:
                invalid_ids.append(gid)
        
        if invalid_ids:
            print(f"以下ID无效: {', '.join(invalid_ids)}")
            print("请重新输入有效的礼品ID")
        elif valid_ids:
            selected_gifts = valid_ids
            print(f"已选择 {len(selected_gifts)} 个礼品:")
            for gid in selected_gifts:
                print(f"  - {gifts[str(gid)]['name']} (ID: {gid})")
            break
    
    config["gifts"]["selected_gifts"] = selected_gifts
    
    # 步骤3: 定时任务时间设置
    print("\n[步骤3/4] 定时任务时间设置")
    print("-" * 40)
    print("请设置定时任务执行时间（24小时制，格式: HH:MM）")
    
    time_fields = [
        ("login_time", "自动登录时间", "11:00"),
        ("exchange_time", "自动兑换时间", "12:00"),
        ("signin_time", "自动签到时间", "11:30")
    ]
    
    for field_name, display_name, default_time in time_fields:
        while True:
            time_input = input(f"{display_name} (默认: {default_time}): ").strip()
            
            if not time_input:  # 使用默认值
                config["settings"][field_name] = default_time
                print(f"已设置为默认时间: {default_time}")
                break
            
            # 验证时间格式
            if re.match(r'^\d{1,2}:\d{2}$', time_input):
                # 验证时间值
                parts = time_input.split(':')
                hour = int(parts[0])
                minute = int(parts[1])
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    config["settings"][field_name] = time_input
                    print(f"已设置为: {time_input}")
                    break
                else:
                    print("时间值无效，小时应在0-23之间，分钟应在0-59之间")
            else:
                print("时间格式错误，请使用 HH:MM 格式（如 09:30）")
    
    # 步骤4: 浏览器模式设置
    print("\n[步骤4/4] 浏览器模式设置")
    print("-" * 40)
    print("请选择浏览器运行模式：")
    print("1. 无头模式 (headless) - 后台运行，不显示浏览器界面（推荐服务器使用）")
    print("2. 图形界面模式 (gui) - 显示浏览器界面（需要桌面环境）")
    
    while True:
        mode_choice = input("请选择模式 (1 或 2，默认: 1): ").strip()
        
        if not mode_choice or mode_choice == "1":
            config["settings"]["browser_default_mode"] = "headless"
            print("已选择无头模式")
            break
        elif mode_choice == "2":
            config["settings"]["browser_default_mode"] = "gui"
            print("已选择图形界面模式")
            break
        else:
            print("输入无效，请选择 1 或 2")
    
    # 显示配置摘要
    print("\n" + "="*60)
    print("配置摘要")
    print("="*60)
    print(f"账号: {config['account']['username'][:3]}*****{config['account']['username'][-3:] if len(config['account']['username']) > 6 else '***'}")
    print(f"已选择礼品: {len(selected_gifts)} 个")
    for gid in selected_gifts:
        print(f"  - {gifts[str(gid)]['name']}")
    print(f"自动登录时间: {config['settings']['login_time']}")
    print(f"自动兑换时间: {config['settings']['exchange_time']}")
    print(f"自动签到时间: {config['settings']['signin_time']}")
    print(f"浏览器模式: {config['settings']['browser_default_mode']}")
    print("="*60)
    
    # 确认保存
    while True:
        confirm = input("\n是否保存以上配置？(y/n): ").strip().lower()
        if confirm in ['y', 'yes', '是']:
            if save_config(config):
                print("配置已保存！")
                print("您可以随时通过 'config' 或 'zs' 命令修改配置。")
                return config
            else:
                print("保存配置失败，将使用默认配置")
                return DEFAULT_CONFIG.copy()
        elif confirm in ['n', 'no', '否']:
            print("配置未保存，将使用默认配置")
            return DEFAULT_CONFIG.copy()
        else:
            print("请输入 y 或 n")

# 全局变量
config = None
settings = None
USERNAME = ""
PASSWORD = ""
driver = None
is_running = True
scheduler_thread = None
current_cookie = ""
last_login_time = None
last_exchange_time = None
last_signin_time = None
login_status = False
browser_mode = None  # 当前浏览器模式（内存中）

# 网站URL
BASE_URL = "https://www.yunmc.vip"
LOGIN_URL = f"{BASE_URL}/login"
TARGET_URL = f"{BASE_URL}/addons?_plugin=points_mall&_controller=index&_action=change"
POINTS_MALL_URL = f"{BASE_URL}/addons?_plugin=points_mall&_controller=index&_action=exchange"
POINTS_CENTER_URL = f"{BASE_URL}/addons?_plugin=points_mall&_controller=index&_action=index"
EXCHANGE_HISTORY_URL = f"{BASE_URL}/addons?_plugin=points_mall&_controller=index&_action=exchange_log"

def reload_config():
    """重新加载配置并更新全局变量"""
    global config, settings, USERNAME, PASSWORD
    
    config = load_config()
    settings = config["settings"]
    USERNAME = config["account"]["username"]
    PASSWORD = config["account"]["password"]
    
    # 检查账号密码是否已配置
    if not USERNAME or not PASSWORD:
        print_with_time("警告: 账号或密码未配置")
    
    return config

# 初始化配置
reload_config()

# ============ 浏览器管理模块 ============
def init_browser():
    """初始化浏览器"""
    global driver, browser_mode
    
    if driver is not None:
        try:
            driver.quit()
        except:
            pass
    
    try:
        chrome_options = Options()
        
        # 使用当前浏览器模式
        if browser_mode is None:
            # 如果还没有设置浏览器模式，使用默认模式
            browser_mode = settings.get("browser_default_mode", "headless")
        
        if browser_mode == "headless":
            chrome_options.add_argument("--headless")
        else:
            # 图形界面模式
            print_with_time("使用图形界面模式")
            
            # 设置显示（仅Linux/Unix系统需要）
            if platform.system() != "Windows" and "DISPLAY" not in os.environ:
                os.environ["DISPLAY"] = ":0"
                print_with_time(f"设置DISPLAY环境变量: {os.environ['DISPLAY']}")
            
            # 图形界面模式下的优化 - 确保最大化
            chrome_options.add_argument("--start-maximized")
        
        # 通用选项
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # 优化选项
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Windows适配：自动检测操作系统并选择正确的ChromeDriver路径
        system_platform = platform.system()
        
        if system_platform == "Windows":
            # Windows系统下的ChromeDriver路径
            chrome_driver_paths = [
                "chromedriver.exe",  # 当前目录
                "C:\\Windows\\chromedriver.exe",  # Windows系统目录
                os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "chromedriver\\chromedriver.exe"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "chromedriver\\chromedriver.exe"),
            ]
        else:
            # Linux/Unix系统下的ChromeDriver路径
            chrome_driver_paths = [
                "/usr/bin/chromedriver",  # 标准路径
                "/usr/local/bin/chromedriver",  # 本地安装路径
                "/snap/bin/chromedriver",  # Snap安装
                "chromedriver",  # PATH环境变量中的chromedriver
            ]
        
        # 查找可用的ChromeDriver
        chrome_driver_found = None
        for path in chrome_driver_paths:
            if os.path.exists(path):
                chrome_driver_found = path
                break
        
        if chrome_driver_found:
            print_with_time(f"使用ChromeDriver: {chrome_driver_found}")
            service = Service(executable_path=chrome_driver_found)
        else:
            print_with_time("警告: 未找到ChromeDriver，尝试使用系统PATH中的驱动")
            service = Service()
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 关键修复：确保所有模式下都有足够大的窗口尺寸
        if browser_mode == "headless":
            # 无头模式下设置大尺寸窗口
            driver.set_window_size(1920, 1080)
            print_with_time(f"无头模式设置窗口尺寸: 1920x1080")
        else:
            # GUI模式下确保最大化
            try:
                driver.maximize_window()
                print_with_time("图形模式已最大化窗口")
            except:
                # 某些系统可能不支持maximize_window，使用set_window_size
                driver.set_window_size(1920, 1080)
                print_with_time("图形模式设置窗口尺寸: 1920x1080")
            
            # 获取实际窗口尺寸
            try:
                size = driver.get_window_size()
                print_with_time(f"实际窗口尺寸: {size['width']}x{size['height']}")
            except:
                pass
        
        # 设置超时
        driver.set_page_load_timeout(15)
        driver.set_script_timeout(15)
        driver.implicitly_wait(5)
        
        print_with_time(f"浏览器初始化成功 (模式: {browser_mode}, 系统: {system_platform})")
        return True
    except Exception as e:
        print_with_time(f"浏览器初始化失败: {e}")
        
        # 如果图形界面模式失败，尝试无头模式
        if browser_mode == "gui":
            print_with_time("图形界面模式失败，尝试无头模式...")
            browser_mode = "headless"
            return init_browser()
        
        return False

def close_browser():
    """关闭浏览器"""
    global driver
    if driver is not None:
        try:
            driver.quit()
        except:
            pass
        driver = None
        print_with_time("浏览器已关闭")

def take_screenshot(description="", screenshot_type="auto"):
    """截取浏览器当前页面"""
    global driver
    
    if driver is None:
        print_with_time("浏览器未初始化，无法截图")
        return False
    
    # 检查截图总开关
    if not settings.get("screenshot_enabled", False):
        return False
    
    # 检查对应的子开关
    if screenshot_type == "auto" and not settings.get("screenshot_auto_enabled", False):
        return False
    elif screenshot_type == "manual" and not settings.get("screenshot_manual_enabled", False):
        return False
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if description:
            safe_desc = re.sub(r'[^\w\-_\. ]', '_', description)
            filename = f"screenshot_{timestamp}_{safe_desc}.png"
        else:
            filename = f"screenshot_{timestamp}.png"
        
        driver.save_screenshot(filename)
        
        try:
            url = driver.current_url
            title = driver.title
            print_with_time(f"截图已保存: {filename}")
            print_with_time(f"  页面标题: {title}")
            print_with_time(f"  页面URL: {url}")
        except:
            print_with_time(f"截图已保存: {filename}")
        
        return True
        
    except Exception as e:
        print_with_time(f"截图失败: {e}")
        return False

# ============ Cookie 管理 ============
def load_cookie():
    """从文件加载Cookie"""
    global current_cookie
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                data = json.load(f)
                current_cookie = data.get('cookie', '')
                if current_cookie:
                    print_with_time("从文件加载Cookie")
                    return True
        except Exception as e:
            print_with_time(f"加载Cookie文件失败: {e}")
    return False

def save_cookie(cookie_str):
    """保存Cookie到文件"""
    global current_cookie
    current_cookie = cookie_str
    
    data = {
        'cookie': cookie_str,
        'save_time': datetime.now().isoformat()
    }
    
    try:
        with open(COOKIE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print_with_time(f"Cookie已保存到文件，共 {len(cookie_str)} 字符")
        return True
    except Exception as e:
        print_with_time(f"保存Cookie失败: {e}")
        return False

# ============ 浏览器登录模块 ============
def browser_login_and_get_cookie(close_after_login=None):
    """通过浏览器登录并获取Cookie"""
    global driver, last_login_time, login_status, current_cookie
    
    if not init_browser():
        return False
    
    try:
        print_with_time("正在通过浏览器登录...")
        
        # 检查账号密码是否已配置
        if not USERNAME or not PASSWORD:
            print_with_time("错误: 账号或密码未配置，请先使用config命令配置")
            return False
        
        # 步骤1: 访问登录页面
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        # 截图点1: 登录前页面状态
        take_screenshot("登录前_页面加载完成", "auto")
        
        # 步骤2: 直接查找登录表单元素
        try:
            email_input = driver.find_element(By.CSS_SELECTOR, "input[name='email'], #emailInp")
            password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password'], #emailPwdInp")
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except Exception as e:
            print_with_time(f"查找登录表单元素时出错: {e}")
            take_screenshot("登录失败_找不到表单元素", "auto")
            return False
        
        # 步骤3: 填写登录信息
        email_input.clear()
        email_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(PASSWORD)
        
        # 截图点2: 输入账号密码后
        take_screenshot("登录中_账号密码已填写", "auto")
        
        # 步骤4: 提交登录
        submit_button.click()
        time.sleep(3)
        
        # 检查登录结果
        current_url = driver.current_url
        page_source = driver.page_source
        
        # 判断登录是否成功
        login_success = False
        if "login" not in current_url and "signin" not in current_url:
            login_success = True
        
        if not login_success and ("退出登录" in page_source or "logout" in page_source.lower()):
            login_success = True
        
        if login_success:
            login_status = True
            last_login_time = datetime.now()
            # 截图点3: 登录成功
            take_screenshot("登录成功", "auto")
            print_with_time("登录成功")
        else:
            # 截图点3: 登录失败
            take_screenshot("登录失败", "auto")
            print_with_time("登录失败")
            return False
        
        # 获取Cookies并格式化为字符串
        cookies = driver.get_cookies()
        cookie_str = ""
        for cookie in cookies:
            cookie_str += f"{cookie['name']}={cookie['value']}; "
        cookie_str = cookie_str.strip()
        
        if not cookie_str:
            print_with_time("未能获取到有效的Cookie")
            return False
        
        # 保存Cookie
        save_cookie(cookie_str)
        
        print_with_time(f"Cookie已获取并保存，预览: {cookie_str[:100]}...")
        
        # 根据设置决定是否关闭浏览器
        if close_after_login is None:
            close_after_login = settings.get("close_browser_after_login", False)
        
        if close_after_login:
            close_browser()
        
        return True
        
    except Exception as e:
        print_with_time(f"浏览器登录过程中发生异常: {e}")
        take_screenshot("登录异常", "auto")
        return False

# ============ HTTP请求兑换模块 ============
def http_exchange_gift_burst(gift_ids=None, burst_count=None, burst_interval=None):
    """通过HTTP请求兑换礼品（支持多礼品、多线程、连发）"""
    global last_exchange_time
    
    if not current_cookie:
        print_with_time("错误: 没有可用的Cookie，请先登录")
        return False
    
    # 获取配置
    if gift_ids is None:
        gift_ids = [str(gid) for gid in config["gifts"]["selected_gifts"]]
    
    if not gift_ids:
        print_with_time("错误: 没有选择任何礼品")
        return False
    
    if burst_count is None:
        burst_count = settings.get("burst_count", 10)
    
    if burst_interval is None:
        burst_interval = settings.get("burst_interval", 1)
    
    # 准备礼品信息
    gifts_info = config["gifts"]["gift_list"]
    selected_gifts_info = []
    for gift_id in gift_ids:
        if str(gift_id) in gifts_info:
            selected_gifts_info.append((str(gift_id), gifts_info[str(gift_id)]))
    
    if not selected_gifts_info:
        print_with_time("错误: 选择的礼品无效")
        return False
    
    print_with_time(f"开始兑换 {len(selected_gifts_info)} 个礼品，连发次数: {burst_count}，间隔: {burst_interval}秒")
    for gift_id, gift_info in selected_gifts_info:
        print_with_time(f"  - {gift_info['name']} (ID: {gift_id}, 消耗积分: {gift_info['points']})")
    
    # 创建一个线程安全字典来跟踪每个礼品的兑换成功状态
    success_dict = {}
    for gift_id, _ in selected_gifts_info:
        success_dict[gift_id] = False
    
    # 创建一个锁，用于线程安全地更新成功字典
    success_lock = threading.Lock()
    
    def exchange_single(gift_id, burst_index, success_dict, success_lock):
        """单次兑换"""
        # 检查这个礼品是否已经兑换成功
        with success_lock:
            if success_dict.get(gift_id, False):
                return None  # 如果已经成功，直接返回
        
        try:
            url = TARGET_URL
            data = f"id={gift_id}"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Cookie': current_cookie,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Origin': BASE_URL,
                'Referer': f'{BASE_URL}/',
            }
            
            start_time = time.time()
            response = requests.post(url, data=data, headers=headers, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            # 解析响应
            result = {
                'gift_id': gift_id,
                'gift_name': gifts_info.get(gift_id, {}).get('name', '未知'),
                'burst_index': burst_index,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status_code': response.status_code,
                'response_time_ms': round(response_time, 2),
                'raw_response': response.text
            }
            
            # 尝试解析JSON
            try:
                json_data = response.json()
                result['code'] = json_data.get('code')
                result['msg'] = json_data.get('msg')
            except json.JSONDecodeError:
                result['code'] = None
                result['msg'] = '非JSON响应'
            
            # 如果兑换成功，标记为成功
            if result.get('code') == 200:
                with success_lock:
                    success_dict[gift_id] = True
            
            return result
            
        except Exception as e:
            return {
                'gift_id': gift_id,
                'gift_name': gifts_info.get(gift_id, {}).get('name', '未知'),
                'burst_index': burst_index,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status_code': 0,
                'response_time_ms': 0,
                'code': None,
                'msg': f'请求异常: {str(e)}',
                'raw_response': ''
            }
    
    # 执行连发兑换
    all_results = []
    
    for burst_index in range(burst_count):
        # 检查是否还有未成功的礼品
        with success_lock:
            active_gifts = []
            for gift_id, gift_info in selected_gifts_info:
                if not success_dict.get(gift_id, False):
                    active_gifts.append((gift_id, gift_info))
        
        if not active_gifts:
            print_with_time("所有礼品都已兑换成功，停止连发")
            break
        
        print_with_time(f"第 {burst_index + 1}/{burst_count} 次连发，剩余 {len(active_gifts)} 个礼品...")
        
        # 创建线程池并发兑换
        threads = []
        thread_results = []
        
        for gift_id, gift_info in active_gifts:
            thread = threading.Thread(
                target=lambda gid=gift_id, idx=burst_index: thread_results.append(
                    exchange_single(gid, idx, success_dict, success_lock)
                )
            )
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 收集结果
        for result in thread_results:
            if result is None:  # 跳过的礼品
                continue
            
            all_results.append(result)
            
            if result.get('code') == 200:
                print_with_time(f"  ✓ {result['gift_name']}: 兑换成功 (响应: {result['response_time_ms']}ms)")
            else:
                print_with_time(f"  ✗ {result['gift_name']}: 兑换失败 ({result.get('msg', '未知错误')})")
        
        # 如果不是最后一次，则等待间隔
        if burst_index < burst_count - 1 and len(active_gifts) > 0:
            time.sleep(burst_interval)
    
    # 统计结果
    success_count = sum(1 for r in all_results if r.get('code') == 200)
    total_count = len(all_results)
    
    print_with_time(f"兑换完成: 成功 {success_count}/{total_count} 次")
    
    # 记录最后一次兑换时间
    if success_count > 0:
        last_exchange_time = datetime.now()
    
    return success_count > 0

# ============ HTTP请求兑换模块 ============
def http_exchange_gift():
    """通过HTTP请求兑换礼品（兼容原有代码）"""
    # 检查连发开关状态
    if not settings.get("burst_enabled", False):
        # 如果连发功能关闭，只执行1次兑换
        return http_exchange_gift_burst(burst_count=1, burst_interval=0)
    else:
        # 如果连发功能开启，使用配置的连发参数
        burst_count = settings.get("burst_count", 10)
        burst_interval = settings.get("burst_interval", 1)
        return http_exchange_gift_burst(burst_count=burst_count, burst_interval=burst_interval)

# ============ 自动签到模块 ============
def auto_signin():
    """自动签到功能"""
    global driver, last_signin_time
    
    print_with_time("开始执行自动签到...")
    
    # 检查是否已登录
    if not login_status or driver is None:
        print_with_time("未登录，正在尝试登录...")
        if not browser_login_and_get_cookie(close_after_login=False):
            print_with_time("登录失败，无法签到")
            return False
    
    try:
        # 访问积分中心页面
        driver.get(POINTS_CENTER_URL)
        time.sleep(3)
        
        # 提取并显示当前积分
        try:
            points_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'badge') and contains(@class, 'points-badge')]")
            for element in points_elements:
                points_text = element.text
                if "当前积分" in points_text or "分" in points_text:
                    print_with_time(f"当前积分: {points_text}")
                    break
        except Exception as e:
            print_with_time(f"提取积分信息失败: {e}")
        
        take_screenshot("积分中心页面", "auto")
        
        # 简化签到逻辑：直接查找按钮并点击
        signin_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), '签到') or contains(text(), '立即签到') or contains(@onclick, 'sign')]")
        clicked = False
        
        for btn in signin_buttons:
            if btn.is_displayed() and btn.is_enabled():
                btn.click()
                print_with_time("已点击签到按钮")
                clicked = True
                time.sleep(3)
                
                # 再次提取并显示当前积分
                try:
                    points_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'badge') and contains(@class, 'points-badge')]")
                    for element in points_elements:
                        points_text = element.text
                        if "当前积分" in points_text or "分" in points_text:
                            print_with_time(f"点击签到后积分: {points_text}")
                            break
                except Exception as e:
                    print_with_time(f"提取签到后积分信息失败: {e}")
                
                take_screenshot("点击签到后", "auto")
                break
        
        if not clicked:
            print_with_time("未找到可点击的签到按钮，可能今日已签到。")
        
        # 简单的结果判断
        page_text = driver.page_source
        if "签到成功" in page_text or "成功" in driver.title or "已签到" in page_text:
            last_signin_time = datetime.now()
            print_with_time("签到成功")
        else:
            print_with_time("签到完成")
        
        # 签到完成后关闭浏览器
        if settings.get("close_browser_after_login", False) and driver is not None:
            close_browser()
            
        return True
            
    except Exception as e:
        print_with_time(f"签到过程中发生异常: {e}")
        # 异常情况下也尝试关闭浏览器
        if settings.get("close_browser_after_login", False) and driver is not None:
            try:
                close_browser()
            except:
                pass
        return False

# ============ 完整流程 ============
def full_auto_process():
    """完整自动化流程: 登录 -> 兑换"""
    print_with_time("开始执行完整自动化流程")
    
    # 步骤1: 登录获取Cookie
    if browser_login_and_get_cookie():
        time.sleep(2)
        # 步骤2: HTTP请求兑换
        if http_exchange_gift():
            print_with_time("完整流程执行成功")
            return True
        else:
            print_with_time("兑换失败")
            return False
    else:
        print_with_time("登录失败")
        return False

def auto_login_only():
    """仅自动登录"""
    print_with_time("执行自动登录")
    return browser_login_and_get_cookie()

def auto_exchange_only():
    """仅自动兑换"""
    print_with_time("执行自动兑换")
    
    # 检查Cookie
    if not current_cookie:
        print_with_time("未找到Cookie，尝试从文件加载...")
        if not load_cookie():
            print_with_time("文件中也无有效Cookie，请先登录")
            return False
    
    return http_exchange_gift()

# ============ 定时任务 ============
def scheduled_login():
    """定时登录任务"""
    if settings.get("auto_task_enabled", True) and settings.get("auto_login_enabled", True):
        print_with_time("定时任务: 执行登录")
        auto_login_only()

def scheduled_exchange():
    """定时兑换任务"""
    if settings.get("auto_task_enabled", True) and settings.get("auto_exchange_enabled", True):
        # 从配置获取时间
        exchange_time_str = settings.get("exchange_time", "12:00")
        # 确保格式为 HH:MM:SS
        if exchange_time_str.count(':') == 1:
            exchange_time_str = exchange_time_str + ":00"
        
        # 解析时间
        time_parts = exchange_time_str.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2]) if len(time_parts) > 2 else 0
        
        now = datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        
        # 计算到目标时间的等待时间
        if now < target_time:
            sleep_seconds = (target_time - now).total_seconds()
            if sleep_seconds > 0.1:  # 如果还差0.1秒以上
                sleep_seconds -= 0.05  # 提前0.05秒开始
                print_with_time(f"兑换任务等待 {sleep_seconds:.3f} 秒以达到 {exchange_time_str} ...")
                time.sleep(sleep_seconds)
            
            # 微调等待
            while datetime.now() < target_time:
                time.sleep(0.001)  # 1毫秒精度
                
        elif now > target_time:
            print_with_time(f"已过 {exchange_time_str}，立即执行兑换。")
        
        print_with_time(f"定时任务: 执行兑换 ({exchange_time_str}) 当前时间: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        # 根据连发设置执行兑换
        if settings.get("burst_enabled", False):
            burst_count = settings.get("burst_count", 10)
            burst_interval = settings.get("burst_interval", 1)
            print_with_time(f"连发模式: 将执行 {burst_count} 次兑换，间隔 {burst_interval} 秒")
            http_exchange_gift_burst(burst_count=burst_count, burst_interval=burst_interval)
        else:
            http_exchange_gift()

def scheduled_signin():
    """定时签到任务"""
    if settings.get("auto_task_enabled", True) and settings.get("auto_signin_enabled", True):
        print_with_time("定时任务: 执行自动签到")
        auto_signin()

def start_scheduler():
    """启动定时任务调度"""
    global config, settings
    
    # 重新加载配置
    reload_config()
    
    # 清除所有现有任务
    schedule.clear()
    
    if settings.get("auto_task_enabled", True):
        # 登录时间
        if settings.get("auto_login_enabled", True):
            login_time = settings.get("login_time", "11:00")
            # 确保时间格式正确
            if login_time.count(':') == 1:
                login_time = login_time + ":00"
            schedule.every().day.at(login_time).do(scheduled_login)
        
        # 兑换时间
        if settings.get("auto_exchange_enabled", True):
            exchange_time = settings.get("exchange_time", "12:00")
            if exchange_time.count(':') == 1:
                exchange_time = exchange_time + ":00"
            schedule.every().day.at(exchange_time).do(scheduled_exchange)
        
        # 签到时间
        if settings.get("auto_signin_enabled", True):
            signin_time = settings.get("signin_time", "11:30")
            if signin_time.count(':') == 1:
                signin_time = signin_time + ":00"
            schedule.every().day.at(signin_time).do(scheduled_signin)
        
        print_with_time("定时任务已启动")
        if settings.get("auto_login_enabled", True):
            print_with_time(f"  - 登录时间: {login_time}")
        if settings.get("auto_exchange_enabled", True):
            print_with_time(f"  - 兑换时间: {exchange_time}")
        if settings.get("auto_signin_enabled", True):
            print_with_time(f"  - 签到时间: {signin_time}")
    else:
        print_with_time("定时任务已禁用")
    
    print_with_time("定时任务将在后台运行")
    
    while is_running:
        schedule.run_pending()
        time.sleep(0.1)  # 提高定时精度，改为0.1秒

# ============ 礼品管理模块 ============
def cmd_select_gifts():
    """选择礼品功能"""
    global config
    
    print_with_time("选择要兑换的礼品")
    print_with_time("="*60)
    
    # 礼品映射表
    gifts = config["gifts"]["gift_list"]
    selected_gifts = [str(gid) for gid in config["gifts"]["selected_gifts"]]
    
    while True:
        print_with_time("\n可选礼品:")
        print_with_time("服务器区\t\t规格\t\tID\t名称")
        print_with_time("-"*60)
        
        # 按服务器区分类显示
        server_groups = {}
        for gift_id, gift_info in gifts.items():
            server = gift_info["server"]
            if server not in server_groups:
                server_groups[server] = []
            server_groups[server].append((gift_id, gift_info))
        
        # 显示每个服务器区的礼品
        for server, server_gifts in server_groups.items():
            print_with_time(f"{server}:")
            for gift_id, gift_info in server_gifts:
                selected_mark = "✓" if gift_id in selected_gifts else " "
                print_with_time(f"  [{selected_mark}] {gift_info['spec']:8} ID:{gift_id:2} - {gift_info['name']} (消耗积分: {gift_info['points']})")
            print_with_time("")
        
        print_with_time(f"当前已选择 {len(selected_gifts)} 个礼品:")
        for gift_id in selected_gifts:
            if gift_id in gifts:
                print_with_time(f"  - {gifts[gift_id]['name']} (ID: {gift_id})")
        
        print_with_time("\n操作:")
        print_with_time("1. 选择/取消选择礼品")
        print_with_time("2. 全选")
        print_with_time("3. 清空选择")
        print_with_time("4. 保存并返回")
        print_with_time("0. 取消并返回")
        
        choice = input("\n请选择操作 (0-4): ").strip()
        
        if choice == "0":
            print_with_time("取消修改")
            break
        elif choice == "4":
            config["gifts"]["selected_gifts"] = [int(gid) for gid in selected_gifts if gid in gifts]
            if save_config(config):
                print_with_time("礼品选择已保存")
            break
        elif choice == "1":
            gift_id = input("请输入要选择/取消选择的礼品ID (多个用逗号分隔): ").strip()
            gift_ids = [gid.strip() for gid in gift_id.split(',') if gid.strip()]
            
            for gid in gift_ids:
                if gid in gifts:
                    if gid in selected_gifts:
                        selected_gifts.remove(gid)
                        print_with_time(f"已取消选择: {gifts[gid]['name']}")
                    else:
                        selected_gifts.append(gid)
                        print_with_time(f"已选择: {gifts[gid]['name']}")
                else:
                    print_with_time(f"无效的礼品ID: {gid}")
        elif choice == "2":
            selected_gifts.clear()
            selected_gifts.extend(gifts.keys())
            print_with_time(f"已全选 {len(selected_gifts)} 个礼品")
        elif choice == "3":
            selected_gifts.clear()
            print_with_time("已清空所有选择")

# ============ 兑换记录查看功能 ============
def cmd_get_exchange_history():
    """获取兑换记录命令 - 已修改为从HTML解析积分"""
    print_with_time("获取兑换记录")
    print_with_time("="*60)
    
    if not login_status or driver is None:
        print_with_time("未登录，正在尝试登录...")
        if not browser_login_and_get_cookie(close_after_login=False):
            print_with_time("登录失败，无法获取记录")
            return False
    
    try:
        # 直接访问兑换记录页面
        driver.get("https://www.yunmc.vip/addons?_plugin=points_mall&_controller=index&_action=record")
        time.sleep(2)  # 减少等待时间
        
        take_screenshot("兑换记录页面", "auto")
        
        # 获取当前页面源代码
        page_source = driver.page_source
        current_url = driver.current_url
        print_with_time(f"当前页面URL: {current_url}")
        
        if not page_source:
            print_with_time("页面源代码为空")
            return False
        
        # 使用正则表达式解析表格数据
        exchange_records = []
        
        # 查找<tr>标签内的所有<td>内容
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', page_source, re.DOTALL | re.IGNORECASE)
        
        for row in rows:
            # 提取行中的所有<td>单元格
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
            
            if len(cells) >= 6:  # 至少有6列数据
                record = {}
                
                # 解析各个单元格
                for i, cell in enumerate(cells):
                    # 清理HTML标签，但保留文本内容
                    clean_cell = re.sub(r'<[^>]+>', ' ', cell)
                    clean_cell = re.sub(r'\s+', ' ', clean_cell).strip()
                    
                    if not clean_cell:
                        continue
                    
                    # 第1列: 优惠码
                    if i == 0:
                        # 查找优惠码
                        code_match = re.search(r'优惠码[：:]?\s*([A-Za-z0-9]{8,20})', cell)
                        if code_match:
                            record['coupon_code'] = code_match.group(1)
                        else:
                            # 备用方法：直接查找字母数字组合
                            code_match = re.search(r'([A-Za-z0-9]{8,20})', clean_cell)
                            if code_match:
                                record['coupon_code'] = code_match.group(1)
                    
                    # 第2列: 奖品类型
                    elif i == 1:
                        # 提取奖品类型文本
                        prize_text = re.sub(r'<[^>]+>', '', cell)
                        prize_text = re.sub(r'\s+', ' ', prize_text).strip()
                        if prize_text:
                            record['gift_type'] = prize_text
                    
                    # 第3列: 消耗积分
                    elif i == 2:
                        # 从HTML中直接解析积分数值
                        points_match = re.search(r'>\s*(\d+)\s*<', cell)
                        if points_match:
                            try:
                                record['points'] = int(points_match.group(1))
                            except ValueError:
                                record['points'] = None
                        else:
                            # 备用方法：从文本中提取数字
                            points_match = re.search(r'(\d+)', clean_cell)
                            if points_match:
                                try:
                                    record['points'] = int(points_match.group(1))
                                except ValueError:
                                    record['points'] = None
                    
                    # 第4列: 兑换日期
                    elif i == 3:
                        # 查找日期时间
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', clean_cell)
                        if date_match:
                            record['exchange_date'] = date_match.group(1)
                    
                    # 第5列: 发放状态
                    elif i == 4:
                        if '已发放' in cell:
                            record['status'] = '已发放'
                        elif '未发放' in cell:
                            record['status'] = '未发放'
                        elif '发放中' in cell:
                            record['status'] = '发放中'
                        elif 'status-success' in cell:
                            record['status'] = '已发放'
                        elif 'status-warning' in cell:
                            record['status'] = '未发放'
                        elif 'status-processing' in cell:
                            record['status'] = '发放中'
                
                # 如果记录包含优惠码，则添加到列表
                if 'coupon_code' in record:
                    # 设置默认值
                    if 'points' not in record:
                        record['points'] = None
                    exchange_records.append(record)
        
        if not exchange_records:
            # 尝试通过XPath直接查找表格
            print_with_time("通过正则解析失败，尝试XPath解析...")
            try:
                # 查找所有表格行
                rows = driver.find_elements(By.XPATH, "//table//tr[td]")
                
                for row in rows:
                    try:
                        # 获取所有单元格
                        cells = row.find_elements(By.XPATH, ".//td")
                        
                        if len(cells) >= 6:  # 应该有6列
                            record = {}
                            
                            # 解析每一列
                            for i, cell in enumerate(cells):
                                cell_text = cell.text.strip()
                                cell_html = cell.get_attribute('innerHTML')
                                
                                if not cell_text and not cell_html:
                                    continue
                                
                                # 第1列: 优惠码
                                if i == 0:
                                    code_match = re.search(r'优惠码[：:]?\s*([A-Za-z0-9]{8,20})', cell_html or '')
                                    if code_match:
                                        record['coupon_code'] = code_match.group(1)
                                    else:
                                        # 从文本中提取
                                        code_match = re.search(r'([A-Za-z0-9]{8,20})', cell_text)
                                        if code_match:
                                            record['coupon_code'] = code_match.group(1)
                                
                                # 第2列: 奖品类型
                                elif i == 1:
                                    if cell_text:
                                        record['gift_type'] = cell_text
                                
                                # 第3列: 消耗积分
                                elif i == 2:
                                    # 从HTML中查找积分数值
                                    points_match = re.search(r'>\s*(\d+)\s*<', cell_html or '')
                                    if points_match:
                                        try:
                                            record['points'] = int(points_match.group(1))
                                        except ValueError:
                                            record['points'] = None
                                    else:
                                        # 从文本中提取数字
                                        points_match = re.search(r'(\d+)', cell_text)
                                        if points_match:
                                            try:
                                                record['points'] = int(points_match.group(1))
                                            except ValueError:
                                                record['points'] = None
                                
                                # 第4列: 兑换日期
                                elif i == 3:
                                    date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', cell_text)
                                    if date_match:
                                        record['exchange_date'] = date_match.group(1)
                                    elif cell_text:
                                        record['exchange_date'] = cell_text
                                
                                # 第5列: 发放状态
                                elif i == 4:
                                    if '已发放' in cell_text or 'status-success' in (cell_html or ''):
                                        record['status'] = '已发放'
                                    elif '未发放' in cell_text or 'status-warning' in (cell_html or ''):
                                        record['status'] = '未发放'
                                    elif '发放中' in cell_text or 'status-processing' in (cell_html or ''):
                                        record['status'] = '发放中'
                                    elif cell_text:
                                        record['status'] = cell_text
                            
                            # 如果有优惠码，添加到记录
                            if 'coupon_code' in record:
                                # 如果没有找到积分，设置为None
                                if 'points' not in record:
                                    record['points'] = None
                                exchange_records.append(record)
                    except Exception as e:
                        print_with_time(f"解析行时出错: {e}")
                        continue
            except Exception as e:
                print_with_time(f"XPath解析失败: {e}")
        
        if exchange_records:
            print_with_time(f"找到 {len(exchange_records)} 条兑换记录:")
            print_with_time("="*100)
            print_with_time(f"{'序号':<4} {'优惠码':<15} {'奖品类型':<25} {'消耗积分':<8} {'兑换日期':<20} {'状态':<8}")
            print_with_time("-"*100)
            
            for i, record in enumerate(exchange_records, 1):
                # 获取记录中的各个字段，提供默认值
                coupon_code = record.get('coupon_code', '未知')
                gift_type = record.get('gift_type', '未知')
                points = record.get('points', '未知')
                exchange_date = record.get('exchange_date', '未知')
                status = record.get('status', '未知')
                
                # 截断过长的字符串
                if len(gift_type) > 20:
                    gift_type = gift_type[:17] + "..."
                if len(exchange_date) > 20:
                    exchange_date = exchange_date[:17] + "..."
                
                print_with_time(f"{i:<4} {coupon_code:<15} {gift_type:<25} {points:<8} {exchange_date:<20} {status:<8}")
            
            print_with_time("="*100)
            print_with_time(f"总计: {len(exchange_records)} 条记录")
            
            # 计算总消耗积分（只计算数字类型的积分）
            total_points = 0
            points_count = 0
            for r in exchange_records:
                points = r.get('points', 0)
                if isinstance(points, int):
                    total_points += points
                    points_count += 1
            print_with_time(f"总消耗积分: {total_points} (基于 {points_count} 条有积分记录)")
            
            # 显示统计信息
            status_counts = {}
            for record in exchange_records:
                status = record.get('status', '未知')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if status_counts:
                print_with_time("状态统计:")
                for status, count in status_counts.items():
                    print_with_time(f"  {status}: {count} 条")
        else:
            print_with_time("未找到兑换记录")
        
        # 获取兑换记录后关闭浏览器
        if settings.get("close_browser_after_login", False) and driver is not None:
            close_browser()
        
        return True
        
    except Exception as e:
        print_with_time(f"获取兑换记录失败: {e}")
        
        # 异常情况下也尝试关闭浏览器
        if settings.get("close_browser_after_login", False) and driver is not None:
            try:
                close_browser()
            except:
                pass
        return False

# ============ 命令函数 ============
def cmd_status():
    """显示状态"""
    print("\n" + "="*60)
    print("当前状态")
    print("="*60)
    
    if not USERNAME or not PASSWORD:
        print_with_time("账号密码: 未配置 (使用config命令配置)")
    else:
        print_with_time(f"账号: {USERNAME[:3]}*****{USERNAME[-3:] if len(USERNAME) > 6 else '***'}")
        print_with_time("密码: ********")
    
    print(f"登录状态: {'已登录' if login_status else '未登录'}")
    
    if last_login_time:
        print(f"最后登录: {last_login_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if last_exchange_time:
        print(f"最后兑换: {last_exchange_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if last_signin_time:
        print(f"最后签到: {last_signin_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"Cookie状态: {'已加载' if current_cookie else '未加载'}")
    if current_cookie:
        cookie_preview = current_cookie[:80] + "..." if len(current_cookie) > 80 else current_cookie
        print(f"Cookie预览: {cookie_preview}")
    
    print(f"浏览器状态: {'已初始化' if driver else '未初始化'}")
    if driver:
        try:
            url = driver.current_url[:80] if len(driver.current_url) > 80 else driver.current_url
            print(f"当前页面: {url}")
        except:
            print("当前页面: 浏览器可能已失效")
    
    print(f"定时任务: {'运行中' if scheduler_thread and scheduler_thread.is_alive() else '未运行'}")
    print(f"自动任务总开关: {'开启' if settings.get('auto_task_enabled', True) else '关闭'}")
    print(f"自动登录开关: {'开启' if settings.get('auto_login_enabled', True) else '关闭'}")
    print(f"自动兑换开关: {'开启' if settings.get('auto_exchange_enabled', True) else '关闭'}")
    print(f"自动签到开关: {'开启' if settings.get('auto_signin_enabled', True) else '关闭'}")
    print(f"浏览器当前模式: {browser_mode if browser_mode else '未设置'}")
    print(f"浏览器默认模式: {settings.get('browser_default_mode', 'headless')}")
    print(f"登录后关闭浏览器: {'是' if settings.get('close_browser_after_login', False) else '否'}")
    print(f"截屏总开关: {'开启' if settings.get('screenshot_enabled', False) else '关闭'}")
    print(f"自动截屏开关: {'开启' if settings.get('screenshot_auto_enabled', False) else '关闭'}")
    print(f"手动截屏开关: {'开启' if settings.get('screenshot_manual_enabled', False) else '关闭'}")
    print(f"连发功能开关: {'开启' if settings.get('burst_enabled', False) else '关闭'}")
    print(f"连发次数: {settings.get('burst_count', 10)}")
    print(f"连发间隔(秒): {settings.get('burst_interval', 1)}")
    
    # 显示已选择的礼品
    selected_gifts = config["gifts"]["selected_gifts"]
    gifts_info = config["gifts"]["gift_list"]
    print(f"已选择礼品: {len(selected_gifts)} 个")
    for gift_id in selected_gifts:
        gift_str = str(gift_id)
        if gift_str in gifts_info:
            print(f"  - {gifts_info[gift_str]['name']} (ID: {gift_id})")
    
    print("="*60)

def cmd_config():
    """配置账号密码"""
    global config
    
    print_with_time("配置账号密码")
    print_with_time("="*60)
    
    print_with_time(f"当前账号: {config['account']['username']}")
    print_with_time(f"当前密码: {'*' * len(config['account']['password']) if config['account']['password'] else ''}")
    
    print_with_time("\n输入新配置 (直接按Enter保持原值):")
    
    new_username = input("新账号: ").strip()
    new_password = input("新密码: ").strip()
    
    if new_username:
        config['account']['username'] = new_username
    if new_password:
        config['account']['password'] = new_password
    
    # 保存配置
    if save_config(config):
        # 重新加载配置以更新全局变量
        reload_config()
        
        print_with_time("账号密码配置已保存")
        print_with_time(f"配置文件: {os.path.abspath(CONFIG_FILE)}")
    else:
        print_with_time("保存配置失败")

def cmd_settings():
    """设置功能"""
    global config, settings, browser_mode
    
    print_with_time("系统设置")
    print_with_time("="*60)
    
    while True:
        print_with_time("\n当前设置:")
        print_with_time(f"1. 自动任务总开关: {'开启' if settings.get('auto_task_enabled', True) else '关闭'}")
        print_with_time(f"2. 自动登录开关: {'开启' if settings.get('auto_login_enabled', True) else '关闭'}")
        print_with_time(f"3. 自动兑换开关: {'开启' if settings.get('auto_exchange_enabled', True) else '关闭'}")
        print_with_time(f"4. 自动签到开关: {'开启' if settings.get('auto_signin_enabled', True) else '关闭'}")
        print_with_time(f"5. 登录时间: {settings.get('login_time', '11:00')}")
        print_with_time(f"6. 兑换时间: {settings.get('exchange_time', '12:00')}")
        print_with_time(f"7. 签到时间: {settings.get('signin_time', '11:30')}")
        print_with_time(f"8. 登录完成是否退出浏览器: {'是' if settings.get('close_browser_after_login', False) else '否'}")
        print_with_time(f"9. 浏览器当前显示模式: {browser_mode if browser_mode else settings.get('browser_default_mode', 'headless')}")
        print_with_time(f"10. 浏览器默认显示模式: {settings.get('browser_default_mode', 'headless')}")
        print_with_time(f"11. 截屏总开关: {'开启' if settings.get('screenshot_enabled', False) else '关闭'}")
        print_with_time(f"12. 自动截屏开关: {'开启' if settings.get('screenshot_auto_enabled', False) else '关闭'}")
        print_with_time(f"13. 手动截屏开关: {'开启' if settings.get('screenshot_manual_enabled', False) else '关闭'}")
        print_with_time(f"14. 连发功能开关: {'开启' if settings.get('burst_enabled', False) else '关闭'}")
        print_with_time(f"15. 连发次数: {settings.get('burst_count', 10)}")
        print_with_time(f"16. 连发间隔(秒): {settings.get('burst_interval', 1)}")
        print_with_time(f"17. 礼品选择设置")
        print_with_time("18. 保存并返回")
        print_with_time("0. 取消并返回")
        
        choice = input("\n请选择要修改的项 (0-18): ").strip()
        
        if choice == "0":
            print_with_time("取消修改")
            break
        elif choice == "18":
            if save_config(config):
                print_with_time("设置已保存")
                # 重启定时任务
                global scheduler_thread
                if scheduler_thread and scheduler_thread.is_alive():
                    print_with_time("重启定时任务...")
                    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
                    scheduler_thread.start()
            break
        elif choice == "1":
            current = settings.get("auto_task_enabled", True)
            settings["auto_task_enabled"] = not current
            print_with_time(f"自动任务总开关已切换为: {'开启' if settings['auto_task_enabled'] else '关闭'}")
        elif choice == "2":
            current = settings.get("auto_login_enabled", True)
            settings["auto_login_enabled"] = not current
            print_with_time(f"自动登录开关已切换为: {'开启' if settings['auto_login_enabled'] else '关闭'}")
        elif choice == "3":
            current = settings.get("auto_exchange_enabled", True)
            settings["auto_exchange_enabled"] = not current
            print_with_time(f"自动兑换开关已切换为: {'开启' if settings['auto_exchange_enabled'] else '关闭'}")
        elif choice == "4":
            current = settings.get("auto_signin_enabled", True)
            settings["auto_signin_enabled"] = not current
            print_with_time(f"自动签到开关已切换为: {'开启' if settings['auto_signin_enabled'] else '关闭'}")
        elif choice == "5":
            new_time = input(f"请输入登录时间 (格式: HH:MM 或 HH:MM:SS) (当前: {settings.get('login_time', '11:00')}): ").strip()
            if new_time and re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', new_time):
                # 如果用户输入的是 HH:MM 格式，自动补上秒
                if new_time.count(':') == 1:
                    new_time = new_time + ":00"
                settings["login_time"] = new_time
                print_with_time(f"登录时间已设置为: {new_time}")
            elif new_time:
                print_with_time("时间格式错误，请使用 HH:MM 或 HH:MM:SS 格式")
        elif choice == "6":
            new_time = input(f"请输入兑换时间 (格式: HH:MM 或 HH:MM:SS) (当前: {settings.get('exchange_time', '12:00')}): ").strip()
            if new_time and re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', new_time):
                if new_time.count(':') == 1:
                    new_time = new_time + ":00"
                settings["exchange_time"] = new_time
                print_with_time(f"兑换时间已设置为: {new_time}")
            elif new_time:
                print_with_time("时间格式错误，请使用 HH:MM 或 HH:MM:SS 格式")
        elif choice == "7":
            new_time = input(f"请输入签到时间 (格式: HH:MM 或 HH:MM:SS) (当前: {settings.get('signin_time', '11:30')}): ").strip()
            if new_time and re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', new_time):
                if new_time.count(':') == 1:
                    new_time = new_time + ":00"
                settings["signin_time"] = new_time
                print_with_time(f"签到时间已设置为: {new_time}")
            elif new_time:
                print_with_time("时间格式错误，请使用 HH:MM 或 HH:MM:SS 格式")
        elif choice == "8":
            current = settings.get("close_browser_after_login", False)
            settings["close_browser_after_login"] = not current
            print_with_time(f"登录后关闭浏览器已切换为: {'是' if settings['close_browser_after_login'] else '否'}")
        elif choice == "9":
            print_with_time("浏览器当前显示模式 (临时切换，仅本次运行有效):")
            print_with_time("1. 无头模式 (headless)")
            print_with_time("2. 图形界面模式 (gui) - 需要桌面环境")
            mode_choice = input("请选择浏览器当前模式 (1-2): ").strip()
            if mode_choice == "1":
                browser_mode = "headless"
                print_with_time("浏览器当前模式已设置为: 无头模式")
                # 关闭当前浏览器，下次打开时使用新模式
                close_browser()
            elif mode_choice == "2":
                browser_mode = "gui"
                print_with_time("浏览器当前模式已设置为: 图形界面模式")
                # 关闭当前浏览器，下次打开时使用新模式
                close_browser()
        elif choice == "10":
            print_with_time("浏览器默认显示模式 (程序重新打开时使用的模式):")
            print_with_time("1. 无头模式 (headless)")
            print_with_time("2. 图形界面模式 (gui)")
            default_choice = input("请选择浏览器默认模式 (1-2): ").strip()
            if default_choice == "1":
                settings["browser_default_mode"] = "headless"
                # 更新当前模式
                browser_mode = "headless"
                # 无头模式默认关闭所有截图
                settings["screenshot_enabled"] = False
                settings["screenshot_auto_enabled"] = False
                settings["screenshot_manual_enabled"] = False
                print_with_time("浏览器默认模式已设置为: 无头模式")
                print_with_time("截图总开关、自动截图和手动截图已关闭")
                # 关闭当前浏览器，下次打开时使用新模式
                close_browser()
            elif default_choice == "2":
                settings["browser_default_mode"] = "gui"
                # 更新当前模式
                browser_mode = "gui"
                # GUI模式默认开启总开关，但自动和手动截图保持用户设置
                settings["screenshot_enabled"] = True
                print_with_time("浏览器默认模式已设置为: 图形界面模式")
                print_with_time("截图总开关已开启")
                # 关闭当前浏览器，下次打开时使用新模式
                close_browser()
        elif choice == "11":
            current = settings.get("screenshot_enabled", False)
            settings["screenshot_enabled"] = not current
            print_with_time(f"截屏总开关已切换为: {'开启' if settings['screenshot_enabled'] else '关闭'}")
        elif choice == "12":
            current = settings.get("screenshot_auto_enabled", False)
            settings["screenshot_auto_enabled"] = not current
            print_with_time(f"自动截屏开关已切换为: {'开启' if settings['screenshot_auto_enabled'] else '关闭'}")
        elif choice == "13":
            current = settings.get("screenshot_manual_enabled", False)
            settings["screenshot_manual_enabled"] = not current
            print_with_time(f"手动截屏开关已切换为: {'开启' if settings['screenshot_manual_enabled'] else '关闭'}")
        elif choice == "14":
            current = settings.get("burst_enabled", False)
            settings["burst_enabled"] = not current
            print_with_time(f"连发功能开关已切换为: {'开启' if settings['burst_enabled'] else '关闭'}")
        elif choice == "15":
            try:
                new_count = int(input(f"请输入连发次数 (当前: {settings.get('burst_count', 10)}): ").strip())
                if 1 <= new_count <= 100:
                    settings["burst_count"] = new_count
                    print_with_time(f"连发次数已设置为: {new_count}")
                else:
                    print_with_time("连发次数必须在1-100之间")
            except ValueError:
                print_with_time("请输入有效的数字")
        elif choice == "16":
            try:
                new_interval = float(input(f"请输入连发间隔(秒) (当前: {settings.get('burst_interval', 1)}): ").strip())
                if 0.1 <= new_interval <= 10:
                    settings["burst_interval"] = new_interval
                    print_with_time(f"连发间隔已设置为: {new_interval}秒")
                else:
                    print_with_time("连发间隔必须在0.1-10秒之间")
            except ValueError:
                print_with_time("请输入有效的数字")
        elif choice == "17":
            cmd_select_gifts()

def cmd_auto_signin():
    """自动签到命令"""
    print_with_time("执行自动签到流程")
    
    # 先检查是否需要登录
    if not login_status or driver is None:
        print_with_time("未登录，正在尝试登录...")
        if not browser_login_and_get_cookie(close_after_login=False):
            print_with_time("登录失败，无法签到")
            return False
    
    return auto_signin()

def cmd_parse_cookie():
    """解析cookie命令"""
    print_with_time("解析Cookie信息")
    print_with_time("="*60)
    
    if not current_cookie:
        print_with_time("当前无Cookie，尝试从文件加载...")
        if not load_cookie():
            print_with_time("文件中也无有效Cookie")
            return
    
    if not current_cookie:
        print_with_time("无Cookie可解析")
        return
    
    print_with_time("Cookie原始内容:")
    print_with_time(f"  {current_cookie}")
    print_with_time("")
    
    # 解析Cookie
    cookies = {}
    cookie_parts = current_cookie.strip(';').split('; ')
    
    for part in cookie_parts:
        if '=' in part:
            key, value = part.split('=', 1)
            cookies[key] = value
    
    print_with_time("解析结果:")
    for i, (key, value) in enumerate(cookies.items()):
        print_with_time(f"  {i+1:2d}. {key}: {value[:20]}{'...' if len(value) > 20 else ''}")
        
        # 检查是否是JWT令牌
        if len(value.split('.')) == 3:
            print_with_time(f"      类型: JWT令牌")
            try:
                # 解码JWT
                jwt_parts = value.split('.')
                if len(jwt_parts) == 3:
                    # 解码头部
                    header_encoded = jwt_parts[0]
                    # 添加可能的填充字符
                    while len(header_encoded) % 4 != 0:
                        header_encoded += '='
                    header_json = base64.b64decode(header_encoded).decode('utf-8')
                    header_data = json.loads(header_json)
                    
                    # 解码载荷
                    payload_encoded = jwt_parts[1]
                    # 添加可能的填充字符
                    while len(payload_encoded) % 4 != 0:
                        payload_encoded += '='
                    payload_json = base64.b64decode(payload_encoded).decode('utf-8')
                    payload_data = json.loads(payload_json)
                    
                    print_with_time(f"      JWT头: {json.dumps(header_data, ensure_ascii=False, indent=8)}")
                    print_with_time(f"      JWT载荷: {json.dumps(payload_data, ensure_ascii=False, indent=8)}")
                    
                    # 解析时间信息
                    if 'iat' in payload_data:
                        iat_time = datetime.fromtimestamp(payload_data['iat'])
                        print_with_time(f"      签发时间: {iat_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if 'nbf' in payload_data:
                        nbf_time = datetime.fromtimestamp(payload_data['nbf'])
                        print_with_time(f"      生效时间: {nbf_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    if 'exp' in payload_data:
                        exp_time = datetime.fromtimestamp(payload_data['exp'])
                        print_with_time(f"      过期时间: {exp_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # 计算剩余有效期
                        now = datetime.now()
                        if exp_time > now:
                            remaining = exp_time - now
                            print_with_time(f"      剩余有效期: {remaining.days}天 {remaining.seconds//3600}小时{(remaining.seconds%3600)//60}分钟")
                        else:
                            print_with_time(f"      状态: 已过期")
                    
            except Exception as e:
                print_with_time(f"      解码JWT失败: {e}")
    
    # 特别解析重要Cookie
    important_cookies = ['session', 'token', 'auth', 'user', 'id']
    print_with_time("")
    print_with_time("重要Cookie字段:")
    
    for cookie_name in important_cookies:
        for key, value in cookies.items():
            if cookie_name.lower() in key.lower():
                print_with_time(f"  {key}: {value[:20]}{'...' if len(value) > 20 else ''}")
                break
    
    print_with_time(f"")
    print_with_time(f"Cookie总长度: {len(current_cookie)} 字符")
    print_with_time(f"Cookie字段数: {len(cookies)} 个")
    print_with_time("="*60)

def cmd_browser():
    """浏览器管理命令"""
    print_with_time("浏览器管理")
    print_with_time("1. 关闭浏览器")
    print_with_time("2. 重新初始化浏览器")
    print_with_time("3. 获取当前页面URL")
    print_with_time("4. 刷新当前页面")
    
    choice = input("请选择 (1-4, 其他取消): ").strip()
    
    if choice == "1":
        close_browser()
    elif choice == "2":
        close_browser()
        time.sleep(1)
        if init_browser():
            print_with_time("浏览器重新初始化成功")
        else:
            print_with_time("浏览器初始化失败")
    elif choice == "3":
        if driver:
            print_with_time(f"当前URL: {driver.current_url}")
            print_with_time(f"页面标题: {driver.title}")
        else:
            print_with_time("浏览器未初始化")
    elif choice == "4":
        if driver:
            driver.refresh()
            time.sleep(2)
            print_with_time("页面已刷新")
        else:
            print_with_time("浏览器未初始化")

def cmd_screenshot(description=""):
    """手动截图命令"""
    if not driver:
        print_with_time("浏览器未初始化，请先登录或初始化浏览器")
        return
    
    print_with_time(f"正在截图: {description if description else '当前页面'}")
    if take_screenshot(description, "manual"):
        print_with_time("截图成功")
    else:
        print_with_time("截图失败")

def cmd_log():
    """查看日志"""
    if os.path.exists(LOG_FILE):
        print_with_time(f"日志文件: {os.path.abspath(LOG_FILE)}")
        print_with_time(f"文件大小: {os.path.getsize(LOG_FILE)} 字节")
        
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    print_with_time("\n最近10条日志:")
                    for line in lines[-10:]:
                        print(line.strip())
                else:
                    print_with_time("日志文件为空")
        except Exception as e:
            print_with_time(f"读取日志文件失败: {e}")
    else:
        print_with_time("日志文件不存在")

def cmd_help():
    """显示帮助"""
    help_text = """
可用命令:
  start    - 完整流程 (登录+兑换)
  start1   - 仅登录
  start2   - 仅兑换
  dk       - 自动签到
  status   - 显示当前状态
  config   - 配置账号密码
  zs       - 系统设置
  gift     - 选择礼品
  jx       - 解析Cookie信息
  jp       - 截图浏览器当前页面
  browser  - 浏览器管理
  lp       - 查看兑换记录
  log      - 查看日志
  exit     - 退出程序
  help     - 显示此帮助

设置功能 (zs命令):
  1. 自动任务总开关
  2. 自动登录开关
  3. 自动兑换开关
  4. 自动签到开关
  5. 登录/兑换/签到时间调整 (支持秒，格式HH:MM:SS)
  6. 登录后是否关闭浏览器
  7. 浏览器当前显示模式
  8. 浏览器默认显示模式
  9. 截屏总开关
  10. 自动截屏开关
  11. 手动截屏开关
  12. 连发功能开关
  13. 连发次数
  14. 连发间隔(秒)
  15. 礼品选择设置

连发功能:
  - 开启后会在指定时间点连续发送多个请求
  - 可设置连发次数和间隔时间
  - 支持多礼品多线程并发

定时任务 (后台运行):
  可自定义时间，支持秒级精度，默认:
  - 11:00:00: 自动登录
  - 11:30:00: 自动签到
  - 12:00:00: 自动兑换
    """
    print(help_text)

# ============ 主程序 ============
def main():
    global is_running, scheduler_thread, config, settings, browser_mode
    
    print("\n" + "="*60)
    print("海绵科创综合脚本 v3.2")
    print("="*60)
    print("欢迎使用")
    print("="*60)
    
    # 检查是否是首次运行（配置文件不存在或账号密码未配置）
    is_first_run = False
    if not os.path.exists(CONFIG_FILE):
        is_first_run = True
        print_with_time("检测到首次运行，启动配置向导...")
        config = first_run_wizard()
    else:
        # 加载现有配置
        reload_config()
        if not config["account"]["username"] or not config["account"]["password"]:
            is_first_run = True
            print_with_time("检测到账号密码未配置，启动配置向导...")
            config = first_run_wizard()
            reload_config()
    
    # 初始化浏览器模式
    browser_mode = settings.get("browser_default_mode", "headless")
    print_with_time(f"使用浏览器默认模式: {browser_mode}")
    
    # 根据浏览器默认模式同步截图设置
    if browser_mode == "headless":
        # 无头模式默认关闭所有截图
        settings["screenshot_enabled"] = False
        settings["screenshot_auto_enabled"] = False
        settings["screenshot_manual_enabled"] = False
    else:
        # GUI模式默认开启总开关
        settings["screenshot_enabled"] = True
    
    # 保存配置以确保截图设置同步
    save_config(config)
    
    # 尝试加载已保存的Cookie
    load_cookie()
    
    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()
    
    print_with_time("程序已启动，定时任务在后台运行")
    print_with_time("输入 'help' 查看可用命令")
    print("="*60)
    
    # 命令行交互循环
    while is_running:
        try:
            cmd = input("\n>>> ").strip()
            
            if not cmd:
                continue
                
            cmd_lower = cmd.lower()
            
            if cmd_lower == "start":
                full_auto_process()
            elif cmd_lower == "start1":
                auto_login_only()
            elif cmd_lower == "start2":
                auto_exchange_only()
            elif cmd_lower == "dk":
                cmd_auto_signin()
            elif cmd_lower == "status":
                cmd_status()
            elif cmd_lower == "config":
                cmd_config()
            elif cmd_lower == "zs":
                cmd_settings()
            elif cmd_lower == "gift":
                cmd_select_gifts()
            elif cmd_lower == "jx":
                cmd_parse_cookie()
            elif cmd_lower == "browser":
                cmd_browser()
            elif cmd_lower == "lp":
                cmd_get_exchange_history()
            elif cmd_lower == "log":
                cmd_log()
            elif cmd_lower == "exit":
                print_with_time("正在退出程序...")
                is_running = False
                break
            elif cmd_lower == "help":
                cmd_help()
            elif cmd_lower.startswith("jp "):
                description = cmd[3:].strip()
                cmd_screenshot(description)
            elif cmd_lower == "jp":
                cmd_screenshot("")
            else:
                print_with_time(f"未知命令: {cmd}")
                print_with_time("输入 'help' 查看可用命令")
                
        except KeyboardInterrupt:
            print_with_time("\n收到Ctrl+C中断信号，正在退出程序...")
            is_running = False
            break
        except EOFError:
            print_with_time("\n收到EOF信号，正在退出程序...")
            is_running = False
            break
        except Exception as e:
            print_with_time(f"命令执行错误: {e}")
    
    # 清理资源
    close_browser()
    print_with_time("程序已退出")

if __name__ == "__main__":
    main()
