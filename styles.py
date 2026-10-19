"""Glassmorphism design system for Gnani Voice Studio.

HOW THE STYLING IS ATTACHED (so it does not depend on Streamlit's internal HTML):
  * Cards      : st.container(key="card_...")  ->  Streamlit adds the class  st-key-card_...
  * Buttons    : st.button(key="gp_...")       ->  st-key-gp_...   (primary glass, orange)
                 st.button(key="gs_...")       ->  st-key-gs_...   (stop / danger glass, red)
                 st.button(key="gg_...")       ->  st-key-gg_...   (ghost glass, white)
  The CSS below targets those key classes, so you restyle a button just by changing its key prefix.
"""

import urllib.parse

_G = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
      "<path fill='#EA4335' d='M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z'/>"
      "<path fill='#4285F4' d='M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z'/>"
      "<path fill='#FBBC05' d='M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z'/>"
      "<path fill='#34A853' d='M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z'/></svg>")
GOOGLE_ICON_URI = "data:image/svg+xml;utf8," + urllib.parse.quote(_G)

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Figtree:wght@400;500;600&family=Noto+Sans+Telugu:wght@400;500&display=swap');

:root{
  --navy:#0E1A3A; --muted:#4F5D78; --orange:#E8600F; --orange-deep:#BE4305; --orange-soft:#FFE9D6;
  --glass:rgba(255,255,255,.66); --glass-line:rgba(255,255,255,.78); --line:rgba(232,96,15,.16);
  --ok:#1F6B42; --warn:#7A4A00; --err:#9B1C14;
}
.stApp, .stApp button, .stApp textarea, .stApp input{font-family:'Figtree',system-ui,sans-serif;}
.stApp{
  color:var(--navy); background-color:#FFFDFB;
  background-image:
    radial-gradient(900px 520px at 6% -6%, rgba(255,140,60,.20), transparent 62%),
    radial-gradient(760px 520px at 100% 0%, rgba(255,196,130,.26), transparent 58%),
    radial-gradient(900px 620px at 50% 112%, rgba(255,120,40,.12), transparent 62%);
  background-attachment:fixed;
}
#MainMenu, footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:1120px;padding:2rem 1.5rem 4rem;}
h1,h2,h3{color:var(--navy);}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"]{background:rgba(255,246,236,.82);border-right:1px solid var(--line);
  -webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);}
.user-card{display:flex;align-items:center;gap:.7rem;background:var(--glass);border:1px solid var(--glass-line);
  border-radius:16px;padding:.7rem .8rem;margin:1rem 0 .6rem;box-shadow:0 10px 24px -18px rgba(190,67,5,.45);}
.avatar{flex:none;width:38px;height:38px;border-radius:50%;display:grid;place-items:center;font-weight:700;color:#fff;
  background:linear-gradient(135deg,#E8600F,#A53703);}
.avatar.big{width:68px;height:68px;font-size:1.7rem;}
.user-card .who{min-width:0;}
.user-card b{display:block;font-size:.95rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.user-card small{color:var(--muted);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}

/* ---------- Headings ---------- */
.page-head{display:flex;align-items:center;gap:.9rem;margin:0 0 .2rem;}
.page-title{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:2rem;letter-spacing:-.02em;margin:0;padding:0;color:var(--navy);}
.page-lede{color:var(--muted);font-size:1.03rem;max-width:64ch;margin:.3rem 0 1.4rem;}
.brand-mark{width:48px;height:48px;border-radius:14px;display:grid;place-items:center;
  background:linear-gradient(135deg,#F37A2C,#BE4305);box-shadow:0 10px 22px -10px rgba(190,67,5,.8);}
.chip{flex:none;width:44px;height:44px;border-radius:13px;display:grid;place-items:center;color:var(--orange-deep);
  background:linear-gradient(135deg,rgba(255,255,255,.9),var(--orange-soft));border:1px solid var(--line);}

/* ---------- Glass cards ---------- */
[class*="st-key-card_"], .st-key-band{
  background:var(--glass);border:1px solid var(--glass-line);border-radius:22px;padding:1.5rem;
  -webkit-backdrop-filter:blur(18px) saturate(150%);backdrop-filter:blur(18px) saturate(150%);
  box-shadow:0 0 0 1px var(--line), 0 18px 40px -24px rgba(190,67,5,.42), inset 0 1px 0 rgba(255,255,255,.9);}
.st-key-band{padding:1.4rem;margin-bottom:1.4rem;background:rgba(255,238,220,.45);}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  [class*="st-key-card_"], .st-key-band{background:rgba(255,255,255,.95);}
}
.card-head{display:flex;gap:.9rem;align-items:flex-start;margin-bottom:.9rem;}
.card-head h3{font-family:'Bricolage Grotesque',sans-serif;font-weight:600;font-size:1.28rem;margin:0;padding:0;}
.card-head p{margin:.15rem 0 0;color:var(--muted);font-size:.95rem;}

/* ---------- Glass buttons (see key prefixes in the module docstring) ---------- */
[class*="st-key-gp_"], [class*="st-key-gs_"], [class*="st-key-gg_"]{width:100%;}
[class*="st-key-gp_"] button, [class*="st-key-gs_"] button, [class*="st-key-gg_"] button{
  width:100%;min-height:46px;border-radius:14px;font-weight:600;font-size:.98rem;cursor:pointer;
  -webkit-backdrop-filter:blur(12px) saturate(160%);backdrop-filter:blur(12px) saturate(160%);
  transition:transform .18s ease, box-shadow .18s ease, background .18s ease, border-color .18s ease, filter .18s ease;}
[class*="st-key-gp_"] button *, [class*="st-key-gs_"] button *, [class*="st-key-gg_"] button *{color:inherit !important;}
[class*="st-key-gp_"] button{
  color:#fff !important;border:1px solid rgba(255,255,255,.5) !important;
  background:linear-gradient(135deg, rgba(200,76,6,.96), rgba(165,55,3,.97)) !important;
  box-shadow:0 12px 26px -12px rgba(165,55,3,.75), inset 0 1px 0 rgba(255,255,255,.38);}
[class*="st-key-gp_"] button:hover:not(:disabled){transform:translateY(-1px);filter:brightness(1.07);
  box-shadow:0 16px 30px -12px rgba(165,55,3,.85), inset 0 1px 0 rgba(255,255,255,.45);}
[class*="st-key-gs_"] button{
  color:var(--err) !important;border:1px solid rgba(155,28,20,.38) !important;background:rgba(255,236,233,.72) !important;
  box-shadow:0 10px 22px -16px rgba(155,28,20,.6), inset 0 1px 0 rgba(255,255,255,.8);}
[class*="st-key-gs_"] button:hover:not(:disabled){transform:translateY(-1px);background:rgba(255,226,222,.92) !important;border-color:rgba(155,28,20,.6) !important;}
[class*="st-key-gg_"] button{
  color:var(--orange-deep) !important;border:1px solid rgba(232,96,15,.30) !important;background:rgba(255,255,255,.62) !important;
  box-shadow:0 10px 22px -16px rgba(190,67,5,.5), inset 0 1px 0 rgba(255,255,255,.9);}
[class*="st-key-gg_"] button:hover:not(:disabled){transform:translateY(-1px);background:rgba(255,255,255,.9) !important;border-color:rgba(232,96,15,.6) !important;}
[class*="st-key-gp_"] button:active:not(:disabled), [class*="st-key-gs_"] button:active:not(:disabled),
[class*="st-key-gg_"] button:active:not(:disabled){transform:translateY(0) scale(.985);}
[class*="st-key-gp_"] button:disabled, [class*="st-key-gs_"] button:disabled, [class*="st-key-gg_"] button:disabled{
  opacity:.5;cursor:not-allowed;box-shadow:none;}
button:focus-visible, a:focus-visible, textarea:focus-visible, input:focus-visible{outline:3px solid #FF9A57 !important;outline-offset:2px;}

/* Continue with Google: the real multicolour Google "G" */
.st-key-gg_google button{gap:.7rem;color:var(--navy) !important;}
.st-key-gg_google button::before{content:"";width:20px;height:20px;flex:none;background:url("__GOOGLE__") center/contain no-repeat;}

/* Quick-access cards */
[class*="st-key-card_quick"] a{display:flex;justify-content:center;align-items:center;min-height:44px;border-radius:14px;font-weight:600;
  color:var(--orange-deep) !important;text-decoration:none;background:rgba(255,255,255,.62);border:1px solid rgba(232,96,15,.30);
  transition:transform .18s ease, background .18s ease;}
[class*="st-key-card_quick"] a:hover{transform:translateY(-1px);background:rgba(255,255,255,.92);}
[class*="st-key-card_quick"] a *{color:inherit !important;}

/* ---------- Inputs ---------- */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div{border-radius:12px;}
.stTextInput input:focus, .stTextArea textarea:focus{border-color:var(--orange) !important;box-shadow:0 0 0 3px rgba(232,96,15,.2) !important;}
[class*="st-key-card_"] textarea{font-family:'Noto Sans Telugu','Figtree',sans-serif !important;font-size:1.1rem;line-height:1.85;background:rgba(255,252,248,.9);}

/* ---------- Pills, notices, loading ---------- */
.pill{display:inline-flex;align-items:center;gap:.5rem;font-size:.88rem;font-weight:500;padding:.3rem .8rem;border-radius:999px;
  background:rgba(255,255,255,.7);color:var(--muted);border:1px solid var(--line);margin:.2rem 0 .8rem;}
.pill::before{content:"";width:8px;height:8px;border-radius:50%;background:#C9B6A3;}
.pill.ready{background:var(--orange-soft);color:var(--orange-deep);border-color:#FFD0A8;} .pill.ready::before{background:var(--orange);}
.pill.done{background:#E7F5EC;color:var(--ok);border-color:#BFE1CC;} .pill.done::before{background:var(--ok);}
.pill.warn{background:#FFF4D6;color:var(--warn);border-color:#F2DC9B;} .pill.warn::before{background:#D49A00;}
.pill.busy::before{background:var(--orange);animation:blink 1s ease-in-out infinite;}
@keyframes blink{50%{opacity:.25}}
.notice{border-radius:16px;padding:1rem 1.2rem;margin:.4rem 0 1.2rem;border:1px solid;
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);}
.notice b{display:block;margin-bottom:.15rem;}
.notice.error{background:rgba(255,238,235,.85);border-color:#F1C4BE;color:#6E140E;}
.notice.warn{background:rgba(255,247,222,.9);border-color:#F2DC9B;color:#5E3A00;}
.notice.info{background:rgba(255,246,236,.9);border-color:var(--line);color:var(--navy);}
.notice.ok{background:rgba(232,246,237,.9);border-color:#BFE1CC;color:#164F30;}
.loading{display:flex;align-items:center;gap:1rem;background:var(--glass);border:1px solid var(--glass-line);border-radius:18px;
  padding:1rem 1.25rem;margin:.4rem 0 1.4rem;box-shadow:0 0 0 1px var(--line), 0 14px 30px -22px rgba(190,67,5,.55);}
.bars{display:flex;align-items:center;gap:4px;height:32px;}
.bars span{width:5px;height:100%;border-radius:3px;background:linear-gradient(180deg,#F37A2C,#A53703);animation:wave 1s ease-in-out infinite;}
.bars span:nth-child(2){animation-delay:.12s}.bars span:nth-child(3){animation-delay:.24s}
.bars span:nth-child(4){animation-delay:.36s}.bars span:nth-child(5){animation-delay:.48s}
@keyframes wave{0%,100%{transform:scaleY(.25)}50%{transform:scaleY(1)}}
.loading b{display:block;font-weight:600;} .loading small{color:var(--muted);}

/* ---------- Microphone hero, transcript, chat ---------- */
.mic-hero{display:flex;align-items:center;gap:1.4rem;margin-bottom:1rem;}
.mic-orb{position:relative;flex:none;width:92px;height:92px;border-radius:50%;display:grid;place-items:center;color:#fff;
  background:linear-gradient(135deg,#E8600F,#A53703);box-shadow:0 18px 30px -14px rgba(165,55,3,.9), inset 0 1px 0 rgba(255,255,255,.4);}
.mic-orb::after{content:"";position:absolute;inset:-9px;border-radius:50%;border:2px solid rgba(232,96,15,.35);animation:ring 2.4s ease-out infinite;}
.mic-orb.busy::after{border-color:rgba(165,55,3,.7);animation-duration:1s;}
@keyframes ring{0%{transform:scale(.92);opacity:.9}100%{transform:scale(1.25);opacity:0}}
.mic-hero h3{font-family:'Bricolage Grotesque',sans-serif;font-size:1.35rem;margin:0;padding:0;}
.mic-hero p{margin:.2rem 0 0;color:var(--muted);}
.t-head{display:flex;justify-content:space-between;align-items:flex-end;gap:1rem;flex-wrap:wrap;margin-bottom:.4rem;}
.t-head h2{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:1.5rem;margin:0;padding:0;}
.t-meta{color:var(--muted);font-size:.9rem;}
.hint{color:var(--muted);font-size:.88rem;margin:.5rem 0 1rem;}
.latest{background:rgba(255,246,236,.9);border:1px solid var(--line);border-radius:14px;padding:.8rem 1rem;margin:.2rem 0 1rem;font-family:'Noto Sans Telugu','Figtree',sans-serif;}
.latest small{display:block;color:var(--muted);font-family:'Figtree',sans-serif;margin-bottom:.2rem;}
.chat{display:flex;flex-direction:column;gap:.7rem;margin:.4rem 0 1rem;}
.bubble{max-width:82%;padding:.8rem 1rem;border-radius:18px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;
  font-family:'Noto Sans Telugu','Figtree',sans-serif;box-shadow:0 10px 24px -18px rgba(14,26,58,.5);}
.bubble small{display:block;font-family:'Figtree',sans-serif;font-size:.78rem;margin-bottom:.15rem;opacity:.85;}
.bubble.user{align-self:flex-end;color:#fff;background:linear-gradient(135deg, rgba(200,76,6,.96), rgba(165,55,3,.97));border-bottom-right-radius:6px;}
.bubble.assistant{align-self:flex-start;color:var(--navy);background:rgba(255,255,255,.82);border:1px solid var(--glass-line);border-bottom-left-radius:6px;}
.empty{color:var(--muted);text-align:center;padding:1.6rem 1rem;border:1px dashed rgba(232,96,15,.35);border-radius:16px;background:rgba(255,255,255,.45);}

/* ---------- Dashboard ---------- */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:.9rem;margin:0 0 1.4rem;}
.stat{background:var(--glass);border:1px solid var(--glass-line);border-radius:18px;padding:1rem 1.1rem;
  box-shadow:0 0 0 1px var(--line), 0 14px 30px -24px rgba(190,67,5,.5);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);}
.stat b{display:block;font-family:'Bricolage Grotesque',sans-serif;font-size:1.9rem;line-height:1.1;color:var(--navy);}
.stat span{color:var(--muted);font-size:.9rem;}
.activity{display:flex;gap:.8rem;align-items:flex-start;padding:.7rem 0;border-bottom:1px solid var(--line);}
.activity:last-child{border-bottom:0;}
.activity .dot{flex:none;width:10px;height:10px;border-radius:50%;background:var(--orange);margin-top:.5rem;}
.activity b{display:block;} .activity small{color:var(--muted);}
.fine{color:var(--muted);font-size:.85rem;margin-top:1.6rem;text-align:center;}

@media (max-width:760px){ .stats{grid-template-columns:repeat(2,1fr);} }
@media (max-width:640px){
  .block-container{padding:1.1rem .9rem 3rem;} .page-title{font-size:1.6rem;}
  [class*="st-key-card_"], .st-key-band{padding:1.05rem;border-radius:20px;}
  .mic-hero{flex-direction:column;align-items:flex-start;} .bubble{max-width:94%;}
}
@media (prefers-reduced-motion:reduce){
  .bars span, .mic-orb::after, .pill.busy::before{animation:none;}
  [class*="st-key-gp_"] button, [class*="st-key-gs_"] button, [class*="st-key-gg_"] button{transition:none;}
}
</style>
""".replace("__GOOGLE__", GOOGLE_ICON_URI)

# Signed-out pages: no sidebar, split brand/form layout.
AUTH_CSS = """
<style>
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]{display:none !important;}
.block-container{max-width:1000px;padding-top:3rem;}
.st-key-auth_brand{background:linear-gradient(150deg,#D4560A 0%,#9A3303 100%);color:#fff;border-radius:28px;padding:2.2rem;min-height:100%;
  box-shadow:0 30px 50px -30px rgba(154,51,3,.9), inset 0 1px 0 rgba(255,255,255,.3);}
.st-key-auth_brand h2{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:2rem;line-height:1.15;letter-spacing:-.02em;color:#fff;margin:1.2rem 0 .8rem;padding:0;}
.st-key-auth_brand p, .st-key-auth_brand li{color:#FFF1E6;font-size:1rem;}
.st-key-auth_brand ul{padding-left:1.1rem;margin:1rem 0 0;} .st-key-auth_brand li{margin:.45rem 0;}
.st-key-auth_brand .brand-mark{background:rgba(255,255,255,.2);box-shadow:inset 0 1px 0 rgba(255,255,255,.4);}
.auth-title{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:1.7rem;margin:0 0 .2rem;padding:0;}
.auth-sub{color:var(--muted);margin:0 0 1rem;}
.or-line{display:flex;align-items:center;gap:.8rem;color:var(--muted);font-size:.9rem;margin:1rem 0;}
.or-line::before, .or-line::after{content:"";flex:1;height:1px;background:var(--line);}
</style>
"""
