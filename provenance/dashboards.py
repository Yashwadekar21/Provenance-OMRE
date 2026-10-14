import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import db, knowledge
from .ui import alert, metric, sources


def assistant(user, title):
    st.subheader(title)
    question = st.text_input("Ask about authorized organizational knowledge", key=f"question_{user['id']}_{title}")
    if st.button("Ask question", key=f"ask_{user['id']}_{title}"):
        response, citations = knowledge.answer(question, user)
        st.write(response)
        sources(citations)


def graph_view(user, projects, key_prefix):
    st.subheader("Authorized knowledge graph")
    options = [{"id": None, "name": "All authorized projects"}] + projects
    selected = st.selectbox(
        "Project scope",
        options,
        format_func=lambda item: item["name"],
        key=f"{key_prefix}_graph_project",
    )
    snapshot = knowledge.graph_snapshot(user, selected["id"])
    st.caption(f"Graph source: {snapshot['backend']}. Only authorized project relationships are shown.")
    if not snapshot["nodes"]:
        st.info("No graph relationships are available for this scope yet.")
        return
    positions = {
        node["id"]: (
            index % 3,
            -(index // 3),
        )
        for index, node in enumerate(snapshot["nodes"])
    }
    edge_x, edge_y = [], []
    for edge in snapshot["edges"]:
        start, end = positions[edge["source"]], positions[edge["target"]]
        edge_x.extend([start[0], end[0], None])
        edge_y.extend([start[1], end[1], None])
    node_x = [positions[node["id"]][0] for node in snapshot["nodes"]]
    node_y = [positions[node["id"]][1] for node in snapshot["nodes"]]
    colors = {"Project": "#315ee8", "Document": "#16a36b", "Decision": "#d97706"}
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines", line={"color": "#cbd5e1", "width": 1},
        hoverinfo="skip",
    ))
    figure.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=[node["label"] for node in snapshot["nodes"]],
        textposition="bottom center",
        marker={
            "size": 20,
            "color": [colors.get(node["type"], "#64748b") for node in snapshot["nodes"]],
        },
        customdata=[node["type"] for node in snapshot["nodes"]],
        hovertemplate="%{text}<br>Type: %{customdata}<extra></extra>",
    ))
    figure.update_layout(
        height=460,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        xaxis={"visible": False},
        yaxis={"visible": False},
        showlegend=False,
    )
    st.plotly_chart(figure, width="stretch", key=f"{key_prefix}_graph_chart")
    st.subheader("Impact analysis")
    impact_rows = [
        {
            "entity": node["label"],
            "type": node["type"],
            "connected_relationships": sum(
                1 for edge in snapshot["edges"] if node["id"] in (edge["source"], edge["target"])
            ),
        }
        for node in snapshot["nodes"]
    ]
    st.dataframe(
        pd.DataFrame(impact_rows).sort_values("connected_relationships", ascending=False),
        width="stretch",
    )


def employee(user):
    projects = db.user_projects(user["id"])
    decisions = db.user_decisions(user["id"])
    notices = db.notifications(user["id"])
    st.title("Employee Workspace")
    columns = st.columns(4)
    for column, values in zip(columns, [
        ("Assigned Projects", len(projects), "Project membership"),
        ("Pending Actions", 3, "Open review items"),
        ("Recent Decisions", len(decisions), "Within scope"),
        ("Notifications", len(notices), "Unread and recent"),
    ]):
        with column:
            metric(*values)
    tabs = st.tabs(["My Projects", "AI Assistant", "Documents", "Decision History", "Submit Knowledge", "Notifications"])
    with tabs[0]:
        st.dataframe(pd.DataFrame(projects)[["name", "description", "status"]] if projects else pd.DataFrame(), width="stretch")
    with tabs[1]:
        assistant(user, "AI Assistant")
    with tabs[2]:
        if not projects:
            st.info("You need project access before uploading documents.")
        else:
            project = st.selectbox("Project", projects, format_func=lambda item: item["name"], key="employee_upload_project")
            uploaded = st.file_uploader("Upload PDF, DOCX, TXT, or CSV", type=["pdf", "docx", "txt", "csv"])
            if uploaded and st.button("Process document"):
                try:
                    knowledge.process_upload(user, project["id"], uploaded)
                    alert("Document processed and indexed.", "success")
                    st.rerun()
                except ValueError as exc:
                    alert(str(exc), "error")
            documents = db.project_documents(project["id"])
            st.dataframe(pd.DataFrame(documents)[["title", "file_type", "status", "version"]] if documents else pd.DataFrame(), width="stretch")
            if documents:
                selected_document = st.selectbox(
                    "Document maintenance",
                    documents,
                    format_func=lambda item: item["title"],
                    key="employee_document_maintenance",
                )
                maintenance = st.radio(
                    "Action",
                    ["Reprocess", "Delete"],
                    horizontal=True,
                    key="employee_document_action",
                )
                if st.button("Run document action", key="employee_document_action_button"):
                    try:
                        if maintenance == "Delete":
                            knowledge.delete_document(user, selected_document["id"])
                            alert("Document and its indexed evidence were deleted.", "success")
                        else:
                            knowledge.reprocess_document(user, selected_document["id"])
                            alert("Document indexes were rebuilt.", "success")
                        st.rerun()
                    except ValueError as exc:
                        alert(str(exc), "error")
    with tabs[3]:
        st.dataframe(pd.DataFrame(decisions)[["title", "project_name", "status", "updated_at"]] if decisions else pd.DataFrame(), width="stretch")
    with tabs[4]:
        project = st.selectbox("Proposal project", projects, format_func=lambda item: item["name"], key="proposal_project") if projects else None
        title = st.text_input("Decision title")
        description = st.text_area("Proposal description")
        rationale = st.text_area("Rationale")
        if st.button("Submit proposal") and project:
            if not title.strip() or not description.strip():
                alert("Title and description are required.", "error")
            else:
                connection = db.connect()
                connection.execute(
                    """INSERT INTO decisions(project_id,title,description,rationale,alternatives,status,
                    proposer_id,owner_id,created_at,updated_at,evidence) VALUES(?,?,?,?,?,'Proposed',?,?,?,?,?)""",
                    (project["id"], title.strip(), description.strip(), rationale.strip(), "To be reviewed", user["id"], user["id"], db.now(), db.now(), "Employee proposal"),
                )
                connection.commit()
                connection.close()
                db.log_event(user["id"], "decision_proposal", title.strip())
                alert("Proposal submitted for review.", "success")
    with tabs[5]:
        for notice in notices:
            st.write(f"- {notice['message']} ({notice['notification_type']})")


def project_head(user):
    projects = db.user_projects(user["id"])
    st.title("Project Head Dashboard")
    columns = st.columns(5)
    for column, values in zip(columns, [
        ("Managed Projects", len(projects), "Under your authority"),
        ("Recorded Decisions", sum(len(db.project_decisions(p["id"])) for p in projects), "Portfolio"),
        ("Pending Approvals", 5, "Needs review"),
        ("Open Risks", 2, "High-impact items"),
        ("Conflicts", 1, "Unresolved"),
    ]):
        with column:
            metric(*values)
    tabs = st.tabs(["Project Overview", "Decision Management", "Impact Analyzer", "Knowledge Graph", "Conflict Center", "Knowledge Gaps", "Team Memory"])
    with tabs[0]:
        for project in projects:
            with st.expander(f"{project['name']} — {project['status']}"):
                st.write(project["description"])
                st.table(pd.DataFrame(db.project_members(project["id"])))
                st.dataframe(pd.DataFrame(db.project_documents(project["id"])), width="stretch")
    with tabs[1]:
        decisions = [item for project in projects for item in db.project_decisions(project["id"])]
        for decision in decisions:
            st.markdown(f"**{decision['title']}** — {decision['status']}")
            st.write(decision["description"])
            action = st.selectbox("Review action", ["No action", "Approved", "Under Review", "Rejected"], key=f"review_{decision['id']}")
            if action != "No action" and st.button("Save review", key=f"save_{decision['id']}"):
                connection = db.connect()
                connection.execute("UPDATE decisions SET status=?,approver_id=?,updated_at=? WHERE id=?", (action, user["id"], db.now(), decision["id"]))
                connection.commit()
                connection.close()
                alert("Decision review saved.", "success")
                st.rerun()
    with tabs[2]:
        st.subheader("Project impact analysis")
        if not projects:
            st.info("No managed projects are available for analysis.")
        else:
            impact_project = st.selectbox(
                "Project to analyze",
                projects,
                format_func=lambda item: item["name"],
                key="project_head_impact_project",
            )
            try:
                impact = knowledge.impact_analysis(user, impact_project["id"])
                metric_columns = st.columns(4)
                for column, values in zip(metric_columns, [
                    ("Documents", impact["documents"], "Authorized project sources"),
                    ("Decisions", impact["decisions"], "Recorded decisions"),
                    ("Relationships", impact["relationships"], f"{impact['backend']} graph"),
                    ("Affected entities", len(impact["affected_entities"]), "Potentially impacted"),
                ]):
                    with column:
                        metric(*values)
                if impact["affected_entities"]:
                    st.dataframe(pd.DataFrame(impact["affected_entities"]), width="stretch")
                else:
                    st.info("No connected entities are available for this project yet.")
            except ValueError as exc:
                alert(str(exc), "error")
    with tabs[3]:
        graph_view(user, projects, "project_head")
    with tabs[4]:
        intelligence = db.executive_intelligence(user)
        st.subheader("Conflict and risk signals")
        conflicts = [
            item for item in intelligence["risks"]
            if item["priority"] == "High"
        ]
        st.dataframe(pd.DataFrame(conflicts), width="stretch")
    with tabs[5]:
        intelligence = db.executive_intelligence(user)
        st.subheader("Knowledge gaps")
        st.dataframe(pd.DataFrame(intelligence["knowledge_gaps"]), width="stretch")
    with tabs[6]:
        assistant(user, "Team Memory")


def ceo(user):
    summary = db.org_summary()
    st.title("Executive Overview")
    columns = st.columns(5)
    for column, values in zip(columns, [
        ("Total Projects", summary["projects"], "All portfolios"),
        ("Recorded Decisions", summary["decisions"], "Organization"),
        ("Awaiting Approval", summary["waiting_approval"], "Executive review"),
        ("High Priority Risks", summary["high_priority_risks"], "Leadership review"),
        ("Knowledge Health", f"{summary['knowledge_health']}%", "Completeness"),
    ]):
        with column:
            metric(*values)
    tabs = st.tabs(["Executive AI Assistant", "Strategic Decisions", "Cross-Project Analysis", "Risk Dashboard", "Knowledge Graph", "Knowledge Health", "Decision Timeline", "Reports"])
    with tabs[0]:
        assistant(user, "Executive AI Assistant")
    with tabs[1]:
        connection = db.connect()
        rows = connection.execute("SELECT d.title,p.name AS project_name,d.status,d.updated_at FROM decisions d JOIN projects p ON p.id=d.project_id ORDER BY d.updated_at DESC").fetchall()
        connection.close()
        st.dataframe(pd.DataFrame([dict(row) for row in rows]), width="stretch")
    with tabs[2]:
        intelligence = db.executive_intelligence(user)
        st.subheader("Shared topics across authorized projects")
        st.dataframe(pd.DataFrame(intelligence["shared_topics"]), width="stretch")
    with tabs[3]:
        intelligence = db.executive_intelligence(user)
        st.subheader("Live risk register")
        st.dataframe(pd.DataFrame(intelligence["risks"]), width="stretch")
    with tabs[4]:
        graph_view(user, db.user_projects(user["id"]), "ceo")
    with tabs[5]:
        st.metric("Knowledge completeness", f"{summary['knowledge_health']}%")
        st.write(
            f"Missing approval record: {summary['missing_approval']} | "
            f"Missing owner: {summary['missing_owner']} | "
            f"Documents indexed: {summary['documents']}"
        )
    with tabs[6]:
        timeline = db.executive_report()["timeline"]
        st.dataframe(pd.DataFrame(timeline), width="stretch")
    with tabs[7]:
        report = db.executive_report()
        st.download_button(
            "Download executive decision report",
            data=pd.DataFrame(report["decisions"]).to_csv(index=False),
            file_name="provenance-executive-decisions.csv",
            mime="text/csv",
            width="stretch",
        )
        st.dataframe(pd.DataFrame(report["decisions"]), width="stretch")
