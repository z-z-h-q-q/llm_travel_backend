# llm_travel backend (Python / FastAPI)

## 运行说明

-- **配置本地supabase数据库**
```supabase init```
```supabase start```
启动成功后，会输出本地服务的访问信息，会用到API URL、Database URL、Publishable key和Secret key
按照travel_plans.sql，执行sql语句进行建表

- **拉取镜像**：
```
docker pull crpi-qk3obbgceulitt7u.cn-shanghai.personal.cr.aliyuncs.com/llm_course/backend:V1.0.1
```
- **运行镜像**:
```
docker run -d --name travel_backend -p 8000:8000 -e SUPABASE_URL="URL" -e SUPABASE_SERVICE_ROLE_KEY="KEY" -e AMAP_KEY="KEY" -e COZE_API_BASE="KEY" -e COZE_API_TOKEN="TOKEN" -e COZE_WORKFLOW_ID="ID" -e COZE_AGENT_ID="ID" -e APP_ENV="development" -e DATABASE_URL="URL" -e XINGHUO_API_URL="URL" -e XINGHUO_API_KEY="KEY" -e XINGHUO_MODEL="Lite" crpi-qk3obbgceulitt7u.cn-shanghai.personal.cr.aliyuncs.com/llm_course/backend:V1.0.1
```

-- **容器终端验证服务启动**
```
# 进入容器后执行
curl http://localhost:8000
```
若返回{"ok":true,"app":"llm_travel_backend"}，说明后端容器正确启动

## 代码说明

This backend provides:
- Auth endpoints (register/login)
- Travel plan CRUD (/travel/plans)
- AI planning endpoint (/ai/plan) to call coza agent
- Map routing (/map/route) using Amap (高德)
-- Speech recognition endpoint (/speech/recognize) was previously a placeholder for iFlyTek.
	Server-side ASR integration has been removed from this deployment. Use the
	browser Web Speech API (client-side) for microphone input, or configure
	an alternative server-side provider and add its integration yourself.

Environment variables (use `.env`):

- COZA_AGENT_URL, COZA_API_KEY
- AMAP_KEY
- (Deprecated) XUNFEI_APPID, XUNFEI_API_KEY - server-side iFlyTek keys have been removed
- JWT_SECRET
- DATABASE_URL (default sqlite:///./travel.db)

Run locally:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Notes:
- `speech_provider.recognize_iflytek` is a placeholder; implement real iFlyTek auth & protocol there.
- `llm_provider` expects a Coza orchestration endpoint returning plan JSON; adapt as needed.

Supabase notes:

- To use Supabase as cloud sync, set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in your `.env`.
- Create a table named `travel_plans` with at least the following columns:
	- id (int, primary key, auto increment)
	- owner_id (text)
	- title (text)
	- data (json)
	- created_at (timestamp)
	- updated_at (timestamp)
- The backend will call Supabase REST endpoints to list/create/update/delete plans for the authenticated user. The frontend should authenticate with Supabase (supabase-js) and include `Authorization: Bearer <access_token>` in requests to the backend. The backend will validate tokens via Supabase `/auth/v1/user` endpoint.

