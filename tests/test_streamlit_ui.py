"""Interaction-level smoke coverage for the Stockout Investigation UI."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py"
EXAMPLES = [
    "Why did stockouts increase?",
    "Which suppliers caused delays?",
    "Which stores are at highest risk?",
    "Which products have low days of cover?",
    "Which promotion created unexpected demand?",
]


def _app() -> AppTest:
    app = AppTest.from_file(str(APP_PATH))
    app.run(timeout=30)
    assert not app.exception
    return app


def _visible_text(app: AppTest) -> str:
    element_groups = (
        app.markdown,
        app.caption,
        app.title,
        app.error,
        app.warning,
        app.info,
        app.success,
    )
    return "\n".join(
        str(element.value)
        for group in element_groups
        for element in group
        if getattr(element, "value", None) is not None
    )


def _run_question(app: AppTest, question: str = "Why did stockouts increase?") -> AppTest:
    app.text_area[0].set_value(question).run(timeout=30)
    app.button[-1].click().run(timeout=30)
    assert not app.exception
    return app


def test_question_composer_has_examples_and_populates_main_input() -> None:
    app = _app()

    assert [button.label for button in app.button[:-1]] == EXAMPLES
    assert app.text_area[0].placeholder == "Ask anything about stockouts…"
    assert app.text_area[0].value == ""

    app.button[3].click().run(timeout=30)

    assert app.text_area[0].value == EXAMPLES[3]


def test_governed_result_renders_kpis_loading_citations_drafts_and_audit() -> None:
    app = _app()
    app.button[0].click().run(timeout=30)
    _run_question(app, app.text_area[0].value)

    assert app.text_area[0].value == EXAMPLES[0]
    assert [(metric.label, metric.value) for metric in app.metric] == [
        ("Affected stores", "4"),
        ("Affected products", "2"),
        ("Estimated lost sales", "$1,685"),
        ("Minimum days of cover", "0.5"),
    ]
    assert len(app.status) == 1
    assert app.status[0].label == "Governed answer ready"
    assert [step.value for step in app.status[0].markdown] == [
        "Checking access",
        "Reading stockout data",
        "Reading inventory",
        "Checking supplier and promotion signals",
        "Retrieving SOP",
    ]

    rendered = _visible_text(app)
    assert EXAMPLES[0] in rendered
    assert "SOP citations" in rendered
    assert "Draft only — human approval required" in rendered
    assert "9 append-only audit record(s) captured" in rendered


def test_readonly_role_renders_access_denied_and_audit_state() -> None:
    app = _app()
    app.selectbox[0].set_value("Read-only (no operational access)").run(timeout=30)
    _run_question(app)

    assert [error.value for error in app.error] == ["Access denied"]
    assert "1 append-only audit record(s) captured" in _visible_text(app)


def test_store_manager_result_is_limited_to_selected_store() -> None:
    app = _app()
    app.selectbox[0].set_value("Store Manager (store-scoped)").run(timeout=30)
    app.selectbox[2].set_value("MEL-001").run(timeout=30)
    _run_question(app)

    assert [(metric.label, metric.value) for metric in app.metric][:3] == [
        ("Affected stores", "1"),
        ("Affected products", "1"),
        ("Estimated lost sales", "$620"),
    ]
    rendered = _visible_text(app)
    assert "MEL-001" in rendered
    assert "MEL-002" not in rendered
    assert "SYD-001" not in rendered


def test_empty_and_generic_error_states_are_clear() -> None:
    app = _app()
    app.selectbox[2].set_value("vitamins").run(timeout=30)
    _run_question(app)

    assert not app.metric
    assert "No stockout signal in this scope" in _visible_text(app)
    assert "8 append-only audit record(s) captured" in _visible_text(app)

    app = _app()
    app.session_state["run"] = {"error": True}
    app.run(timeout=30)

    assert [error.value for error in app.error] == ["We could not complete this investigation."]
    assert "No internal details are shown here." in _visible_text(app)
