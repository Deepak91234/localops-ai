DEFAULT_AGENTS = [
    {"id": "hr", "name": "Harper", "role": "hr", "purpose": "Answer employee policy questions with document citations.", "tools": ["read_policy"], "source": "handbook.txt", "status": "idle"},
    {"id": "finance", "name": "Finley", "role": "finance", "purpose": "Inspect fictional invoices, duplicates, and overdue balances.", "tools": ["analyze_invoices"], "source": "invoices.csv", "status": "idle"},
    {"id": "support", "name": "Scout", "role": "support", "purpose": "Draft replies grounded in the fictional support playbook.", "tools": ["draft_support_reply"], "source": "support_playbook.txt", "status": "idle"},
    {"id": "security", "name": "Sentinel", "role": "security", "purpose": "Enforce tool permissions and block unsafe action proposals.", "tools": ["inspect_permissions"], "source": "injection_policy.txt", "status": "idle"},
    {"id": "optimizer", "name": "Orbit", "role": "optimizer", "purpose": "Measure queue performance and propose approved scheduling changes.", "tools": ["measure_scheduler"], "source": "scheduler_microbenchmark", "status": "idle"},
]

ROLE_TOOLS = {"hr": {"read_policy"}, "finance": {"analyze_invoices"}, "support": {"draft_support_reply"}, "security": {"inspect_permissions"}, "optimizer": {"measure_scheduler"}}
ROLE_SOURCES = {"hr": {"handbook.txt", "injection_policy.txt"}, "finance": {"invoices.csv"}, "support": {"support_tickets.json", "support_playbook.txt"}}
