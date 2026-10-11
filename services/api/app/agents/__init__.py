DEFAULT_AGENTS = [
    {"id": "hr", "name": "Harper", "role": "hr", "purpose": "Answer employee policy questions with document citations.", "tools": ["read_policy"], "source": "", "source_ids": [], "status": "idle"},
    {"id": "finance", "name": "Finley", "role": "finance", "purpose": "Inspect assigned invoices, duplicates, and overdue balances.", "tools": ["analyze_invoices"], "source": "", "source_ids": [], "status": "idle"},
    {"id": "support", "name": "Scout", "role": "support", "purpose": "Draft replies grounded in assigned support knowledge.", "tools": ["draft_support_reply"], "source": "", "source_ids": [], "status": "idle"},
    {"id": "security", "name": "Sentinel", "role": "security", "purpose": "Enforce tool permissions and block unsafe action proposals.", "tools": ["inspect_permissions"], "source": "", "source_ids": [], "status": "idle"},
    {"id": "optimizer", "name": "Orbit", "role": "optimizer", "purpose": "Measure queue performance and propose approved scheduling changes.", "tools": ["measure_scheduler"], "source": "", "source_ids": [], "status": "idle"},
]

ROLE_TOOLS = {"hr": {"read_policy", "read_knowledge"}, "finance": {"analyze_invoices", "read_knowledge"}, "support": {"draft_support_reply", "read_knowledge"}, "custom": {"read_knowledge"}, "security": {"inspect_permissions"}, "optimizer": {"measure_scheduler"}}
