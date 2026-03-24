海绵科技综合脚本

一个自动化脚本，用于海绵科技网站的每日登录、自动签到与积分兑换。

"[图片] https://img.shields.io/badge/python-3.6+-blue.svg" (https://www.python.org/)

"[图片] https://img.shields.io/badge/License-MIT-yellow.svg" (LICENSE)

"[图片] https://img.shields.io/badge/code%20style-PEP8-brightgreen.svg" (https://www.python.org/dev/peps/pep-0008/)

 功能

-  全自动流程：自动登录、签到、兑换礼品，解放双手。
-  配置驱动：所有账号、定时任务、行为选项均通过外部JSON文件配置，与代码分离。
-  定时任务：内置任务调度器，可自定义每日执行登录、签到、兑换的时间。
-  双模式支持：支持
"headless"（无头）和
"gui"（图形界面）两种浏览器模式，适应服务器与个人电脑环境。
-  状态持久化：自动保存与加载Cookie，避免频繁登录。
-  操作可追溯：关键步骤自动截图，所有运行日志完整记录到文件。
-  交互式CLI：提供丰富的命令行命令，方便手动执行、调试和状态查看。

 前置依赖

运行本脚本需要准备以下环境：

1. 系统与浏览器依赖（必需）

这是Selenium自动化运行的基础。

- Google Chrome 或 Chromium 浏览器
- ChromeDriver（其版本必须与已安装的Chrome浏览器的主版本号匹配）

Linux安装示例：

# Ubuntu/Debian
sudo apt update
sudo apt install chromium-browser chromium-chromedriver

# CentOS/RHEL
sudo yum install epel-release
sudo yum install chromium chromium-driver

其他系统请访问 "ChromeDriver官网" (https://chromedriver.chromium.org/) 下载匹配的驱动，并确保
"chromedriver"命令可在终端中执行。

2. Python包依赖

脚本所需的Python第三方库如下（详见 
"requirements.txt"）：

selenium>=4.15.0
requests>=2.31.0
schedule>=1.2.0


 核心使用指南

程序运行后，在 
">>>" 提示符下输入命令：

命令 功能描述

"start" 执行完整流程（登录 → 兑换）

"start1" 仅执行登录（更新Cookie）

"start2" 仅使用现有Cookie兑换礼品

"dk" 执行自动签到任务

"status" 显示程序运行状态、Cookie、定时任务等信息

"config" 重新配置账号密码

"zs" 进入系统设置菜单，调整任务时间、浏览器模式等

"jp [描述]" 截取当前浏览器页面并保存

"browser" 管理浏览器（关闭、重新初始化等）

"log" 查看最近的运行日志

"help" 显示命令帮助

"exit" 安全退出程序

⚙️ 配置详解

所有配置均通过JSON文件管理，无需修改代码。

1. 账号配置 (
"yunmc_config.json")

{
  "username": "您的登录邮箱",
  "password": "您的登录密码"
}

2. 程序设置 (
"yunmc_settings.json")

{
  "auto_task_enabled": true,       // 总开关
  "login_time": "11:00",           // 自动登录时间
  "exchange_time": "12:00",        // 自动兑换时间
  "signin_time": "11:30",          // 自动签到时间
  "auto_signin_enabled": true,     // 签到任务开关
  "close_browser_after_login": false, // 登录后关闭浏览器以节省资源
  "browser_default_mode": "headless"  // 默认浏览器模式：`headless` 或 `gui`
}

修改设置后，在程序内使用 
"zs" 命令的“保存”选项或重启程序生效。

 高级与故障排除

浏览器模式

- 
"headless" (无头模式)：无图形界面，资源占用少，适用于服务器。推荐部署使用。
- 
"gui" (图形界面模式)：会打开浏览器窗口，便于直观调试和验证。适用于桌面环境。

文件说明

- 
"rz.txt": 完整的运行日志，包含时间戳和所有操作记录。
- 
"yunmc_cookie.json": 自动保存的网站会话Cookie，避免重复登录。
- 
"screenshot_*.png": 自动或手动截取的屏幕截图，用于问题排查。

常见问题

Q: 浏览器初始化失败，提示
"session not created"

A: 99%的原因是ChromeDriver版本与已安装的Chrome浏览器版本不匹配。请确保两者主版本号一致。

Q: 定时任务到了时间没有执行

A: 请检查：

1. 程序是否在后台持续运行（建议使用
"screen"或
"tmux"）。
2. 
"auto_task_enabled" 是否设置为 
"true"。
3. 系统时间和时区设置是否正确。

Q: 登录失败怎么办？

A: 建议：

1. 在
"zs"设置中临时切换为
"gui"模式，观察登录过程。
2. 检查
"rz.txt"日志和自动生成的
"screenshot_*.png"截图文件分析原因。
3. 手动执行
"start1"命令测试登录流程。
