# Gnani Voice Studio

Speech-to-Text, Text-to-Speech and an AI Voice Agent for Indian languages, with sign-up, login and
"Continue with Google". Built with Python and Streamlit.

**Start the app with:** `streamlit run streamlit_app.py` (this is the only file you launch).

## Files

| File | What it does |
|---|---|
| `streamlit_app.py` | The entry point. Sets up navigation and logs people in. |
| `page_auth.py` | Log in, Sign up, Continue with Google |
| `page_dashboard.py` | Dashboard |
| `page_stt.py` | Live Speech-to-Text, Audio Upload & Transcription |
| `page_tts.py` | Text-to-Speech |
| `page_agent.py` | AI Voice Agent |
| `page_history.py`, `page_account.py` | History, My Profile, Settings |
| `gnani_client.py` | **All Gnani API calls** (speech-to-text and text-to-speech) |
| `llm_client.py` | The AI model call used by the voice agent |
| `agent_service.py` | Connects speech-to-text, AI model and text-to-speech for one question |
| `google_auth.py` | Checks Google sign-in settings and the Google identity |
| `database.py` | Accounts, history, conversations (SQLite). Upgrades old databases safely. |
| `languages.py`, `voices.py` | The one list of languages, codes and voices |
| `audio_utils.py`, `ui.py`, `styles.py` | Audio checks, shared screen parts, the glass design |
| `assets/logo.svg` | Logo |
| `.env.example`, `.streamlit/secrets.toml.example` | Safe examples of your secret settings |

## 1. Install and run (Windows PowerShell)

**First, back up your current project folder** (copy `Gnani-Voice-Studio` to `Gnani-Voice-Studio-backup`).
Then copy these files over it. Keep your own `.env` and your `voice_studio.db` file.

```powershell
cd C:\Users\HP\Documents\Gnani-Voice-Studio
py -m venv .venv                       # skip if you already have a .venv
.\.venv\Scripts\Activate.ps1           # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open http://localhost:8501. The database upgrades itself on the first start and saves a backup copy next to it
(a file named like `voice_studio.backup-v0-2026....db`). Your existing accounts and history keep working.

## 2. Your `.env` file

Keep your existing `GNANI_API_KEY` line. Add the AI model lines only if you want the Voice Agent (step 4):

```
GNANI_API_KEY=your_gnani_api_key_here
LLM_API_KEY=your_llm_provider_key_here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=a_model_id_from_your_provider
```

## 3. Text-to-Speech

Gnani's official reference puts Text-to-Speech at `https://api.vachana.ai/api/v1/tts/inference` and uses the same
`X-API-Key-ID` header as speech-to-text, so the app reuses your `GNANI_API_KEY`. (Gnani's marketing pages show a different
`api.gnani.ai` address with a Bearer token. The API reference is the authoritative one, so that is what the app uses.)

Nobody can know from outside whether **your account** may use Text-to-Speech. Open **Text-to-Speech**, type a sentence and press
**Generate Speech**. If you see *"Text-to-Speech access was denied"*, ask Gnani support to enable Text-to-Speech on your account
(check the organization is active and has credits). The app never pretends audio was made.

## 4. AI model for the Voice Agent

Gnani's speech APIs do not include a chat model, so the agent needs its own.
1. Go to **Google AI Studio** and create an API key (other OpenAI-compatible providers also work).
2. Put the three `LLM_` lines in `.env`. `LLM_MODEL` must be a model id from your provider's model list.
3. Restart the app. **Settings > Setup status** should say "configured".

Providers set their own prices and free limits, so check them before heavy use. Every question and every answer is one request.

## 5. Continue with Google

1. Open https://console.cloud.google.com and create a project (or pick one).
2. Open **Google Auth Platform** (older menus: *APIs & Services > OAuth consent screen*). Click **Get started**.
   Enter an app name, your support email, choose **External**, add your contact email, accept the policy, **Create**.
3. While the app is in **Testing**, only people you list can sign in: go to **Audience > Test users > Add users** and add your Gmail address.
4. Go to **Clients > Create client**. Application type: **Web application**. Under **Authorized redirect URIs** add exactly
   `http://localhost:8501/oauth2callback`. Click **Create** and copy the **Client ID** and **Client secret**.
5. Copy `.streamlit\secrets.toml.example` to `.streamlit\secrets.toml` and fill it in (make a `cookie_secret` with
   `python -c "import secrets; print(secrets.token_urlsafe(32))"`).
6. Restart the app. The **Continue with Google** button appears on the login page.

Google sometimes renames menu items, so wording may differ a little. When you deploy online, add your real `https://.../oauth2callback`
address in Google Cloud **and** in `redirect_uri`.

## 6. Keep secrets safe

`.gitignore` already excludes `.env`, `.streamlit/secrets.toml` and `*.db`. Never upload those files or paste their contents anywhere.

## 7. Test checklist

**Accounts:** sign up (try a bad email and a weak password) > log in > wrong password > sign out > create a second account and confirm
each account's History shows only its own items.
**Language picker:** type "tam" to find Tamil. Pick Odia: it says "not supported yet" and blocks the action.
**Live Speech-to-Text:** allow the microphone, record, press stop; text appears. Try Copy Transcript and Download Transcript.
**Audio Upload & Transcription:** upload a WAV (works), a `.txt` file (clear error) and a clip longer than 60 seconds (clear error).
**Text-to-Speech:** Telugu, a voice, short text, Generate Speech, play it, Download Audio. Repeat for Tamil, Hindi, English.
**AI Voice Agent:** Start Voice Agent, type a question, then speak one. You should get a written answer and a playable voice answer.
**Google sign-in:** Continue with Google, then sign out from the sidebar.

## Limits (honest list)

* Recording uses Streamlit's built-in microphone widget, so its own buttons keep Streamlit's labels. The app adds the glass styling around it.
* Speech is turn-by-turn. There is no word-by-word streaming and the agent does not listen continuously.
* Email and password logins end when you refresh the page. Google logins can survive a refresh.
* Languages: only languages in Gnani's official tables work (9 of the 22 Eighth Schedule languages, plus English).
