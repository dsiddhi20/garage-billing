import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from datetime import datetime

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to calculate total page count and draw header/footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Draw running footer
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))
        
        # Footer text
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 20, footer_text)
        
        # Terms / Note
        self.drawString(36, 20, "* Subject to Nanded Jurisdiction. All parts fitted are non-refundable.")
        
        # Signature lines
        self.setFont("Helvetica-Bold", 9)
        self.drawRightString(A4[0] - 36, 60, "Authorized Signatory")
        self.setStrokeColor(colors.HexColor("#AAAAAA"))
        self.setLineWidth(0.5)
        self.line(A4[0] - 150, 55, A4[0] - 36, 55)
        
        self.restoreState()

def generate_bill_pdf(bill, customer, vehicle, items, filepath):
    """
    Generates a professional PDF bill using ReportLab matching the physical layout.
    """
    # A4 dimensions are 595.27 x 841.89 points
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=80 # Room for footer and signature
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'GarageTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0C54A0") # Deep Blue
    )
    
    subtitle_style = ParagraphStyle(
        'GarageSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#FFFFFF")
    )
    
    header_text_style = ParagraphStyle(
        'GarageHeader',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#333333")
    )

    label_style = ParagraphStyle(
        'GridLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#333333")
    )

    value_style = ParagraphStyle(
        'GridValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#111111")
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#FFFFFF"),
        alignment=1 # Center
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#111111")
    )

    table_cell_right_style = ParagraphStyle(
        'TableCellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#111111"),
        alignment=2 # Right
    )

    story = []

    # 1. Header Table (Business Details & Contact info)
    # Left side: Logo + Name + Address
    # Right side: Cell info + Bill #
    left_header_data = [
        [Paragraph("Sachin's Sumangal Services", title_style)],
        [Spacer(1, 4)],
        [Table(
            [[Paragraph("MARUTI SERVICING CENTRE", subtitle_style)]],
            colWidths=[200],
            style=TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0C54A0")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ])
        )],
        [Spacer(1, 4)],
        [Paragraph("Near LIC Office, Hingoli Road, Nanded.", header_text_style)]
    ]
    left_header_table = Table(left_header_data, colWidths=[300])
    left_header_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))

    # Format phone list
    phone_lines = [p.strip() for p in bill.get('garage_phones', "9422711826, 9834196573").split(',')]
    phone_text = ", ".join(phone_lines)
    
    right_header_data = [
        [Paragraph(f"<b>Cell:</b> {phone_text}", header_text_style)],
        [Spacer(1, 10)],
        [Paragraph(f"<font size=14 color='#D32F2F'><b>No. {bill['bill_number']}</b></font>", header_text_style)]
    ]
    right_header_table = Table(right_header_data, colWidths=[223])
    right_header_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))

    header_table = Table([[left_header_table, right_header_table]], colWidths=[300, 223])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # Divider line
    divider = Table([[""]], colWidths=[523])
    divider.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor("#0C54A0")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 8))

    # 2. Client & Vehicle Details Table
    bill_date_str = bill['bill_date']
    if isinstance(bill_date_str, datetime):
        bill_date_str = bill_date_str.strftime('%d/%m/%Y')
    elif hasattr(bill_date_str, 'strftime'):
        bill_date_str = bill_date_str.strftime('%d/%m/%Y')
    else:
        # If it's a string, try converting or just clean it up
        try:
            dt = datetime.strptime(str(bill_date_str).split(' ')[0], '%Y-%m-%d')
            bill_date_str = dt.strftime('%d/%m/%Y')
        except:
            bill_date_str = str(bill_date_str)

    customer_address = customer.get('address', '') or ""
    
    details_data = [
        [
            Paragraph("Name:", label_style), Paragraph(customer['name'], value_style),
            Paragraph("Veh. No:", label_style), Paragraph(vehicle['vehicle_number'], value_style)
        ],
        [
            Paragraph("Address:", label_style), Paragraph(customer_address, value_style),
            Paragraph("Model:", label_style), Paragraph(vehicle.get('model', '') or "", value_style)
        ],
        [
            Paragraph("Ph. No:", label_style), Paragraph(customer['mobile'], value_style),
            Paragraph("Km / Odo:", label_style), Paragraph(f"{bill['km']}", value_style)
        ],
        [
            Paragraph("", label_style), Paragraph("", value_style),
            Paragraph("Date:", label_style), Paragraph(bill_date_str, value_style)
        ]
    ]

    details_table = Table(details_data, colWidths=[50, 210, 55, 208])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#EEEEEE")),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 15))

    # 3. Particulars & Itemized Table
    particulars_header = [
        Paragraph("Sr. No.", table_header_style),
        Paragraph("Particulars", table_header_style),
        Paragraph("Amount (INR)", table_header_style)
    ]
    
    particulars_rows = [particulars_header]
    for idx, item in enumerate(items):
        particulars_rows.append([
            Paragraph(f"{idx + 1}", table_cell_style),
            Paragraph(item['description'], table_cell_style),
            Paragraph(f"{float(item['amount']):,.2f}", table_cell_right_style)
        ])

    # Standardize Table size: Pad table with empty rows to match physical bill book height
    min_rows = 8
    if len(items) < min_rows:
        for pad_idx in range(len(items), min_rows):
            particulars_rows.append([
                Paragraph(f"{pad_idx + 1}", table_cell_style),
                Paragraph("", table_cell_style),
                Paragraph("", table_cell_style)
            ])

    # Table styles matching professional layout
    particulars_table = Table(particulars_rows, colWidths=[50, 343, 130])
    particulars_table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0C54A0")), # Deep Blue
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ])
    particulars_table.setStyle(particulars_table_style)
    story.append(particulars_table)
    story.append(Spacer(1, 10))

    # 4. Totals Calculation Grid
    subtotal_val = float(bill['subtotal'])
    discount_val = float(bill.get('discount', 0) or 0)
    tax_val = float(bill.get('tax', 0) or 0)
    total_val = float(bill['total'])

    totals_rows = [
        [Paragraph("Subtotal:", label_style), Paragraph(f"₹ {subtotal_val:,.2f}", table_cell_right_style)],
    ]
    if discount_val > 0:
        totals_rows.append([Paragraph("Discount:", label_style), Paragraph(f"- ₹ {discount_val:,.2f}", table_cell_right_style)])
    if tax_val > 0:
        totals_rows.append([Paragraph("Tax / GST:", label_style), Paragraph(f"+ ₹ {tax_val:,.2f}", table_cell_right_style)])
    
    totals_rows.append([
        Paragraph("<font size=11 color='#0C54A0'><b>TOTAL:</b></font>", label_style),
        Paragraph(f"<font size=11 color='#0C54A0'><b>₹ {total_val:,.2f}</b></font>", table_cell_right_style)
    ])

    totals_table = Table(totals_rows, colWidths=[100, 130])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#EAEAEA")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))

    # Align calculations block to the right of the page
    totals_layout = Table([["", totals_table]], colWidths=[293, 230])
    totals_layout.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(KeepTogether([totals_layout]))

    # Build PDF doc using NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
