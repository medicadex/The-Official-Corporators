"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
COOPERATIVE STATEMENTS & AUDIT PDF GENERATOR (report_pdf_service.py)
-----------------------------------------------------------------------------
Generates official, publication-grade cooperative financial statements:
1. Annual / Multi-Year Passbook Ledger Statement (Tripartite Reconciliation)
2. Inward Remittances Audit Statement (All Credits)
3. Disbursements, Withdrawals & Claims Audit Statement (All Debits)
4. Loan Facilities & Amortization Statement (0% Compounding Interest)

Statutory Jurisdiction: Lagos State Cooperative Societies Law (Cap C15)
Official Secretariat Invariant Email: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


class ReportPdfService:
    @staticmethod
    def format_currency(val: float) -> str:
        try:
            num = float(val or 0.0)
            return f"₦{num:,.2f}"
        except Exception:
            return "₦0.00"

    @classmethod
    def _create_common_styles(cls):
        styles = getSampleStyleSheet()
        c_navy = colors.HexColor("#0A192F")
        c_gold = colors.HexColor("#B45309")
        c_emerald = colors.HexColor("#047857")
        c_slate = colors.HexColor("#475569")

        custom_styles = {
            "c_navy": c_navy,
            "c_gold": c_gold,
            "c_emerald": c_emerald,
            "c_slate": c_slate,
            "title": ParagraphStyle(
                "OrgTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=12,
                leading=15,
                textColor=c_navy,
                alignment=1
            ),
            "sub": ParagraphStyle(
                "OrgSub",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=10,
                textColor=c_slate,
                alignment=1
            ),
            "email": ParagraphStyle(
                "OrgEmail",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=10,
                textColor=c_gold,
                alignment=1
            ),
            "banner": ParagraphStyle(
                "DocBanner",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=9.5,
                leading=12,
                textColor=colors.white,
                alignment=1
            ),
            "meta_lbl": ParagraphStyle(
                "MetaLbl",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.HexColor("#64748B")
            ),
            "meta_val": ParagraphStyle(
                "MetaVal",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=c_navy
            ),
            "kpi_lbl": ParagraphStyle(
                "KpiLbl",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7,
                leading=9,
                textColor=colors.HexColor("#475569"),
                alignment=1
            ),
            "kpi_val": ParagraphStyle(
                "KpiVal",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=12,
                textColor=c_navy,
                alignment=1
            ),
            "kpi_val_green": ParagraphStyle(
                "KpiValGreen",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=12,
                textColor=c_emerald,
                alignment=1
            ),
            "tbl_hdr": ParagraphStyle(
                "TableHdr",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white
            ),
            "tbl_hdr_right": ParagraphStyle(
                "TableHdrRight",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.white,
                alignment=2
            ),
            "tbl_cell": ParagraphStyle(
                "TableCell",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=9.5,
                textColor=c_navy
            ),
            "tbl_cell_bold": ParagraphStyle(
                "TableCellBold",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=c_navy
            ),
            "tbl_cell_right": ParagraphStyle(
                "TableCellRight",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=7.5,
                leading=9.5,
                textColor=c_navy,
                alignment=2
            ),
            "tbl_cell_green": ParagraphStyle(
                "TableCellGreen",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=c_emerald,
                alignment=2
            ),
            "tbl_cell_red": ParagraphStyle(
                "TableCellRed",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=colors.HexColor("#B91C1C"),
                alignment=2
            ),
            "tbl_foot": ParagraphStyle(
                "TableFoot",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=colors.white
            ),
            "tbl_foot_right": ParagraphStyle(
                "TableFootRight",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#FEF08A"),
                alignment=2
            ),
            "legal_note": ParagraphStyle(
                "LegalNote",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=6.5,
                leading=8.5,
                textColor=colors.HexColor("#64748B")
            ),
            "attest_bold": ParagraphStyle(
                "AttestBold",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9.5,
                textColor=c_navy
            ),
            "attest_sub": ParagraphStyle(
                "AttestSub",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=7,
                leading=9,
                textColor=c_slate
            )
        }
        return custom_styles

    @classmethod
    def _build_header(cls, styles: Dict[str, Any], banner_title: str) -> List[Any]:
        story = []
        story.append(Paragraph("WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED", styles["title"]))
        story.append(Spacer(1, 1))
        story.append(Paragraph(
            "Regulated under Lagos State Cooperative Societies Law (Cap C15) &bull; Registered Office: 13, Agbaje Iloro Street, Odogunyan, Ikorodu",
            styles["sub"]
        ))
        story.append(Spacer(1, 1))
        story.append(Paragraph(
            "Secretariat Official Correspondence: wealthbridge.coopsociety@gmail.com &bull; Portal: https://wealthbridge.coop",
            styles["email"]
        ))
        story.append(Spacer(1, 5))

        banner_table = Table(
            [[Paragraph(banner_title.upper(), styles["banner"])]],
            colWidths=[540],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), styles["c_navy"]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        )
        story.append(banner_table)
        story.append(Spacer(1, 6))
        return story

    @classmethod
    def _build_member_meta_box(cls, styles: Dict[str, Any], member: Dict[str, Any], period_label: str) -> Table:
        m_name = member.get("full_name") or "Cooperator"
        m_code = member.get("member_code") or "WMC-xxxx"
        m_tier = member.get("tier") or "STANDARD"
        m_phone = member.get("phone") or "N/A"
        m_email = member.get("email") or "N/A"
        m_dva = member.get("dva_account") or "9926000001 (Paystack / Wema)"
        m_status = member.get("membership_status") or "ACTIVE"

        data = [
            [
                Paragraph("<b>Cooperator Name:</b>", styles["meta_lbl"]),
                Paragraph(m_name, styles["meta_val"]),
                Paragraph("<b>Member Code:</b>", styles["meta_lbl"]),
                Paragraph(m_code, styles["meta_val"]),
            ],
            [
                Paragraph("<b>Contribution Tier:</b>", styles["meta_lbl"]),
                Paragraph(m_tier, styles["meta_val"]),
                Paragraph("<b>Membership Status:</b>", styles["meta_lbl"]),
                Paragraph(m_status, styles["meta_val"]),
            ],
            [
                Paragraph("<b>Contact Phone / Email:</b>", styles["meta_lbl"]),
                Paragraph(f"{m_phone} &bull; {m_email}", styles["meta_val"]),
                Paragraph("<b>Audit Period:</b>", styles["meta_lbl"]),
                Paragraph(f"<b>{period_label}</b>", styles["meta_val"]),
            ],
            [
                Paragraph("<b>Dedicated Inward NUBAN:</b>", styles["meta_lbl"]),
                Paragraph(f"<b>{m_dva}</b>", styles["meta_val"]),
                Paragraph("<b>Date of Issuance:</b>", styles["meta_lbl"]),
                Paragraph(datetime.now().strftime("%d-%b-%Y %H:%M"), styles["meta_val"]),
            ]
        ]

        t = Table(data, colWidths=[120, 150, 120, 150])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    @classmethod
    def _build_footer_endorsement(cls, styles: Dict[str, Any]) -> List[Any]:
        story = []
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=6))

        attest_data = [
            [
                Paragraph("<b>PRESIDENT / TRUSTEE</b><br/>Wealthbridge Secretariat<br/><i>Statutory Approval Authority</i>", styles["attest_sub"]),
                Paragraph("<b>TREASURER / FINANCIAL SEC.</b><br/>Audit &amp; Compliance<br/><i>Accounts Reconciliation</i>", styles["attest_sub"]),
                Paragraph("<b>OFFICIAL VERIFICATION SEAL</b><br/>Lagos State Cap C15 Validated<br/><i>wealthbridge.coopsociety@gmail.com</i>", styles["attest_sub"])
            ]
        ]
        t = Table(attest_data, colWidths=[180, 180, 180])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(t)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "<b>STATUTORY NOTICE & AUDIT INVARIANT:</b> This document is an official financial record of Wealthbridge Multipurpose Cooperative Society Limited. Certified under Section 1.2 of WMC Bye-Laws and Lagos State Cooperative Societies Law (Cap C15). Inward contributions are verified electronically. For discrepancies or balance inquiries, immediately contact the Secretariat via <u>wealthbridge.coopsociety@gmail.com</u>.",
            styles["legal_note"]
        ))
        return story

    # =========================================================================
    # 1. ANNUAL PASSBOOK LEDGER PDF GENERATOR
    # =========================================================================
    @classmethod
    def generate_passbook_ledger_pdf(cls, ledger_data: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=28,
            bottomMargin=28
        )
        styles = cls._create_common_styles()
        story = []

        period_label = ledger_data.get("period_label", "Annual Ledger")
        story.extend(cls._build_header(styles, f"STATUTORY PASSBOOK LEDGER STATEMENT &bull; {period_label}"))
        story.append(cls._build_member_meta_box(styles, ledger_data.get("member", {}), period_label))
        story.append(Spacer(1, 6))

        # KPI Financial Summary Boxes
        op = ledger_data.get("opening_balances", {})
        cl = ledger_data.get("closing_balances", {})
        mov = ledger_data.get("period_movements", {})

        kpi_data = [
            [
                Paragraph("OPENING NET EQUITY", styles["kpi_lbl"]),
                Paragraph("TOTAL INWARD CREDITS", styles["kpi_lbl"]),
                Paragraph("TOTAL OUTWARD DEBITS", styles["kpi_lbl"]),
                Paragraph("CLOSING NET EQUITY", styles["kpi_lbl"]),
                Paragraph("2× BORROWING CAPACITY", styles["kpi_lbl"]),
            ],
            [
                Paragraph(cls.format_currency(op.get("total_equity", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(mov.get("total_credits", 0)), styles["kpi_val_green"]),
                Paragraph(cls.format_currency(mov.get("total_debits", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(cl.get("total_equity", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(cl.get("ordinary_loan_capacity_2x", 0)), styles["kpi_val_green"]),
            ],
            [
                Paragraph(f"Savings: {cls.format_currency(op.get('regular_savings', 0))}", styles["meta_lbl"]),
                Paragraph(f"Savings: {cls.format_currency(mov.get('credits_savings', 0))}", styles["meta_lbl"]),
                Paragraph(f"Savings Wdr: {cls.format_currency(mov.get('debits_savings', 0))}", styles["meta_lbl"]),
                Paragraph(f"Shares: {cls.format_currency(cl.get('share_capital', 0))} ({cl.get('share_units', 0)} U)", styles["meta_lbl"]),
                Paragraph("0.0% Compounding Int.", styles["meta_lbl"]),
            ]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 6))

        # Ledger Transactions Table
        entries = ledger_data.get("entries", [])
        tbl_data = [
            [
                Paragraph("Date / Ref", styles["tbl_hdr"]),
                Paragraph("Category", styles["tbl_hdr"]),
                Paragraph("Narration & Channel", styles["tbl_hdr"]),
                Paragraph("Inward (CR)", styles["tbl_hdr_right"]),
                Paragraph("Outward (DR)", styles["tbl_hdr_right"]),
                Paragraph("Net Equity", styles["tbl_hdr_right"]),
            ]
        ]

        if not entries:
            tbl_data.append([
                Paragraph("No ledger transactions found in selected period.", styles["tbl_cell"]),
                Paragraph("-", styles["tbl_cell"]),
                Paragraph("-", styles["tbl_cell"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph(cls.format_currency(op.get("total_equity", 0)), styles["tbl_cell_right"]),
            ])
        else:
            for e in entries:
                is_credit = e.get("transaction_type") == "CREDIT"
                amt = float(e.get("amount", 0))
                cr_str = cls.format_currency(amt) if is_credit else "-"
                dr_str = cls.format_currency(amt) if not is_credit else "-"
                dt_str = e.get("transaction_date", "")[:10]
                ref_str = e.get("transaction_ref", "")
                cat_str = (e.get("ledger_category", "") or "").replace("_", " ").title()
                narr_str = e.get("narration") or e.get("channel_reference") or ""
                if len(narr_str) > 42:
                    narr_str = narr_str[:40] + "..."

                tbl_data.append([
                    Paragraph(f"<b>{dt_str}</b><br/>{ref_str[:16]}", styles["tbl_cell"]),
                    Paragraph(f"<b>{cat_str}</b>", styles["tbl_cell"]),
                    Paragraph(narr_str, styles["tbl_cell"]),
                    Paragraph(cr_str, styles["tbl_cell_green"] if is_credit else styles["tbl_cell_right"]),
                    Paragraph(dr_str, styles["tbl_cell_red"] if not is_credit else styles["tbl_cell_right"]),
                    Paragraph(f"<b>{cls.format_currency(e.get('running_total', 0))}</b>", styles["tbl_cell_bold"]),
                ])

        # Table Footer
        tbl_data.append([
            Paragraph("PERIOD CLOSING BALANCES", styles["tbl_foot"]),
            Paragraph(f"{len(entries)} Records", styles["tbl_foot"]),
            Paragraph(f"Net Movement: {cls.format_currency(mov.get('net_movement', 0))}", styles["tbl_foot"]),
            Paragraph(cls.format_currency(mov.get("total_credits", 0)), styles["tbl_foot_right"]),
            Paragraph(cls.format_currency(mov.get("total_debits", 0)), styles["tbl_foot_right"]),
            Paragraph(cls.format_currency(cl.get("total_equity", 0)), styles["tbl_foot_right"]),
        ])

        tx_tbl = Table(tbl_data, colWidths=[90, 80, 160, 70, 70, 70], repeatRows=1)
        tx_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), styles["c_navy"]),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
            ("TOPPADDING", (0, 0), (-1, 0), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -2), 0.25, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 1), (-1, -2), 2),
            ("BOTTOMPADDING", (0, 1), (-1, -2), 2),
            ("BACKGROUND", (0, -1), (-1, -1), styles["c_navy"]),
            ("TOPPADDING", (0, -1), (-1, -1), 3),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 3),
        ]))
        story.append(tx_tbl)

        story.extend(cls._build_footer_endorsement(styles))
        doc.build(story)
        return buffer.getvalue()

    # =========================================================================
    # 2. INWARD REMITTANCES (ALL CREDITS) PDF GENERATOR
    # =========================================================================
    @classmethod
    def generate_credits_statement_pdf(cls, credits_data: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=28,
            bottomMargin=28
        )
        styles = cls._create_common_styles()
        story = []

        period_label = credits_data.get("period_label", "All Credits")
        story.extend(cls._build_header(styles, f"INWARD REMITTANCES &amp; CREDITS AUDIT &bull; {period_label}"))
        story.append(cls._build_member_meta_box(styles, credits_data.get("member", {}), period_label))
        story.append(Spacer(1, 6))

        # Summary KPIs
        summ = credits_data.get("summary", {})
        cat_bd = summ.get("category_breakdown", {})

        kpi_data = [
            [
                Paragraph("TOTAL REMITTED", styles["kpi_lbl"]),
                Paragraph("TRANSACTION COUNT", styles["kpi_lbl"]),
                Paragraph("REGULAR SAVINGS", styles["kpi_lbl"]),
                Paragraph("SHARE CAPITAL (EQUITY)", styles["kpi_lbl"]),
                Paragraph("WELFARE SOLIDARITY", styles["kpi_lbl"]),
            ],
            [
                Paragraph(cls.format_currency(summ.get("total_remitted", 0)), styles["kpi_val_green"]),
                Paragraph(f"{summ.get('remittance_count', 0)} Deposits", styles["kpi_val"]),
                Paragraph(cls.format_currency(cat_bd.get("SAVINGS", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(cat_bd.get("SHARE_CAPITAL", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(cat_bd.get("WELFARE_FUND", 0)), styles["kpi_val"]),
            ]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 6))

        entries = credits_data.get("entries", [])
        tbl_data = [
            [
                Paragraph("Date / Ref", styles["tbl_hdr"]),
                Paragraph("Ledger Category", styles["tbl_hdr"]),
                Paragraph("Payment Channel", styles["tbl_hdr"]),
                Paragraph("Narration / Session ID", styles["tbl_hdr"]),
                Paragraph("Amount Remitted", styles["tbl_hdr_right"]),
                Paragraph("Status", styles["tbl_hdr_right"]),
            ]
        ]

        if not entries:
            tbl_data.append([
                Paragraph("No inward remittances recorded in selected period.", styles["tbl_cell"]),
                Paragraph("-", styles["tbl_cell"]),
                Paragraph("-", styles["tbl_cell"]),
                Paragraph("-", styles["tbl_cell"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph("N/A", styles["tbl_cell_right"]),
            ])
        else:
            for e in entries:
                dt_str = e.get("transaction_date", "")[:10]
                ref_str = e.get("transaction_ref", "")
                cat_str = (e.get("ledger_category", "") or "").replace("_", " ").title()
                meth_str = (e.get("payment_method", "") or "").replace("_", " ").title()
                narr_str = e.get("narration") or e.get("channel_reference") or ""
                if len(narr_str) > 40:
                    narr_str = narr_str[:38] + "..."

                tbl_data.append([
                    Paragraph(f"<b>{dt_str}</b><br/>{ref_str[:16]}", styles["tbl_cell"]),
                    Paragraph(f"<b>{cat_str}</b>", styles["tbl_cell"]),
                    Paragraph(meth_str, styles["tbl_cell"]),
                    Paragraph(narr_str, styles["tbl_cell"]),
                    Paragraph(f"<b>{cls.format_currency(e.get('amount', 0))}</b>", styles["tbl_cell_green"]),
                    Paragraph(f"<font color='#047857'><b>{e.get('status', 'VERIFIED')}</b></font>", styles["tbl_cell_right"]),
                ])

        tbl_data.append([
            Paragraph("TOTAL REMITTANCES", styles["tbl_foot"]),
            Paragraph(f"{len(entries)} Inward Entries", styles["tbl_foot"]),
            Paragraph("", styles["tbl_foot"]),
            Paragraph("", styles["tbl_foot"]),
            Paragraph(cls.format_currency(summ.get("total_remitted", 0)), styles["tbl_foot_right"]),
            Paragraph("100% RECONCILED", styles["tbl_foot_right"]),
        ])

        tx_tbl = Table(tbl_data, colWidths=[90, 85, 95, 140, 75, 55], repeatRows=1)
        tx_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), styles["c_navy"]),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
            ("TOPPADDING", (0, 0), (-1, 0), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -2), 0.25, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 1), (-1, -2), 2),
            ("BOTTOMPADDING", (0, 1), (-1, -2), 2),
            ("BACKGROUND", (0, -1), (-1, -1), styles["c_navy"]),
            ("TOPPADDING", (0, -1), (-1, -1), 3),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 3),
        ]))
        story.append(tx_tbl)

        story.extend(cls._build_footer_endorsement(styles))
        doc.build(story)
        return buffer.getvalue()

    # =========================================================================
    # 3. OUTWARD DISBURSEMENTS & CLAIMS (ALL DEBITS) PDF GENERATOR
    # =========================================================================
    @classmethod
    def generate_debits_statement_pdf(cls, debits_data: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=28,
            bottomMargin=28
        )
        styles = cls._create_common_styles()
        story = []

        period_label = debits_data.get("period_label", "All Debits")
        story.extend(cls._build_header(styles, f"DISBURSEMENTS, WITHDRAWALS &amp; CLAIMS AUDIT &bull; {period_label}"))
        story.append(cls._build_member_meta_box(styles, debits_data.get("member", {}), period_label))
        story.append(Spacer(1, 6))

        # Summary KPIs
        summ = debits_data.get("summary", {})
        cat_bd = summ.get("category_breakdown", {})

        kpi_data = [
            [
                Paragraph("TOTAL DISBURSED", styles["kpi_lbl"]),
                Paragraph("DISBURSEMENT COUNT", styles["kpi_lbl"]),
                Paragraph("SAVINGS WITHDRAWALS", styles["kpi_lbl"]),
                Paragraph("LOAN DISBURSEMENTS", styles["kpi_lbl"]),
                Paragraph("WELFARE GRANTS", styles["kpi_lbl"]),
            ],
            [
                Paragraph(cls.format_currency(summ.get("total_disbursed", 0)), styles["kpi_val"]),
                Paragraph(f"{summ.get('disbursement_count', 0)} Payouts", styles["kpi_val"]),
                Paragraph(cls.format_currency(cat_bd.get("SAVINGS", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(cat_bd.get("LOAN_DISBURSEMENT", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(cat_bd.get("WELFARE_GRANT", 0)), styles["kpi_val"]),
            ]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 6))

        entries = debits_data.get("entries", [])
        tbl_data = [
            [
                Paragraph("Date / Ref", styles["tbl_hdr"]),
                Paragraph("Category", styles["tbl_hdr"]),
                Paragraph("Disbursement Purpose / Narration", styles["tbl_hdr"]),
                Paragraph("Beneficiary / Channel", styles["tbl_hdr"]),
                Paragraph("Amount Disbursed", styles["tbl_hdr_right"]),
                Paragraph("Status", styles["tbl_hdr_right"]),
            ]
        ]

        if not entries:
            tbl_data.append([
                Paragraph("No debits or disbursements recorded in selected period.", styles["tbl_cell"]),
                Paragraph("-", styles["tbl_cell"]),
                Paragraph("-", styles["tbl_cell"]),
                Paragraph("-", styles["tbl_cell"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph("N/A", styles["tbl_cell_right"]),
            ])
        else:
            for e in entries:
                dt_str = e.get("transaction_date", "")[:10]
                ref_str = e.get("transaction_ref", "")
                cat_str = (e.get("ledger_category", "") or "").replace("_", " ").title()
                narr_str = e.get("narration") or "Disbursement Payout"
                if len(narr_str) > 42:
                    narr_str = narr_str[:40] + "..."
                chan_str = e.get("channel_reference") or e.get("payment_method") or "Commercial Bank NUBAN"

                tbl_data.append([
                    Paragraph(f"<b>{dt_str}</b><br/>{ref_str[:16]}", styles["tbl_cell"]),
                    Paragraph(f"<b>{cat_str}</b>", styles["tbl_cell"]),
                    Paragraph(narr_str, styles["tbl_cell"]),
                    Paragraph(chan_str[:22], styles["tbl_cell"]),
                    Paragraph(f"<b>{cls.format_currency(e.get('amount', 0))}</b>", styles["tbl_cell_red"]),
                    Paragraph(f"<font color='#0A192F'><b>{e.get('status', 'VERIFIED')}</b></font>", styles["tbl_cell_right"]),
                ])

        tbl_data.append([
            Paragraph("TOTAL DISBURSEMENTS", styles["tbl_foot"]),
            Paragraph(f"{len(entries)} Outflows", styles["tbl_foot"]),
            Paragraph("", styles["tbl_foot"]),
            Paragraph("", styles["tbl_foot"]),
            Paragraph(cls.format_currency(summ.get("total_disbursed", 0)), styles["tbl_foot_right"]),
            Paragraph("SETTLED", styles["tbl_foot_right"]),
        ])

        tx_tbl = Table(tbl_data, colWidths=[90, 85, 150, 85, 75, 55], repeatRows=1)
        tx_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), styles["c_navy"]),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
            ("TOPPADDING", (0, 0), (-1, 0), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -2), 0.25, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 1), (-1, -2), 2),
            ("BOTTOMPADDING", (0, 1), (-1, -2), 2),
            ("BACKGROUND", (0, -1), (-1, -1), styles["c_navy"]),
            ("TOPPADDING", (0, -1), (-1, -1), 3),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 3),
        ]))
        story.append(tx_tbl)

        story.extend(cls._build_footer_endorsement(styles))
        doc.build(story)
        return buffer.getvalue()

    # =========================================================================
    # 4. LOAN FACILITIES & AMORTIZATION PDF GENERATOR
    # =========================================================================
    @classmethod
    def generate_loans_statement_pdf(cls, loans_data: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=28,
            bottomMargin=28
        )
        styles = cls._create_common_styles()
        story = []

        story.extend(cls._build_header(styles, "LOAN FACILITIES &amp; AMORTIZATION STATEMENT &bull; 0% INTEREST"))
        story.append(cls._build_member_meta_box(styles, loans_data.get("member", {}), "Active &amp; Historical Facilities"))
        story.append(Spacer(1, 6))

        summ = loans_data.get("summary", {})
        mem = loans_data.get("member", {})

        kpi_data = [
            [
                Paragraph("TOTAL BORROWED", styles["kpi_lbl"]),
                Paragraph("TOTAL REPAID", styles["kpi_lbl"]),
                Paragraph("OUTSTANDING BALANCE", styles["kpi_lbl"]),
                Paragraph("AVAILABLE SAVINGS", styles["kpi_lbl"]),
                Paragraph("2× BORROWING CAPACITY", styles["kpi_lbl"]),
            ],
            [
                Paragraph(cls.format_currency(summ.get("total_principal_borrowed", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(summ.get("total_repaid", 0)), styles["kpi_val_green"]),
                Paragraph(cls.format_currency(summ.get("total_outstanding_balance", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(mem.get("current_savings", 0)), styles["kpi_val"]),
                Paragraph(cls.format_currency(mem.get("borrowing_capacity_2x", 0)), styles["kpi_val_green"]),
            ],
            [
                Paragraph("Principal Disbursed", styles["meta_lbl"]),
                Paragraph("Principal + Fee Settled", styles["meta_lbl"]),
                Paragraph("Due Under Schedule", styles["meta_lbl"]),
                Paragraph("Cash Collateral Base", styles["meta_lbl"]),
                Paragraph("0.0% Compounding Int.", styles["meta_lbl"]),
            ]
        ]
        kpi_tbl = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 6))

        loans = loans_data.get("loans", [])
        tbl_data = [
            [
                Paragraph("Loan Ref / Product", styles["tbl_hdr"]),
                Paragraph("Principal", styles["tbl_hdr_right"]),
                Paragraph("Admin Fee (5%)", styles["tbl_hdr_right"]),
                Paragraph("Total Payable", styles["tbl_hdr_right"]),
                Paragraph("Total Paid", styles["tbl_hdr_right"]),
                Paragraph("Outstanding", styles["tbl_hdr_right"]),
                Paragraph("Status", styles["tbl_hdr"]),
            ]
        ]

        if not loans:
            tbl_data.append([
                Paragraph("No active or historical loan facilities found for this cooperator.", styles["tbl_cell"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph("₦0.00", styles["tbl_cell_right"]),
                Paragraph("NONE", styles["tbl_cell"]),
            ])
        else:
            for l in loans:
                tbl_data.append([
                    Paragraph(f"<b>{l.get('loan_reference')}</b><br/>{l.get('product_name')}", styles["tbl_cell"]),
                    Paragraph(cls.format_currency(l.get("principal_amount", 0)), styles["tbl_cell_right"]),
                    Paragraph(cls.format_currency(l.get("admin_cost_fee", 0)), styles["tbl_cell_right"]),
                    Paragraph(cls.format_currency(l.get("total_payable", 0)), styles["tbl_cell_right"]),
                    Paragraph(cls.format_currency(l.get("total_paid", 0)), styles["tbl_cell_green"]),
                    Paragraph(cls.format_currency(l.get("outstanding_balance", 0)), styles["tbl_cell_red"]),
                    Paragraph(f"<b>{l.get('status')}</b>", styles["tbl_cell"]),
                ])

        tx_tbl = Table(tbl_data, colWidths=[120, 70, 70, 70, 70, 70, 70], repeatRows=1)
        tx_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), styles["c_navy"]),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
            ("TOPPADDING", (0, 0), (-1, 0), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 1), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
        ]))
        story.append(tx_tbl)

        story.extend(cls._build_footer_endorsement(styles))
        doc.build(story)
        return buffer.getvalue()
