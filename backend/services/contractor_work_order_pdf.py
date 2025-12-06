"""
Contractor Work Order PDF Generator
Generates comprehensive, printable work orders for contractors with all task details
"""

from io import BytesIO
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ContractorWorkOrderPDF:
    """Generate contractor work order PDFs with all task details"""

    def __init__(self):
        self.font_config = FontConfiguration()

    def generate_work_order(
        self,
        labor_item: Dict[str, Any],
        quote: Dict[str, Any],
        contractor: Dict[str, Any],
        photos: List[Dict[str, Any]] = None,
        materials: List[Dict[str, Any]] = None,
        examples: List[Dict[str, Any]] = None
    ) -> bytes:
        """
        Generate complete work order PDF for contractor

        Args:
            labor_item: Labor task details
            quote: Quote information
            contractor: Contractor details
            photos: Example photos (optional)
            materials: Materials needed list (optional)
            examples: Work examples for reference (optional)

        Returns:
            bytes: PDF file content
        """
        html_content = self._generate_html(
            labor_item, quote, contractor, photos or [], materials or [], examples or []
        )

        # Convert HTML to PDF
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(
            pdf_file,
            font_config=self.font_config
        )

        pdf_file.seek(0)
        return pdf_file.read()

    def _generate_html(
        self,
        labor_item: Dict[str, Any],
        quote: Dict[str, Any],
        contractor: Dict[str, Any],
        photos: List[Dict[str, Any]],
        materials: List[Dict[str, Any]],
        examples: List[Dict[str, Any]]
    ) -> str:
        """Generate HTML content for work order"""

        task_name = labor_item.get('task_name', 'Installation Task')
        estimated_hours = labor_item.get('estimated_hours', 0)
        hourly_rate = labor_item.get('hourly_rate', 0)
        estimated_total = labor_item.get('labor_subtotal', 0)
        materials_cost = labor_item.get('materials_cost', 0)
        total_cost = labor_item.get('total_cost', 0)

        # Property/customer details
        customer_name = quote.get('customer_name', '')
        customer_phone = quote.get('customer_phone', '')
        customer_email = quote.get('customer_email', '')
        property_address = labor_item.get('work_location_address', 'See quote for details')

        # Contractor details
        contractor_name = contractor.get('company_name', '')
        contractor_phone = contractor.get('phone', '')
        contractor_email = contractor.get('email', '')

        # Access & safety notes
        access_notes = labor_item.get('access_notes', 'Contact customer for access details')
        safety_notes = labor_item.get('safety_notes', 'Follow standard safety procedures')

        # Description & scope
        description = labor_item.get('description', '')
        scope_of_work = labor_item.get('scope_of_work', '')

        # Materials needed
        materials_needed = labor_item.get('materials_needed', []) + materials

        # Generate unique work order number
        work_order_number = f"WO-{quote.get('quote_number', 'DRAFT')}-{labor_item.get('line_number', 1)}"
        issue_date = datetime.now().strftime('%B %d, %Y')

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Work Order - {work_order_number}</title>
    <style>
        @page {{
            size: letter;
            margin: 0.5in;
            @top-right {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #666;
            }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
        }}

        .header h1 {{
            font-size: 24pt;
            margin-bottom: 5px;
        }}

        .header .work-order-number {{
            font-size: 14pt;
            opacity: 0.9;
        }}

        .priority-banner {{
            background: #f59e0b;
            color: white;
            padding: 10px 20px;
            text-align: center;
            font-weight: bold;
            font-size: 12pt;
            margin-bottom: 15px;
            border-radius: 6px;
        }}

        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}

        .info-box {{
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            padding: 15px;
            background: #f9fafb;
        }}

        .info-box h3 {{
            color: #667eea;
            font-size: 12pt;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 2px solid #667eea;
        }}

        .info-row {{
            margin: 8px 0;
        }}

        .info-label {{
            font-weight: 600;
            color: #6b7280;
            display: inline-block;
            width: 120px;
        }}

        .info-value {{
            color: #111827;
        }}

        .section {{
            margin: 20px 0;
            padding: 20px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            page-break-inside: avoid;
        }}

        .section-title {{
            font-size: 14pt;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}

        .task-summary {{
            background: #eff6ff;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #3b82f6;
            margin-bottom: 15px;
        }}

        .cost-breakdown {{
            background: #f0fdf4;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #10b981;
        }}

        .cost-breakdown table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .cost-breakdown td {{
            padding: 8px 0;
            border-bottom: 1px solid #d1fae5;
        }}

        .cost-breakdown .cost-label {{
            font-weight: 600;
            color: #065f46;
        }}

        .cost-breakdown .cost-value {{
            text-align: right;
            font-weight: 600;
            color: #047857;
        }}

        .cost-breakdown .total-row {{
            border-top: 2px solid #10b981;
            border-bottom: none;
            font-size: 12pt;
        }}

        .materials-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}

        .materials-table th {{
            background: #667eea;
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: 600;
        }}

        .materials-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #e5e7eb;
        }}

        .materials-table tr:nth-child(even) {{
            background: #f9fafb;
        }}

        .checklist {{
            margin: 15px 0;
        }}

        .checklist-item {{
            padding: 10px;
            margin: 8px 0;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            background: white;
        }}

        .checkbox {{
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 2px solid #667eea;
            border-radius: 3px;
            margin-right: 10px;
            vertical-align: middle;
        }}

        .scope-section {{
            background: #fef3c7;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #f59e0b;
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 9pt;
        }}

        .alert-box {{
            background: #fee2e2;
            border: 2px solid #ef4444;
            border-radius: 6px;
            padding: 15px;
            margin: 15px 0;
        }}

        .alert-box .alert-title {{
            color: #dc2626;
            font-weight: bold;
            font-size: 11pt;
            margin-bottom: 8px;
        }}

        .alert-box .alert-content {{
            color: #991b1b;
        }}

        .success-box {{
            background: #d1fae5;
            border: 2px solid #10b981;
            border-radius: 6px;
            padding: 15px;
            margin: 15px 0;
        }}

        .success-box .success-title {{
            color: #047857;
            font-weight: bold;
            font-size: 11pt;
            margin-bottom: 8px;
        }}

        .photo-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 15px 0;
        }}

        .photo-box {{
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
        }}

        .photo-box img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            margin-bottom: 8px;
        }}

        .photo-caption {{
            font-size: 9pt;
            color: #6b7280;
            font-style: italic;
        }}

        .signature-section {{
            margin-top: 30px;
            page-break-inside: avoid;
        }}

        .signature-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }}

        .signature-box {{
            border: 1px solid #9ca3af;
            padding: 15px;
            border-radius: 6px;
        }}

        .signature-line {{
            border-bottom: 2px solid #000;
            margin: 30px 0 10px 0;
            height: 40px;
        }}

        .signature-label {{
            font-size: 9pt;
            color: #6b7280;
        }}

        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            font-size: 9pt;
            color: #6b7280;
        }}

        .page-break {{
            page-break-after: always;
        }}
    </style>
</head>
<body>

    <!-- Header -->
    <div class="header">
        <h1>🔧 WORK ORDER</h1>
        <div class="work-order-number">{work_order_number}</div>
        <div style="margin-top: 10px; font-size: 10pt;">Issued: {issue_date}</div>
    </div>

    <!-- Priority Banner (if urgent) -->
    {'<div class="priority-banner">⚠️ URGENT - Priority Installation Required</div>' if labor_item.get('priority') == 'urgent' else ''}

    <!-- Contact Information Grid -->
    <div class="info-grid">
        <!-- Customer Info -->
        <div class="info-box">
            <h3>📍 Customer / Property</h3>
            <div class="info-row">
                <span class="info-label">Customer:</span>
                <span class="info-value">{customer_name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Phone:</span>
                <span class="info-value">{customer_phone}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Email:</span>
                <span class="info-value">{customer_email}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Address:</span>
                <span class="info-value">{property_address}</span>
            </div>
        </div>

        <!-- Contractor Info -->
        <div class="info-box">
            <h3>👷 Contractor Assigned</h3>
            <div class="info-row">
                <span class="info-label">Company:</span>
                <span class="info-value">{contractor_name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Phone:</span>
                <span class="info-value">{contractor_phone}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Email:</span>
                <span class="info-value">{contractor_email}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Start Date:</span>
                <span class="info-value">{datetime.now().strftime('%B %d, %Y')}</span>
            </div>
        </div>
    </div>

    <!-- Task Summary -->
    <div class="section">
        <div class="section-title">📋 Task Summary</div>
        <div class="task-summary">
            <h3 style="font-size: 14pt; margin-bottom: 10px;">{task_name}</h3>
            <p style="color: #1f2937; line-height: 1.6;">{description}</p>
        </div>

        <div class="cost-breakdown">
            <table>
                <tr>
                    <td class="cost-label">Estimated Hours:</td>
                    <td class="cost-value">{self._format_hours(estimated_hours)} hours</td>
                </tr>
                <tr>
                    <td class="cost-label">Hourly Rate:</td>
                    <td class="cost-value">${self._format_currency(hourly_rate)}/hour</td>
                </tr>
                <tr>
                    <td class="cost-label">Labor Estimate:</td>
                    <td class="cost-value">${self._format_currency(estimated_total)}</td>
                </tr>
                <tr>
                    <td class="cost-label">Materials Estimate:</td>
                    <td class="cost-value">${self._format_currency(materials_cost)}</td>
                </tr>
                <tr class="total-row">
                    <td class="cost-label">TOTAL ESTIMATE:</td>
                    <td class="cost-value">${self._format_currency(total_cost)}</td>
                </tr>
            </table>
        </div>
    </div>

    <!-- Access & Safety Information -->
    <div class="info-grid">
        <div class="success-box">
            <div class="success-title">🔑 Access Information</div>
            <div class="success-content">{access_notes}</div>
        </div>

        <div class="alert-box">
            <div class="alert-title">⚠️ Safety Requirements</div>
            <div class="alert-content">{safety_notes}</div>
        </div>
    </div>

    <!-- Materials Needed -->
    {self._generate_materials_section(materials_needed)}

    <!-- Detailed Scope of Work -->
    {self._generate_scope_section(scope_of_work)}

    <!-- Example Photos (if provided) -->
    {self._generate_examples_section(examples)}

    <!-- Pre-Installation Checklist -->
    <div class="section">
        <div class="section-title">✅ Pre-Installation Checklist</div>
        <div class="checklist">
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Site Survey Complete:</strong> Verified all installation locations
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Materials Verified:</strong> All materials and tools accounted for
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Power Verified:</strong> Confirmed power availability at all locations
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Network Verified:</strong> Confirmed network connectivity (WiFi/Ethernet)
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Customer Contact:</strong> Spoke with customer, confirmed requirements
            </div>
        </div>
    </div>

    <!-- Installation Checklist -->
    <div class="section page-break">
        <div class="section-title">🔧 Installation Checklist</div>
        <div class="checklist">
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Unbox & Inspect:</strong> All devices inspected for damage
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Before Photos:</strong> Took before photos of all installation locations
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Installation:</strong> All devices installed per specifications
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Wiring:</strong> All wiring completed, connections secure
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Configuration:</strong> Devices configured and paired with hub
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Testing:</strong> All devices tested - lock/unlock, status reporting
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>After Photos:</strong> Took after photos showing completed work
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Cleanup:</strong> Work area cleaned, debris removed
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Customer Walkthrough:</strong> Demonstrated operation to customer
            </div>
            <div class="checklist-item">
                <span class="checkbox"></span>
                <strong>Documentation:</strong> Uploaded all photos and notes to system
            </div>
        </div>
    </div>

    <!-- Time & Materials Log -->
    <div class="section">
        <div class="section-title">⏱️ Time & Materials Log</div>

        <h4 style="margin: 15px 0 10px 0; color: #667eea;">Daily Time Log:</h4>
        <table class="materials-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Start Time</th>
                    <th>End Time</th>
                    <th>Hours</th>
                    <th>Work Performed</th>
                </tr>
            </thead>
            <tbody>
                <tr><td colspan="5" style="text-align: center; color: #6b7280; padding: 20px;">Log time entries via mobile app or record here</td></tr>
                <tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
                <tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
                <tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
            </tbody>
        </table>

        <h4 style="margin: 20px 0 10px 0; color: #667eea;">Additional Materials Used:</h4>
        <table class="materials-table">
            <thead>
                <tr>
                    <th>Material</th>
                    <th>Quantity</th>
                    <th>Unit Cost</th>
                    <th>Total</th>
                    <th>Reason</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
                <tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
                <tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
            </tbody>
        </table>
    </div>

    <!-- Notes & Issues -->
    <div class="section">
        <div class="section-title">📝 Notes & Issues</div>
        <div style="border: 1px solid #e5e7eb; border-radius: 4px; padding: 15px; min-height: 150px; background: white;">
            <p style="color: #6b7280; font-style: italic;">Record any issues, questions, or special notes here. Upload to system via mobile app.</p>
        </div>
    </div>

    <!-- Signatures -->
    <div class="signature-section">
        <div class="section-title">✍️ Completion Signatures</div>

        <div class="signature-grid">
            <div class="signature-box">
                <strong>Contractor Signature:</strong>
                <div class="signature-line"></div>
                <div class="signature-label">Name: _________________________</div>
                <div class="signature-label" style="margin-top: 5px;">Date: _________________________</div>
            </div>

            <div class="signature-box">
                <strong>Customer / Manager Approval:</strong>
                <div class="signature-line"></div>
                <div class="signature-label">Name: _________________________</div>
                <div class="signature-label" style="margin-top: 5px;">Date: _________________________</div>
            </div>
        </div>

        <div style="margin-top: 20px; padding: 15px; background: #f3f4f6; border-radius: 6px;">
            <p style="font-size: 9pt; color: #4b5563; text-align: center;">
                By signing above, both parties acknowledge that the work described in this work order has been completed
                according to specifications and is acceptable. Any variance from the estimate has been explained and approved.
            </p>
        </div>
    </div>

    <!-- Footer -->
    <div class="footer">
        <p>SomniProperty Management System | {work_order_number}</p>
        <p style="margin-top: 5px;">For questions or issues, contact Property Management at support@somniproperty.com</p>
    </div>

</body>
</html>
        """

        return html

    def _generate_materials_section(self, materials: List[Dict[str, Any]]) -> str:
        """Generate materials needed section"""
        if not materials:
            return ""

        materials_rows = ""
        for material in materials:
            name = material.get('name', 'Unknown Material')
            qty = material.get('quantity', 0)
            unit = material.get('unit', 'ea')
            cost = material.get('cost_per_unit', 0)
            total = material.get('total_cost', qty * cost if cost else 0)

            materials_rows += f"""
            <tr>
                <td>{name}</td>
                <td style="text-align: center;">{qty} {unit}</td>
                <td style="text-align: right;">${self._format_currency(cost)}</td>
                <td style="text-align: right; font-weight: 600;">${self._format_currency(total)}</td>
            </tr>
            """

        return f"""
    <div class="section">
        <div class="section-title">🔩 Materials Needed</div>
        <table class="materials-table">
            <thead>
                <tr>
                    <th>Material</th>
                    <th style="text-align: center;">Quantity</th>
                    <th style="text-align: right;">Unit Cost</th>
                    <th style="text-align: right;">Total</th>
                </tr>
            </thead>
            <tbody>
                {materials_rows}
            </tbody>
        </table>
        <p style="margin-top: 10px; font-size: 9pt; color: #6b7280; font-style: italic;">
            ⚠️ These materials should be provided. If additional materials are needed, photograph receipts and log in the system.
        </p>
    </div>
        """

    def _generate_scope_section(self, scope: str) -> str:
        """Generate detailed scope of work section"""
        if not scope:
            return ""

        return f"""
    <div class="section">
        <div class="section-title">📐 Detailed Scope of Work</div>
        <div class="scope-section">{scope}</div>
    </div>
        """

    def _generate_examples_section(self, examples: List[Dict[str, Any]]) -> str:
        """Generate example photos section"""
        if not examples:
            return ""

        photo_boxes = ""
        for example in examples[:4]:  # Limit to 4 examples
            photo_url = example.get('primary_photo_url', '')
            title = example.get('example_title', 'Example Work')
            description = example.get('example_description', '')

            photo_boxes += f"""
            <div class="photo-box">
                <img src="{photo_url}" alt="{title}" />
                <div class="photo-caption"><strong>{title}</strong></div>
                <div class="photo-caption">{description[:100]}...</div>
            </div>
            """

        return f"""
    <div class="section page-break">
        <div class="section-title">📸 Example Work for Reference</div>
        <p style="margin-bottom: 15px; color: #6b7280;">
            These are examples of similar installations we've completed. Use these as reference for quality and best practices.
        </p>
        <div class="photo-grid">
            {photo_boxes}
        </div>
    </div>
        """

    def _format_currency(self, amount) -> str:
        """Format currency value"""
        if amount is None:
            amount = 0
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        return f"{amount:,.2f}"

    def _format_hours(self, hours) -> str:
        """Format hours value"""
        if hours is None:
            hours = 0
        if not isinstance(hours, Decimal):
            hours = Decimal(str(hours))
        return f"{hours:.1f}"


# Utility function for easy import
async def generate_contractor_work_order(
    labor_item: Dict[str, Any],
    quote: Dict[str, Any],
    contractor: Dict[str, Any],
    photos: List[Dict[str, Any]] = None,
    materials: List[Dict[str, Any]] = None,
    examples: List[Dict[str, Any]] = None
) -> bytes:
    """
    Generate a contractor work order PDF

    Args:
        labor_item: Labor task details
        quote: Quote information
        contractor: Contractor details
        photos: Example photos (optional)
        materials: Materials needed list (optional)
        examples: Work examples for reference (optional)

    Returns:
        bytes: PDF file content
    """
    generator = ContractorWorkOrderPDF()
    return generator.generate_work_order(
        labor_item, quote, contractor, photos or [], materials or [], examples or []
    )
