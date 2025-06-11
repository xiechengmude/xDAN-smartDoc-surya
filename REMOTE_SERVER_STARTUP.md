# 远程服务器启动指南

## 🚀 登录并启动 xDAN Smart API

### 1. 登录远程服务器
```bash
# SSH登录到远程服务器
ssh username@159.54.182.15

# 或者如果有特定的SSH密钥
ssh -i /path/to/your/key username@159.54.182.15
```

### 2. 进入项目目录
```bash
# 进入项目目录
cd /path/to/xDAN-smartDoc-surya

# 或者如果项目在用户主目录
cd ~/xDAN-smartDoc-surya
```

### 3. 激活Python环境
```bash
# 如果使用conda环境
conda activate your_env_name

# 或者如果使用venv
source venv/bin/activate

# 或者如果使用pipenv
pipenv shell
```

### 4. 更新代码到最新版本
```bash
# 拉取最新代码
git pull origin dev

# 检查当前分支和提交
git log --oneline -3
```

### 5. 启动API服务

#### 方式一：直接启动 (前台运行)
```bash
# 基本启动 (默认端口8000)
python pdf_to_markdown_api.py

# 指定端口启动
python pdf_to_markdown_api.py --port 8000

# 指定主机和端口
python pdf_to_markdown_api.py --host 0.0.0.0 --port 8000

# 自定义并发数
python pdf_to_markdown_api.py --host 0.0.0.0 --port 8000 --max-concurrent 15
```

#### 方式二：后台启动 (推荐)
```bash
# 使用nohup后台启动
nohup python pdf_to_markdown_api.py --host 0.0.0.0 --port 8000 > api.log 2>&1 &

# 查看进程ID
echo $!

# 查看日志
tail -f api.log
```

#### 方式三：使用screen (推荐)
```bash
# 创建新的screen会话
screen -S xdan-api

# 在screen中启动API
python pdf_to_markdown_api.py --host 0.0.0.0 --port 8000

# 按 Ctrl+A 然后按 D 来分离screen会话

# 重新连接到screen会话
screen -r xdan-api

# 查看所有screen会话
screen -ls
```

#### 方式四：使用systemd服务 (生产环境推荐)
```bash
# 创建服务文件
sudo nano /etc/systemd/system/xdan-api.service
```

服务文件内容：
```ini
[Unit]
Description=xDAN Smart API Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/xDAN-smartDoc-surya
Environment=PATH=/path/to/your/python/env/bin
ExecStart=/path/to/your/python/env/bin/python pdf_to_markdown_api.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动systemd服务：
```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start xdan-api

# 设置开机自启
sudo systemctl enable xdan-api

# 查看服务状态
sudo systemctl status xdan-api

# 查看服务日志
sudo journalctl -u xdan-api -f
```

### 6. 验证服务启动

#### 检查进程
```bash
# 查看Python进程
ps aux | grep pdf_to_markdown_api

# 查看端口占用
netstat -tlnp | grep 8000
# 或者
ss -tlnp | grep 8000
```

#### 测试API连接
```bash
# 测试基本连接
curl -I http://localhost:8000/docs

# 测试API密钥 (使用启动时显示的密钥)
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/performance
```

### 7. 启动时的输出信息
正常启动时您应该看到类似输出：
```
🚀 GPU 优化模式已启用 - 设备: cuda
📊 批处理大小: RECOGNITION=512, DETECTOR=36, LAYOUT=32, TABLE_REC=64
⚡ 模型编译已启用
🌐 启动服务: http://0.0.0.0:8000
🚀 正在启动 xDAN Smart API...
🔧 设备类型: cuda
⚙️  最大并发任务数: 10
📦 正在加载 Surya 模型...
✅ 模型加载完成
🔑 默认 API 密钥已生成: xxxxxxxxxxxxx
🎉 xDAN Smart API 启动完成！
```

### 8. 常用管理命令

#### 停止服务
```bash
# 如果是前台运行，按 Ctrl+C

# 如果是后台运行，找到进程ID并杀死
ps aux | grep pdf_to_markdown_api
kill PID_NUMBER

# 或者杀死所有相关进程
pkill -f pdf_to_markdown_api

# 如果使用systemd
sudo systemctl stop xdan-api
```

#### 重启服务
```bash
# 先停止再启动
pkill -f pdf_to_markdown_api
nohup python pdf_to_markdown_api.py --host 0.0.0.0 --port 8000 > api.log 2>&1 &

# 如果使用systemd
sudo systemctl restart xdan-api
```

#### 查看日志
```bash
# 如果使用nohup
tail -f api.log

# 如果使用systemd
sudo journalctl -u xdan-api -f

# 查看最近的错误
sudo journalctl -u xdan-api --since "1 hour ago"
```

### 9. 防火墙配置 (如果需要)
```bash
# 开放8000端口 (Ubuntu/Debian)
sudo ufw allow 8000

# 开放8000端口 (CentOS/RHEL)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 10. 性能监控
```bash
# 监控GPU使用情况 (如果有GPU)
nvidia-smi -l 1

# 监控CPU和内存
htop

# 监控API性能
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/performance
```

## 🔧 故障排查

### 常见问题
1. **端口被占用**: 使用 `netstat -tlnp | grep 8000` 检查
2. **权限问题**: 确保用户有执行权限
3. **Python环境**: 确保激活了正确的Python环境
4. **依赖缺失**: 运行 `pip install -r requirements.txt`
5. **GPU问题**: 检查CUDA和PyTorch安装

### 日志分析
- 查看启动日志确认优化配置是否正确加载
- 检查是否有CUDA/MPS相关错误
- 确认模型加载是否成功

## 📝 快速启动脚本

您也可以创建一个快速启动脚本：

```bash
# 创建启动脚本
nano start_api.sh
```

脚本内容：
```bash
#!/bin/bash
cd /path/to/xDAN-smartDoc-surya
source /path/to/your/env/bin/activate
git pull origin dev
nohup python pdf_to_markdown_api.py --host 0.0.0.0 --port 8000 > api.log 2>&1 &
echo "API started with PID: $!"
echo "View logs with: tail -f api.log"
```

使脚本可执行：
```bash
chmod +x start_api.sh
./start_api.sh
``` 