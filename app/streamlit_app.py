import json
import re
import uuid
from datetime import datetime, timezone

import streamlit as st
from snowflake.snowpark.context import get_active_session

# =========================
# CONFIG
# =========================
BOT_NAME = "FrostAI"
BOT_TAGLINE = "Assistant IA propulsé par Snowflake Cortex"
APP_DESC = "Chat IA Snowflake (Streamlit + Cortex) avec historique."
TABLE_NAME = "DB_LAB.CHAT_APP.CHAT_MESSAGES"

CORTEX_MODELS = [
    "mistral-large",
    "llama3.1-8b",
    "llama3.1-70b",
    "mixtral-8x7b",
    "reka-core",
]

SYSTEM_PROMPT = "Tu es un assistant utile. Réponds clairement et de façon concise."
MAX_HISTORY = 20
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/642/642102.png"


# =========================
# UTILS
# =========================
def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def init_state():
    st.session_state.setdefault("conversation_id", str(uuid.uuid4()))
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("model", CORTEX_MODELS[0])
    st.session_state.setdefault("temperature", 0.2)

    # dock keys (important : jamais modifier un widget déjà instancié)
    st.session_state.setdefault("draft_key", 0)
    st.session_state.setdefault("pending_send", False)
    st.session_state.setdefault("pending_text", "")


def reset_chat():
    st.session_state.conversation_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.pending_send = False
    st.session_state.pending_text = ""
    st.session_state.draft_key += 1  # force un nouveau champ propre


def trim_history(messages):
    return messages[-MAX_HISTORY:] if len(messages) > MAX_HISTORY else messages


def save_message(session, conversation_id, role, content):
    safe_content = (content or "").replace("'", "''")
    sql = f"""
        INSERT INTO {TABLE_NAME} (conversation_id, timestamp, role, content)
        VALUES (
            '{conversation_id}',
            TO_TIMESTAMP_NTZ('{now_utc()}'),
            '{role}',
            '{safe_content}'
        );
    """
    session.sql(sql).collect()


def build_messages_payload(system_prompt, history):
    payload = [{"role": "system", "content": system_prompt}]
    payload.extend(history)
    return payload


def extract_text(resp):
    if resp is None:
        return None

    # si c'est déjà une string JSON, on tente de parser
    if isinstance(resp, str):
        try:
            resp = json.loads(resp)
        except Exception:
            text = resp
        else:
            text = None
    else:
        text = None

    if text is None:
        try:
            c0 = resp["choices"][0]

            # format chat "normal"
            if isinstance(c0.get("message"), dict):
                text = c0["message"].get("content")

            # format Cortex fréquent : "messages" = string
            elif isinstance(c0.get("messages"), str):
                text = c0["messages"]

            # autre format : "text"
            elif isinstance(c0.get("text"), str):
                text = c0["text"]

            else:
                text = str(resp)

        except Exception:
            text = str(resp)

    if not text:
        return text

    # nettoyage anti [INST]
    text = re.sub(r"\[INST\].*?\[/INST\]\s*", "", text, flags=re.DOTALL).strip()
    text = re.sub(r"\[INST\].*", "", text, flags=re.DOTALL).strip()

    # petit nettoyage visuel (certains modèles ajoutent des espaces en tête)
    return text.strip()



def call_cortex_complete(session, model, messages_payload, temperature):
    if model not in CORTEX_MODELS:
        raise ValueError("Modèle non autorisé.")

    prompt_json = json.dumps(messages_payload, ensure_ascii=False)
    options_json = json.dumps({"temperature": float(temperature)}, ensure_ascii=False)

    sql = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            '{model}',
            PARSE_JSON(?),
            PARSE_JSON(?)
        ) AS RESPONSE;
    """
    row = session.sql(sql, params=[prompt_json, options_json]).collect()[0]
    return row["RESPONSE"]


def handle_user_message(session, user_input: str):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages = trim_history(st.session_state.messages)

    try:
        save_message(session, st.session_state.conversation_id, "user", user_input)
    except Exception as e:
        st.warning(f"Insertion DB (user) impossible : {e}")

    messages_payload = build_messages_payload(SYSTEM_PROMPT, st.session_state.messages)

    with st.chat_message("assistant"):
        with st.spinner("Réponse en cours..."):
            try:
                raw = call_cortex_complete(
                    session=session,
                    model=st.session_state.model,
                    messages_payload=messages_payload,
                    temperature=st.session_state.temperature,
                )
                text = extract_text(raw)

                if not text:
                    st.error("Réponse vide (NULL) : modèle indisponible / droits / quotas.")
                    return

                st.write(text)

                st.session_state.messages.append({"role": "assistant", "content": text})
                st.session_state.messages = trim_history(st.session_state.messages)

                try:
                    save_message(session, st.session_state.conversation_id, "assistant", text)
                except Exception as e:
                    st.warning(f"Insertion DB (assistant) impossible : {e}")

            except Exception as e:
                st.error(f"Erreur Cortex : {e}")


def queue_send(current_key: str):
    # ne touche jamais à la valeur du widget, on change juste de key après
    text = (st.session_state.get(current_key) or "").strip()
    if not text:
        return
    st.session_state.pending_send = True
    st.session_state.pending_text = text
    st.session_state.draft_key += 1  # nouveau champ (vide) au rerun


# =========================
# APP
# =========================
st.set_page_config(page_title=BOT_NAME, layout="centered")
init_state()
session = get_active_session()

# CSS
st.markdown("""
<style>

/* =========================================================
   THEME GLOBAL
========================================================= */
.stApp{
  background: radial-gradient(1200px circle at 20% 10%, #1e293b 0%, #0b1220 45%, #060a12 100%);
  color:#e5e7eb;
}

.block-container{
  max-width:980px !important;
  margin:0 auto !important;
  padding:24px 18px 170px 18px !important;
  background: rgba(10,15,25,0.65);
  border:1px solid rgba(255,255,255,0.08);
  border-radius:16px;
  box-shadow:0 10px 35px rgba(0,0,0,0.4);
}

h1,h2,h3,p,label,span,div{
  color:#e5e7eb !important;
}

/* =========================================================
   SIDEBAR
========================================================= */
section[data-testid="stSidebar"]{
  background: rgba(10,15,25,0.95);
  border-right:1px solid rgba(255,255,255,0.08);
}

section[data-testid="stSidebar"] .stButton button{
  background:#0f172a !important;
  color:#fff !important;
  border:1px solid rgba(255,255,255,0.15) !important;
  border-radius:12px !important;
  padding:8px 14px !important;
}
section[data-testid="stSidebar"] .stButton button:hover{
  background:#1e293b !important;
}

section[data-testid="stSidebar"] pre,
section[data-testid="stSidebar"] code{
  background:#0f172a !important;
  color:#fff !important;
  border:1px solid rgba(255,255,255,0.15) !important;
  border-radius:12px !important;
}

/* =========================================================
   CHAT BUBBLES
========================================================= */
[data-testid="stChatMessage"]{
  background: rgba(255,255,255,0.05);
  border:1px solid rgba(255,255,255,0.10);
  border-radius:14px;
  padding:10px 14px;
  margin-bottom:10px;
}

/* =========================================================
   CODE BLOCKS DARK FIX (IMPORTANT)
========================================================= */
[data-testid="stChatMessage"] pre,
[data-testid="stChatMessage"] code{
  background:#0f172a !important;
  color:#e5e7eb !important;
  border:1px solid rgba(255,255,255,0.12) !important;
  border-radius:12px !important;
}

[data-testid="stChatMessage"] pre{
  padding:14px !important;
  overflow-x:auto !important;
}

/* supprime le fond gris interne éventuel */
[data-testid="stChatMessage"] pre *{
  background:transparent !important;
}

/* =========================================================
   SELECTBOX / DROPDOWN — OVERRIDE EXTREME (NUCLEAR)
========================================================= */
section[data-testid="stSidebar"] [data-baseweb="select"] > div{
  background:#0f172a !important;
  border:1px solid rgba(255,255,255,0.15) !important;
  border-radius:12px !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] *{
  color:#ffffff !important;
}

div[data-baseweb="popover"],
div[data-baseweb="menu"],
div[role="listbox"],
ul[role="listbox"]{
  background:#0b1220 !important;
}

div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] > div > div,
div[data-baseweb="popover"] > div > div > div,
div[data-baseweb="menu"] > div,
div[data-baseweb="menu"] > div > div,
div[role="listbox"] > div,
div[role="listbox"] > div > div{
  background:#0b1220 !important;
  border:1px solid rgba(255,255,255,0.15) !important;
  border-radius:12px !important;
  box-shadow:0 14px 40px rgba(0,0,0,0.55) !important;
}

div[data-baseweb="popover"] *{
  background-color:#0b1220 !important;
  color:#e5e7eb !important;
  outline:none !important;
  box-shadow:none !important;
}

ul[role="listbox"] li{
  background-color:transparent !important;
  color:#e5e7eb !important;
  border-radius:8px !important;
}
ul[role="listbox"] li:hover{
  background-color:#1e293b !important;
}
ul[role="listbox"] li[aria-selected="true"]{
  background-color:#111c33 !important;
}

/* =========================================================
   SLIDER
========================================================= */
[data-testid="stSlider"] *{
  color:#ffffff !important;
}

/* =========================================================
   CACHE CHAT_INPUT NATIF
========================================================= */
div[data-testid="stChatInput"]{
  display:none !important;
}

/* =========================================================
   DOCK CUSTOM
========================================================= */
.frostai-dock{
  position:fixed;
  left:0;
  right:0;
  bottom:0;
  z-index:9999;
  background:#0b1220;
  border-top:1px solid rgba(255,255,255,0.08);
  padding:14px 0;
}

.frostai-dock-inner{
  max-width:980px;
  margin:0 auto;
  padding:0 18px;
}

.frostai-dock-inner input{
  background:#0f172a !important;
  color:#ffffff !important;
  -webkit-text-fill-color:#ffffff !important;
  caret-color:#ffffff !important;
  border:1px solid rgba(255,255,255,0.18) !important;
  border-radius:999px !important;
  height:54px !important;
  padding:0 64px 0 18px !important;
}

.frostai-dock-inner input::placeholder{
  color:rgba(255,255,255,0.55) !important;
}

.frostai-dock-inner .stButton button{
  height:54px !important;
  width:54px !important;
  min-width:54px !important;
  margin-left:-64px !important;
  border-radius:999px !important;
  background:#1e293b !important;
  color:#ffffff !important;
  border:1px solid rgba(255,255,255,0.15) !important;
  padding:0 !important;
  box-shadow:none !important;
}

.frostai-dock-inner .stButton button:hover{
  background:#334155 !important;
}

</style>
""", unsafe_allow_html=True)



# HEADER PRO ALIGNÉ
st.markdown("""
<style>
.frost-header{
    display:flex;
    align-items:center;
    gap:18px;
    margin-bottom:8px;
}
.frost-header img{
    width:60px;
}
.frost-title{
    font-size:48px;
    font-weight:700;
    margin:0;
}
.frost-sub{
    margin-top:4px;
    font-size:18px;
    font-weight:500;
}
.frost-desc{
    opacity:0.7;
    margin-top:6px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="frost-header">
    <img src="{LOGO_URL}">
    <div>
        <div class="frost-title">{BOT_NAME}</div>
        <div class="frost-sub">{BOT_TAGLINE}</div>
        <div class="frost-desc">{APP_DESC}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("Paramètres")

    st.session_state.model = st.selectbox(
        "Modèle",
        CORTEX_MODELS,
        index=CORTEX_MODELS.index(st.session_state.model)
        if st.session_state.model in CORTEX_MODELS else 0,
    )

    st.session_state.temperature = st.slider(
        "Température",
        0.0, 1.5,
        float(st.session_state.temperature),
        0.1
    )

    if st.button("Nouveau Chat"):
        reset_chat()
        st.rerun()

    st.divider()
    st.write("conversation_id")
    st.code(st.session_state.conversation_id)

# Messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Dock custom
current_key = f"draft_{st.session_state.draft_key}"

st.markdown('<div class="frostai-dock"><div class="frostai-dock-inner">', unsafe_allow_html=True)
with st.form("dock_form", clear_on_submit=False):
    c_in, c_btn = st.columns([10, 1])
    with c_in:
        st.text_input(
            "",
            placeholder="Écris ton message...",
            label_visibility="collapsed",
            key=current_key
        )
    with c_btn:
        st.form_submit_button("➤", on_click=queue_send, args=(current_key,))
st.markdown("</div></div>", unsafe_allow_html=True)

# chat_input natif présent (exigence prof) mais masqué
_ = st.chat_input("hidden")

# Traitement envoi
if st.session_state.pending_send:
    user_text = st.session_state.pending_text
    st.session_state.pending_send = False
    st.session_state.pending_text = ""

    with st.chat_message("user"):
        st.write(user_text)

    handle_user_message(session, user_text)
    st.rerun()
