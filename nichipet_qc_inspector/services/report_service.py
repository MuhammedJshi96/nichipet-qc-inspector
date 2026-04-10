from pathlib import Path
import csv
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

OUTPUT_DIR = Path("reports")
OUTPUT_DIR.mkdir(exist_ok=True)

def export_html(result):
    path = OUTPUT_DIR / f"{result.metadata.inspection_id}.html"
    html = []
    html.append("<html><head><meta charset='utf-8'><title>Nichipet QC Report</title></head><body>")
    html.append("<h1>Nichipet QC Report</h1>")
    html.append(f"<p><strong>Inspection ID:</strong> {result.metadata.inspection_id}</p>")
    html.append(f"<p><strong>Operator:</strong> {result.metadata.operator_name}</p>")
    html.append(f"<p><strong>Pipette number:</strong> {result.metadata.pipette_serial_number}</p>")
    html.append(f"<p><strong>Model:</strong> {result.metadata.model_code}</p>")
    html.append(f"<p><strong>Mode:</strong> {result.metadata.mode}</p>")
    html.append(f"<p><strong>Decision:</strong> {result.final_use_decision}</p>")
    html.append(f"<p><strong>Non-compliant conditions:</strong> {result.non_compliant_conditions}</p>")

    for idx, p in enumerate(result.point_results, start=1):
        html.append(f"<h2>Point {idx} — {p.selected_volume_ul} μL</h2>")
        html.append("<ul>")
        html.append(f"<li>Mean volume: {p.mean_volume_ul:.4f} μL</li>")
        html.append(f"<li>Systematic error: {p.systematic_error_percent:.4f}%</li>")
        html.append(f"<li>Absolute systematic error: {p.absolute_systematic_error_percent:.4f}%</li>")
        html.append(f"<li>CV: {p.cv_percent:.4f}%</li>")
        html.append(f"<li>AC limit: {p.ac_limit_percent:.4f}%</li>")
        html.append(f"<li>CV limit: {p.cv_limit_percent:.4f}%</li>")
        html.append(f"<li>Result: {'PASS' if p.passed else 'FAIL'}</li>")
        html.append("</ul>")

    html.append("</body></html>")
    path.write_text("\n".join(html), encoding="utf-8")
    return path

def export_pdf(result):
    path = OUTPUT_DIR / f"{result.metadata.inspection_id}.pdf"
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = [
        Paragraph("Nichipet QC Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Inspection ID: {result.metadata.inspection_id}", styles["BodyText"]),
        Paragraph(f"Operator: {result.metadata.operator_name}", styles["BodyText"]),
        Paragraph(f"Pipette number: {result.metadata.pipette_serial_number}", styles["BodyText"]),
        Paragraph(f"Model: {result.metadata.model_code}", styles["BodyText"]),
        Paragraph(f"Mode: {result.metadata.mode}", styles["BodyText"]),
        Paragraph(f"Decision: {result.final_use_decision}", styles["BodyText"]),
        Spacer(1, 12),
    ]

    for idx, p in enumerate(result.point_results, start=1):
        story.append(Paragraph(f"Point {idx} — {p.selected_volume_ul} μL", styles["Heading2"]))
        table = Table(
            [
                ["Mean volume", f"{p.mean_volume_ul:.4f} μL"],
                ["Systematic error", f"{p.systematic_error_percent:.4f}%"],
                ["Absolute systematic error", f"{p.absolute_systematic_error_percent:.4f}%"],
                ["CV", f"{p.cv_percent:.4f}%"],
                ["AC limit", f"{p.ac_limit_percent:.4f}%"],
                ["CV limit", f"{p.cv_limit_percent:.4f}%"],
                ["Result", "PASS" if p.passed else "FAIL"],
            ],
            colWidths=[180, 220],
        )
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ]))
        story.append(table)
        story.append(Spacer(1, 8))

    doc.build(story)
    return path

def export_csv(result):
    path = OUTPUT_DIR / f"{result.metadata.inspection_id}.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Point",
                "Selected volume (uL)",
                "Mean volume (uL)",
                "Systematic error %",
                "Absolute systematic error %",
                "CV %",
                "AC limit %",
                "CV limit %",
                "Result",
            ]
        )
        for idx, p in enumerate(result.point_results, start=1):
            writer.writerow(
                [
                    idx,
                    p.selected_volume_ul,
                    p.mean_volume_ul,
                    p.systematic_error_percent,
                    p.absolute_systematic_error_percent,
                    p.cv_percent,
                    p.ac_limit_percent,
                    p.cv_limit_percent,
                    "PASS" if p.passed else "FAIL",
                ]
            )
    return path