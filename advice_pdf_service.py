"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
OFFICIAL PAYMENT ADVICE PDF GENERATOR (advice_pdf_service.py)
-----------------------------------------------------------------------------
Generates an official, publication-grade Monthly Payment Advice & Remittance
Slip PDF conforming to Lagos State Cooperative Societies Law (Cap C15).

Official Secretariat Invariant Email: wealthbridge.coopsociety@gmail.com
Document Reference: WMC-ADV-PDF-V1
=============================================================================
"""

import io
from datetime import datetime
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


class AdvicePdfService:
    @staticmethod
    def format_currency(val: float) -> str:
        try:
            num = float(val or 0.0)
            return f"₦{num:,.2f}"
        except Exception:
            return "₦0.00"

    @classmethod
    def generate_pdf(
        cls,
        advice: Dict[str, Any],
        member: Dict[str, Any],
        dva_account: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Builds a comprehensive, single-page official remittance PDF slip.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=32,
            bottomMargin=32
        )

        styles = getSampleStyleSheet()

        # Custom Typography Styles
        c_navy = colors.HexColor("#0A192F")
        c_gold = colors.HexColor("#B45309")
        c_emerald = colors.HexColor("#047857")
        c_slate = colors.HexColor("#475569")
        c_border = colors.HexColor("#CBD5E1")
        c_bg_light = colors.HexColor("#F8FAFC")

        style_title = ParagraphStyle(
            "OrgTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=c_navy,
            alignment=1
        )
        style_sub = ParagraphStyle(
            "OrgSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=c_slate,
            alignment=1
        )
        style_email = ParagraphStyle(
            "OrgEmail",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=c_gold,
            alignment=1
        )
        style_banner = ParagraphStyle(
            "DocBanner",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.white,
            alignment=1
        )
        style_cell_label = ParagraphStyle(
            "CellLabel",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748B")
        )
        style_cell_value = ParagraphStyle(
            "CellValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=c_navy
        )
        style_tbl_hdr = ParagraphStyle(
            "TableHdr",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white
        )
        style_tbl_hdr_right = ParagraphStyle(
            "TableHdrRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=2
        )
        style_tbl_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=c_navy
        )
        style_tbl_cell_bold = ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=c_navy
        )
        style_tbl_cell_right = ParagraphStyle(
            "TableCellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=c_navy,
            alignment=2
        )
        style_tbl_cell_green = ParagraphStyle(
            "TableCellGreen",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=c_emerald,
            alignment=2
        )
        style_tbl_cell_due = ParagraphStyle(
            "TableCellDue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#B91C1C"),
            alignment=2
        )
        style_tbl_foot = ParagraphStyle(
            "TableFoot",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.white
        )
        style_tbl_foot_right = ParagraphStyle(
            "TableFootRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#FEF08A"),
            alignment=2
        )
        style_note_bold = ParagraphStyle(
            "NoteBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=c_navy
        )
        style_note_text = ParagraphStyle(
            "NoteText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=c_slate
        )

        story = []

        # 1. Organization Header & Letterhead
        story.append(Paragraph("WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED", style_title))
        story.append(Spacer(1, 2))
        story.append(Paragraph("Operating under Lagos State Cooperative Societies Law (Cap C15) &bull; Registered Secretariat: Odogunyan, Ikorodu, Lagos State", style_sub))
        story.append(Spacer(1, 1))
        story.append(Paragraph("Official Secretariat Contact: wealthbridge.coopsociety@gmail.com &bull; Custody Banker: Polaris Bank Limited", style_email))
        story.append(Spacer(1, 4))

        # Banner Box
        banner_table = Table(
            [[Paragraph("OFFICIAL MONTHLY PAYMENT ADVICE & REMITTANCE VOUCHER", style_banner)]],
            colWidths=[540],
            rowHeights=[20]
        )
        banner_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_navy),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 8))

        # 2. Cooperator & Advice Profile Meta Grid
        member_name = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip() or "Valued Cooperator"
        member_code = member.get("member_code") or f"WMC-2026-{member.get('id', 1):03d}"
        tier = (advice.get("tier") or member.get("contribution_tier") or "STANDARD").upper()
        adv_ref = advice.get("advice_reference") or f"WMC-ADV-{advice.get('billing_period', '2026-10')}"
        billing_period = advice.get("billing_period") or datetime.now().strftime("%Y-%m")
        issue_date = str(advice.get("issue_date") or f"{billing_period}-01")
        due_date = str(advice.get("due_date") or f"{billing_period}-28")
        status_label = (advice.get("status") or "DUE").replace("_", " ").upper()

        meta_data = [
            [
                Paragraph("<b>COOPERATOR NAME:</b>", style_cell_label),
                Paragraph(member_name, style_cell_value),
                Paragraph("<b>ADVICE REFERENCE:</b>", style_cell_label),
                Paragraph(adv_ref, style_cell_value),
            ],
            [
                Paragraph("<b>MEMBER CODE:</b>", style_cell_label),
                Paragraph(f"<font color='#B45309'><b>{member_code}</b></font>", style_cell_value),
                Paragraph("<b>CONTRIBUTION TIER:</b>", style_cell_label),
                Paragraph(f"{tier} TIER", style_cell_value),
            ],
            [
                Paragraph("<b>BILLING PERIOD:</b>", style_cell_label),
                Paragraph(billing_period, style_cell_value),
                Paragraph("<b>DATE OF ISSUANCE:</b>", style_cell_label),
                Paragraph(issue_date, style_cell_value),
            ],
            [
                Paragraph("<b>FULFILLMENT STATUS:</b>", style_cell_label),
                Paragraph(f"<b>{status_label}</b>", style_cell_value),
                Paragraph("<b>STATUTORY DUE DATE:</b>", style_cell_label),
                Paragraph(f"<font color='#B91C1C'><b>{due_date} (Strictly due by 28th)</b></font>", style_cell_value),
            ],
        ]

        meta_table = Table(meta_data, colWidths=[110, 160, 120, 150])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_bg_light),
            ("BOX", (0, 0), (-1, -1), 0.75, c_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 8))

        # 3. Itemized Financial Assessment Table (Strict Priority Waterfall)
        breakdown = advice.get("breakdown") or {}
        fines = breakdown.get("fines", {})
        reg_fee = breakdown.get("registration_fee", {})
        loan = breakdown.get("loan_repayment", {})
        welfare = breakdown.get("welfare", {})
        shares = breakdown.get("share_capital", {})
        savings = breakdown.get("regular_savings", {})
        targets = breakdown.get("target_savings", {})
        arrears = breakdown.get("arrears", {})
        totals = advice.get("totals", {})

        tbl_data = [
            [
                Paragraph("Priority / Line Item", style_tbl_hdr),
                Paragraph("Statutory / Policy Category", style_tbl_hdr),
                Paragraph("Advised (Expected)", style_tbl_hdr_right),
                Paragraph("Amount Paid", style_tbl_hdr_right),
                Paragraph("Remaining Due", style_tbl_hdr_right),
            ],
            [
                Paragraph("<b>P1. Disciplinary Fines</b>", style_tbl_cell_bold),
                Paragraph("Statutory Compliance & Sanctions", style_tbl_cell),
                Paragraph(cls.format_currency(fines.get("expected", 0)), style_tbl_cell_right),
                Paragraph(cls.format_currency(fines.get("paid", 0)), style_tbl_cell_green),
                Paragraph(cls.format_currency(fines.get("remaining", 0)), style_tbl_cell_due if fines.get("remaining", 0) > 0 else style_tbl_cell_right),
            ],
        ]

        p_idx = 2
        # Priority 2: Mandatory Entrance / Registration Fee (Article 7)
        if reg_fee.get("expected", 0) > 0 or reg_fee.get("paid", 0) > 0:
            tbl_data.append([
                Paragraph(f"<b>P{p_idx}. Entrance / Registration Fee</b>", style_tbl_cell_bold),
                Paragraph("Statutory Onboarding (Article 7)", style_tbl_cell),
                Paragraph(cls.format_currency(reg_fee.get("expected", 0)), style_tbl_cell_right),
                Paragraph(cls.format_currency(reg_fee.get("paid", 0)), style_tbl_cell_green),
                Paragraph(cls.format_currency(reg_fee.get("remaining", 0)), style_tbl_cell_due if reg_fee.get("remaining", 0) > 0 else style_tbl_cell_right),
            ])
            p_idx += 1

        tbl_data.extend([
            [
                Paragraph(f"<b>P{p_idx}. Active Loan Repayment</b>", style_tbl_cell_bold),
                Paragraph("Credit Facility Amortization", style_tbl_cell),
                Paragraph(cls.format_currency(loan.get("expected", 0)), style_tbl_cell_right),
                Paragraph(cls.format_currency(loan.get("paid", 0)), style_tbl_cell_green),
                Paragraph(cls.format_currency(loan.get("remaining", 0)), style_tbl_cell_due if loan.get("remaining", 0) > 0 else style_tbl_cell_right),
            ],
            [
                Paragraph(f"<b>P{p_idx+1}. Welfare Solidarity Pool</b>", style_tbl_cell_bold),
                Paragraph("Mandatory Welfare (Article 13)", style_tbl_cell),
                Paragraph(cls.format_currency(welfare.get("expected", 0)), style_tbl_cell_right),
                Paragraph(cls.format_currency(welfare.get("paid", 0)), style_tbl_cell_green),
                Paragraph(cls.format_currency(welfare.get("remaining", 0)), style_tbl_cell_due if welfare.get("remaining", 0) > 0 else style_tbl_cell_right),
            ],
            [
                Paragraph(f"<b>P{p_idx+2}. Share Capital Equity</b>", style_tbl_cell_bold),
                Paragraph("Cooperative Equity (Article 12)", style_tbl_cell),
                Paragraph(cls.format_currency(shares.get("expected", 0)), style_tbl_cell_right),
                Paragraph(cls.format_currency(shares.get("paid", 0)), style_tbl_cell_green),
                Paragraph(cls.format_currency(shares.get("remaining", 0)), style_tbl_cell_due if shares.get("remaining", 0) > 0 else style_tbl_cell_right),
            ],
            [
                Paragraph(f"<b>P{p_idx+3}. Regular Co-op Savings</b>", style_tbl_cell_bold),
                Paragraph("Liquid Collateral (2x Borrowing)", style_tbl_cell),
                Paragraph(cls.format_currency(savings.get("expected", 0)), style_tbl_cell_right),
                Paragraph(cls.format_currency(savings.get("paid", 0)), style_tbl_cell_green),
                Paragraph(cls.format_currency(savings.get("remaining", 0)), style_tbl_cell_due if savings.get("remaining", 0) > 0 else style_tbl_cell_right),
            ],
            [
                Paragraph(f"<b>P{p_idx+4}. Target Savings Commitments</b>", style_tbl_cell_bold),
                Paragraph("Voluntary Project Ledgers", style_tbl_cell),
                Paragraph(cls.format_currency(targets.get("expected", 0)), style_tbl_cell_right),
                Paragraph(cls.format_currency(targets.get("paid", 0)), style_tbl_cell_green),
                Paragraph(cls.format_currency(targets.get("remaining", 0)), style_tbl_cell_due if targets.get("remaining", 0) > 0 else style_tbl_cell_right),
            ],
        ])

        if arrears.get("expected", 0) > 0:
            tbl_data.append([
                Paragraph("<b>Rollover Prior Arrears</b>", style_tbl_cell_bold),
                Paragraph("Prior Month Outstanding Balance", style_tbl_cell),
                Paragraph(cls.format_currency(arrears.get("expected", 0)), style_tbl_cell_right),
                Paragraph("₦0.00", style_tbl_cell_right),
                Paragraph(cls.format_currency(arrears.get("expected", 0)), style_tbl_cell_due),
            ])

        # Totals Row
        tot_exp = totals.get("total_expected", 0)
        tot_paid = totals.get("total_paid", 0)
        tot_bal = totals.get("outstanding_balance", 0)

        tbl_data.append([
            Paragraph("TOTAL MONTHLY OBLIGATIONS", style_tbl_foot),
            Paragraph("CONSOLIDATED ASSESSMENT", style_tbl_foot),
            Paragraph(cls.format_currency(tot_exp), style_tbl_foot_right),
            Paragraph(cls.format_currency(tot_paid), style_tbl_foot_right),
            Paragraph(cls.format_currency(tot_bal), style_tbl_foot_right),
        ])

        col_w = [145, 135, 85, 85, 90]
        item_table = Table(tbl_data, colWidths=col_w)
        item_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), c_navy),
            ("ALIGN", (0, 0), (-1, 0), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -2), 0.5, c_border),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, c_bg_light]),
            ("BACKGROUND", (0, -1), (-1, -1), c_navy),
            ("LINEABOVE", (0, -1), (-1, -1), 1.5, c_gold),
        ]))
        story.append(item_table)
        story.append(Spacer(1, 8))

        # 4. Bank Transfer Settlement Channels Box
        dva_num = (dva_account and dva_account.get("account_number")) or member.get("paystack_dva_account_number") or "9926000001"
        dva_bank = (dva_account and dva_account.get("bank_name")) or "Wema Bank (Paystack DVA)"
        bank_box_data = [
            [
                Paragraph("<b>INSTANT DEDICATED VIRTUAL ACCOUNT (PAYSTACK DVA)</b>", style_note_bold),
                Paragraph("<b>SOCIETY CUSTODY TREASURY (POLARIS BANK)</b>", style_note_bold),
            ],
            [
                Paragraph(f"Account Number: <b><font size='10' color='#0A192F'>{dva_num}</font></b><br/>Bank: <b>{dva_bank}</b><br/>Beneficiary: <b>Wealthbridge / {member_name}</b>", style_note_text),
                Paragraph("Account Number: <b><font size='10' color='#0A192F'>4091807498</font></b><br/>Bank: <b>Polaris Bank Limited</b><br/>Beneficiary: <b>Wealthbridge Multipurpose Coop</b>", style_note_text),
            ],
            [
                Paragraph(
                    "<b>Automated Waterfall Distribution Protocol:</b> Any inward transfer into your Dedicated Account is automatically applied strictly across obligations in priority sequence (1. Fines &rarr; 2. Entrance Fee &rarr; 3. Loans &rarr; 4. Welfare &rarr; 5. Shares &rarr; 6. Regular Savings &rarr; 7. Targets). Any surplus above total expected bill is <b>100% credited into your unencumbered Regular Savings</b>.",
                    style_note_text
                ),
                Paragraph(
                    "<b>Remittance Deadline:</b> Monthly payments are due strictly on or before the <b>28th day of each calendar month</b>. Unpaid obligations roll over into the subsequent monthly advice as arrears.",
                    style_note_text
                )
            ]
        ]
        bank_table = Table(bank_box_data, colWidths=[270, 270])
        bank_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#93C5FD")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(bank_table)
        story.append(Spacer(1, 10))

        # 5. Signatures & Official Audit Certification
        sig_data = [
            [
                Paragraph("___________________________________<br/><b>Financial Secretary</b><br/>Wealthbridge Multipurpose Secretariat", style_note_text),
                Paragraph("___________________________________<br/><b>General Secretary / President</b><br/>Executive Committee Endorsement", style_note_text),
                Paragraph(f"<b>AUDIT CERTIFIED DOCUMENT</b><br/>Platform Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>Official Invariant: <b>wealthbridge.coopsociety@gmail.com</b>", style_note_text),
            ]
        ]
        sig_table = Table(sig_data, colWidths=[180, 180, 180])
        sig_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(sig_table)

        doc.build(story)
        return buffer.getvalue()
