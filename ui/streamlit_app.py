"""Modern Streamlit UI for the governed Stockout Investigation Agent.

This module is intentionally a presentation layer. Every finding, KPI,
citation, draft and refusal comes from ``StockoutInvestigationAgent`` and its
seven allowlisted tools. It does not run SQL, expose credentials, or take an
external action.

Run from the repository root:

    python -m streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.governed_rag import GovernedRetriever  # noqa: E402
from scripts.stockout_agent import (  # noqa: E402
    AgentContext,
    InvestigationRequest,
    StockoutInvestigationAgent,
)
from scripts.stockout_agent.contracts import AuditRecord  # noqa: E402
from scripts.stockout_agent.fixtures import MEL_STORES  # noqa: E402
from scripts.stockout_agent.gateway import (  # noqa: E402
    InMemoryAuditSink,
    InMemoryDraftSink,
)

# Display metadata only — this UI introduces no data sources or business rules.
ROLES = {
    "Supply Chain Analyst (national)": "PHARMARETAIL_SUPPLY_CHAIN_ANALYST",
    "AI App (national service)": "PHARMARETAIL_AI_APP",
    "Admin (national)": "PHARMARETAIL_ADMIN",
    "Area Manager (region-scoped)": "PHARMARETAIL_AREA_MANAGER",
    "Store Manager (store-scoped)": "PHARMARETAIL_STORE_MANAGER",
    "Read-only (no operational access)": "PHARMARETAIL_READONLY",
}
REGIONS = {"Melbourne": "MELBOURNE", "Sydney": "SYDNEY"}
STORES = {"MELBOURNE": list(MEL_STORES), "SYDNEY": ["SYD-001"]}
CATEGORIES = ["pain relief", "vitamins"]
EXAMPLE_QUESTIONS = (
    "Why did stockouts increase?",
    "Which suppliers caused delays?",
    "Which stores are at highest risk?",
    "Which products have low days of cover?",
    "Which promotion created unexpected demand?",
)
WORKFLOW_STEPS = (
    "Checking access",
    "Reading stockout data",
    "Reading inventory",
    "Checking supplier and promotion signals",
    "Retrieving SOP",
    "Generating governed answer",
)
CONFIDENCE = {
    "LOW": ("High confidence", "#0b6b45", "#e8f6ef"),
    "MEDIUM": ("Medium confidence", "#8a5a00", "#fff4d6"),
    "HIGH": ("Low confidence", "#a13232", "#fdecec"),
}

st.set_page_config(
    page_title="PharmaRetail AI Control Tower",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root {
        --pr-ink: #162033;
        --pr-muted: #667085;
        --pr-line: #e6eaf0;
        --pr-surface: #ffffff;
        --pr-canvas: #f6f8fb;
        --pr-brand: #2859c5;
        --pr-brand-dark: #1e469e;
      }
      .stApp { background: var(--pr-canvas); color: var(--pr-ink); }
      .block-container { max-width: 1440px; padding-top: 2.25rem; padding-bottom: 3rem; }
      section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--pr-line);
      }
      section[data-testid="stSidebar"] > div { padding-top: 1.25rem; }
      h1, h2, h3, h4, h5 { color: var(--pr-ink); letter-spacing: -0.025em; }
      h1 { font-weight: 680; }
      p, .stCaption { color: var(--pr-muted); }
      div[data-testid="stMetric"] {
        background: var(--pr-surface);
        border: 1px solid var(--pr-line);
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);
      }
      div[data-testid="stMetric"] label {
        color: var(--pr-muted);
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--pr-ink);
        font-weight: 680;
      }
      div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--pr-surface);
        border-color: var(--pr-line) !important;
        border-radius: 14px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);
      }
      .pr-eyebrow {
        color: var(--pr-brand);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
      }
      .pr-subtitle { color: var(--pr-muted); font-size: 1rem; margin: 0; max-width: 760px; }
      .pr-question-label { color: var(--pr-muted); font-size: 0.82rem; font-weight: 650; }
      .pr-answer-question {
        color: var(--pr-ink);
        font-size: 1.06rem;
        font-weight: 600;
        line-height: 1.55;
        margin: 0;
      }
      .pr-pill {
        display: inline-block;
        background: #edf3ff;
        border: 1px solid #dce7ff;
        border-radius: 999px;
        color: #254c9e;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        padding: 0.22rem 0.56rem;
      }
      .pr-draft-tag {
        display: inline-block;
        background: #fff4d6;
        border: 1px solid #f3dd9c;
        border-radius: 7px;
        color: #7a5200;
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.3rem 0.58rem;
      }
      .pr-citation {
        background: #f7f9fc;
        border-left: 3px solid var(--pr-brand);
        border-radius: 6px;
        color: #344054;
        font-size: 0.86rem;
        margin: 0.42rem 0;
        padding: 0.55rem 0.7rem;
      }
      .pr-empty {
        background: #fbfcfe;
        border: 1px dashed #cfd8e6;
        border-radius: 14px;
        padding: 2.3rem 1.6rem;
        text-align: center;
      }
      div.stButton > button[kind="primary"] {
        min-height: 3rem;
        border-radius: 10px;
        font-weight: 650;
      }
      div.stButton > button[kind="secondary"] {
        border-color: #d7deea;
        border-radius: 10px;
        color: #344054;
      }
      [data-testid="stTextArea"] textarea {
        border-radius: 12px;
        border-color: #cbd5e1;
        font-size: 1rem;
        line-height: 1.45;
      }
      [data-testid="stTextArea"] textarea:focus { border-color: var(--pr-brand); }
      @media (max-width: 760px) {
        .block-container { padding: 1rem 0.75rem 2rem; }
        div[data-testid="stMetric"] { margin-bottom: 0.5rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Agent wiring (cached; offline governed fixtures — no credentials in the UI)
# ---------------------------------------------------------------------------
@st.cache_resource
def _retriever() -> GovernedRetriever:
    return GovernedRetriever.from_corpus(REPO_ROOT / "sop")


def _build_agent() -> tuple[StockoutInvestigationAgent, InMemoryAuditSink, InMemoryDraftSink]:
    audit_sink = InMemoryAuditSink()
    draft_sink = InMemoryDraftSink()
    agent = StockoutInvestigationAgent(
        retriever=_retriever(), audit_sink=audit_sink, draft_sink=draft_sink
    )
    return agent, audit_sink, draft_sink


def _finding(result_dict: dict, code: str) -> dict | None:
    return next((finding for finding in result_dict["findings"] if finding["code"] == code), None)


def _log_ui_read(agent, request, context, sequence: int, tool_name: str, result) -> None:
    """Log the two display-only KPI reads through the existing audit tool."""
    agent.toolset.log_ai_interaction(
        AuditRecord(
            query_hash=request.query_hash,
            sequence=sequence,
            actor=context.user,
            actor_role=context.role,
            tool_name=tool_name,
            action_name="UI_DISPLAY_READ",
            object_name="STREAMLIT_KPI_PANEL",
            row_count=result.row_count,
            outcome=result.outcome,
            refused=False,
            refusal_reason=None,
            citation_count=len(result.citations),
            event_timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )


def _set_question(question: str) -> None:
    """Populate the main question field from a ready-made example."""
    st.session_state["question_input"] = question


def _render_citation(reference: str, icon: str) -> None:
    """Render a provenance reference as display text, never as a live action."""
    st.caption(f"{icon} {reference}")


def _render_signal_card(title: str, icon: str, finding: dict | None, empty_copy: str) -> None:
    """Render one evidence category without deriving any new business result."""
    with st.container(border=True):
        st.markdown(f"##### {icon} {title}")
        if finding is None:
            st.caption(empty_copy)
            return
        st.write(finding["statement"])
        metrics = finding.get("metrics", {})
        if metrics:
            st.caption(
                " · ".join(f"{key.replace('_', ' ')}: {value}" for key, value in metrics.items())
            )


def _render_audit_status(run: dict, result: dict) -> None:
    """Show audit state after every terminal response state."""
    st.markdown("### Audit log status")
    with st.container(border=True):
        audit_count = run["audit_count"]
        draft_count = run["draft_count"]
        status = f"{audit_count} append-only audit record(s) captured"
        if draft_count:
            status += f" · {draft_count} action draft(s) remain pending human approval"
        else:
            status += " · no external action was taken"
        st.success(status, icon="🧾")
        st.caption(f"Query hash: {result['query_hash'][:12]}…")
        with st.expander("View audit trail"):
            audit_frame = pd.DataFrame(run["audit_rows"])
            audit_columns = [
                "sequence",
                "tool_name",
                "action_name",
                "object_name",
                "row_count",
                "outcome",
            ]
            if audit_frame.empty:
                st.caption("No audit rows available.")
            else:
                st.dataframe(
                    audit_frame[[column for column in audit_columns if column in audit_frame]],
                    width="stretch",
                    hide_index=True,
                )


# ---------------------------------------------------------------------------
# Sidebar — scope and filters only
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🏥 PharmaRetail")
    st.caption("AI Control Tower · Governed stockout investigations")
    st.divider()
    st.markdown("#### Investigation scope")

    role_label = st.selectbox("Role", list(ROLES.keys()), index=0)
    role = ROLES[role_label]
    region_label = st.selectbox("Region", list(REGIONS.keys()), index=0)
    region = REGIONS[region_label]

    allowed_stores: tuple[str, ...] = ()
    allowed_regions: tuple[str, ...] = ()
    if role == "PHARMARETAIL_STORE_MANAGER":
        assigned_store = st.selectbox(
            "Assigned store (scoped)",
            STORES[region],
            help="The investigation passes this store as the only permitted store scope.",
        )
        allowed_stores = (assigned_store,)
        st.caption(f"Data visibility is limited to **{assigned_store}**.")
    elif role == "PHARMARETAIL_AREA_MANAGER":
        allowed_regions = (region,)
        st.caption(f"Data visibility is limited to **{region_label}**.")
    elif role == "PHARMARETAIL_READONLY":
        st.info("This role cannot run operational investigations.", icon="🔒")

    st.markdown("#### Investigation window")
    category = st.selectbox("Category", CATEGORIES, index=0)
    window_days = st.slider("Window (days)", min_value=7, max_value=28, value=14, step=7)
    as_of = st.date_input("As-of date", value=date(2026, 2, 2))
    st.divider()
    st.caption(
        "Allowlisted tools only · role and store scope enforced · cited evidence · "
        "append-only audit"
    )


# ---------------------------------------------------------------------------
# Main question composer
# ---------------------------------------------------------------------------
if "question_input" not in st.session_state:
    st.session_state["question_input"] = ""

st.markdown('<div class="pr-eyebrow">Governed decision support</div>', unsafe_allow_html=True)
st.title("Stockout Investigation")
st.markdown(
    '<p class="pr-subtitle">Ask a question, then review a fully cited investigation. '
    "The agent reads only approved sources and drafts recommendations for human approval.</p>",
    unsafe_allow_html=True,
)

st.markdown("### What would you like to investigate?")
st.caption("Start with an example or write a question in your own words.")
example_columns = st.columns(5, gap="small")
for index, example in enumerate(EXAMPLE_QUESTIONS):
    with example_columns[index]:
        st.button(
            example,
            key=f"example_question_{index}",
            on_click=_set_question,
            args=(example,),
            width="stretch",
        )

question_column, run_column = st.columns([6, 1.35], gap="medium")
with question_column:
    question = st.text_area(
        "Investigation question",
        key="question_input",
        placeholder="Ask anything about stockouts…",
        height=126,
        label_visibility="collapsed",
    )
with run_column:
    st.markdown("<div style='height: 0.25rem'></div>", unsafe_allow_html=True)
    run_clicked = st.button(
        "Run investigation",
        type="primary",
        width="stretch",
    )
    st.caption("Governed and audited")


# ---------------------------------------------------------------------------
# Run the investigation — the only place the agent is invoked
# ---------------------------------------------------------------------------
if run_clicked:
    if not question.strip():
        st.session_state["run"] = {"input_error": True}
    else:
        try:
            with st.status("Starting governed investigation", expanded=True) as workflow:
                for workflow_step in WORKFLOW_STEPS[:-1]:
                    workflow.write(workflow_step)
                workflow.update(label=WORKFLOW_STEPS[-1], state="running", expanded=True)

                agent, audit_sink, draft_sink = _build_agent()
                request = InvestigationRequest(
                    question=question.strip(),
                    region=region,
                    category=category,
                    window_days=window_days,
                    as_of_date=as_of,
                )
                context = AgentContext(
                    user="UI_DEMO_USER",
                    role=role,
                    allowed_store_ids=allowed_stores,
                    allowed_regions=allowed_regions,
                )
                result = agent.investigate(request, context)

                # Keep the existing audited, allowlisted reads that power the requested KPI cards.
                kpi_payload: dict | None = None
                inventory_payload: dict | None = None
                if not result.refused:
                    kpi = agent.toolset.get_stockout_metrics(context, request)
                    _log_ui_read(agent, request, context, 90, "get_stockout_metrics", kpi)
                    inventory = agent.toolset.get_inventory_position(context, request)
                    _log_ui_read(agent, request, context, 91, "get_inventory_position", inventory)
                    kpi_payload = dict(kpi.payload) if kpi.outcome == "OK" else None
                    inventory_payload = (
                        dict(inventory.payload) if inventory.outcome == "OK" else None
                    )

                st.session_state["run"] = {
                    "result": result.to_dict(),
                    "kpi": kpi_payload,
                    "inventory": inventory_payload,
                    "audit_count": len(audit_sink.records),
                    "audit_rows": [record.to_dict() for record in audit_sink.records],
                    "draft_count": len(draft_sink.records),
                }
                workflow.update(label="Governed answer ready", state="complete", expanded=False)
        except Exception:  # noqa: BLE001 - never surface internal details or credentials
            st.session_state["run"] = {"error": True}


# ---------------------------------------------------------------------------
# Terminal states: initial / input / error / refused / empty / results
# ---------------------------------------------------------------------------
run = st.session_state.get("run")

if run is None:
    st.markdown("<div class='pr-empty'>", unsafe_allow_html=True)
    st.markdown("#### Begin with a question")
    st.markdown(
        "Use the examples above or ask about suppliers, stores, products, inventory, "
        "or promotions. "
        "Your role and data scope are set in the left panel."
    )
    st.caption("No investigation has run yet — this is an empty workspace, not an error.")
    st.markdown("</div>", unsafe_allow_html=True)

elif run.get("input_error"):
    with st.container(border=True):
        st.warning("Add a question before running an investigation.", icon="✍️")
        st.caption("Choose an example above or enter a question in the main text area.")

elif run.get("error"):
    with st.container(border=True):
        st.error("We could not complete this investigation.", icon="🛑")
        st.caption(
            "No internal details are shown here. Review the scope and question, then try again."
        )

else:
    res = run["result"]
    st.markdown("### Investigation response")
    with st.container(border=True):
        st.caption("QUESTION")
        st.write(res["request"]["question"])
        st.caption(
            f"Scope: {res['request']['region'].title()} · {res['request']['category'].title()} · "
            f"{res['request']['window_days']} days ending {res['request']['as_of_date']}"
        )

    if res["refused"] and res["refusal_reason"] == "ACCESS_DENIED":
        with st.container(border=True):
            st.error("Access denied", icon="🔒")
            st.markdown(
                "This read-only role is not authorised to run stockout investigations. "
                "No governed data was returned."
            )
            st.caption("The refusal was recorded in the append-only audit log.")
        _render_audit_status(run, res)

    elif res["refused"]:
        with st.container(border=True):
            st.warning(
                f"Request refused — {res['refusal_reason'].replace('_', ' ').title()}",
                icon="⚠️",
            )
            st.caption("The agent blocked this request before data access. The refusal is audited.")
        _render_audit_status(run, res)

    else:
        spike = _finding(res, "STOCKOUT_SPIKE")
        if spike is None:
            st.markdown("<div class='pr-empty'>", unsafe_allow_html=True)
            st.markdown("#### No stockout signal in this scope")
            st.info(res["summary"], icon="ℹ️")
            st.caption("No actions were drafted because the governed evidence did not support one.")
            st.markdown("</div>", unsafe_allow_html=True)

            policy = _finding(res, "POLICY_GUIDANCE")
            if policy and policy["citations"]:
                st.markdown("### SOP citations")
                with st.container(border=True):
                    for citation in policy["citations"]:
                        _render_citation(citation["reference"], "📄")
            _render_audit_status(run, res)

        else:
            label, color, background = CONFIDENCE.get(res["uncertainty"], CONFIDENCE["MEDIUM"])
            with st.container(border=True):
                st.markdown("#### Root cause summary")
                st.markdown(
                    f'<span class="pr-pill" style="background:{background};color:{color};">'
                    f"{label}</span>",
                    unsafe_allow_html=True,
                )
                st.write(res["summary"])

            kpi = run.get("kpi") or {}
            inventory = run.get("inventory") or {}
            st.markdown("### Investigation KPIs")
            kpi_columns = st.columns(4, gap="medium")
            kpi_columns[0].metric("Affected stores", len(kpi.get("affected_stores", [])))
            kpi_columns[1].metric("Affected products", len(kpi.get("affected_skus", [])))
            kpi_columns[2].metric(
                "Estimated lost sales", f"${kpi.get('estimated_lost_sales', 0):,.0f}"
            )
            kpi_columns[3].metric(
                "Minimum days of cover",
                inventory.get("min_days_of_cover", "—"),
                help=(
                    "Lowest days-of-cover across the permitted scope. Threshold: "
                    f"{inventory.get('cover_threshold_days', 2.0)} days."
                ),
            )

            left_column, right_column = st.columns([1.15, 1], gap="medium")
            with left_column:
                st.markdown("### Root cause detail")
                with st.container(border=True):
                    dominant = (
                        str(kpi.get("dominant_root_cause", "UNKNOWN")).replace("_", " ").title()
                    )
                    st.markdown(f"**Dominant driver:** {dominant}")
                    st.caption(
                        f"Stockout events: {spike['metrics']['prior_events']} prior → "
                        f"{spike['metrics']['current_events']} current"
                    )
                    severity = kpi.get("severity_breakdown", {})
                    if severity:
                        st.caption("Current-window event severity")
                        st.bar_chart(
                            pd.DataFrame(
                                {"events": list(severity.values())}, index=list(severity.keys())
                            ),
                            height=175,
                            color="#2859c5",
                        )

                st.markdown("### Signals")
                _render_signal_card(
                    "Supplier signal",
                    "🚚",
                    _finding(res, "SUPPLIER_OTIF_DECLINE"),
                    "No material supplier delay signal was found in the permitted scope.",
                )
                _render_signal_card(
                    "Promotion signal",
                    "🏷️",
                    _finding(res, "PROMO_UNDERFORECAST"),
                    "No unexpected promotion-demand signal was found in the permitted scope.",
                )
                _render_signal_card(
                    "Inventory signal",
                    "📦",
                    _finding(res, "LOW_DAYS_OF_COVER"),
                    "No low-cover inventory signal was found in the permitted scope.",
                )

            with right_column:
                st.markdown("### SOP citations")
                with st.container(border=True):
                    policy_references = list(
                        dict.fromkeys(
                            citation["reference"]
                            for citation in res["citations"]
                            if citation["kind"] == "POLICY"
                        )
                    )
                    if policy_references:
                        for reference in policy_references:
                            _render_citation(reference, "📄")
                    else:
                        st.caption("No SOP citation was returned for this result.")
                    st.caption(f"Citation coverage: {res['citation_coverage'] * 100:.0f}%")

                st.markdown("### Recommended actions")
                with st.container(border=True):
                    st.markdown(
                        '<span class="pr-draft-tag">Draft only — human approval required</span>',
                        unsafe_allow_html=True,
                    )
                    actions = res["recommended_actions"]
                    if actions:
                        for action in actions:
                            st.markdown(f"#### {action['title']}")
                            st.write(action["body"])
                            st.caption(
                                f"Priority: {action['priority']} · "
                                f"Target: {action['target_system']} · "
                                f"Status: {action['status']}"
                            )
                            action_references = action.get("citations", [])
                            if action_references:
                                st.caption(
                                    "Evidence: "
                                    + " · ".join(
                                        citation["reference"] for citation in action_references
                                    )
                                )
                    else:
                        st.info("No actions were drafted for this result.", icon="ℹ️")

                with st.expander("Governed data sources"):
                    data_references = list(
                        dict.fromkeys(
                            citation["reference"]
                            for citation in res["citations"]
                            if citation["kind"] == "DATA"
                        )
                    )
                    if data_references:
                        for reference in data_references:
                            _render_citation(reference, "🗄️")
                    else:
                        st.caption("No governed data source citation was returned.")

            _render_audit_status(run, res)
