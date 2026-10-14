import streamlit as st


def metric(title, value, details):
    st.markdown(
        f"<div class='metric-card'><div class='metric-title'>{title}</div>"
        f"<div class='metric-value'>{value}</div><div class='metric-details'>{details}</div></div>",
        unsafe_allow_html=True,
    )


def alert(message, kind="info"):
    colors = {"info": "#dfe9ff", "success": "#eaf9ed", "warning": "#fff1d6", "error": "#ffe0e0"}
    st.markdown(
        f"<div style='padding:.8rem 1rem;border-radius:.85rem;background:{colors.get(kind, colors['info'])};"
        f"border-left:4px solid #2b6df6;margin:.6rem 0'>{message}</div>",
        unsafe_allow_html=True,
    )


def sources(items):
    seen = set()
    for item in items:
        key = (item.get("title"), item.get("project"), item.get("source"))
        if key in seen:
            continue
        seen.add(key)
        st.markdown(
            f"<div class='source-box'><strong>{item['title']}</strong><br>"
            f"Project: {item['project']}<br>Source: {item['source']}</div>",
            unsafe_allow_html=True,
        )


def apply_styles():
    st.markdown(
        """<style>
        .stApp{background:linear-gradient(180deg,#f7f9ff 0%,#edf2ff 100%);color:#0f172a}
        div[data-testid='stSidebar']{background:#111827}
        .landing-shell{padding:2rem 0 1rem}
        .landing-kicker{color:#315ee8;font-size:.8rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase}
        .landing-title{font-size:clamp(2.5rem,6vw,5.2rem);line-height:1.02;font-weight:800;
          letter-spacing:-.06em;color:#101b4d;margin:.5rem 0 1rem}
        .landing-title span{color:#7658e8}
        .landing-copy{font-size:1.1rem;line-height:1.7;color:#53627a;max-width:40rem}
        .landing-card{background:#ffffffd9;border:1px solid #dce4f5;border-radius:1.2rem;padding:1.3rem;
          box-shadow:0 18px 45px #1d2c6f12;height:100%}
        .landing-card h4{margin:.4rem 0;color:#172554}
        .landing-card p{color:#64748b;line-height:1.55}
        .auth-panel{background:#fff;border:1px solid #dce4f5;border-radius:1.2rem;padding:1.4rem;
          box-shadow:0 18px 45px #1d2c6f14}
        .metric-card{background:linear-gradient(180deg,#fff,#f7f9ff);border:1px solid #e2e8f0;
          border-radius:1rem;padding:1rem;box-shadow:0 12px 22px #0f172a0d;margin-bottom:1rem}
        .metric-title{color:#5e6d8a;font-size:.82rem;text-transform:uppercase;letter-spacing:.08em}
        .metric-value{font-size:2rem;font-weight:700;color:#0f172a;margin:.2rem 0}
        .metric-details{color:#53627a;font-size:.8rem}
        .source-box{border:1px solid #cbd5e1;background:#f8fafc;padding:.75rem;border-radius:.8rem;margin-bottom:.6rem}
        .role-badge{background:linear-gradient(135deg,#2d5cf5,#8f6cf8);color:#fff;padding:.45rem .75rem;
          border-radius:999px;font-size:.78rem;font-weight:600;display:inline-block}
        </style>""",
        unsafe_allow_html=True,
    )


def sidebar(user, options):
    st.sidebar.title("PROVENANCE")
    st.sidebar.caption(f"Signed in as {user['full_name']}")
    st.sidebar.markdown(f"<div class='role-badge'>{user['role'].replace('_',' ').title()}</div>", unsafe_allow_html=True)
    return st.sidebar.radio("Navigation", options)
