# 使用自定义基础镜像
FROM crpi-qk3obbgceulitt7u.cn-shanghai.personal.cr.aliyuncs.com/llm_course/python:3.11-slim-with-buildtools

WORKDIR /app

# 复制依赖并安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app ./app
COPY travel.db ./travel.db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
