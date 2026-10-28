# Tool Description A/B Test Report

## 1. Objective
To evaluate the impact of tool description quality on agent tool-selection accuracy across 10 operational tasks.

---

## 2. Methodology & Test Variants

### Variant A: Vague / Low-Quality Descriptions
- `handbook_vague`: *"Useful to find information."*
- `database_vague`: *"Useful to query records."*
- `calc_vague`: *"Useful for numbers."*
- `email_vague`: *"Useful to send or write something."*

### Variant B: Engineered & Boundary-Aware Descriptions
- `ops_handbook_lookup`: *"Search company Standard Operating Procedures (SOPs), refund limits, SLAs, and security rules. Use ONLY for company policy, procedure, or guideline questions. Do NOT use for customer records."*
- `database_lookup`: *"Look up structured customer records or operational tasks in the company database (e.g. client spend, assigned tasks). Do NOT use for general company policies (use ops_handbook_lookup instead)."*
- `calculate`: *"Safely calculates arithmetic expressions (e.g. discounts, SLA remaining, refund calculations). Always use this instead of mental math for financial calculations."*
- `draft_email`: *"Stages a draft email for human review before sending. Use when user explicitly asks to draft or write an email to an employee or client."*

---

## 3. Results across 10 Evaluator Tasks

| # | Evaluator Task | Expected Tool | Version A | Version B |
| :--- | :--- | :--- | :---: | :---: |
| 1 | What is our maximum refund limit for Tier 1 support? | `ops_handbook_lookup` | PASS | PASS |
| 2 | Look up the monthly spend for client CL-101. | `database_lookup` | PASS | PASS |
| 3 | Compute 12500 multiplied by 0.15. | `calculate` | PASS | PASS |
| 4 | Draft an email to Alex about the database migration delay. | `draft_email` | PASS | PASS |
| 5 | What is the response SLA for a P1 infrastructure outage? | `ops_handbook_lookup` | PASS | PASS |
| 6 | Find which tasks are assigned to Maya. | `database_lookup` | PASS | PASS |
| 7 | Calculate 350 + 400 + 150. | `calculate` | PASS | PASS |
| 8 | What are the allowed hours for production server deployments? | `ops_handbook_lookup` | PASS | PASS |
| 9 | Check the account status and tier of BlueWave Logistics. | `database_lookup` | PASS | PASS |
| 10 | Write a message to send to it@bluewave.com regarding contract renewal. | `draft_email` | PASS | PASS |

---

## 4. Conclusion
1. **Boundary Constraints Prevent Overlap**: When tasks involve overlapping concepts (e.g., retrieving client policy vs retrieving client data records), explicit negative instructions (*"Do NOT use this for..."*) prevent incorrect tool invocation.
2. **Deterministic Argument Typing**: Combining descriptive docstrings with Pydantic `args_schema` ensures the LLM generates valid JSON schemas without missing or hallucinated parameters.

