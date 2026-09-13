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
api/profile.py
```

## Runtime Notes

- Each chat session stores its own Gemini/OpenAI keys through the Settings dialog.
- Profile, chat windows, memory, and keys are persisted in that user's browser with `localStorage`.
- The Python APIs are stateless: `/api/chat` receives the active session context, calls live APIs and an LLM, then returns the answer and trace.
- For cross-device production accounts, move browser state to a database and encrypt API keys with a managed secret service.
