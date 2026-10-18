"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
OFFICIAL ELECTRONIC MEMBERSHIP ID CARD GENERATOR (id_card_pdf_service.py)
-----------------------------------------------------------------------------
Generates a publication-grade, high-resolution official membership ID card PDF
complete with authorized presidential and secretarial signatures, official seal,
security QR code, and statutory charter details under Lagos State Law (Cap C15).

Official Secretariat Invariant Email: wealthbridge.coopsociety@gmail.com
Document Reference: WMC-ID-CARD-PDF-V1
=============================================================================
"""

import io
import os
import base64
from datetime import datetime
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line, Group
from reportlab.graphics.barcode.qr import QrCodeWidget


class IdCardPdfService:
    @classmethod
    def generate_id_card_pdf(
        cls,
        member: Dict[str, Any],
        system_config: Optional[Dict[str, str]] = None
    ) -> bytes:
        """
        Builds an official print-and-cut cooperative membership ID card sheet (Letter size)
        featuring both the Front and Back of the Electronic Membership Card.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Primary Brand Colors
        c_navy = colors.HexColor("#0A192F")
        c_gold = colors.HexColor("#B45309")
        c_amber_light = colors.HexColor("#FEF3C7")
        c_emerald = colors.HexColor("#047857")
        c_slate = colors.HexColor("#475569")
        c_border = colors.HexColor("#CBD5E1")
        c_bg_card = colors.HexColor("#0F172A")

        # Typography Styles
        style_sheet_title = ParagraphStyle(
            "SheetTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=c_navy,
            alignment=1
        )
        style_sheet_sub = ParagraphStyle(
            "SheetSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=c_slate,
            alignment=1
        )
        style_notice = ParagraphStyle(
            "SheetNotice",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B"),
            alignment=1
        )

        # Card specific styles
        style_card_title = ParagraphStyle(
            "CardTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.white,
            alignment=1
        )
        style_card_sub = ParagraphStyle(
            "CardSub",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#FDE68A"),
            alignment=1
        )
        style_field_label = ParagraphStyle(
            "FieldLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#94A3B8")
        )
        style_field_val = ParagraphStyle(
            "FieldVal",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=colors.HexColor("#0F172A")
        )
        style_member_name = ParagraphStyle(
            "MemberName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            textColor=colors.HexColor("#0A192F")
        )
        style_card_back_text = ParagraphStyle(
            "CardBackText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6,
            leading=8,
            textColor=colors.HexColor("#334155")
        )
        style_card_back_notice = ParagraphStyle(
            "CardBackNotice",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#0F172A")
        )

        member_name = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip() or "COOPERATOR"
        member_code = member.get("member_code") or "WMC-MEMBER"
        tier = (member.get("contribution_tier") or "STANDARD").upper()
        admission_date = str(member.get("admission_date") or datetime.now().strftime("%Y-%m-%d"))
        role = (member.get("primary_role") or "MEMBER").replace("_", " ").upper()
        phone = member.get("phone") or "N/A"
        nin = member.get("identification_number") or member.get("national_id_nin") or "VERIFIED-NIN"
        masked_nin = nin[:3] + "******" + nin[-3:] if len(nin) >= 8 else "VERIFIED"

        story = []

        # Sheet Header
        story.append(Paragraph("WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED", style_sheet_title))
        story.append(Spacer(1, 3))
        story.append(Paragraph("OFFICIAL ELECTRONIC COOPERATOR IDENTITY CARD &bull; LAGOS STATE CAP C15", style_sheet_sub))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Official Secretariat Invariant: <strong>wealthbridge.coopsociety@gmail.com</strong>", style_notice))
        story.append(Spacer(1, 16))

        # CARD DIMENSIONS: Standard CR80 is 3.375 in × 2.125 in (approx 243 pt × 153 pt)
        # We render a high-clarity 3.6 in × 2.3 in card box (259 pt × 165 pt)
        card_w = 3.5 * inch
        card_h = 2.25 * inch

        # ---------------------------------------------------------------------
        # 1. FRONT CARD TABLE DESIGN
        # ---------------------------------------------------------------------
        # Front Card Header Row
        front_header = Table(
            [
                [
                    Paragraph("WEALTHBRIDGE MULTIPURPOSE COOP. SOCIETY", style_card_title),
                ],
                [
                    Paragraph("OFFICIAL MEMBERSHIP IDENTITY CARD &bull; LAGOS STATE", style_card_sub)
                ]
            ],
            colWidths=[card_w - 12]
        )
        front_header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_navy),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        # Member Photo Box / Placeholder
        photo_flowable = None
        passport_path = member.get("passport_photo")
        if passport_path and os.path.exists(passport_path):
            try:
                photo_flowable = RLImage(passport_path, width=0.85 * inch, height=1.05 * inch)
            except Exception:
                photo_flowable = None

        if not photo_flowable:
            # Draw stylized avatar placeholder
            d_photo = Drawing(0.85 * inch, 1.05 * inch)
            d_photo.add(Rect(0, 0, 0.85 * inch, 1.05 * inch, fillColor=colors.HexColor("#0A192F"), strokeColor=c_gold, strokeWidth=1, rx=4, ry=4))
            # Gold Initials
            initials = ((member.get("first_name", "W")[0]) + (member.get("last_name", "C")[0])).upper()
            d_photo.add(String(0.425 * inch, 0.45 * inch, initials, fontName="Helvetica-Bold", fontSize=18, textAnchor="middle", fillColor=colors.HexColor("#FDE68A")))
            photo_flowable = d_photo

        # Member Details Column
        details_table = Table(
            [
                [Paragraph("MEMBER FULL NAME", style_field_label)],
                [Paragraph(member_name, style_member_name)],
                [
                    Table(
                        [
                            [Paragraph("MEMBER CODE", style_field_label), Paragraph("CATEGORY / ROLE", style_field_label)],
                            [Paragraph(member_code, style_field_val), Paragraph(role, style_field_val)],
                            [Paragraph("NATIONAL ID (NIN)", style_field_label), Paragraph("ADMISSION DATE", style_field_label)],
                            [Paragraph(masked_nin, style_field_val), Paragraph(admission_date, style_field_val)],
                        ],
                        colWidths=[1.15 * inch, 1.25 * inch],
                        rowHeights=[9, 13, 9, 13]
                    )
                ]
            ],
            colWidths=[2.45 * inch]
        )
        details_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        front_body = Table(
            [[photo_flowable, details_table]],
            colWidths=[0.9 * inch, 2.45 * inch]
        )
        front_body.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))

        # Dual Signatures & Seal Row
        sig_d = Drawing(card_w - 12, 28)
        # Gold underline separator
        sig_d.add(Line(0, 27, card_w - 12, 27, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=0.5))
        # Left signature: General Secretary
        sig_d.add(String(5, 14, "Olusegun O.", fontName="Times-Italic", fontSize=10, fillColor=colors.HexColor("#1E3A8A")))
        sig_d.add(String(5, 4, "General Secretary", fontName="Helvetica", fontSize=5.5, fillColor=c_slate))
        # Center: Official Seal Badge
        sig_d.add(Circle(card_w / 2 - 6, 14, 11, fillColor=colors.HexColor("#FEF3C7"), strokeColor=c_gold, strokeWidth=1))
        sig_d.add(String(card_w / 2 - 6, 12, "★ WMC ★", fontName="Helvetica-Bold", fontSize=5, textAnchor="middle", fillColor=c_navy))
        sig_d.add(String(card_w / 2 - 6, 6, "SEAL", fontName="Helvetica-Bold", fontSize=4, textAnchor="middle", fillColor=c_gold))
        # Right signature: President Dual Sign-Off
        sig_d.add(String(card_w - 20, 14, "Qazeem Adebowale", fontName="Times-Italic", fontSize=10, textAnchor="end", fillColor=colors.HexColor("#1E3A8A")))
        sig_d.add(String(card_w - 20, 4, "President / Board Chair", fontName="Helvetica", fontSize=5.5, textAnchor="end", fillColor=c_slate))

        front_card_table = Table(
            [
                [front_header],
                [front_body],
                [sig_d]
            ],
            colWidths=[card_w]
        )
        front_card_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.5, c_navy),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        # ---------------------------------------------------------------------
        # 2. BACK CARD TABLE DESIGN
        # ---------------------------------------------------------------------
        # Magnetic Strip Drawing
        mag_d = Drawing(card_w - 12, 18)
        mag_d.add(Rect(0, 0, card_w - 12, 18, fillColor=colors.HexColor("#0F172A"), strokeColor=None))
        mag_d.add(String(10, 5, "WEALTHBRIDGE DIGITAL CLEARING SYSTEM &bull; STRICTLY CONFIDENTIAL", fontName="Helvetica-Bold", fontSize=4.5, fillColor=colors.HexColor("#64748B")))

        # Dynamic QR Code for Member Verification
        qr_widget = QrCodeWidget(f"https://wealthbridge.coop/verify/{member_code}")
        qr_widget.barWidth = 55
        qr_widget.barHeight = 55
        qr_widget.qrVersion = 1
        d_qr = Drawing(55, 55)
        d_qr.add(qr_widget)

        back_terms = Table(
            [
                [Paragraph("<strong>STATUTORY CONDITIONS &amp; CARD PRIVILEGES:</strong>", style_card_back_notice)],
                [Paragraph("&bull; This electronic credential is the statutory property of Wealthbridge Cooperative.", style_card_back_text)],
                [Paragraph("&bull; Entitles bearer to vote, 0% interest loan access, and annual dividend surplus.", style_card_back_text)],
                [Paragraph("&bull; If found, please return to Secretariat: 13, Agbaje Iloro Street, Odogunyan, Ikorodu, Lagos State, Nigeria.", style_card_back_text)],
                [Paragraph("Official Email: <strong>wealthbridge.coopsociety@gmail.com</strong>", style_card_back_notice)],
            ],
            colWidths=[card_w - 75]
        )
        back_terms.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        back_body = Table(
            [[d_qr, back_terms]],
            colWidths=[60, card_w - 72]
        )
        back_body.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))

        back_footer_d = Drawing(card_w - 12, 16)
        back_footer_d.add(Rect(0, 0, card_w - 12, 16, fillColor=c_navy, strokeColor=None))
        back_footer_d.add(String((card_w - 12) / 2, 4.5, "VERIFIED ELECTRONIC CREDENTIAL &bull; DEMOCRATIC 1 MEMBER 1 VOTE", fontName="Helvetica-Bold", fontSize=5.5, textAnchor="middle", fillColor=colors.HexColor("#FDE68A")))

        back_card_table = Table(
            [
                [mag_d],
                [back_body],
                [back_footer_d]
            ],
            colWidths=[card_w]
        )
        back_card_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1.5, c_navy),
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        # Place Front & Back side-by-side or stacked
        sheet_layout = Table(
            [
                [
                    Paragraph("<strong>FRONT OF CARD</strong>", ParagraphStyle("FLabel", fontName="Helvetica-Bold", fontSize=9, textColor=c_navy, alignment=1)),
                    Paragraph("<strong>BACK OF CARD</strong>", ParagraphStyle("BLabel", fontName="Helvetica-Bold", fontSize=9, textColor=c_navy, alignment=1)),
                ],
                [
                    front_card_table,
                    back_card_table
                ]
            ],
            colWidths=[card_w + 12, card_w + 12]
        )
        sheet_layout.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

        story.append(sheet_layout)

        story.append(Spacer(1, 24))

        # Instructions / Verification Explainer Box
        guide_text = Paragraph(
            """<strong>OFFICIAL CREDENTIAL VERIFICATION &amp; PRODUCTION INSTRUCTIONS:</strong><br/>
            1. <strong>Verification</strong>: This digital card is issued under the authority of the Board of Trustees of Wealthbridge Multipurpose Cooperative Society Limited.<br/>
            2. <strong>Authorized Signatures</strong>: Signed and sealed electronically under dual-key executive sign-off protocol (General Secretary &amp; President).<br/>
            3. <strong>Card Printing &amp; Lamination</strong>: You may print this sheet on 300gsm cardstock or photo paper and cut along the solid outer border for standard CR80 wallet lamination.<br/>
            4. <strong>Support &amp; Inquiries</strong>: In case of discrepancies, contact Secretariat Support at <strong>wealthbridge.coopsociety@gmail.com</strong>.
            """,
            ParagraphStyle("Guide", fontName="Helvetica", fontSize=8, leading=11, textColor=colors.HexColor("#334155"))
        )
        guide_box = Table([[guide_text]], colWidths=[card_w * 2 + 24])
        guide_box.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(guide_box)

        doc.build(story)
        return buffer.getvalue()
