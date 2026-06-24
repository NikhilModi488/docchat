"""
generate_sample_pdfs.py
=======================
Utility that writes 5 realistic multi-page sample PDFs into ./data so the demo
works out-of-the-box. Run once:

    python generate_sample_pdfs.py

Requires `reportlab` (already in requirements.txt). The content is fictional
company documentation — handy, hallucination-testable material for the RAG demo.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# (filename, title, list-of-paragraphs)
DOCUMENTS: list[tuple[str, str, list[str]]] = [
    (
        "HR_Policy.pdf",
        "Acme Corp — Human Resources Policy",
        [
            "Working Hours: Standard working hours are 9:00 AM to 6:00 PM, Monday through Friday, with a one-hour lunch break. Remote employees may adopt flexible hours provided they overlap at least four core hours (11:00 AM–3:00 PM) with their team.",
            "Leave Policy: Full-time employees accrue 20 days of paid annual leave per year, plus 12 days of sick leave. Annual leave must be requested at least two weeks in advance through the HR portal. Unused leave of up to 5 days may be carried over to the next calendar year.",
            "Parental Leave: New parents are entitled to 16 weeks of paid parental leave, which must be taken within 12 months of the child's birth or adoption.",
            "Code of Conduct: Employees are expected to act with integrity and professionalism. Harassment, discrimination, and conflicts of interest are strictly prohibited and may result in termination.",
            "Performance Reviews: Formal performance reviews are conducted twice a year, in June and December. Ratings range from 1 (Needs Improvement) to 5 (Outstanding) and influence annual compensation adjustments.",
        ],
    ),
    (
        "Employee_Handbook.pdf",
        "Acme Corp — Employee Handbook",
        [
            "Onboarding: All new hires complete a two-week onboarding program covering company values, security training, and role-specific tooling. A dedicated buddy is assigned for the first 30 days.",
            "Expense Reimbursement: Business expenses must be submitted within 30 days with valid receipts. Approved categories include travel, client meals (up to $75 per person), and professional development.",
            "Equipment: Each employee receives a company laptop and a $500 annual home-office stipend. IT support is available via the internal helpdesk between 8:00 AM and 8:00 PM.",
            "Travel Policy: Economy class is standard for flights under 6 hours; business class is permitted for longer flights with manager approval. Hotel bookings should not exceed $200 per night without prior authorization.",
            "Security: Employees must enable multi-factor authentication on all corporate accounts and must never share passwords. Lost or stolen devices must be reported to IT within 24 hours.",
        ],
    ),
    (
        "Product_Spec.pdf",
        "Acme Cloud Platform — Product Specification",
        [
            "Overview: Acme Cloud is a managed platform-as-a-service offering autoscaling compute, managed databases, and an integrated observability suite.",
            "Compute Tiers: The platform offers three tiers — Starter (2 vCPU, 4 GB RAM), Pro (8 vCPU, 32 GB RAM), and Enterprise (custom). Autoscaling responds to CPU utilisation thresholds configurable between 50% and 90%.",
            "Databases: Managed PostgreSQL and Redis are available with automated daily backups retained for 30 days. Point-in-time recovery is supported on the Enterprise tier.",
            "SLA: Acme Cloud guarantees 99.95% uptime for Pro and Enterprise tiers. Service credits of 10% are issued for each 0.1% below the SLA in a billing month.",
            "Security & Compliance: The platform is SOC 2 Type II certified and supports data residency in the US, EU, and APAC regions. All data is encrypted at rest with AES-256 and in transit with TLS 1.3.",
        ],
    ),
    (
        "Finance_FAQ.pdf",
        "Acme Corp — Finance FAQ",
        [
            "Payroll: Salaries are paid on the last business day of each month via direct deposit. Payslips are available in the finance portal by the 25th.",
            "Invoicing: Vendor invoices are processed on net-30 terms. Invoices must reference a valid purchase order number to be approved.",
            "Budgets: Departmental budgets are set annually in Q4 for the following fiscal year, which runs from April 1 to March 31.",
            "Stock Options: Eligible employees receive stock options vesting over four years with a one-year cliff. The strike price is set at the fair market value on the grant date.",
            "Tax Documents: Annual tax statements are issued by January 31. Employees can update tax withholding preferences at any time through the finance portal.",
        ],
    ),
    (
        "IT_Security_Guide.pdf",
        "Acme Corp — IT Security Guide",
        [
            "Password Policy: Passwords must be at least 14 characters and include upper- and lower-case letters, numbers, and symbols. Passwords expire every 90 days and cannot be reused within 12 cycles.",
            "Phishing: Employees must report suspicious emails to security@acme.example using the 'Report Phishing' button. Never click links or open attachments from unknown senders.",
            "Data Classification: Data is classified as Public, Internal, Confidential, or Restricted. Restricted data (e.g., customer PII) must never be stored on personal devices or unapproved cloud services.",
            "Incident Response: Suspected security incidents must be reported within one hour. The incident response team follows a four-phase process: identify, contain, eradicate, and recover.",
            "VPN: Remote access to internal systems requires the corporate VPN with multi-factor authentication. Split tunneling is disabled to ensure all traffic is inspected.",
        ],
    ),
]


def build_pdf(filename: str, title: str, paragraphs: list[str]) -> None:
    """Render a single PDF with a title page heading and body paragraphs."""
    path = DATA_DIR / filename
    doc = SimpleDocTemplate(str(path), pagesize=LETTER)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 18)]
    for para in paragraphs:
        story.append(Paragraph(para, styles["BodyText"]))
        story.append(Spacer(1, 12))
    doc.build(story)
    print(f"  [ok] wrote {path.relative_to(path.parent.parent)}")


def main() -> None:
    print("Generating sample PDFs into ./data ...")
    for filename, title, paragraphs in DOCUMENTS:
        build_pdf(filename, title, paragraphs)
    print("Done. 5 sample PDFs created.")


if __name__ == "__main__":
    main()
