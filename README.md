# 海绵科创综合脚本

## 项目简介
这是一个自动兑换积分礼品的Python脚本，支持自动登录、定时兑换、多礼品选择、连发请求等功能。专门用于海绵科创

## 功能特性
- 自动登录获取Cookie
- 定时任务执行（登录、兑换、签到）
- 多礼品选择与兑换
- 连发请求功能
- 兑换记录查看
- Cookie解析
- 浏览器管理
- 截图功能
- 日志记录

## 安装要求

### 系统要求
- Python 3.8+
- Chrome浏览器
- ChromeDriver

### Windows系统特别标注
第208行脚本中指定了ChromeDriver的路径为 /usr/bin/chromedriver，在Windows上运行时，您需要将其修改为您的ChromeDriver在Windows上的实际路径（例如 C:\\path\\to\\chromedriver.exe）

### 系统依赖安装

#### 1. 基础系统更新

bash

sudo apt update

sudo apt upgrade -y


#### 2. 安装Python3和pip3

bash

sudo apt install python3 python3-pip python3-venv -y


#### 3. 安装Chrome浏览器

bash

安装必要的依赖

sudo apt install -y wget gnupg

下载并安装Chrome

wget -q -O - "https://dl-ssl.google.com/linux/linux_signing_key.pub" (https://dl-ssl.google.com/linux/linux_signing_key.pub) | sudo apt-key add -

sudo sh -c 'echo "deb [arch=amd64] "http://dl.google.com/linux/chrome/deb/" (http://dl.google.com/linux/chrome/deb/) stable main" >> /etc/apt/sources.list.d/google-chrome.list'

sudo apt update

sudo apt install -y google-chrome-stable

检查Chrome版本

google-chrome --version


#### 4. 安装ChromeDriver

bash

获取Chrome版本

CHROME_VERSION= (google-chrome --version | awk '{print  3}' | cut -d'.' -f1)

下载对应版本的ChromeDriver

CHROMEDRIVER_VERSION= (curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_ CHROME_VERSION")

wget -N "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" (https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip)

解压并安装

unzip -o chromedriver_linux64.zip

chmod +x chromedriver

sudo mv chromedriver /usr/bin/chromedriver

清理

rm chromedriver_linux64.zip

验证安装

chromedriver --version


#### 5. 安装X11相关依赖（用于图形界面模式）

bash

sudo apt install -y xvfb x11-apps


## Python依赖

### 依赖文件内容 (requirements.txt)

selenium==4.15.0

schedule==1.2.0

requests==2.31.0


### 安装Python依赖

bash

创建虚拟环境

python3 -m venv venv

source venv/bin/activate

安装依赖

pip install -r requirements.txt


## 使用方法

### 1. 首次运行

bash

python3 main.py


首次运行会生成配置文件模板，需要编辑`config.json`文件填写账号密码。

### 2. 常用命令

start     - 完整流程（登录+兑换）

start1    - 仅登录

start2    - 仅兑换

dk        - 自动签到

status    - 显示当前状态

config    - 配置账号密码

zs        - 系统设置

gift      - 选择礼品

jx        - 解析Cookie信息

jp        - 截图浏览器当前页面

browser   - 浏览器管理

lp        - 查看兑换记录

log       - 查看日志

help      - 显示帮助

exit      - 退出程序


### 3. 配置账号密码
运行脚本后，输入`config`命令配置账号密码，或直接编辑`config.json`文件。

### 4. 礼品选择
输入`gift`命令选择要兑换的礼品，支持多选。

## 定时任务
脚本启动后会自动在后台运行定时任务：
- 登录时间：11:00:00
- 签到时间：11:30:00
- 兑换时间：12:00:00

可通过`zs`命令调整时间设置。

## 文件结构

.

├── main.py              # 主程序

├── config.json          # 配置文件

├── yunmc_cookie.json    # Cookie存储

├── rz.txt              # 日志文件

├── screenshot_*.png    # 截图文件

├── requirements.txt    # Python依赖

└── README.md          # 说明文档


## 注意事项

### 1. 无头模式
默认使用无头模式运行，不显示浏览器界面。如需图形界面，可在设置中切换。

### 2. 时间设置
时间格式支持HH:MM或HH:MM:SS，支持秒级精度。

### 3. 连发功能
开启连发功能后，会在指定时间点连续发送多个请求，避免因网络延迟错过兑换。

### 4. 浏览器资源
默认启用"登录后关闭浏览器"选项，减少资源占用。可在设置中关闭。

### 5. 截图功能
默认关闭截图功能，需要时可在设置中开启。

## 故障排除

### 1. ChromeDriver版本问题
确保ChromeDriver版本与Chrome浏览器版本匹配。

### 2. 无头模式问题
如果无头模式无法正常工作，尝试安装Xvfb：

bash

sudo apt install xvfb

Xvfb :99 &

export DISPLAY=:99


### 3. 权限问题
确保ChromeDriver有执行权限：

bash

chmod +x /usr/bin/chromedriver