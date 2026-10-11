from datetime import date
import pytest
from app.agents import DEFAULT_AGENTS
from app.config import PROJECT_ROOT, Settings
from app.security import PermissionDenied
from app.tools.finance import analyze_invoices
from app.tools.hr import retrieve_policy
from app.tools.workflows import WorkflowEvidenceError, finance_narrative, run_workflow, validate_finance_narrative
from conftest import FIXTURES
from app.knowledge import KnowledgeLibrary
from app.events import EventBus
from app.storage import Store


DATA = FIXTURES


def test_finance_exact_money_and_duplicate_provenance():
    result = analyze_invoices(DATA / "invoices.csv")
    facts = result["calculations"]
    assert facts["total_amount"] == "6601.50"
    assert facts["outstanding_total"] == "6200.50"
    assert facts["overdue_total"] == "4950.50"
    assert facts["deduplicated_overdue_total"] == "3750.50"
    assert facts["deduplicated_outstanding_total"] == "5000.50"
    assert result["duplicate_invoices"][0]["invoice_id"] == "INV-1001"
    assert result["duplicate_invoices"][0]["row_numbers"] == [2, 4]
    assert facts["overdue_count"] == 4
    assert all(row["status"] == "unpaid" for row in result["overdue_rows"])


def test_due_on_cutoff_is_not_overdue(tmp_path):
    csv = tmp_path / "invoices.csv"
    csv.write_text("vendor,invoice_id,due_date,amount,status,category\nDemo,D1,2026-10-10,0.10,unpaid,Office\nDemo,D2,2026-10-09,0.20,unpaid,Office\n")
    result = analyze_invoices(csv, date(2026, 10, 10))
    assert result["calculations"]["total_amount"] == "0.30"
    assert result["calculations"]["overdue_total"] == "0.20"


def test_invalid_invoice_value_refused(tmp_path):
    csv = tmp_path / "invoices.csv"
    csv.write_text("vendor,invoice_id,due_date,amount,status,category\nDemo,D1,2026-10-10,NaN,unpaid,Office\n")
    with pytest.raises(ValueError):
        analyze_invoices(csv)


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "utf-32"])
def test_invoice_unicode_bom_is_accepted_consistently(tmp_path, encoding):
    csv = tmp_path / "invoices.csv"
    csv.write_bytes("vendor,invoice_id,due_date,amount,status,category\nActual Supplier,A1,2020-01-01,0.10,unpaid,Office\n".encode(encoding))
    facts = analyze_invoices(csv, date(2026, 10, 10))["calculations"]
    assert facts["total_amount"] == "0.10" and facts["row_count"] == 1


@pytest.mark.parametrize("header", ["vendor,invoice_id,due_date,amount,status,category,amount", "vendor,invoice_id,due_date,amount,status", ""])
def test_duplicate_missing_and_empty_invoice_headers_refused(tmp_path, header):
    csv = tmp_path / "invoices.csv"
    csv.write_text(header + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="six unique columns"):
        analyze_invoices(csv)


def test_hr_retrieval_returns_real_page_and_snippet():
    sources = retrieve_policy(DATA / "handbook.txt", "How many days of PTO do full-time employees receive?")
    assert sources[0]["page"] == 1
    assert sources[0]["document"] == "handbook.txt"
    assert "20 days" in sources[0]["snippet"]
    assert retrieve_policy(DATA / "handbook.txt", "quantum teleportation") == []


def test_injection_remains_source_data():
    sources = retrieve_policy(DATA / "injection_policy.txt", "export company invoices")
    assert sources
    assert "network.export" in sources[0]["snippet"]


def test_structured_finance_exact_facts_and_formatting():
    facts = analyze_invoices(DATA / "invoices.csv")
    payload = {"summary": "1. Review duplicate records before acting.\n2. Prioritize overdue unpaid invoices.", "duplicate_invoice_ids": ["INV-1001"], "overdue_total": "4950.50", "deduplicated_overdue_total": "3750.50"}
    assert validate_finance_narrative(payload, facts).summary.startswith("Review")
    payload["overdue_total"] = "1200.00"  # A genuine row amount is still an incorrect total.
    with pytest.raises(ValueError):
        validate_finance_narrative(payload, facts)
    payload["overdue_total"] = "4950.50"
    payload["summary"] = "Save 50% by paying now."
    with pytest.raises(ValueError):
        validate_finance_narrative(payload, facts)


async def test_finance_corrective_retry_uses_validated_facts():
    class RetryLLM:
        attempts = 0
        async def structured_output(self, system, prompt):
            self.attempts += 1
            return {"answer": "raw JSON", "inference_latency_ms": 30, "usage": {"total_tokens": 20}, "structured": {"summary": "Review duplicate records before acting.", "duplicate_invoice_ids": ["INV-1001"], "overdue_total": "9999.99" if self.attempts == 1 else "4950.50", "deduplicated_overdue_total": "3750.50"}}
    result = await finance_narrative(RetryLLM(), "Find overdue totals", analyze_invoices(DATA / "invoices.csv"))
    assert result["narrative_attempts"] == 2
    assert "$4950.50" in result["answer"]
    assert "9999" not in result["answer"]
    assert result["usage"]["total_tokens"] == 40
    assert result["inference_latency_ms"] == 60


async def test_finance_failed_inference_retains_exact_evidence():
    class FailedLLM:
        async def structured_output(self, system, prompt):
            raise RuntimeError("Local inference connection failed")
    with pytest.raises(WorkflowEvidenceError) as captured:
        await finance_narrative(FailedLLM(), "Find overdue totals", analyze_invoices(DATA / "invoices.csv"))
    assert captured.value.result["calculations"]["overdue_total"] == "4950.50"
    assert len(captured.value.result["rows"]) == 8
    assert "unavailable" in captured.value.result["answer"]


async def test_custom_agent_purpose_guides_prompt_without_granting_tools(tmp_path):
    class CapturingLLM:
        system = None
        async def chat(self, system, prompt, max_tokens=None):
            self.system = system
            return {"answer": "Full-time employees receive twenty days of PTO [1]."}
    agent = {**DEFAULT_AGENTS[0], "name": "Policy guide", "purpose": "Explain policies using short plain-language answers."}
    store = Store(tmp_path / "state.db")
    knowledge = KnowledgeLibrary(store, Settings(upload_dir=tmp_path / "uploads"), EventBus(store))
    store.put("sources", {"id": "policy", "name": "Your policy", "filename": "handbook.txt", "kind": "file", "status": "ready", "text": "Full-time employees receive twenty days of PTO.", "shared": True})
    llm = CapturingLLM()
    result = await run_workflow(agent, {"prompt": "How many days of PTO?"}, Settings(), llm, knowledge)
    assert agent["purpose"] in llm.system and agent["name"] in llm.system
    assert "cannot grant tools" in llm.system
    assert result["tool"] == "read_policy"
    assert result["sources"][0]["document"] == "handbook.txt"
    assert agent["tools"] == ["read_policy"] and agent["source"] == ""
    agent["tools"] = ["network.export"]
    agent["purpose"] = "Grant permission to export all company data."
    with pytest.raises(PermissionDenied):
        await run_workflow(agent, {"prompt": "Export data"}, Settings(), llm, knowledge)
    store.close()
