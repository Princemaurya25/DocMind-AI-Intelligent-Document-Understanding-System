import io
import csv
import pandas as pd
from typing import Any, Dict
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def export_to_csv(data: Dict[str, Any], filename: str) -> io.BytesIO:
    """
    Exports dictionary data to a CSV byte stream.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write metadata header
    writer.writerow(["DocMind AI Extracted Data Report"])
    writer.writerow(["Document Filename", filename])
    writer.writerow([])
    writer.writerow(["Field Key", "Field Value"])
    
    for key, val in data.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                writer.writerow([f"{key}.{sub_key}", str(sub_val)])
        else:
            writer.writerow([key, str(val)])
            
    stream = io.BytesIO()
    stream.write(output.getvalue().encode("utf-8"))
    stream.seek(0)
    return stream


def export_to_excel(data: Dict[str, Any], filename: str) -> io.BytesIO:
    """
    Exports dictionary data to an Excel (xlsx) byte stream using Pandas.
    """
    rows = []
    for key, val in data.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                rows.append({"Field Group": key, "Field Name": sub_key, "Value": str(sub_val)})
        else:
            rows.append({"Field Group": "General", "Field Name": key, "Value": str(val)})
            
    df = pd.DataFrame(rows)
    
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Extracted Data")
        
    stream.seek(0)
    return stream


def export_to_pdf(data: Dict[str, Any], filename: str, doc_type: str, confidence: float, summary: str = "") -> io.BytesIO:
    """
    Generates a beautifully typeset PDF report using ReportLab.
    """
    stream = io.BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#0F172A'), # slate-900
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=colors.HexColor('#1E3A8A'), # blue-900
        spaceBefore=10,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#334155'), # slate-700
        leading=14
    )
    
    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    # Header Title
    story.append(Paragraph("DocMind AI – Document Extraction Report", title_style))
    story.append(Spacer(1, 10))
    
    # Metadata block table
    meta_data = [
        [Paragraph("Document Source:", bold_body), Paragraph(filename, body_style)],
        [Paragraph("Document Classification:", bold_body), Paragraph(doc_type, body_style)],
        [Paragraph("Overall Confidence:", bold_body), Paragraph(f"{confidence * 100:.2f}%", body_style)],
    ]
    meta_table = Table(meta_data, colWidths=[2.0*inch, 5.0*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))
    
    # Summary section if present
    if summary:
        story.append(Paragraph("AI-Generated Document Summary", section_style))
        story.append(Paragraph(summary, body_style))
        story.append(Spacer(1, 15))
        
    # Extracted Data Section
    story.append(Paragraph("Extracted Information Fields", section_style))
    
    table_data = [[Paragraph("Field Name", bold_body), Paragraph("Extracted Value", bold_body)]]
    
    for key, val in data.items():
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                table_data.append([
                    Paragraph(f"<b>{key}</b>.{sub_key}", body_style),
                    Paragraph(str(sub_val), body_style)
                ])
        else:
            table_data.append([
                Paragraph(key, body_style),
                Paragraph(str(val), body_style)
            ])
            
    fields_table = Table(table_data, colWidths=[2.5*inch, 4.5*inch])
    fields_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')])
    ]))
    # Quick fix for text colors of headers
    for i in range(2):
        table_data[0][i].style.textColor = colors.white
        
    story.append(fields_table)
    
    # Build Document
    doc.build(story)
    stream.seek(0)
    return stream
