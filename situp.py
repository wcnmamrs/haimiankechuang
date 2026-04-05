#!/usr/bin/env python3
"""
海绵科创脚本 - 自动依赖安装器
版本: 1.0
功能: 自动检测环境、安装依赖、配置浏览器和驱动
"""

import os
import sys
import platform
import subprocess
import json
import time
import requests
import zipfile
import tarfile
import shutil
from pathlib import Path

class AutoInstaller:
    def __init__(self):
        self.system = platform.system()
        self.arch = platform.machine()
        self.is_termux = self._detect_termux()
        self.home_dir = str(Path.home())
        self.current_dir = os.getcwd()
        
    def _detect_termux(self):
        """检测是否是Termux环境"""
        if self.system == "Linux":
            # 检查ANDROID_ROOT环境变量
            if os.environ.get('ANDROID_ROOT') or os.environ.get('TERMUX_VERSION'):
                return True
            # 检查特定文件
            android_files = [
                '/system/build.prop',
                '/data/local/tmp',
                '/data/data/com.termux'
            ]
            for file_path in android_files:
                if os.path.exists(file_path):
                    return True
        return False
    
    def print_header(self):
        """打印标题"""
        print("\n" + "="*60)
        print("海绵科创脚本 - 自动依赖安装器")
        print("="*60)
        print(f"系统: {self.system}")
        print(f"架构: {self.arch}")
        print(f"Termux: {'是' if self.is_termux else '否'}")
        print(f"工作目录: {self.current_dir}")
        print("="*60)
    
    def check_python_dependencies(self):
        """检查Python依赖"""
        print("\n[1/6] 检查Python依赖...")
        
        required_packages = [
            'selenium',
            'schedule',
            'requests',
            'pytest'  # 可选，用于测试
        ]
        
        try:
            import selenium
            import schedule
            import requests
            print("✓ 所有Python依赖已安装")
            return True
        except ImportError as e:
            print(f"✗ 缺少依赖: {e}")
            return False
    
    def install_python_dependencies(self):
        """安装Python依赖"""
        print("\n[2/6] 安装Python依赖...")
        
        if self.is_termux:
            # Termux环境
            print("检测到Termux环境，需要先设置镜像源...")
            subprocess.run(['termux-change-repo'], shell=False)
            print("正在安装Termux依赖...")
            
            # 安装必要的系统包
            termux_packages = [
                'python', 'clang', 'make', 'libjpeg-turbo', 'libpng',
                'freetype', 'libxml2', 'libxslt', 'libwebp', 'openssl'
            ]
            
            for pkg in termux_packages:
                print(f"安装 {pkg}...")
                result = subprocess.run(['pkg', 'install', '-y', pkg], 
                                       capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ {pkg} 安装成功")
                else:
                    print(f"  ✗ {pkg} 安装失败: {result.stderr}")
        
        # 安装Python包
        pip_packages = [
            'selenium',
            'schedule',
            'requests',
            'pytest'  # 可选
        ]
        
        for package in pip_packages:
            print(f"安装Python包: {package}...")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 
                                      '--upgrade', package])
                print(f"  ✓ {package} 安装成功")
            except subprocess.CalledProcessError as e:
                print(f"  ✗ {package} 安装失败: {e}")
                return False
        
        return True
    
    def install_chrome_linux(self):
        """在Linux上安装Chrome"""
        print("\n[3/6] 在Linux上安装Chrome...")
        
        # 检测发行版
        distro = self._detect_linux_distro()
        print(f"检测到Linux发行版: {distro}")
        
        chrome_installed = False
        
        if distro in ['ubuntu', 'debian', 'linuxmint']:
            # Debian系发行版
            print("安装Chrome for Debian/Ubuntu...")
            
            # 下载Chrome安装包
            chrome_url = "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
            if self.arch == "aarch64":
                chrome_url = "https://dl.google.com/linux/direct/google-chrome-stable_current_arm64.deb"
            
            deb_file = "/tmp/google-chrome-stable.deb"
            
            try:
                # 下载
                print(f"下载Chrome: {chrome_url}")
                response = requests.get(chrome_url, stream=True)
                with open(deb_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # 安装
                subprocess.run(['apt-get', 'update'], check=False)
                subprocess.run(['apt-get', 'install', '-f', deb_file], check=False)
                subprocess.run(['apt-get', 'install', '-y', 'libxss1', 'libappindicator1', 'libindicator7'], check=False)
                subprocess.run(['dpkg', '-i', deb_file], check=False)
                
                chrome_installed = True
            except Exception as e:
                print(f"Chrome安装失败: {e}")
                # 尝试安装Chromium
                chrome_installed = self._install_chromium_linux(distro)
        
        elif distro in ['centos', 'fedora', 'rhel']:
            # RedHat系发行版
            print("安装Chrome for CentOS/Fedora...")
            chrome_installed = self._install_chromium_linux(distro)
        
        elif distro == 'arch':
            # Arch Linux
            print("安装Chrome for Arch Linux...")
            chrome_installed = self._install_chromium_linux(distro)
        
        else:
            # 其他发行版，尝试安装Chromium
            print(f"不支持的发行版 {distro}，尝试安装Chromium...")
            chrome_installed = self._install_chromium_linux(distro)
        
        return chrome_installed
    
    def _install_chromium_linux(self, distro):
        """在Linux上安装Chromium"""
        print("安装Chromium...")
        
        try:
            if distro in ['ubuntu', 'debian', 'linuxmint']:
                subprocess.run(['apt-get', 'update'], check=False)
                subprocess.run(['apt-get', 'install', '-y', 'chromium-browser', 'chromium-driver'], check=True)
            elif distro in ['centos', 'fedora', 'rhel']:
                subprocess.run(['dnf', 'install', '-y', 'chromium', 'chromedriver'], check=True)
            elif distro == 'arch':
                subprocess.run(['pacman', '-S', '--noconfirm', 'chromium', 'chromedriver'], check=True)
            else:
                # 通用方法
                subprocess.run(['apt-get', 'install', '-y', 'chromium-browser'], check=False)
            
            print("✓ Chromium安装成功")
            return True
        except Exception as e:
            print(f"✗ Chromium安装失败: {e}")
            return False
    
    def _detect_linux_distro(self):
        """检测Linux发行版"""
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if 'ID=' in line:
                        return line.split('=')[1].strip().strip('"').lower()
        
        # 尝试其他方法
        if os.path.exists('/etc/debian_version'):
            return 'debian'
        elif os.path.exists('/etc/redhat-release'):
            return 'centos'
        elif os.path.exists('/etc/arch-release'):
            return 'arch'
        
        return 'unknown'
    
    def install_chrome_windows(self):
        """在Windows上安装Chrome"""
        print("\n[3/6] 在Windows上安装Chrome...")
        
        # 检查Chrome是否已安装
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe")
        ]
        
        for path in chrome_paths:
            if os.path.exists(path):
                print(f"✓ Chrome已安装: {path}")
                return True
        
        # 如果Chrome未安装，则尝试安装
        print("Chrome未安装，尝试下载安装...")
        
        try:
            chrome_url = "https://dl.google.com/chrome/install/latest/chrome_installer.exe"
            installer_path = os.path.join(os.environ.get('TEMP', ''), "chrome_installer.exe")
            
            # 下载Chrome安装程序
            print(f"下载Chrome安装程序...")
            response = requests.get(chrome_url, stream=True)
            with open(installer_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 静默安装Chrome
            print("正在安装Chrome（请稍等）...")
            subprocess.run([installer_path, '/silent', '/install'], shell=True, check=True)
            
            # 等待安装完成
            time.sleep(10)
            
            # 检查是否安装成功
            for path in chrome_paths:
                if os.path.exists(path):
                    print(f"✓ Chrome安装成功: {path}")
                    return True
            
            print("✗ Chrome安装失败")
            return False
            
        except Exception as e:
            print(f"✗ Chrome安装失败: {e}")
            return False
    
    def install_chrome_termux(self):
        """在Termux上安装Chrome/Chromium"""
        print("\n[3/6] 在Termux上安装浏览器...")
        
        # Termux不支持Chrome，我们尝试安装Chromium
        print("Termux环境，尝试安装Chromium和相关依赖...")
        
        try:
            # 安装基本依赖
            subprocess.run(['pkg', 'update', '-y'], check=False)
            subprocess.run(['pkg', 'upgrade', '-y'], check=False)
            
            # 安装必要的包
            packages = [
                'python', 'clang', 'make', 'binutils',
                'libjpeg-turbo', 'libpng', 'freetype',
                'libxml2', 'libxslt', 'libwebp',
                'openssl', 'zlib', 'termux-x11'
            ]
            
            for pkg in packages:
                print(f"安装 {pkg}...")
                subprocess.run(['pkg', 'install', '-y', pkg], check=False)
            
            print("注意: Termux环境下无法直接安装Chrome/Chromium")
            print("建议使用无头模式，但需要特殊配置")
            
            return False
            
        except Exception as e:
            print(f"✗ Termux依赖安装失败: {e}")
            return False
    
    def install_chromedriver(self):
        """安装ChromeDriver"""
        print("\n[4/6] 安装ChromeDriver...")
        
        # 检测Chrome版本
        chrome_version = self._get_chrome_version()
        if not chrome_version:
            print("无法检测Chrome版本，将使用最新版ChromeDriver")
            chrome_version = "latest"
        
        print(f"Chrome版本: {chrome_version}")
        
        # 确定系统架构
        if self.system == "Windows":
            os_name = "win32"
            driver_name = "chromedriver.exe"
        elif self.system == "Darwin":
            os_name = "mac64"
            driver_name = "chromedriver"
        elif self.arch == "aarch64":
            os_name = "linux64"
            driver_name = "chromedriver"
        else:
            os_name = "linux64"
            driver_name = "chromedriver"
        
        # 如果是Termux，尝试通过包管理器安装
        if self.is_termux:
            return self._install_chromedriver_termux()
        
        # 获取ChromeDriver版本
        if chrome_version == "latest":
            driver_version_url = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
        else:
            # 获取对应版本
            major_version = chrome_version.split('.')[0]
            driver_version_url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
        
        try:
            # 获取ChromeDriver版本
            response = requests.get(driver_version_url)
            driver_version = response.text.strip()
            print(f"ChromeDriver版本: {driver_version}")
            
            # 构建下载URL
            driver_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_{os_name}.zip"
            
            # 下载
            print(f"下载ChromeDriver: {driver_url}")
            temp_dir = "/tmp" if self.system != "Windows" else os.environ.get('TEMP', '')
            zip_path = os.path.join(temp_dir, "chromedriver.zip")
            
            response = requests.get(driver_url, stream=True)
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 解压
            extract_dir = temp_dir
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # 移动文件到合适位置
            driver_src = os.path.join(extract_dir, driver_name)
            driver_dst = os.path.join(self.current_dir, driver_name)
            
            shutil.copy(driver_src, driver_dst)
            
            # 设置执行权限（Linux/Mac）
            if self.system in ["Linux", "Darwin"]:
                os.chmod(driver_dst, 0o755)
            
            # 清理
            os.remove(zip_path)
            
            print(f"✓ ChromeDriver安装完成: {driver_dst}")
            return True
            
        except Exception as e:
            print(f"✗ ChromeDriver安装失败: {e}")
            print("尝试通过包管理器安装...")
            return self._install_chromedriver_package()
    
    def _get_chrome_version(self):
        """获取Chrome版本"""
        try:
            if self.system == "Windows":
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                ]
                
                for path in chrome_paths:
                    if os.path.exists(path):
                        result = subprocess.run([path, '--version'], 
                                              capture_output=True, text=True, shell=True)
                        if result.returncode == 0:
                            version = result.stdout.strip()
                            # 提取版本号
                            if 'Google Chrome' in version:
                                return version.split(' ')[2]
            
            elif self.system == "Linux":
                # 尝试chrome
                result = subprocess.run(['google-chrome', '--version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    if 'Google Chrome' in version:
                        return version.split(' ')[2]
                
                # 尝试chromium
                result = subprocess.run(['chromium-browser', '--version'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip().split(' ')[1]
            
            elif self.system == "Darwin":
                result = subprocess.run(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', 
                                       '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    if 'Google Chrome' in version:
                        return version.split(' ')[2]
        
        except Exception as e:
            print(f"获取Chrome版本时出错: {e}")
        
        return None
    
    def _install_chromedriver_package(self):
        """通过包管理器安装ChromeDriver"""
        try:
            if self.system == "Linux":
                distro = self._detect_linux_distro()
                
                if distro in ['ubuntu', 'debian', 'linuxmint']:
                    subprocess.run(['apt-get', 'update'], check=False)
                    subprocess.run(['apt-get', 'install', '-y', 'chromium-chromedriver'], check=True)
                elif distro in ['centos', 'fedora', 'rhel']:
                    subprocess.run(['yum', 'install', '-y', 'chromedriver'], check=True)
                elif distro == 'arch':
                    subprocess.run(['pacman', '-S', '--noconfirm', 'chromedriver'], check=True)
                
                print("✓ ChromeDriver通过包管理器安装成功")
                return True
            
            elif self.system == "Windows":
                # Windows上没有包管理器，返回False
                return False
        
        except Exception as e:
            print(f"✗ 通过包管理器安装ChromeDriver失败: {e}")
            return False
    
    def _install_chromedriver_termux(self):
        """在Termux上安装ChromeDriver"""
        print("在Termux上安装ChromeDriver...")
        
        try:
            # 尝试通过pkg安装
            subprocess.run(['pkg', 'install', '-y', 'chromedriver'], check=False)
            print("✓ ChromeDriver安装完成（可能需要手动配置）")
            return True
        except Exception as e:
            print(f"✗ ChromeDriver安装失败: {e}")
            return False
    
    def create_config(self):
        """创建配置文件"""
        print("\n[5/6] 创建配置文件...")
        
        config_template = {
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
                "close_browser_after_login": True,
                "browser_default_mode": "headless",
                "screenshot_enabled": False,
                "screenshot_auto_enabled": False,
                "screenshot_manual_enabled": False,
                "burst_enabled": False,
                "burst_count": 10,
                "burst_interval": 1
            },
            "gifts": {
                "selected_gifts": [20],
                "gift_list": {
                    "20": {"name": "2H4G服务器(Minecraft)", "server": "我的世界区", "spec": "2h4g", "points": 1200},
                    "19": {"name": "4H8G服务器(Minecraft)", "server": "我的世界区", "spec": "4h8g", "points": 2400},
                    "18": {"name": "8H16G服务器(Minecraft)", "server": "我的世界区", "spec": "8h16g", "points": 4800},
                    "17": {"name": "4H8G服务器(Palworld)", "server": "Palworld区", "spec": "4h8g", "points": 2400},
                    "16": {"name": "6H12G服务器(Palworld)", "server": "Palworld区", "spec": "6h12g", "points": 3600},
                    "15": {"name": "8H16G服务器(Palworld)", "server": "Palworld区", "spec": "8h16g", "points": 4800}
                }
            }
        }
        
        config_path = os.path.join(self.current_dir, "config.json")
        
        if not os.path.exists(config_path):
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_template, f, indent=2, ensure_ascii=False)
            print(f"✓ 配置文件已创建: {config_path}")
        else:
            print(f"✓ 配置文件已存在: {config_path}")
        
        return True
    
    def test_installation(self):
        """测试安装"""
        print("\n[6/6] 测试安装...")
        
        tests_passed = 0
        total_tests = 2
        
        # 测试1: Python依赖
        print("测试1: 检查Python依赖...")
        try:
            import selenium
            import schedule
            import requests
            print("  ✓ Python依赖测试通过")
            tests_passed += 1
        except ImportError as e:
            print(f"  ✗ Python依赖测试失败: {e}")
        
        # 测试2: ChromeDriver
        print("测试2: 检查ChromeDriver...")
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            # 尝试启动Chrome
            driver = webdriver.Chrome(options=chrome_options)
            driver.quit()
            print("  ✓ ChromeDriver测试通过")
            tests_passed += 1
        except Exception as e:
            print(f"  ✗ ChromeDriver测试失败: {e}")
            print(f"  错误详情: {str(e)[:200]}")
        
        print(f"\n测试结果: {tests_passed}/{total_tests} 通过")
        
        if tests_passed >= 1:
            print("✓ 安装测试基本通过")
            return True
        else:
            print("✗ 安装测试失败")
            return False
    
    def start_main_script(self):
        """启动主脚本"""
        print("\n" + "="*60)
        print("启动主脚本...")
        print("="*60)
        
        main_script = "main.py"
        
        if not os.path.exists(main_script):
            print(f"✗ 找不到主脚本: {main_script}")
            print("请确保主脚本 'main.py' 在当前目录中")
            return False
        
        try:
            # 启动主脚本
            subprocess.run([sys.executable, main_script])
            return True
        except Exception as e:
            print(f"✗ 启动主脚本失败: {e}")
            return False
    
    def run(self):
        """运行安装器"""
        self.print_header()
        
        # 检查是否需要sudo权限
        if self.system == "Linux" and not self.is_termux and os.geteuid() != 0:
            print("\n警告: 需要管理员权限安装系统包")
            print("请使用: sudo python setup.py")
            response = input("是否继续尝试非管理员安装? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
        
        # 安装步骤
        steps = [
            ("检查Python依赖", self.check_python_dependencies),
            ("安装Python依赖", self.install_python_dependencies),
            ("安装Chrome浏览器", self.install_chrome_based_on_os),
            ("安装ChromeDriver", self.install_chromedriver),
            ("创建配置文件", self.create_config),
            ("测试安装", self.test_installation)
        ]
        
        for step_name, step_func in steps:
            print(f"\n正在执行: {step_name}")
            if not step_func():
                print(f"步骤失败: {step_name}")
                response = input("是否继续? (y/n): ")
                if response.lower() != 'y':
                    break
        
        # 启动主脚本
        self.start_main_script()
    
    def install_chrome_based_on_os(self):
        """根据操作系统安装Chrome"""
        if self.is_termux:
            return self.install_chrome_termux()
        elif self.system == "Windows":
            return self.install_chrome_windows()
        elif self.system == "Linux":
            return self.install_chrome_linux()
        elif self.system == "Darwin":
            print("macOS系统，请手动安装Chrome")
            print("访问: https://www.google.com/chrome/")
            return False
        else:
            print(f"不支持的操作系统: {self.system}")
            return False

def main():
    """主函数"""
    try:
        installer = AutoInstaller()
        installer.run()
    except KeyboardInterrupt:
        print("\n\n安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n安装过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
