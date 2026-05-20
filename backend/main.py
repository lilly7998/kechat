"""
KeChat - 可聊 轻量即时通讯系统
FastAPI 主入口 - API + WebSocket 服务
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import init_db, SessionLocal, User, Message, Conversation
import uvicorn

# ── 配置 ──
SECRET_KEY = "kechat-demo-secret-key-change-in-production"
ALGORITHM = "HS256"
app = FastAPI(title="KeChat API", version="0.1.0")

# CORS - 允许任何来源（Demo用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── WebSocket 连接管理器 ──
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

manager = ConnectionManager()


# ── 依赖注入 ──
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = None, db: Session = None):
    """从JWT token获取当前用户"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = int(user_id_str)
    except (JWTError, ValueError, TypeError):
        return None
    return db.query(User).filter(User.id == user_id).first()


# ── 请求模型 ──
class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = ""


class LoginRequest(BaseModel):
    username: str
    password: str


class SendMessageRequest(BaseModel):
    receiver_id: int
    content: str


# ── API路由 ──

@app.on_event("startup")
def on_startup():
    init_db()
    # 创建默认测试用户（如果不存在）
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        admin = User(
            username="admin",
            display_name="管理员",
            password_hash=pwd_context.hash("123456"),
        )
        db.add(admin)
    if not db.query(User).filter(User.username == "demo").first():
        demo = User(
            username="demo",
            display_name="演示用户",
            password_hash=pwd_context.hash("123456"),
        )
        db.add(demo)
    db.commit()
    db.close()


@app.get("/")
def root():
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return HTMLResponse("<h1>KeChat 可聊</h1><p>前端尚未部署</p>")


# ── 用户认证 ──

@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "用户名已存在")
    user = User(
        username=req.username,
        display_name=req.display_name or req.username,
        password_hash=pwd_context.hash(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"ok": True, "token": token, "user": {"id": user.id, "username": user.username, "display_name": user.display_name}}
    
    
@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not pwd_context.verify(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = create_access_token({"sub": str(user.id)})
    return {"ok": True, "token": token, "user": {"id": user.id, "username": user.username, "display_name": user.display_name}}


# ── 用户管理 ──

@app.get("/api/users")
def list_users(token: str = Query(...), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(401, "未登录")
    users = db.query(User).filter(User.id != user.id).all()
    return {"ok": True, "users": [
        {"id": u.id, "username": u.username, "display_name": u.display_name,
         "is_online": u.is_online, "last_seen": u.last_seen.isoformat() if u.last_seen else None}
        for u in users
    ]}


@app.get("/api/me")
def get_me(token: str = Query(...), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(401, "未登录")
    return {"ok": True, "user": {"id": user.id, "username": user.username, "display_name": user.display_name}}


# ── 消息 ──

@app.get("/api/messages/{peer_id}")
def get_messages(peer_id: int, token: str = Query(...), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(401, "未登录")
    messages = db.query(Message).filter(
        ((Message.sender_id == user.id) & (Message.receiver_id == peer_id)) |
        ((Message.sender_id == peer_id) & (Message.receiver_id == user.id))
    ).order_by(Message.created_at.asc()).limit(100).all()
    return {"ok": True, "messages": [
        {"id": m.id, "sender_id": m.sender_id, "content": m.content,
         "msg_type": m.msg_type, "created_at": m.created_at.isoformat(), "is_read": m.is_read}
        for m in messages
    ]}


@app.get("/api/conversations")
def get_conversations(token: str = Query(...), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not user:
        raise HTTPException(401, "未登录")
    convs = db.query(Conversation).filter(Conversation.user_id == user.id).order_by(
        Conversation.last_message_time.desc()
    ).limit(50).all()
    result = []
    for c in convs:
        peer = db.query(User).filter(User.id == c.peer_id).first()
        result.append({
            "peer_id": c.peer_id,
            "peer_name": peer.display_name if peer else "未知",
            "last_message": c.last_message,
            "last_message_time": c.last_message_time.isoformat() if c.last_message_time else None,
            "unread_count": c.unread_count,
        })
    return {"ok": True, "conversations": result}


# ── WebSocket ──

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    db = SessionLocal()
    user = get_current_user(token, db)
    if not user:
        await websocket.close(code=4001, reason="未登录")
        db.close()
        return

    # 更新在线状态
    user.is_online = True
    db.commit()

    await manager.connect(user.id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            action = msg.get("action", "send")
            if action == "send":
                receiver_id = msg["receiver_id"]
                content = msg["content"]
                msg_type = msg.get("msg_type", "text")

                # 保存消息
                message = Message(
                    sender_id=user.id,
                    receiver_id=receiver_id,
                    content=content,
                    msg_type=msg_type,
                )
                db.add(message)

                # 更新/创建会话（发送方）
                conv = db.query(Conversation).filter(
                    Conversation.user_id == user.id,
                    Conversation.peer_id == receiver_id,
                ).first()
                if conv:
                    conv.last_message = content
                    conv.last_message_time = message.created_at
                else:
                    conv = Conversation(user_id=user.id, peer_id=receiver_id,
                                        last_message=content, last_message_time=message.created_at)
                    db.add(conv)

                # 更新/创建会话（接收方）
                conv_peer = db.query(Conversation).filter(
                    Conversation.user_id == receiver_id,
                    Conversation.peer_id == user.id,
                ).first()
                if conv_peer:
                    conv_peer.last_message = content
                    conv_peer.last_message_time = message.created_at
                    conv_peer.unread_count = (conv_peer.unread_count or 0) + 1
                else:
                    conv_peer = Conversation(user_id=receiver_id, peer_id=user.id,
                                             last_message=content, last_message_time=message.created_at,
                                             unread_count=1)
                    db.add(conv_peer)

                db.commit()

                # 发送给接收方（如果在线）
                await manager.send_to_user(receiver_id, {
                    "type": "new_message",
                    "message": {
                        "id": message.id,
                        "sender_id": user.id,
                        "sender_name": user.display_name,
                        "content": content,
                        "msg_type": msg_type,
                        "created_at": message.created_at.isoformat(),
                    }
                })

                # 回执给发送方
                await websocket.send_json({
                    "type": "message_sent",
                    "message_id": message.id,
                    "created_at": message.created_at.isoformat(),
                })

            elif action == "read":
                # 标记已读
                peer_id = msg["peer_id"]
                db.query(Message).filter(
                    Message.sender_id == peer_id,
                    Message.receiver_id == user.id,
                    Message.is_read == False,
                ).update({"is_read": True})
                conv_peer = db.query(Conversation).filter(
                    Conversation.user_id == user.id,
                    Conversation.peer_id == peer_id,
                ).first()
                if conv_peer:
                    conv_peer.unread_count = 0
                db.commit()

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        user.is_online = False
        user.last_seen = datetime.utcnow()
        db.commit()
        manager.disconnect(user.id)
        db.close()


# ── 启动 ──
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8088"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
