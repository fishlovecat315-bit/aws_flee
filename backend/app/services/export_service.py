import csv
import io
from decimal import Decimal


class ExportService:
    HEADERS = ["date", "department", "account_name", "tag_value", "business_module", "amount_usd"]

    def export_excel(self, data: list[dict]) -> bytes:
        """Generate .xlsx file using openpyxl and return bytes."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "AWS Costs"

        ws.append(self.HEADERS)

        for row in data:
            ws.append([
                str(row.get("date", "")),
                row.get("department", ""),
                row.get("account_name", ""),
                row.get("tag_value", ""),
                row.get("business_module", ""),
                float(row.get("amount_usd", 0)),
            ])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf.read()

    def export_csv(self, data: list[dict]) -> bytes:
        """Generate .csv file using csv module and return UTF-8 BOM bytes."""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=self.HEADERS, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            writer.writerow({
                "date": str(row.get("date", "")),
                "department": row.get("department", ""),
                "account_name": row.get("account_name", ""),
                "tag_value": row.get("tag_value", ""),
                "business_module": row.get("business_module", ""),
                "amount_usd": str(row.get("amount_usd", "")),
            })
        # UTF-8 BOM for Excel compatibility
        return ("\ufeff" + buf.getvalue()).encode("utf-8")

    def export_pdf(self, data: list[dict]) -> bytes:
        """Generate .pdf file using WeasyPrint and return bytes."""
        from weasyprint import HTML

        rows_html = ""
        for row in data:
            amount = row.get("amount_usd", Decimal("0"))
            rows_html += (
                f"<tr>"
                f"<td>{row.get('date', '')}</td>"
                f"<td>{row.get('department', '')}</td>"
                f"<td>{row.get('account_name', '')}</td>"
                f"<td>{row.get('tag_value', '')}</td>"
                f"<td>{row.get('business_module', '')}</td>"
                f"<td>{amount}</td>"
                f"</tr>"
            )

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; font-size: 12px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 4px 8px; text-align: left; }}
  th {{ background-color: #f0f0f0; font-weight: bold; }}
</style>
</head>
<body>
<h2>AWS Cost Report</h2>
<table>
  <thead>
    <tr>
      <th>Date</th><th>Department</th><th>Account</th>
      <th>Tag Value</th><th>Business Module</th><th>Amount (USD)</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>
</body>
</html>"""

        return HTML(string=html).write_pdf()
