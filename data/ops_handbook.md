# Operations Handbook & Standard Operating Procedures (SOP)

## SOP-001: Refund and Credit Approval Limits
- Tier 1 Support: Can issue refunds up to $50 without prior approval.
- Operations Lead: Can approve refunds between $51 and $500.
- Operations Director (or VP of Finance): Must approve any refund or credit exceeding $500.
- All refunds above $1,000 require a documented incident report and explicit sign-off from Finance.

## SOP-002: Infrastructure Incident Escalation
- P1 (Critical Outage affecting > 50% users):
  - Notify the on-call Site Reliability Engineer (SRE) immediately via PagerDuty.
  - SRE has a 5-minute response SLA.
  - Incident Commander role must be assigned within 15 minutes.
  - Executive status page must be updated every 30 minutes.
- P2 (Major Degradation affecting < 50% users):
  - Response SLA is 15 minutes.
  - Updates posted every 60 minutes.
- P3 (Minor issue/bug): Handled during standard business hours (9 AM - 5 PM EST).

## SOP-003: Server Deployment & Rollback Protocol
- Production deployments can only take place Tuesday through Thursday between 10:00 AM and 3:00 PM UTC.
- Deployments require a green CI/CD pipeline and approval from at least two code reviewers.
- In case of deployment failure or error rate spike > 1%, the automated canary rollback triggers immediately.
- Manual rollback command: `deployctl rollback --service <service_name> --to-version <previous_tag>`.

## SOP-004: Client Data Access & Security
- Customer PII (Personally Identifiable Information) must never be exported to unencrypted spreadsheets or third-party tools.
- Read access to customer database records requires active SSO authentication with multi-factor authentication (MFA).
- Any suspected data breach must be reported to security@company.internal within 1 hour of discovery.

