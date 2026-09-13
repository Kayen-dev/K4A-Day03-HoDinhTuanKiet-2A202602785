# Deploy on Vercel

## Import Settings

When importing the GitHub repository into Vercel:

```text
Framework Preset: Other
Root Directory: ./
Build Command: leave empty
Output Directory: leave empty
Install Command: pip install -r requirements.txt
```

Vercel will serve:

```text
web/index.html
web/app.js
web/styles.css
```

and Python serverless endpoints:

```text
api/state.py
api/chat.py
api/settings.py
api/sessions.py
```

## Runtime Notes

- Each chat session can store its own Gemini/OpenAI keys through the Settings dialog.
- On Vercel, local JSON state is written to `/tmp/travel-agent`. This is suitable for demos, but not durable production storage.
- For production persistence, replace `src/state_store.py` with Vercel KV, Upstash Redis, Supabase, or Postgres.
