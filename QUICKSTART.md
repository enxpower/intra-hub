# INTRA-HUB v1.0 快速启动指南

## 5分钟快速部署

### 第一步：上传到服务器

```bash
# 在本地机器上
scp -r intra-hub-v1.0 user@your-server:~/

# SSH登录
ssh user@your-server
```

### 第二步：运行安装脚本

```bash
cd ~/intra-hub-v1.0
chmod +x setup.sh install_scheduler.sh check_installation.sh
sudo ./setup.sh
```

### 第三步：配置 Notion 凭证

```bash
sudo nano /opt/intra-hub/.env
```

修改这两行：
```
NOTION_TOKEN=你的_notion_integration_token
NOTION_DATABASE_ID=2fa95c292b0e80b0a5b0f6a3d20b64f1
```

保存并退出 (Ctrl+X, Y, Enter)

### 第四步：复制代码文件

```bash
sudo cp -r ~/intra-hub-v1.0/sync /opt/intra-hub/
sudo cp -r ~/intra-hub-v1.0/renderer /opt/intra-hub/
sudo cp ~/intra-hub-v1.0/requirements.txt /opt/intra-hub/
sudo cp ~/intra-hub-v1.0/install_scheduler.sh /opt/intra-hub/
```

### 第五步：安装 Python 依赖

```bash
cd /opt/intra-hub
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

### 第六步：配置 Nginx

```bash
sudo cp ~/intra-hub-v1.0/nginx.conf.example /etc/nginx/sites-available/intra-hub

# 根据需要编辑配置（修改 server_name 等）
sudo nano /etc/nginx/sites-available/intra-hub

# 启用站点
sudo ln -s /etc/nginx/sites-available/intra-hub /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

### 第七步：安装定时任务

```bash
cd /opt/intra-hub
sudo ./install_scheduler.sh
```

### 第八步：运行检查脚本

```bash
cd ~/intra-hub-v1.0
sudo bash check_installation.sh
```

确保所有检查项都通过（绿色 ✓）

### 第九步：首次同步

```bash
# 手动触发同步
sudo systemctl start intra-hub-sync.service

# 监控日志
sudo journalctl -u intra-hub-sync.service -f
```

### 第十步：访问站点

在浏览器中打开：
```
http://your-server-ip/
```

或

```
http://intra-hub.internal/
```

---

## 常用命令

```bash
# 手动触发同步
sudo systemctl start intra-hub-sync.service

# 查看实时日志
sudo journalctl -u intra-hub-sync.service -f

# 查看定时器状态
systemctl status intra-hub-sync.timer

# 查看下次运行时间
systemctl list-timers intra-hub-sync.timer

# 重启 Nginx
sudo systemctl restart nginx

# 检查安装
sudo bash ~/intra-hub-v1.0/check_installation.sh
```

---

## 故障排除速查

### 问题：同步报错 "NOTION_TOKEN not set"

```bash
sudo cat /opt/intra-hub/.env  # 检查配置
sudo nano /opt/intra-hub/.env  # 编辑配置
```

### 问题：权限错误

```bash
sudo chown -R www-data:www-data /opt/intra-hub/public/
sudo chown -R www-data:www-data /opt/intra-hub/data/
sudo chmod -R 755 /opt/intra-hub/
sudo chmod 600 /opt/intra-hub/.env
```

### 问题：Nginx 404

```bash
sudo nginx -t  # 测试配置
ls -la /opt/intra-hub/public/  # 检查文件
sudo systemctl restart nginx  # 重启服务
```

### 问题：Python 模块找不到

```bash
cd /opt/intra-hub
source venv/bin/activate
pip install -r requirements.txt
```

---

## 完成！

系统现在会每天凌晨 2:00 自动同步 Notion 文档。

在 Notion 中勾选 `PUBLISH` 复选框即可发布文档到内网。

---

**需要帮助？** 查看完整 README.md 文档。
