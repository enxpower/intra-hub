# INTRA-HUB v1.0 - 项目文件说明

## 文件清单

```
intra-hub-v1.0/
│
├── README.md                    # 完整安装和使用文档
├── QUICKSTART.md               # 5分钟快速启动指南
├── PROJECT.md                  # 本文件 - 项目说明
├── requirements.txt            # Python 依赖包列表
├── .env.template               # 环境变量模板
│
├── setup.sh                    # 服务器初始化脚本（需 root）
├── install_scheduler.sh        # 定时任务安装脚本（需 root）
├── check_installation.sh       # 安装检查脚本
├── nginx.conf.example          # Nginx 配置示例
│
├── sync/                       # Notion 同步模块
│   ├── __init__.py
│   ├── notion_sync.py         # Notion API 同步核心
│   └── main.py                # 同步主程序入口
│
└── renderer/                   # HTML 渲染模块
    ├── __init__.py
    ├── html_renderer.py       # 主渲染引擎
    ├── block_renderer.py      # Notion 块渲染器
    └── barcode_generator.py   # Code128 条形码生成器
```

## 模块说明

### sync/ - 同步模块

**notion_sync.py**
- 连接 Notion API
- 拉取数据库所有页面
- 分配 DOC-ID（首次发布时）
- 将 DOC-ID 写回 Notion（双向同步）
- 获取页面完整内容（blocks）
- 缓存到 JSON 文件

**main.py**
- 主程序入口
- 创建备份
- 调用同步逻辑
- 调用渲染逻辑
- 生成搜索索引
- 清理已撤销文档

### renderer/ - 渲染模块

**block_renderer.py**
- 将 Notion blocks 转换为 HTML
- 支持段落、标题、列表、代码块、表格等
- 处理富文本格式（粗体、斜体、代码等）
- 错误隔离（单个块失败不影响其他块）

**html_renderer.py**
- 主渲染引擎
- 渲染文档详情页
- 生成首页（分页，10条/页）
- 生成搜索索引 JSON
- 管理访问统计（浏览、下载、分享）
- 清理已撤销文档

**barcode_generator.py**
- 生成 Code128 条形码
- 输出为 Base64 数据 URI
- 可保存为 PNG 文件
- 包含人类可读文本

## 工作流程

1. **定时触发**（systemd timer，每天凌晨 2:00）
2. **创建备份**（完整系统快照）
3. **同步 Notion**
   - 获取所有页面
   - 分配/验证 DOC-ID
   - 写回 Notion
   - 缓存内容
4. **渲染 HTML**
   - 为每个发布文档生成详情页
   - 生成条形码
   - 嵌入统计数据
5. **生成首页**
   - 分页列表（10条/页）
   - 显示所有元数据
6. **生成搜索索引**
   - JSON 格式
   - 客户端搜索支持
7. **清理撤销文档**
   - 删除未发布文档的 HTML

## 数据流

```
Notion Database
    ↓
[notion_sync.py] → 拉取数据
    ↓
data/cache/*.json → 缓存
    ↓
[html_renderer.py] → 渲染
    ↓
public/*.html → 发布
    ↓
Nginx → 内网访问
```

## 关键特性

### 1. 双向同步
- 服务器生成 DOC-ID
- 写回 Notion 的 DOC_ID 字段
- 保持一致性

### 2. 文档编号系统
- 格式：DOC-XXXX（例如 DOC-0001）
- 首次发布时分配
- 永久不变
- 全局唯一

### 3. 高保真渲染
- 支持 Notion 主要块类型
- 保持格式和样式
- 响应式设计
- 打印友好

### 4. 条形码
- Code128 标准
- 高对比度
- 包含文本标签
- 位于页面右上角

### 5. 统计追踪
- 浏览次数
- 下载次数
- 分享次数
- 仅内网统计

### 6. 自动备份
- 每次同步前创建
- 保留最近 7 个
- 完整系统快照
- 可快速恢复

## 安全考虑

- ✅ 内网访问专用（VPN/防火墙）
- ✅ .env 权限 600（保护凭证）
- ✅ www-data 用户运行（最小权限）
- ✅ 无外部依赖/API 调用
- ✅ 无用户认证（内网信任环境）
- ✅ 静态文件服务（无动态攻击面）

## 性能指标

- 同步 100 文档：约 5-10 分钟
- 渲染 100 页面：约 3-5 分钟
- 首页加载时间：< 100ms
- 详情页加载：< 200ms
- 磁盘占用：约 50MB（100 文档）

## 技术栈

- **语言**：Python 3.8+, Bash, HTML/CSS
- **API**：Notion API (notion-client)
- **条形码**：python-barcode
- **Web 服务器**：Nginx
- **调度**：systemd timer
- **存储**：JSON 文件（无数据库）

## 扩展性

当前设计支持：
- 数千个文档
- 数十个并发用户
- 单服务器部署

如需扩展：
- 添加数据库（PostgreSQL/MySQL）
- 实现真实统计 API
- 添加用户认证
- 多服务器负载均衡

## 维护建议

- 每周检查日志
- 每月审查备份
- 每季度清理旧备份
- 监控磁盘空间
- 保持 Notion API token 有效性

## 许可证

内部使用专用 - 专有软件

## 版本

**v1.0.0** - 2024 年初始发布

严格遵循 SPEC.md 规格文档实现。

---

**INTRA-HUB** - Internal Documentation Made Simple
