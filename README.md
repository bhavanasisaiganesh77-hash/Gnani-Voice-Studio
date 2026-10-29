# Gnani Voice Studio

Speech to Text and Text to Speech for Indian languages, with sign-up, login, "Continue with Google"
and a floating help assistant. Built with Python and Streamlit.

**Start the app with:** `streamlit run streamlit_app.py` (the only file you launch).

## Pages

Dashboard, Speak Live, Record / Upload, Text to Speech, History, Profile, Settings.
The assistant button (bottom-right) appears on every page once you are signed in, and never on Log in or Sign up.

## Files

| File | What it does |
|---|---|
| `streamlit_app.py` | Entry point: navigation, login check, assistant |
| `assistant.py` | The floating assistant (button, chat panel) |
| `agent_service.py` | The assistant's answers: built-in help, plus the AI model when configured |
| `llm_client.py` | Optional AI model call (OpenAI-compatible chat API) |
| `gnani_client.py` | **All Gnani calls** (speech to text, text to speech) |
| `page_*.py` | One file per page group (auth, dashboard, stt, tts, history, account) |
| `database.py` | Accounts, history (SQLite). Upgrades older databases automatically. |
| `google_auth.py` | Google sign-in checks |
| `languages.py`, `voices.py` | The one list of languages, codes and voices |
| `audio_utils.py`, `ui.py`, `styles.py` | Audio checks, shared screen parts, the design |

## Run it (Windows PowerShell)

Back up your project folder first, then copy these files over it. Keep your own `.env` and `voice_studio.db`.

```powershell
cd C:\Users\HP\Documents\Gnani-Voice-Studio
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Needs Python 3.10+ and Streamlit 1.49 or newer.

## Settings and secrets

* `.env` (local) holds `GNANI_API_KEY`. The `LLM_` lines are optional.
* `.streamlit/secrets.toml` (local) holds the Google sign-in settings. See `secrets.toml.example`.
* On **Streamlit Community Cloud**, paste the same values into *App settings > Secrets* as TOML. Top-level keys such as
  `GNANI_API_KEY = "..."` are also available to the app as environment variables.
* `.gitignore` already excludes `.env`, `.streamlit/secrets.toml` and `*.db`. Never upload those files.

Nothing about keys, models, endpoints or setup is shown in the interface. Problems are written to the server log
(your terminal locally, *Manage app > Logs* on Community Cloud).

## The assistant

It answers questions about using the app: transcribing, recording, uploading, text to speech, languages, history, account,
and common errors. With the optional `LLM_` settings it uses your AI model, limited to the app's own help facts.
Without them, or if the provider is down, it uses built-in answers, so it always replies. The chat lives only in your
browser session; nothing is saved.

## Notes

* Community Cloud storage is temporary. The SQLite file can be reset when the app restarts or redeploys.
* Email and password sessions end when the page is refreshed. Google sessions can survive a refresh.
* Languages: only those in Gnani's official tables work (9 of the 22 Eighth Schedule languages, plus English).
