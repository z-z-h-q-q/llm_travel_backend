# llm_travel backend (Python / FastAPI)

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

