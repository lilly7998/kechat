# KeChat 可聊

> 💬 **轻量、自主可控的企业内部即时通讯系统**
>
> 替代微信/钉钉，数据自己管，不经过第三方。

---

## 🎯 解决的问题

- **不想用微信/钉钉**做内部沟通 → 数据不在自己手里
- **小团队**需要一个简单、私密的聊天工具
- **自托管**，VPS 上一键部署，数据不流出自家服务器

## ✨ 功能

| 功能 | 状态 |
|:----|:----:|
| ✅ 用户注册/登录 | 可用 |
| ✅ 1对1即时聊天（WebSocket 实时推送） | 可用 |
| ✅ 最近联系人列表 | 可用 |
| ✅ 未读消息计数 | 可用 |
| ✅ Docker 一键部署 | 可用 |
| 🚧 网页版聊天界面 | 开发中 |
| 🚧 手机端适配 | 计划中 |

## 🚀 快速开始

### 方式一：Docker 运行（推荐）

```bash
# 克隆仓库
git clone https://github.com/lilly7998/kechat.git
cd kechat

# 启动服务
docker compose up -d

# 访问 http://localhost:8080
```

### 方式二：直接运行

```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 测试账号

| 用户名 | 密码 | 角色 |
|:-----|:----|:----|
| `admin` | `123456` | 管理员 |
| `demo` | `123456` | 演示用户 |

## 📡 API 文档

启动服务后访问 `http://localhost:8088` 可查看聊天界面。

### 核心接口

| 方法 | 路径 | 说明 |
|:---|:----|:----|
| POST | `/api/register` | 注册新用户 |
| POST | `/api/login` | 登录获取 token |
| GET | `/api/users?token=xxx` | 获取用户列表 |
| GET | `/api/messages/{peer_id}?token=xxx` | 获取聊天历史 |
| GET | `/api/conversations?token=xxx` | 获取会话列表 |
| WS | `/ws?token=xxx` | WebSocket 实时聊天 |

## 🏗 技术栈

- **后端**: Python FastAPI + WebSocket
- **数据库**: SQLite（轻量，零配置）
- **部署**: Docker
- **前端**: 纯 HTML/CSS/JS（无需构建工具）

## 📜 许可证

MIT
