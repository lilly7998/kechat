FROM python:3.11-slim

WORKDIR /app

# 安装后端依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir 'bcrypt<4.1'

# 复制后端代码
COPY backend/ ./backend/

# 复制前端页面
COPY frontend/ ./frontend/

# 暴露端口
EXPOSE 8088

# 启动
ENV PORT=8088
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8088"]
