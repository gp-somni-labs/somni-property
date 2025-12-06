"""
Quote Email Service - SendGrid Integration

Sends professional quote emails to customers with PDF attachments and portal links
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
import base64
from pathlib import Path

from core.config import settings


class QuoteEmailService:
    """
    Send quote emails via SendGrid

    Features:
    - Professional HTML email templates
    - PDF quote attachment
    - Customer portal link
    - Tracking and analytics
    """

    def __init__(self):
        """Initialize SendGrid client"""
        self.api_key = os.getenv('SENDGRID_API_KEY')
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY environment variable not set")

        self.client = SendGridAPIClient(self.api_key)
        self.from_email = os.getenv('SENDGRID_FROM_EMAIL', 'quotes@somniproperty.com')
        self.from_name = os.getenv('SENDGRID_FROM_NAME', 'SomniProperty')
        self.reply_to = os.getenv('SENDGRID_REPLY_TO', 'support@somniproperty.com')

    async def send_quote_email(
        self,
        quote: Dict[str, Any],
        pdf_content: bytes,
        customer_portal_url: str
    ) -> bool:
        """
        Send quote email to customer

        Args:
            quote: Quote dictionary with customer info
            pdf_content: PDF file bytes
            customer_portal_url: Secure portal link

        Returns:
            bool: True if sent successfully
        """
        try:
            # Build email
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(quote['customer_email'], quote['customer_name']),
                subject=f"Your Property Management Quote - {quote['quote_number']}",
                html_content=self._generate_email_html(quote, customer_portal_url)
            )

            # Set reply-to
            message.reply_to = Email(self.reply_to)

            # Attach PDF
            attachment = Attachment()
            attachment.file_content = FileContent(base64.b64encode(pdf_content).decode())
            attachment.file_type = FileType('application/pdf')
            attachment.file_name = FileName(f"Quote-{quote['quote_number']}.pdf")
            attachment.disposition = Disposition('attachment')
            message.attachment = attachment

            # Send email
            response = self.client.send(message)

            return response.status_code in [200, 201, 202]

        except Exception as e:
            print(f"Failed to send quote email: {e}")
            return False

    async def send_quote_reminder(
        self,
        quote: Dict[str, Any],
        customer_portal_url: str,
        days_until_expiry: int
    ) -> bool:
        """
        Send reminder email about expiring quote

        Args:
            quote: Quote dictionary
            customer_portal_url: Portal link
            days_until_expiry: Days until quote expires

        Returns:
            bool: True if sent successfully
        """
        try:
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(quote['customer_email'], quote['customer_name']),
                subject=f"Reminder: Your Quote Expires in {days_until_expiry} Days - {quote['quote_number']}",
                html_content=self._generate_reminder_html(quote, customer_portal_url, days_until_expiry)
            )

            message.reply_to = Email(self.reply_to)

            response = self.client.send(message)
            return response.status_code in [200, 201, 202]

        except Exception as e:
            print(f"Failed to send reminder email: {e}")
            return False

    async def send_quote_accepted_notification(
        self,
        quote: Dict[str, Any],
        admin_emails: list[str]
    ) -> bool:
        """
        Notify admin when customer accepts quote

        Args:
            quote: Quote dictionary
            admin_emails: List of admin email addresses

        Returns:
            bool: True if sent successfully
        """
        try:
            for admin_email in admin_emails:
                message = Mail(
                    from_email=Email(self.from_email, self.from_name),
                    to_emails=To(admin_email),
                    subject=f"Quote Accepted! {quote['quote_number']} - {quote['customer_name']}",
                    html_content=self._generate_acceptance_notification_html(quote)
                )

                self.client.send(message)

            return True

        except Exception as e:
            print(f"Failed to send acceptance notification: {e}")
            return False

    def _generate_email_html(self, quote: Dict[str, Any], portal_url: str) -> str:
        """Generate HTML email for quote delivery"""

        # Format currency
        monthly_total = f"${quote['monthly_total']:,.2f}" if quote.get('monthly_total') else "$0.00"
        annual_total = f"${quote['annual_total']:,.2f}" if quote.get('annual_total') else "$0.00"

        # Format expiry date
        valid_until = quote.get('valid_until')
        if isinstance(valid_until, str):
            valid_until = datetime.fromisoformat(valid_until.replace('Z', '+00:00'))
        expiry_str = valid_until.strftime('%B %d, %Y') if valid_until else 'N/A'

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            background: white;
            padding: 30px;
            border: 1px solid #e5e7eb;
            border-top: none;
        }}
        .pricing-box {{
            background: #f9fafb;
            border: 2px solid #667eea;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
        }}
        .pricing-box .amount {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .pricing-box .period {{
            color: #6b7280;
            font-size: 14px;
        }}
        .cta-button {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }}
        .cta-button:hover {{
            background: #5568d3;
        }}
        .details {{
            margin: 20px 0;
            padding: 15px;
            background: #f9fafb;
            border-left: 4px solid #667eea;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #6b7280;
            font-size: 12px;
            border-top: 1px solid #e5e7eb;
            margin-top: 30px;
        }}
        .expiry-notice {{
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            padding: 12px;
            margin: 15px 0;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏢 Your Property Management Quote</h1>
        <p style="margin: 10px 0 0 0; font-size: 16px;">Quote #{quote['quote_number']}</p>
    </div>

    <div class="content">
        <p>Hello {quote['customer_name']},</p>

        <p>Thank you for your interest in SomniProperty! We're excited to share our customized quote for managing your {quote.get('total_units', 0)} units.</p>

        <div class="pricing-box">
            <div style="color: #6b7280; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Monthly Investment</div>
            <div class="amount">{monthly_total}</div>
            <div class="period">per month</div>
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
                <strong>Annual Total:</strong> {annual_total}
            </div>
        </div>

        <div class="expiry-notice">
            ⏰ <strong>Valid Until:</strong> {expiry_str}
        </div>

        <div style="text-align: center;">
            <a href="{portal_url}" class="cta-button">
                📄 View Interactive Quote
            </a>
        </div>

        <div class="details">
            <h3 style="margin-top: 0;">What's Included:</h3>
            <ul style="margin: 10px 0;">
                <li>Full property management services</li>
                <li>Tenant portal and rent collection</li>
                <li>Maintenance coordination</li>
                <li>Financial reporting and analytics</li>
                {"<li>Smart home services for " + str(int(quote.get('total_units', 0) * quote.get('smart_home_penetration', 0) / 100)) + " units</li>" if quote.get('include_smart_home') else ""}
            </ul>
        </div>

        <p><strong>Next Steps:</strong></p>
        <ol>
            <li>Review the attached PDF quote</li>
            <li>Visit your <a href="{portal_url}">interactive portal</a> to explore visual assets and 3D property scans</li>
            <li>Ask questions or request modifications</li>
            <li>Accept the quote directly through the portal</li>
        </ol>

        <p>Have questions? Simply reply to this email or call us at (555) 123-4567. We're here to help!</p>

        <p>Best regards,<br>
        <strong>The SomniProperty Team</strong></p>
    </div>

    <div class="footer">
        <p>SomniProperty - Professional Property Management & Smart Building Solutions</p>
        <p>This quote was generated on {datetime.utcnow().strftime('%B %d, %Y')}</p>
        <p style="margin-top: 10px;">
            <a href="{portal_url}" style="color: #667eea;">View in Portal</a> |
            <a href="mailto:{self.reply_to}" style="color: #667eea;">Contact Support</a>
        </p>
    </div>
</body>
</html>
        """

        return html

    def _generate_reminder_html(self, quote: Dict[str, Any], portal_url: str, days_until_expiry: int) -> str:
        """Generate HTML for expiration reminder"""

        monthly_total = f"${quote['monthly_total']:,.2f}" if quote.get('monthly_total') else "$0.00"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .urgent-header {{
            background: linear-gradient(135deg, #f59e0b 0%, #dc2626 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
            border-radius: 8px 8px 0 0;
        }}
        .content {{
            background: white;
            padding: 30px;
            border: 1px solid #e5e7eb;
        }}
        .cta-button {{
            display: inline-block;
            background: #dc2626;
            color: white;
            padding: 14px 32px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }}
        .countdown {{
            background: #fef3c7;
            border: 2px solid #f59e0b;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }}
        .countdown .number {{
            font-size: 48px;
            font-weight: bold;
            color: #dc2626;
        }}
    </style>
</head>
<body>
    <div class="urgent-header">
        <h1>⏰ Quote Expiring Soon!</h1>
    </div>

    <div class="content">
        <p>Hello {quote['customer_name']},</p>

        <p>This is a friendly reminder that your property management quote is expiring soon.</p>

        <div class="countdown">
            <div class="number">{days_until_expiry}</div>
            <div>days remaining</div>
        </div>

        <p><strong>Quote #{quote['quote_number']}</strong><br>
        Monthly Investment: <strong>{monthly_total}/month</strong></p>

        <div style="text-align: center;">
            <a href="{portal_url}" class="cta-button">
                Review & Accept Quote
            </a>
        </div>

        <p>Don't miss out on this customized pricing for your {quote.get('total_units', 0)} units. Accept your quote now to lock in these rates!</p>

        <p>Questions? Reply to this email or call us at (555) 123-4567.</p>

        <p>Best regards,<br>
        <strong>The SomniProperty Team</strong></p>
    </div>
</body>
</html>
        """

        return html

    def _generate_acceptance_notification_html(self, quote: Dict[str, Any]) -> str:
        """Generate HTML for admin notification when quote is accepted"""

        monthly_total = f"${quote['monthly_total']:,.2f}" if quote.get('monthly_total') else "$0.00"
        annual_total = f"${quote['annual_total']:,.2f}" if quote.get('annual_total') else "$0.00"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .success-header {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
            border-radius: 8px;
        }}
        .content {{
            background: white;
            padding: 30px;
            border: 1px solid #e5e7eb;
        }}
        .details-box {{
            background: #f0fdf4;
            border: 1px solid #10b981;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="success-header">
        <h1>🎉 Quote Accepted!</h1>
    </div>

    <div class="content">
        <p><strong>Great news!</strong> A customer has accepted their quote.</p>

        <div class="details-box">
            <h3 style="margin-top: 0;">Quote Details</h3>
            <p><strong>Quote Number:</strong> {quote['quote_number']}</p>
            <p><strong>Customer:</strong> {quote['customer_name']}</p>
            <p><strong>Email:</strong> {quote.get('customer_email', 'N/A')}</p>
            <p><strong>Company:</strong> {quote.get('company_name', 'N/A')}</p>
            <p><strong>Units:</strong> {quote.get('total_units', 0)}</p>
            <p><strong>Monthly Revenue:</strong> {monthly_total}</p>
            <p><strong>Annual Revenue:</strong> {annual_total}</p>
        </div>

        <p><strong>Next Steps:</strong></p>
        <ol>
            <li>Contact the customer to schedule onboarding</li>
            <li>Generate service contract in the system</li>
            <li>Set up property in management platform</li>
            <li>Schedule initial property walkthrough</li>
        </ol>

        <p>Log into the admin portal to view full quote details and begin the onboarding process.</p>
    </div>
</body>
</html>
        """

        return html


# Singleton instance
quote_email_service = QuoteEmailService() if os.getenv('SENDGRID_API_KEY') else None
