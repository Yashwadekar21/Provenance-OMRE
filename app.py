import streamlit as st

from provenance import db
from provenance.dashboards import ceo, employee, project_head
from provenance.ui import alert, apply_styles, sidebar


def login_screen():
    st.markdown(
        """
        <div class="landing-shell">
          <div class="landing-kicker">Organizational intelligence platform</div>
          <div class="landing-title">Remember the <span>why</span><br>behind every decision.</div>
          <div class="landing-copy">
            Provenance connects documents, decisions, people, and dependencies so teams can
            understand organizational history before they act.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    feature_columns = st.columns(3)
    features = [
        ("Decision memory", "Capture the rationale, alternatives, owners, and approvals behind important choices."),
        ("Evidence-first AI", "Ask natural-language questions and receive answers grounded in authorized project sources."),
        ("Connected context", "Trace relationships between projects, documents, technologies, risks, and decisions."),
    ]
    for column, (title, copy) in zip(feature_columns, features):
        with column:
            st.markdown(f"<div class='landing-card'><h4>{title}</h4><p>{copy}</p></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    auth_column, intro_column = st.columns([1, 1.25], gap="large")
    with intro_column:
        st.markdown(
            """
            <div class="landing-card">
              <div class="landing-kicker">Built for every level</div>
              <h3>One source of organizational truth</h3>
              <p>Employees contribute knowledge, project heads govern decisions, and executives see
              the cross-project picture—without bypassing access controls.</p>
              <p><strong>Employee</strong> · contribute and discover<br>
              <strong>Project Head</strong> · review and connect<br>
              <strong>CEO</strong> · understand and steer</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with auth_column:
        st.markdown("<div class='auth-panel'>", unsafe_allow_html=True)
        login, register = st.tabs(["Sign in", "Create account"])
        with login:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Enter Provenance", type="primary", width="stretch"):
                user = db.authenticate(email, password)
                if user:
                    st.session_state.update(authenticated=True, user_id=user["id"])
                    db.log_event(user["id"], "login", "User signed in.")
                    st.rerun()
                alert("Invalid email or password.", "error")
            st.caption("Demo: alice.employee@provenance.local / Password123!")
        with register:
            name = st.text_input("Full name", key="registration_name")
            email = st.text_input("Registration email", key="registration_email")
            password = st.text_input("Registration password", type="password", key="registration_password")
            role = st.selectbox("Role", ["employee", "project_head", "ceo"], key="registration_role")
            if st.button("Create account", width="stretch"):
                try:
                    db.register_user(name, email, password, role)
                    alert("Account created. Please sign in.", "success")
                except ValueError as exc:
                    alert(str(exc), "error")
        st.markdown("</div>", unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="PROVENANCE", page_icon="🧭", layout="wide")
    apply_styles()
    db.init_db()
    if not st.session_state.get("authenticated"):
        login_screen()
        return
    connection = db.connect()
    row = connection.execute("SELECT * FROM users WHERE id=?", (st.session_state["user_id"],)).fetchone()
    connection.close()
    if not row:
        st.session_state.clear()
        login_screen()
        return
    user = dict(row)
    options = {
        "employee": ["My Workspace"],
        "project_head": ["Project Head Dashboard"],
        "ceo": ["Executive Overview"],
    }[user["role"]]
    sidebar(user, options)
    if user["role"] == "employee":
        employee(user)
    elif user["role"] == "project_head":
        project_head(user)
    else:
        ceo(user)


if __name__ == "__main__":
    main()
