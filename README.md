# INTRA-HUB v1.0

**Internal Documentation Publishing System**

自动将 Notion 文档发布到公司内网的系统。

---

## 系统概述

INTRA-HUB 从 Notion 数据库同步文档并自动发布到内网静态站点。

### 核心功能

- ✅ Notion 数据库自动同步
- ✅ 文档编号系统（DOC-XXXX）
- ✅ 双向同步（服务器 ↔ Notion）
- ✅ 高保真 HTML 渲染
- ✅ Code128 条形码生成
- ✅ 分页首页（每页10条）
- ✅ 搜索索引
- ✅ 浏览/下载/分享统计
- ✅ 每日自动同步
- ✅ 自动备份

---

## 系统要求

- Ubuntu 20.04+ (或其他 Linux 发行版)
- Python 3.8+
- Nginx
- 至少 2GB 磁盘空间
- VPN/内网访问

---

## 安装步骤

### 1. 准备 Notion 集成

1. 访问 https://www.notion.so/my-integrations
2. 创建新集成（Internal Integration）
3. 复制 Integration Token
4. 将集成添加到你的数据库页面

### 2. 确认 Notion 数据库结构

数据库必须包含以下字段：

**必需字段：**
- `TITLE` (title) - 文档标题
- `PUBLISH` (checkbox) - 发布开关
- `DOC_ID` (text/rich_text) - 文档编号（系统自动填写）

**可选字段（会显示在首页）：**
- `CATEGORY` (select) - 分类
- `TAGS` (multi-select) - 标签
- `AUTHOR` (text/people) - 作者
- `VERSION` (text) - 版本号

### 3. 上传代码到服务器

```bash
# 上传整个 intra-hub-v1.0 目录到服务器
scp -r intra-hub-v1.0 user@your-server:~/

# SSH 登录服务器
ssh user@your-server
```

### 4. 运行安装脚本

```bash
cd ~/intra-hub-v1.0
chmod +x setup.sh install_scheduler.sh
sudo ./setup.sh
```

### 5. 配置环境变量

```bash
sudo nano /opt/intra-hub/.env
```

填入你的 Notion 凭证：

```
NOTION_TOKEN=<YOUR_NOTION_TOKEN>
NOTION_DATABASE_ID=2fa95c292b0e80b0a5b0f6a3d20b64f1
```

### 6. 复制代码文件

```bash
sudo cp -r ~/intra-hub-v1.0/sync /opt/intra-hub/
sudo cp -r ~/intra-hub-v1.0/renderer /opt/intra-hub/
sudo cp ~/intra-hub-v1.0/requirements.txt /opt/intra-hub/
sudo cp ~/intra-hub-v1.0/install_scheduler.sh /opt/intra-hub/
```

### 7. 安装 Python 依赖

```bash
cd /opt/intra-hub
source venv/bin/activate
pip install -r requirements.txt
```

### 8. 配置 Nginx

```bash
sudo cp ~/intra-hub-v1.0/nginx.conf.example /etc/nginx/sites-available/intra-hub
sudo ln -s /etc/nginx/sites-available/intra-hub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9. 安装定时任务

```bash
cd /opt/intra-hub
sudo ./install_scheduler.sh
```

### 10. 首次手动同步测试

```bash
sudo systemctl start intra-hub-sync.service

# 查看日志
sudo journalctl -u intra-hub-sync.service -f
```

---

## 使用方法

### 发布文档

1. 在 Notion 中打开你的文档
2. 勾选 `PUBLISH` 复选框
3. 等待每日自动同步（凌晨2点）或手动触发同步
4. 文档会自动获得 DOC-XXXX 编号
5. 文档发布到内网首页

### 撤销文档

1. 在 Notion 中取消勾选 `PUBLISH`
2. 下次同步时文档会从内网移除

### 手动触发同步

```bash
sudo systemctl start intra-hub-sync.service
```

### 查看同步日志

```bash
# 实时日志
sudo journalctl -u intra-hub-sync.service -f

# 历史日志
sudo tail -f /opt/intra-hub/logs/sync.log
sudo tail -f /opt/intra-hub/logs/main.log
```

### 访问内网站点

在浏览器中访问：
```
http://intra-hub.internal
```

或者你的服务器 IP：
```
http://YOUR_SERVER_IP
```

---

## 目录结构

```
/opt/intra-hub/
├── sync/                 # Notion 同步模块
│   ├── notion_sync.py
│   └── main.py
├── renderer/             # HTML 渲染模块
│   ├── html_renderer.py
│   ├── block_renderer.py
│   └── barcode_generator.py
├── data/                 # 数据存储
│   ├── cache/           # 文档缓存（JSON）
│   │   ├── all_documents.json
│   │   ├── published_documents.json
│   │   └── DOC-XXXX.json
│   ├── metrics/         # 访问统计
│   │   └── metrics.json
│   ├── doc_counter.json # 文档计数器
│   └── doc_mapping.json # 页面ID映射
├── public/              # 公开网站目录
│   ├── index.html       # 首页
│   ├── page-2.html      # 分页
│   ├── search-index.json
│   ├── documents/       # 文档HTML
│   │   └── DOC-XXXX.html
│   └── static/          # 静态资源
│       └── barcodes/
├── logs/                # 日志文件
│   ├── sync.log
│   ├── main.log
│   └── scheduler.log
├── backups/             # 自动备份
│   └── intra-hub_fullbackup_YYYYMMDD-HHMMSS.tgz
├── venv/                # Python 虚拟环境
├── .env                 # 环境配置
└── requirements.txt     # Python 依赖
```

---

## 故障排除

### 问题：同步失败

```bash
# 检查环境变量
sudo cat /opt/intra-hub/.env

# 检查 Notion 连接
cd /opt/intra-hub
source venv/bin/activate
python -c "from notion_client import Client; print('OK')"

# 手动测试同步
sudo -u www-data /opt/intra-hub/venv/bin/python /opt/intra-hub/sync/main.py
```

### 问题：定时任务未运行

```bash
# 检查 timer 状态
sudo systemctl status intra-hub-sync.timer

# 检查下次运行时间
systemctl list-timers intra-hub-sync.timer

# 重启 timer
sudo systemctl restart intra-hub-sync.timer
```

### 问题：Nginx 404

```bash
# 检查 Nginx 配置
sudo nginx -t

# 检查文件权限
ls -la /opt/intra-hub/public/

# 修复权限
sudo chown -R www-data:www-data /opt/intra-hub/public/
sudo chmod -R 755 /opt/intra-hub/public/
```

### 问题：文档编号未写回 Notion

检查 Notion 集成权限：
- Integration 必须有 "Update content" 权限
- Database 必须添加了 Integration

---

## 备份与恢复

### 自动备份

系统每次同步前自动创建备份：
```
/opt/intra-hub/backups/intra-hub_fullbackup_YYYYMMDD-HHMMSS.tgz
```

保留最近 7 个备份。

### 手动恢复

```bash
cd /opt/intra-hub/backups
tar -tzf intra-hub_fullbackup_YYYYMMDD-HHMMSS.tgz  # 查看内容
tar -xzf intra-hub_fullbackup_YYYYMMDD-HHMMSS.tgz -C /opt/intra-hub/  # 恢复
```

---

## 维护命令

```bash
# 手动触发同步
sudo systemctl start intra-hub-sync.service

# 查看实时日志
sudo journalctl -u intra-hub-sync.service -f

# 停用定时任务
sudo systemctl stop intra-hub-sync.timer
sudo systemctl disable intra-hub-sync.timer

# 启用定时任务
sudo systemctl enable intra-hub-sync.timer
sudo systemctl start intra-hub-sync.timer

# 清理旧备份（保留最近5个）
cd /opt/intra-hub/backups
ls -t intra-hub_fullbackup_*.tgz | tail -n +6 | xargs rm -f

# 查看磁盘使用
du -sh /opt/intra-hub/*
```

---

## 安全注意事项

1. ⚠️ **内网访问专用** - 确保服务器只能通过 VPN/内网访问
2. ⚠️ **保护 .env 文件** - 包含敏感凭证，权限设为 600
3. ⚠️ **定期备份** - 系统自动备份，但建议异地备份重要数据
4. ⚠️ **监控日志** - 定期检查 `/opt/intra-hub/logs/` 中的错误

---

## 性能参数

- 同步速度：约 10-20 文档/分钟
- 渲染速度：约 20-30 页面/分钟
- 首页加载：< 100ms (10 文档/页)
- 详情页加载：< 200ms

---

## 技术栈

- **后端**：Python 3.8+
- **Notion API**：notion-client
- **条形码**：python-barcode (Code128)
- **Web服务器**：Nginx
- **定时任务**：systemd timer
- **前端**：纯静态 HTML/CSS

---

## 许可证

Internal Use Only - Proprietary

---

## 支持

遇到问题？

1. 查看日志：`/opt/intra-hub/logs/`
2. 检查故障排除章节
3. 联系系统管理员

---

**INTRA-HUB v1.0** - Built for internal documentation excellence.
