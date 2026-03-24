#!/usr/bin/env python3
"""
海绵科创综合脚本
代码:deepseek模型制作
逆向:QQ3245987504
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
CONFIG_FILE = "yunmc_config.json"
SETTINGS_FILE = "yunmc_settings.json"
COOKIE_FILE = "yunmc_cookie.json"
LOG_FILE = "rz.txt"

# 默认配置
DEFAULT_CONFIG = {
    "username": "",
    "password": ""
}

# 默认设置 - 移除 browser_mode，只保留 browser_default_mode
DEFAULT_SETTINGS = {
    "auto_task_enabled": True,
    "login_time": "11:00",
    "exchange_time": "12:00",
    "signin_time": "11:30",
    "auto_signin_enabled": True,
    "close_browser_after_login": False,
    "browser_default_mode": "headless"  # 只保留默认模式
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

# ============ 配置加载函数 ============
def load_config():
    """从配置文件加载账号密码"""
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            print_with_time(f"加载配置文件失败: {e}")
    else:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print_with_time(f"已创建默认配置文件: {CONFIG_FILE}")
        print_with_time("请编辑此文件并填写您的账号密码")
    
    return config

def load_settings():
    """加载设置"""
    settings = DEFAULT_SETTINGS.copy()
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                user_settings = json.load(f)
                settings.update(user_settings)
        except Exception as e:
            print_with_time(f"加载设置文件失败: {e}")
    else:
        save_settings(settings)
    
    return settings

def save_settings(settings):
    """保存设置 - 不保存 browser_mode"""
    # 确保不保存 browser_mode
    if 'browser_mode' in settings:
        del settings['browser_mode']
    
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except Exception as e:
        print_with_time(f"保存设置失败: {e}")
        return False

# 初始化配置
config = load_config()
USERNAME = config["username"]
PASSWORD = config["password"]

# 加载设置
settings = load_settings()

# 检查账号密码是否已配置
if not USERNAME or not PASSWORD:
    print_with_time("警告: 账号或密码未配置，请编辑配置文件并填写")
    print_with_time(f"配置文件路径: {os.path.abspath(CONFIG_FILE)}")

# 网站URL
BASE_URL = "https://www.yunmc.vip"
LOGIN_URL = f"{BASE_URL}/login"
TARGET_URL = f"{BASE_URL}/addons?_plugin=points_mall&_controller=index&_action=change"
POINTS_MALL_URL = f"{BASE_URL}/addons?_plugin=points_mall&_controller=index&_action=exchange"
POINTS_CENTER_URL = f"{BASE_URL}/addons?_plugin=points_mall&_controller=index&_action=index"

# 全局变量
driver = None
is_running = True
scheduler_thread = None
current_cookie = ""
last_login_time = None
last_exchange_time = None
last_signin_time = None
login_status = False
browser_mode = None  # 当前浏览器模式（内存中）

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
            
            # 设置显示
            if "DISPLAY" not in os.environ:
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
        
        service = Service(executable_path="/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 关键修复：确保所有模式下都有足够大的窗口尺寸
        if browser_mode == "headless":
            # 无头模式下设置大尺寸窗口
            driver.set_window_size(1920, 1080)
            print_with_time(f"无头模式设置窗口尺寸: 1920x1080")
        else:
            # GUI模式下确保最大化
            driver.maximize_window()
            print_with_time("图形模式已最大化窗口")
            
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
        
        print_with_time(f"浏览器初始化成功 (模式: {browser_mode})")
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

def take_screenshot(description=""):
    """截取浏览器当前页面"""
    global driver
    
    if driver is None:
        print_with_time("浏览器未初始化，无法截图")
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
def browser_login_and_get_cookie():
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
        take_screenshot("登录前_页面加载完成")
        
        # 步骤2: 直接查找登录表单元素
        try:
            email_input = driver.find_element(By.CSS_SELECTOR, "input[name='email'], #emailInp")
            password_input = driver.find_element(By.CSS_SELECTOR, "input[name='password'], #emailPwdInp")
            submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except Exception as e:
            print_with_time(f"查找登录表单元素时出错: {e}")
            take_screenshot("登录失败_找不到表单元素")
            return False
        
        # 步骤3: 填写登录信息
        email_input.clear()
        email_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(PASSWORD)
        
        # 截图点2: 输入账号密码后
        take_screenshot("登录中_账号密码已填写")
        
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
            take_screenshot("登录成功")
            print_with_time("登录成功")
        else:
            # 截图点3: 登录失败
            take_screenshot("登录失败")
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
        if settings.get("close_browser_after_login", False):
            close_browser()
        
        return True
        
    except Exception as e:
        print_with_time(f"浏览器登录过程中发生异常: {e}")
        take_screenshot("登录异常")
        return False

# ============ HTTP请求兑换模块 ============
def http_exchange_gift():
    """通过HTTP请求兑换礼品"""
    global last_exchange_time
    
    if not current_cookie:
        print_with_time("错误: 没有可用的Cookie，请先登录")
        return False
    
    try:
        print_with_time("正在通过HTTP请求兑换礼品...")
        
        # 准备请求
        url = TARGET_URL
        data = "id=20"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': current_cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Origin': BASE_URL,
            'Referer': f'{BASE_URL}/',
        }
        
        # 发送请求
        start_time = time.time()
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response_time = (time.time() - start_time) * 1000
        
        # 解析响应
        result = {
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
            
            if 'code' in json_data:
                print_with_time(f"业务状态码: {json_data.get('code')}")
                print_with_time(f"消息: {json_data.get('msg')}")
                
                if json_data.get('code') == 200:
                    last_exchange_time = datetime.now()
                    print_with_time("兑换成功")
                    return True
                elif json_data.get('code') == 400:
                    print_with_time("礼品已兑完")
                    return True
                elif json_data.get('code') == 401 or '未登录' in str(json_data.get('msg', '')):
                    print_with_time("Cookie可能已过期，请重新登录")
                    return False
        except json.JSONDecodeError:
            if "<!doctype html>" in result['raw_response'].lower():
                print_with_time("错误: 服务器返回HTML页面而不是JSON响应")
                return False
        
        print_with_time("未知的兑换结果")
        return False
            
    except requests.exceptions.Timeout:
        print_with_time("请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print_with_time(f"网络请求失败: {e}")
        return False
    except Exception as e:
        print_with_time(f"兑换过程中发生异常: {e}")
        return False

# ============ 自动签到模块 ============
def auto_signin():
    """自动签到功能"""
    global driver, last_signin_time
    
    print_with_time("开始执行自动签到...")
    
    # 检查是否已登录
    if not login_status or driver is None:
        print_with_time("未登录，正在尝试登录...")
        if not browser_login_and_get_cookie():
            print_with_time("登录失败，无法签到")
            return False
    
    try:
        # 访问积分中心页面
        driver.get(POINTS_CENTER_URL)
        time.sleep(3)
        
        take_screenshot("积分中心页面")
        
        # 查找签到按钮
        signin_button = None
        signin_selectors = [
            "//button[contains(text(), '立即签到')]",
            "//button[contains(@onclick, 'sign()')]",
            "//button[contains(@class, 'btn-warning')]"
        ]
        
        for selector in signin_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        signin_button = element
                        print_with_time(f"找到签到按钮: {element.get_attribute('outerHTML')[:100]}")
                        break
                if signin_button:
                    break
            except:
                pass
        
        if not signin_button:
            print_with_time("未找到签到按钮，可能已签到过")
            
            # 检查是否已签到
            page_source = driver.page_source
            if "已签到" in page_source or "签到完成" in page_source:
                print_with_time("今日已签到")
                return True
            else:
                print_with_time("无法找到签到按钮")
                return False
        
        # 点击签到按钮
        signin_button.click()
        time.sleep(3)
        
        # 等待可能出现的提示框，并获取提示信息
        try:
            # 等待最多5秒，查找包含签到结果的元素
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '签到成功') or contains(text(), '已签到') or contains(text(), '签到失败')]"))
            )
        except TimeoutException:
            print_with_time("等待提示信息超时")
        
        # 再次截图
        take_screenshot("签到后页面")
        
        # 获取页面上的所有文本，寻找签到结果
        page_text = driver.page_source
        if "签到成功" in page_text:
            last_signin_time = datetime.now()
            print_with_time("签到成功")
            return True
        elif "已签到" in page_text or "今天已签到" in page_text:
            print_with_time("今日已签到")
            return True
        else:
            # 如果没有找到关键词，尝试查找其他提示元素
            try:
                alert_elements = driver.find_elements(By.CLASS_NAME, "alert")
                for alert in alert_elements:
                    print_with_time(f"发现提示框: {alert.text}")
                    if "成功" in alert.text:
                        last_signin_time = datetime.now()
                        print_with_time("签到成功")
                        return True
            except:
                pass
            
            print_with_time("打卡流程已完成，请检查积分数量是否增加")
            return False
            
    except Exception as e:
        print_with_time(f"签到过程中发生异常: {e}")
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
    if settings.get("auto_task_enabled", True):
        print_with_time("定时任务: 执行登录")
        auto_login_only()

def scheduled_exchange():
    """定时兑换任务"""
    if settings.get("auto_task_enabled", True):
        print_with_time("定时任务: 执行兑换")
        auto_exchange_only()

def scheduled_signin():
    """定时签到任务"""
    if settings.get("auto_task_enabled", True) and settings.get("auto_signin_enabled", True):
        print_with_time("定时任务: 执行自动签到")
        auto_signin()

def start_scheduler():
    """启动定时任务调度"""
    global settings
    
    # 重新加载设置
    settings = load_settings()
    
    # 清除所有现有任务
    schedule.clear()
    
    if settings.get("auto_task_enabled", True):
        # 登录时间
        login_time = settings.get("login_time", "11:00")
        schedule.every().day.at(login_time).do(scheduled_login)
        
        # 兑换时间
        exchange_time = settings.get("exchange_time", "12:00")
        schedule.every().day.at(exchange_time).do(scheduled_exchange)
        
        # 签到时间
        if settings.get("auto_signin_enabled", True):
            signin_time = settings.get("signin_time", "11:30")
            schedule.every().day.at(signin_time).do(scheduled_signin)
        
        print_with_time("定时任务已启动")
        print_with_time(f"  - 登录时间: {login_time}")
        print_with_time(f"  - 兑换时间: {exchange_time}")
        if settings.get("auto_signin_enabled", True):
            print_with_time(f"  - 签到时间: {signin_time}")
    else:
        print_with_time("定时任务已禁用")
    
    print_with_time("定时任务将在后台运行")
    
    while is_running:
        schedule.run_pending()
        time.sleep(1)

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
    print(f"自动任务开关: {'开启' if settings.get('auto_task_enabled', True) else '关闭'}")
    print(f"自动签到开关: {'开启' if settings.get('auto_signin_enabled', True) else '关闭'}")
    print(f"浏览器当前模式: {browser_mode if browser_mode else '未设置'}")
    print(f"浏览器默认模式: {settings.get('browser_default_mode', 'headless')}")
    print(f"登录后关闭浏览器: {'是' if settings.get('close_browser_after_login', False) else '否'}")
    print("="*60)

def cmd_config():
    """配置账号密码"""
    print_with_time("配置账号密码")
    print_with_time("="*60)
    
    # 加载当前配置
    current_config = load_config()
    
    print_with_time(f"当前账号: {current_config['username']}")
    print_with_time(f"当前密码: {'*' * len(current_config['password']) if current_config['password'] else ''}")
    
    print_with_time("\n输入新配置 (直接按Enter保持原值):")
    
    new_username = input("新账号: ").strip()
    new_password = input("新密码: ").strip()
    
    if new_username:
        current_config['username'] = new_username
    if new_password:
        current_config['password'] = new_password
    
    # 保存配置
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(current_config, f, indent=2)
        
        # 更新全局变量
        global USERNAME, PASSWORD
        USERNAME = current_config['username']
        PASSWORD = current_config['password']
        
        print_with_time("账号密码配置已保存")
        print_with_time(f"配置文件: {os.path.abspath(CONFIG_FILE)}")
    except Exception as e:
        print_with_time(f"保存配置失败: {e}")

def cmd_settings():
    """设置功能"""
    global settings, browser_mode
    
    print_with_time("系统设置")
    print_with_time("="*60)
    
    while True:
        print_with_time("\n当前设置:")
        print_with_time(f"1. 自动任务开关: {'开启' if settings.get('auto_task_enabled', True) else '关闭'}")
        print_with_time(f"2. 登录时间: {settings.get('login_time', '11:00')}")
        print_with_time(f"3. 兑换时间: {settings.get('exchange_time', '12:00')}")
        print_with_time(f"4. 签到时间: {settings.get('signin_time', '11:30')}")
        print_with_time(f"5. 自动签到开关: {'开启' if settings.get('auto_signin_enabled', True) else '关闭'}")
        print_with_time(f"6. 登录完成是否退出浏览器: {'是' if settings.get('close_browser_after_login', False) else '否'}")
        print_with_time(f"7. 浏览器当前显示模式: {browser_mode if browser_mode else settings.get('browser_default_mode', 'headless')}")
        print_with_time(f"8. 浏览器默认显示模式: {settings.get('browser_default_mode', 'headless')}")
        print_with_time("9. 保存并返回")
        print_with_time("0. 取消并返回")
        
        choice = input("\n请选择要修改的项 (0-9): ").strip()
        
        if choice == "0":
            print_with_time("取消修改")
            break
        elif choice == "9":
            if save_settings(settings):
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
            print_with_time(f"自动任务开关已切换为: {'开启' if settings['auto_task_enabled'] else '关闭'}")
        elif choice == "2":
            new_time = input(f"请输入登录时间 (当前: {settings.get('login_time', '11:00')}): ").strip()
            if new_time and re.match(r'^\d{1,2}:\d{2}$', new_time):
                settings["login_time"] = new_time
                print_with_time(f"登录时间已设置为: {new_time}")
        elif choice == "3":
            new_time = input(f"请输入兑换时间 (当前: {settings.get('exchange_time', '12:00')}): ").strip()
            if new_time and re.match(r'^\d{1,2}:\d{2}$', new_time):
                settings["exchange_time"] = new_time
                print_with_time(f"兑换时间已设置为: {new_time}")
        elif choice == "4":
            new_time = input(f"请输入签到时间 (当前: {settings.get('signin_time', '11:30')}): ").strip()
            if new_time and re.match(r'^\d{1,2}:\d{2}$', new_time):
                settings["signin_time"] = new_time
                print_with_time(f"签到时间已设置为: {new_time}")
        elif choice == "5":
            current = settings.get("auto_signin_enabled", True)
            settings["auto_signin_enabled"] = not current
            print_with_time(f"自动签到开关已切换为: {'开启' if settings['auto_signin_enabled'] else '关闭'}")
        elif choice == "6":
            current = settings.get("close_browser_after_login", False)
            settings["close_browser_after_login"] = not current
            print_with_time(f"登录后关闭浏览器已切换为: {'是' if settings['close_browser_after_login'] else '否'}")
        elif choice == "7":
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
        elif choice == "8":
            print_with_time("浏览器默认显示模式 (程序重新打开时使用的模式):")
            print_with_time("1. 无头模式 (headless)")
            print_with_time("2. 图形界面模式 (gui)")
            default_choice = input("请选择浏览器默认模式 (1-2): ").strip()
            if default_choice == "1":
                settings["browser_default_mode"] = "headless"
                # 更新当前模式
                browser_mode = "headless"
                print_with_time("浏览器默认模式已设置为: 无头模式")
                # 关闭当前浏览器，下次打开时使用新模式
                close_browser()
            elif default_choice == "2":
                settings["browser_default_mode"] = "gui"
                # 更新当前模式
                browser_mode = "gui"
                print_with_time("浏览器默认模式已设置为: 图形界面模式")
                # 关闭当前浏览器，下次打开时使用新模式
                close_browser()

def cmd_auto_signin():
    """自动签到命令"""
    print_with_time("执行自动签到流程")
    
    # 先检查是否需要登录
    if not login_status or driver is None:
        print_with_time("未登录，正在尝试登录...")
        if not browser_login_and_get_cookie():
            print_with_time("登录失败，无法签到")
            return False
    
    return auto_signin()

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
    if take_screenshot(description):
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
  jp       - 截图浏览器当前页面
  browser  - 浏览器管理
  log      - 查看日志
  exit     - 退出程序
  help     - 显示此帮助

设置功能 (zs命令):
  1. 自动任务开关
  2. 登录/兑换/签到时间调整
  3. 自动签到开关
  4. 登录后是否关闭浏览器
  5. 浏览器显示模式 (无头/图形界面)

定时任务 (后台运行):
  可自定义时间，默认:
  - 11:00: 自动登录
  - 11:30: 自动签到
  - 12:00: 自动兑换
    """
    print(help_text)

# ============ 主程序 ============
def main():
    global is_running, scheduler_thread, settings, browser_mode
    
    print("\n" + "="*60)
    print("海绵科创综合脚本")
    print("="*60)
    print("欢迎使用")
    print("="*60)
    
    # 初始化浏览器模式
    browser_mode = settings.get("browser_default_mode", "headless")
    print_with_time(f"使用浏览器默认模式: {browser_mode}")
    
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
            elif cmd_lower == "browser":
                cmd_browser()
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
            print_with_time("\n收到中断信号，输入 'exit' 退出程序")
        except Exception as e:
            print_with_time(f"命令执行错误: {e}")
    
    # 清理资源
    close_browser()
    print_with_time("程序已退出")

if __name__ == "__main__":
    # 清理旧的设置文件，移除browser_mode
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
            
            # 移除browser_mode字段
            if 'browser_mode' in data:
                del data['browser_mode']
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
                print_with_time("已清理设置文件中的browser_mode字段")
        except:
            pass
    
    main()
