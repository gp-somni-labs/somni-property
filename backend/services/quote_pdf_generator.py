"""
Quote PDF Generator Service

Generates professional PDF quotes using WeasyPrint and HTML templates
Enhanced for comprehensive quote system with subscription tiers and domain-organized products
"""

import logging
from typing import Optional
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from utils.quote_disclaimers import format_disclaimers_for_pdf

logger = logging.getLogger(__name__)


class QuotePDFGenerator:
    """
    Generate professional PDF quotes

    Uses HTML/CSS templates for easy customization and branding
    """

    def __init__(self):
        self.font_config = FontConfiguration()
        self.line_items = []
        self.labor_items = []

    def generate_pdf(self, quote: dict, line_items: list, labor_items: list = None) -> bytes:
        """
        Generate PDF from quote data

        Args:
            quote: Quote dictionary with all quote fields
            line_items: List of quote line item dictionaries
            labor_items: List of labor item dictionaries (optional)

        Returns:
            bytes: PDF file content
        """
        # Store line items and labor items for total calculations
        self.line_items = line_items
        self.labor_items = labor_items or []

        # Generate HTML from template
        html_content = self._generate_html(quote, line_items, self.labor_items)

        # Convert HTML to PDF
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(
            pdf_file,
            stylesheets=[CSS(string=self._get_css())],
            font_config=self.font_config
        )

        pdf_file.seek(0)
        return pdf_file.read()

    def _generate_html(self, quote: dict, line_items: list, labor_items: list) -> str:
        """Generate HTML content for the quote"""

        # Format dates
        created_date = self._format_date(quote.get('created_at'))
        valid_until = self._format_date(quote.get('valid_until'))

        # Get subscription information
        billing_period = quote.get('billing_period', 'monthly')

        # Build sections
        subscription_section = self._generate_subscription_section(quote, line_items)
        products_section = self._generate_products_section(quote, line_items)
        # Use comprehensive labor items if available, otherwise fall back to simple installation section
        installation_section = self._generate_labor_section(quote, labor_items) if labor_items else self._generate_installation_section(quote, line_items)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Quote {quote.get('quote_number', 'N/A')}</title>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="company-info">
            <h1 class="company-name">SomniProperty</h1>
            <p class="tagline">Professional Property Management & Smart Building Solutions</p>
        </div>
        <div class="quote-info">
            <h2 class="quote-number">Quote #{quote.get('quote_number', 'N/A')}</h2>
            <p class="quote-date">Date: {created_date}</p>
            <p class="valid-until">Valid Until: {valid_until}</p>
            <div class="billing-badge">{billing_period.title()} Billing</div>
        </div>
    </div>

    <!-- Status Badge -->
    <div class="status-badge status-{quote.get('status', 'draft')}">
        {quote.get('status', 'draft').upper()}
    </div>

    <!-- Customer Information -->
    <div class="section">
        <h3 class="section-title">Customer Information</h3>
        <table class="info-table">
            <tr>
                <td class="label">Customer Name:</td>
                <td class="value">{quote.get('customer_name', 'N/A')}</td>
                <td class="label">Company:</td>
                <td class="value">{quote.get('company_name', 'N/A') or 'N/A'}</td>
            </tr>
            <tr>
                <td class="label">Email:</td>
                <td class="value">{quote.get('customer_email', 'N/A') or 'N/A'}</td>
                <td class="label">Phone:</td>
                <td class="value">{quote.get('customer_phone', 'N/A') or 'N/A'}</td>
            </tr>
        </table>
    </div>

    <!-- Property Information -->
    {self._generate_property_metadata_section(quote)}

    <!-- Subscription Tiers -->
    {subscription_section}

    <!-- Products & Hardware -->
    {products_section}

    <!-- Installation & Labor -->
    {installation_section}

    <!-- Grand Total Summary -->
    {self._generate_grand_total_section(quote)}

    <!-- Notes -->
    {self._generate_notes_section(quote)}

    <!-- Terms & Conditions -->
    <div class="section terms">
        <h3 class="section-title">Terms & Conditions</h3>
        <p class="terms-text">
            {quote.get('terms_conditions', self._get_default_terms())}
        </p>
    </div>

    <!-- Price Increase Disclaimers -->
    {self._generate_disclaimers_section(quote)}

    <!-- Visual Assets -->
    {self._generate_device_placement_section(quote)}
    {self._generate_floor_plans_section(quote)}
    {self._generate_polycam_section(quote)}
    {self._generate_implementation_photos_section(quote)}
    {self._generate_comparison_photos_section(quote)}

    <!-- Footer -->
    <div class="footer">
        <p class="footer-company">SomniProperty | Professional Property Management Solutions</p>
        <p class="footer-contact">Email: sales@somniproperty.com | Phone: (555) 123-4567</p>
        <p class="footer-note">This quote is valid until {valid_until}. All prices in USD.</p>
        <p class="footer-thanks">Thank you for considering SomniProperty for your smart building needs!</p>
    </div>
</body>
</html>
        """

        return html

    def _generate_property_metadata_section(self, quote: dict) -> str:
        """Generate property information section"""
        total_units = quote.get('total_units')
        property_count = quote.get('property_count', 1)
        property_locations = quote.get('property_locations', [])
        property_types = quote.get('property_types', [])
        smart_home_penetration = quote.get('smart_home_penetration')

        # Skip if no meaningful property data
        if not any([total_units, property_locations, property_types, smart_home_penetration]):
            return ''

        html = '''
        <div class="section property-section">
            <h3 class="section-title">🏠 Property Information</h3>
            <table class="info-table">
        '''

        # Row 1: Units and Properties
        if total_units or property_count:
            html += f'''
                <tr>
                    <td class="label">Total Units:</td>
                    <td class="value">{total_units or 'N/A'} units</td>
                    <td class="label">Properties:</td>
                    <td class="value">{property_count} {('property' if property_count == 1 else 'properties')}</td>
                </tr>
            '''

        # Row 2: Property Types and Smart Home Penetration
        if property_types or smart_home_penetration:
            property_types_str = ', '.join(property_types) if property_types else 'N/A'
            smart_home_str = f"{smart_home_penetration}%" if smart_home_penetration else 'N/A'
            html += f'''
                <tr>
                    <td class="label">Property Types:</td>
                    <td class="value">{property_types_str}</td>
                    <td class="label">Smart Home Coverage:</td>
                    <td class="value">{smart_home_str}</td>
                </tr>
            '''

        # Row 3: Locations (if provided)
        if property_locations:
            locations_str = ', '.join(property_locations)
            html += f'''
                <tr>
                    <td class="label">Locations:</td>
                    <td class="value" colspan="3">{locations_str}</td>
                </tr>
            '''

        html += '''
            </table>
        </div>
        '''

        return html

    def _generate_subscription_section(self, quote: dict, line_items: list) -> str:
        """Generate subscription tiers section"""
        # Filter subscription line items
        subscription_items = [item for item in line_items if item.get('category', '').startswith('subscription_')]

        if not subscription_items:
            return ''

        billing_period = quote.get('billing_period', 'monthly')
        period_label = '/yr' if billing_period == 'annual' else '/mo'

        html = '''
        <div class="section subscription-section">
            <h3 class="section-title">📅 Subscription Services</h3>
            <p class="section-description">Monthly recurring services for ongoing support and monitoring:</p>
            <table class="subscription-table">
                <thead>
                    <tr>
                        <th>Service Type</th>
                        <th>Tier Selected</th>
                        <th>Price</th>
                    </tr>
                </thead>
                <tbody>
        '''

        subscription_total = Decimal('0')
        for item in subscription_items:
            service_type = item.get('category', '').replace('subscription_', '').replace('_', ' ').title()
            tier_name = item.get('description', '').split(' - ')[0]
            price = Decimal(str(item.get('unit_price', 0)))
            subscription_total += price

            html += f'''
                <tr>
                    <td class="service-type">{service_type}</td>
                    <td class="tier-name">
                        <span class="tier-badge">{tier_name}</span>
                    </td>
                    <td class="price-cell">${self._format_currency(price)}{period_label}</td>
                </tr>
            '''

        html += f'''
                </tbody>
                <tfoot>
                    <tr class="total-row">
                        <td colspan="2"><strong>Subscription Total</strong></td>
                        <td class="price-cell"><strong>${self._format_currency(subscription_total)}{period_label}</strong></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        '''

        return html

    def _generate_products_section(self, quote: dict, line_items: list) -> str:
        """Generate domain-organized products section"""
        # Group products by domain
        domains = {}
        for item in line_items:
            category = item.get('category', '')
            # Skip subscription and installation items
            if category.startswith('subscription_') or category == 'installation':
                continue

            if category not in domains:
                domains[category] = []
            domains[category].append(item)

        if not domains:
            return ''

        # Domain icons
        domain_icons = {
            'network': '🌐',
            'lighting': '💡',
            'security': '🎥',
            'locks': '🔐',
            'climate': '🌡️',
            'sensors': '📡'
        }

        html = '''
        <div class="section products-section">
            <h3 class="section-title">🛒 Products & Hardware</h3>
            <p class="section-description">One-time hardware purchases organized by domain:</p>
        '''

        hardware_subtotal = Decimal('0')

        for domain, items in domains.items():
            icon = domain_icons.get(domain, '📦')
            domain_name = domain.replace('_', ' ').title()
            domain_total = sum(Decimal(str(item.get('subtotal', 0))) for item in items)
            hardware_subtotal += domain_total

            html += f'''
            <div class="domain-group">
                <h4 class="domain-header">{icon} {domain_name}</h4>
                <table class="products-table">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Vendor</th>
                            <th>Qty</th>
                            <th>Unit Price</th>
                            <th>Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>
            '''

            for item in items:
                html += f'''
                    <tr>
                        <td class="product-name">{item.get('description', 'N/A')}</td>
                        <td class="vendor-name">{item.get('vendor', 'N/A')}</td>
                        <td class="qty-cell">{item.get('quantity', 1)}</td>
                        <td class="price-cell">${self._format_currency(item.get('unit_price', 0))}</td>
                        <td class="price-cell">${self._format_currency(item.get('subtotal', 0))}</td>
                    </tr>
                '''

            html += f'''
                    </tbody>
                    <tfoot>
                        <tr class="domain-total">
                            <td colspan="4">{domain_name} Total</td>
                            <td class="price-cell"><strong>${self._format_currency(domain_total)}</strong></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            '''

        # Calculate bulk discount
        bulk_discount = self._calculate_bulk_discount(quote, line_items)
        hardware_total = hardware_subtotal - Decimal(str(bulk_discount))

        html += f'''
            <div class="hardware-summary">
                <table class="summary-table">
                    <tr>
                        <td class="summary-label">Hardware Subtotal:</td>
                        <td class="summary-value">${self._format_currency(hardware_subtotal)}</td>
                    </tr>
        '''

        if bulk_discount > 0:
            discount_info = self._get_bulk_discount_info(line_items)
            html += f'''
                    <tr class="discount-row">
                        <td class="summary-label">Bulk Discount ({discount_info}):</td>
                        <td class="summary-value discount">-${self._format_currency(bulk_discount)}</td>
                    </tr>
            '''

        html += f'''
                    <tr class="summary-total">
                        <td class="summary-label">Hardware Total:</td>
                        <td class="summary-value">${self._format_currency(hardware_total)}</td>
                    </tr>
                </table>
            </div>
        </div>
        '''

        return html

    def _generate_installation_section(self, quote: dict, line_items: list) -> str:
        """Generate installation & labor section"""
        installation_items = [item for item in line_items if item.get('category') == 'installation']

        if not installation_items:
            return ''

        installation_hours = quote.get('installation_hours', 2.0)
        installation_rate = quote.get('installation_rate', 150)
        included_hours = 2.0
        billable_hours = max(0, float(installation_hours) - included_hours)

        html = '''
        <div class="section installation-section">
            <h3 class="section-title">🔧 Installation & Labor</h3>
            <table class="installation-table">
                <tbody>
        '''

        for item in installation_items:
            description = item.get('description', '')
            subtotal = item.get('subtotal', 0)

            if 'included' in description.lower():
                html += f'''
                    <tr class="included-row">
                        <td class="install-desc">{description}</td>
                        <td class="install-hours">{included_hours:.1f} hours</td>
                        <td class="install-price">Included</td>
                    </tr>
                '''
            else:
                html += f'''
                    <tr>
                        <td class="install-desc">{description}</td>
                        <td class="install-hours">{billable_hours:.1f} hours @ ${installation_rate}/hr</td>
                        <td class="install-price">${self._format_currency(subtotal)}</td>
                    </tr>
                '''

        installation_total = quote.get('one_time_installation_total', 0)

        html += f'''
                </tbody>
                <tfoot>
                    <tr class="total-row">
                        <td colspan="2"><strong>Installation Total</strong></td>
                        <td class="install-price"><strong>${self._format_currency(installation_total)}</strong></td>
                    </tr>
                </tfoot>
            </table>
            <p class="installation-note">
                Total estimated installation time: {installation_hours:.1f} hours
                ({included_hours:.1f} hours included + {billable_hours:.1f} hours @ ${installation_rate}/hr)
            </p>
        </div>
        '''

        return html

    def _generate_labor_section(self, quote: dict, labor_items: list) -> str:
        """Generate comprehensive labor & installation section from QuoteLaborItem data"""
        if not labor_items or len(labor_items) == 0:
            return ''

        # Group labor items by category
        categories = {}
        for item in labor_items:
            category = item.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)

        # Category icons
        category_icons = {
            'Installation': '🔧',
            'Configuration': '⚙️',
            'Testing': '✅',
            'Training': '📚',
            'Project Management': '📋'
        }

        # Calculate totals
        total_labor_hours = sum(Decimal(str(item.get('estimated_hours', 0))) for item in labor_items)
        total_labor_cost = sum(Decimal(str(item.get('labor_subtotal', 0))) for item in labor_items)
        total_materials_cost = sum(Decimal(str(item.get('materials_cost', 0))) for item in labor_items)
        total_cost = total_labor_cost + total_materials_cost

        html = '''
        <div class="section labor-section">
            <h3 class="section-title">🔧 Installation & Labor</h3>
            <p class="section-description">Detailed breakdown of installation, configuration, and support services:</p>
        '''

        # Display each category
        for category, items in categories.items():
            icon = category_icons.get(category, '📦')
            category_total_hours = sum(Decimal(str(item.get('estimated_hours', 0))) for item in items)
            category_total_cost = sum(Decimal(str(item.get('total_cost', 0))) for item in items)

            html += f'''
            <div class="labor-category-group">
                <h4 class="labor-category-header">{icon} {category}</h4>
                <table class="labor-table">
                    <thead>
                        <tr>
                            <th>Task</th>
                            <th>Hours</th>
                            <th>Rate</th>
                            <th>Labor</th>
                            <th>Materials</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
            '''

            for item in items:
                task_name = item.get('task_name', 'Task')
                description = item.get('description', '')
                estimated_hours = Decimal(str(item.get('estimated_hours', 0)))
                hourly_rate = Decimal(str(item.get('hourly_rate', 0)))
                labor_subtotal = Decimal(str(item.get('labor_subtotal', 0)))
                materials_cost = Decimal(str(item.get('materials_cost', 0)))
                total_item_cost = Decimal(str(item.get('total_cost', 0)))
                materials_needed = item.get('materials_needed', [])

                html += f'''
                    <tr class="labor-item-row">
                        <td class="labor-task">
                            <div class="labor-task-name">{task_name}</div>
                            <div class="labor-task-desc">{description}</div>
                '''

                # Add materials breakdown if materials exist
                if materials_needed:
                    html += '<div class="materials-list"><strong>Materials:</strong> '
                    material_names = [m.get('name', '') for m in materials_needed[:3]]  # Show first 3
                    html += ', '.join(material_names)
                    if len(materials_needed) > 3:
                        html += f' +{len(materials_needed) - 3} more'
                    html += '</div>'

                html += f'''
                        </td>
                        <td class="labor-hours">{self._format_hours(estimated_hours)} hrs</td>
                        <td class="labor-rate">${self._format_currency(hourly_rate)}/hr</td>
                        <td class="labor-cost">${self._format_currency(labor_subtotal)}</td>
                        <td class="materials-cost">${self._format_currency(materials_cost)}</td>
                        <td class="total-cost">${self._format_currency(total_item_cost)}</td>
                    </tr>
                '''

            html += f'''
                    </tbody>
                    <tfoot>
                        <tr class="category-total-row">
                            <td colspan="4"><strong>{category} Subtotal</strong> ({self._format_hours(category_total_hours)} hours)</td>
                            <td colspan="2" class="total-cost"><strong>${self._format_currency(category_total_cost)}</strong></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            '''

        # Grand total for labor section
        html += f'''
            <div class="labor-summary">
                <table class="summary-table">
                    <tr>
                        <td class="summary-label">Total Labor Hours:</td>
                        <td class="summary-value">{self._format_hours(total_labor_hours)} hours</td>
                    </tr>
                    <tr>
                        <td class="summary-label">Total Labor Cost:</td>
                        <td class="summary-value">${self._format_currency(total_labor_cost)}</td>
                    </tr>
                    <tr>
                        <td class="summary-label">Total Materials Cost:</td>
                        <td class="summary-value">${self._format_currency(total_materials_cost)}</td>
                    </tr>
                    <tr class="summary-total">
                        <td class="summary-label">Installation & Labor Total:</td>
                        <td class="summary-value">${self._format_currency(total_cost)}</td>
                    </tr>
                </table>
            </div>
        </div>
        '''

        return html

    def _format_hours(self, hours) -> str:
        """Format hours with proper decimal places"""
        if hours is None:
            hours = 0
        if not isinstance(hours, Decimal):
            hours = Decimal(str(hours))
        return f"{hours:.1f}"

    def _generate_grand_total_section(self, quote: dict) -> str:
        """Generate grand total summary with year 1 and year 2+ costs"""
        # Calculate totals from line items based on item_type
        one_time_hardware = Decimal('0.00')
        monthly_subscription = Decimal('0.00')

        for item in self.line_items:
            item_type = item.get('item_type', '').lower()
            subtotal = Decimal(str(item.get('subtotal', 0)))

            # Categorize items
            if item_type in ['hardware', 'one-time', 'one_time', 'equipment', 'device']:
                one_time_hardware += subtotal
            elif item_type in ['subscription', 'recurring', 'monthly', 'service', 'fee']:
                monthly_subscription += subtotal
            else:
                # Default: treat as monthly subscription (most common in property management)
                monthly_subscription += subtotal

        # Calculate installation labor from labor items
        one_time_installation = Decimal('0.00')
        for labor_item in self.labor_items:
            one_time_installation += Decimal(str(labor_item.get('total_cost', 0)))

        one_time_total = one_time_hardware + one_time_installation

        # If we couldn't calculate monthly from line items, use quote total
        if monthly_subscription == 0 and not self.line_items:
            monthly_subscription = Decimal(str(quote.get('monthly_total', 0)))

        billing_period = quote.get('billing_period', 'monthly')

        if billing_period == 'annual':
            annual_subscription = monthly_subscription
            monthly_equivalent = monthly_subscription / 12
        else:
            annual_subscription = monthly_subscription * 12
            monthly_equivalent = monthly_subscription

        year_1_total = one_time_total + annual_subscription
        year_2_plus = annual_subscription

        # Calculate savings for annual billing
        savings_html = ''
        if billing_period == 'annual':
            monthly_cost = Decimal(str(quote.get('monthly_total', 0)))
            if monthly_cost > 0:
                annual_if_monthly = monthly_cost * 12
                savings = annual_if_monthly - annual_subscription
                if savings > 0:
                    savings_html = f'''
                    <div class="savings-callout">
                        <div class="savings-icon">💰</div>
                        <div class="savings-text">
                            <strong>Annual Savings:</strong> You're saving ${self._format_currency(savings)}
                            with annual billing (17% discount)!
                        </div>
                    </div>
                    '''

        html = f'''
        <div class="section grand-total-section">
            <h3 class="section-title">💵 Quote Totals</h3>

            {savings_html}

            <table class="grand-total-table">
                <tbody>
                    <tr class="section-header">
                        <td colspan="2"><strong>One-Time Costs</strong></td>
                    </tr>
                    <tr>
                        <td class="summary-label">Hardware & Equipment:</td>
                        <td class="summary-value">${self._format_currency(one_time_hardware)}</td>
                    </tr>
                    <tr>
                        <td class="summary-label">Installation Labor:</td>
                        <td class="summary-value">${self._format_currency(one_time_installation)}</td>
                    </tr>
                    <tr class="subtotal-row">
                        <td class="summary-label">One-Time Total:</td>
                        <td class="summary-value">${self._format_currency(one_time_total)}</td>
                    </tr>

                    <tr class="section-header">
                        <td colspan="2"><strong>Recurring Costs</strong></td>
                    </tr>
                    <tr>
                        <td class="summary-label">Monthly Subscription:</td>
                        <td class="summary-value">${self._format_currency(monthly_equivalent)}/mo</td>
                    </tr>
                    <tr class="subtotal-row">
                        <td class="summary-label">Annual Subscription:</td>
                        <td class="summary-value">${self._format_currency(annual_subscription)}/yr</td>
                    </tr>

                    <tr class="year-1-total">
                        <td class="summary-label">
                            <strong>Year 1 Total</strong>
                            <div class="sublabel">(One-time + First year subscription)</div>
                        </td>
                        <td class="summary-value"><strong>${self._format_currency(year_1_total)}</strong></td>
                    </tr>

                    <tr class="year-2-total">
                        <td class="summary-label">
                            <strong>Year 2+ Annual Cost</strong>
                            <div class="sublabel">(Subscription only)</div>
                        </td>
                        <td class="summary-value"><strong>${self._format_currency(year_2_plus)}/yr</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
        '''

        return html

    def _calculate_bulk_discount(self, quote: dict, line_items: list) -> Decimal:
        """Calculate bulk discount amount"""
        # Count total product quantity
        total_qty = 0
        for item in line_items:
            category = item.get('category', '')
            if not category.startswith('subscription_') and category != 'installation':
                total_qty += item.get('quantity', 0)

        # Calculate hardware subtotal
        hardware_subtotal = Decimal('0')
        for item in line_items:
            category = item.get('category', '')
            if not category.startswith('subscription_') and category != 'installation':
                hardware_subtotal += Decimal(str(item.get('subtotal', 0)))

        # Apply discount based on quantity
        if total_qty >= 50:
            return hardware_subtotal * Decimal('0.20')
        elif total_qty >= 25:
            return hardware_subtotal * Decimal('0.15')
        elif total_qty >= 10:
            return hardware_subtotal * Decimal('0.10')

        return Decimal('0')

    def _get_bulk_discount_info(self, line_items: list) -> str:
        """Get bulk discount information string"""
        total_qty = 0
        for item in line_items:
            category = item.get('category', '')
            if not category.startswith('subscription_') and category != 'installation':
                total_qty += item.get('quantity', 0)

        if total_qty >= 50:
            return f"{total_qty} devices - 20% off"
        elif total_qty >= 25:
            return f"{total_qty} devices - 15% off"
        elif total_qty >= 10:
            return f"{total_qty} devices - 10% off"

        return "0% off"

    def _generate_notes_section(self, quote: dict) -> str:
        """Generate notes section if notes exist"""
        notes = quote.get('notes', '')
        if notes:
            return f"""
            <div class="section">
                <h3 class="section-title">Additional Notes</h3>
                <p class="notes-text">{notes}</p>
            </div>
            """
        return ''

    def _generate_disclaimers_section(self, quote: dict) -> str:
        """Generate price increase disclaimers section if disclaimers exist"""
        disclaimers = quote.get('price_increase_disclaimers', [])
        if disclaimers:
            return format_disclaimers_for_pdf(disclaimers)
        return ''

    def _generate_device_placement_section(self, quote: dict) -> str:
        """Generate device placement plan from builder_state"""
        builder_state = quote.get('builder_state', {})
        device_placements = builder_state.get('device_placements', [])

        logger.info(f"📍 Generating device placement section: found {len(device_placements)} placements")

        if not device_placements:
            logger.warning("   ⚠ No device placements in builder_state")
            return ''

        # Group placements by floor
        placements_by_floor = {}
        for placement in device_placements:
            floor = placement.get('floor', 'Unknown Floor')

            if floor not in placements_by_floor:
                placements_by_floor[floor] = []

            product = placement.get('product', {})
            placements_by_floor[floor].append({
                'product_name': product.get('name', 'Unknown Device'),
                'product_category': product.get('category', '').replace('_', ' ').title(),
                'location': f"({placement.get('x', 0):.0f}, {placement.get('y', 0):.0f})",
                'room': placement.get('room', ''),
                'quality_tier': (placement.get('quality_tier', '') or 'Not Specified').replace('_', ' ').title(),
                'priority': (placement.get('priority', '') or 'Not Specified').replace('_', ' ').title(),
                'install_method': (placement.get('install_method', '') or 'Not Specified').replace('_', ' ').title(),
                'notes': placement.get('notes', '')
            })

        logger.info(f"   Grouped into {len(placements_by_floor)} floors")

        # Generate HTML
        html = '<div class="section device-placements" style="page-break-before: always;">'
        html += '<h3 class="section-title">📍 Device Placement Plan</h3>'
        html += '<p class="section-description">Detailed installation plan showing where each device will be installed.</p>'

        for floor_name, placements in sorted(placements_by_floor.items()):
            logger.info(f"   Floor: {floor_name} - {len(placements)} devices")

            html += f'''
            <div class="floor-section">
                <h4 class="floor-name">{floor_name}</h4>
                <table class="placement-table">
                    <thead>
                        <tr>
                            <th>Device</th>
                            <th>Category</th>
                            <th>Room</th>
                            <th>Location</th>
                            <th>Quality</th>
                            <th>Priority</th>
                            <th>Install Method</th>
                        </tr>
                    </thead>
                    <tbody>
            '''

            for device in placements:
                # Format badges based on priority/quality
                quality_class = f"badge-{device['quality_tier'].lower().replace(' ', '-')}"
                priority_class = f"badge-{device['priority'].lower().replace(' ', '-')}"

                html += f'''
                    <tr>
                        <td><strong>{device['product_name']}</strong></td>
                        <td>{device['product_category']}</td>
                        <td>{device['room'] or '—'}</td>
                        <td class="location">{device['location']}</td>
                        <td><span class="badge {quality_class}">{device['quality_tier']}</span></td>
                        <td><span class="badge {priority_class}">{device['priority']}</span></td>
                        <td>{device['install_method']}</td>
                    </tr>
                '''

                # Add notes row if notes exist
                if device['notes']:
                    html += f'''
                    <tr class="notes-row">
                        <td colspan="7" class="device-notes">
                            <strong>Notes:</strong> {device['notes']}
                        </td>
                    </tr>
                    '''

            html += '''
                    </tbody>
                </table>
            </div>
            '''

        html += '</div>'
        logger.info(f"   ✓ Device placement section complete")
        return html

    def _generate_floor_plans_section(self, quote: dict) -> str:
        """Generate floor plans with device annotations"""
        floor_plans = quote.get('floor_plans', [])
        logger.info(f"📐 Generating floor plans section: found {len(floor_plans)} floor plans")

        if not floor_plans:
            logger.warning("   ⚠ No floor plans in quote data")
            return ''

        html = '<div class="section floor-plans"><h3 class="section-title">📐 Floor Plans</h3>'

        for idx, plan in enumerate(floor_plans):
            plan_name = plan.get('name', 'Floor Plan')
            plan_id = plan.get('id', 'unknown')
            file_url = plan.get('file_url', '')

            logger.info(f"   ========================================")
            logger.info(f"   Floor Plan {idx+1}/{len(floor_plans)}")
            logger.info(f"   ----------------------------------------")
            logger.info(f"   Plan Name: {plan_name}")
            logger.info(f"   Plan ID: {plan_id}")
            logger.info(f"   File URL: {file_url}")
            logger.info(f"   URL Length: {len(file_url)} chars")
            logger.info(f"   Annotations: {len(plan.get('annotations', []))} devices")

            # Fetch and embed the image
            if not file_url:
                logger.error(f"   ✗ MISSING FILE URL for plan '{plan_name}' (ID: {plan_id})")
                logger.error(f"   ✗ Skipping floor plan due to missing file_url")
                # Add placeholder for missing URL
                html += f'''
                <div class="floor-plan-page" style="page-break-before: always;">
                    <h4>{plan_name}</h4>
                    <div style="border: 2px dashed #ccc; padding: 40px; text-align: center; background-color: #f9f9f9; margin: 20px 0;">
                        <p style="color: #999; font-size: 16px;">⚠️ Floor Plan Image Unavailable</p>
                        <p style="color: #666; font-size: 12px;">[Floor Plan: {plan_name} - No file URL provided]</p>
                    </div>
                '''
                # Still include device annotations if available
                annotations = plan.get('annotations', [])
                if annotations:
                    html += '''
                    <div class="device-list">
                        <h5>Planned Device Locations:</h5>
                        <ul>
                    '''
                    for annotation in annotations:
                        device_type = annotation.get('device_type', '').replace('_', ' ').title()
                        label = annotation.get('label', '')
                        notes = annotation.get('notes', '')
                        html += f'''
                            <li>
                                <strong>{device_type}:</strong> {label}
                                {f"- {notes}" if notes else ''}
                            </li>
                        '''
                    html += '</ul></div>'
                html += '</div>'
                continue

            # Attempt to fetch the image
            logger.info(f"   → Attempting to fetch image...")
            try:
                image_data = self._fetch_image_as_base64(file_url)

                if image_data:
                    image_data_size = len(image_data)
                    logger.info(f"   ✓ SUCCESS: Image data retrieved")
                    logger.info(f"   ✓ Data URI size: {image_data_size} characters")
                    logger.info(f"   ✓ Embedding image in PDF for '{plan_name}'")

                    html += f'''
                    <div class="floor-plan-page" style="page-break-before: always;">
                        <h4>{plan_name}</h4>
                        <img src="{image_data}" style="max-width: 100%; max-height: 9in; width: auto; height: auto; object-fit: contain; display: block; margin: 0 auto;" />

                        <div class="device-list">
                            <h5>Planned Device Locations:</h5>
                            <ul>
                    '''

                    for annotation in plan.get('annotations', []):
                        device_type = annotation.get('device_type', '').replace('_', ' ').title()
                        label = annotation.get('label', '')
                        notes = annotation.get('notes', '')
                        html += f'''
                            <li>
                                <strong>{device_type}:</strong> {label}
                                {f"- {notes}" if notes else ''}
                            </li>
                        '''

                    html += '</ul></div></div>'
                else:
                    logger.error(f"   ✗ FAILED: Image fetch returned None for '{plan_name}'")
                    logger.error(f"   ✗ Plan ID: {plan_id}")
                    logger.error(f"   ✗ URL attempted: {file_url}")
                    logger.error(f"   ✗ Adding placeholder to PDF instead of skipping")

                    # Add placeholder for failed image fetch
                    html += f'''
                    <div class="floor-plan-page" style="page-break-before: always;">
                        <h4>{plan_name}</h4>
                        <div style="border: 2px dashed #ff6b6b; padding: 40px; text-align: center; background-color: #fff5f5; margin: 20px 0;">
                            <p style="color: #c92a2a; font-size: 16px;">⚠️ Floor Plan Image Could Not Be Loaded</p>
                            <p style="color: #666; font-size: 12px;">[Floor Plan: {plan_name} - Image fetch failed]</p>
                            <p style="color: #999; font-size: 10px;">Check server logs for details</p>
                        </div>
                    '''
                    # Still include device annotations
                    annotations = plan.get('annotations', [])
                    if annotations:
                        html += '''
                        <div class="device-list">
                            <h5>Planned Device Locations:</h5>
                            <ul>
                        '''
                        for annotation in annotations:
                            device_type = annotation.get('device_type', '').replace('_', ' ').title()
                            label = annotation.get('label', '')
                            notes = annotation.get('notes', '')
                            html += f'''
                                <li>
                                    <strong>{device_type}:</strong> {label}
                                    {f"- {notes}" if notes else ''}
                                </li>
                            '''
                        html += '</ul></div>'
                    html += '</div>'

            except Exception as e:
                logger.error(f"   ✗ EXCEPTION during image fetch for '{plan_name}': {str(e)}")
                logger.error(f"   ✗ Plan ID: {plan_id}")
                logger.error(f"   ✗ URL attempted: {file_url}")
                logger.exception(f"   ✗ Full traceback:")

                # Add placeholder for exception
                html += f'''
                <div class="floor-plan-page" style="page-break-before: always;">
                    <h4>{plan_name}</h4>
                    <div style="border: 2px dashed #ff6b6b; padding: 40px; text-align: center; background-color: #fff5f5; margin: 20px 0;">
                        <p style="color: #c92a2a; font-size: 16px;">⚠️ Error Loading Floor Plan Image</p>
                        <p style="color: #666; font-size: 12px;">[Floor Plan: {plan_name} - Exception occurred]</p>
                        <p style="color: #999; font-size: 10px;">Check server logs for details</p>
                    </div>
                '''
                # Still include device annotations
                annotations = plan.get('annotations', [])
                if annotations:
                    html += '''
                    <div class="device-list">
                        <h5>Planned Device Locations:</h5>
                        <ul>
                    '''
                    for annotation in annotations:
                        device_type = annotation.get('device_type', '').replace('_', ' ').title()
                        label = annotation.get('label', '')
                        notes = annotation.get('notes', '')
                        html += f'''
                            <li>
                                <strong>{device_type}:</strong> {label}
                                {f"- {notes}" if notes else ''}
                            </li>
                        '''
                    html += '</ul></div>'
                html += '</div>'

        html += '</div>'
        logger.info(f"   ========================================")
        logger.info(f"   ✓ Floor plans section complete")
        logger.info(f"   ========================================")
        return html

    def _generate_polycam_section(self, quote: dict) -> str:
        """Generate Polycam 3D scan links with QR codes"""
        scans = quote.get('polycam_scans', [])
        if not scans:
            return ''

        html = '<div class="section polycam-scans"><h3 class="section-title">🏠 3D Property Scans</h3>'
        html += '<p>Scan the QR codes below to view interactive 3D models of your property:</p>'

        for scan in scans:
            qr_code = self._generate_qr_code(scan['url'])
            html += f'''
            <div class="polycam-item">
                <div class="qr-code">
                    <img src="data:image/png;base64,{qr_code}" />
                </div>
                <div class="scan-info">
                    <h4>{scan.get('name', '3D Scan')}</h4>
                    <p><a href="{scan['url']}">{scan['url']}</a></p>
                    <p class="instructions">Scan with your phone to explore the 3D model</p>
                </div>
            </div>
            '''

        html += '</div>'
        return html

    def _generate_implementation_photos_section(self, quote: dict) -> str:
        """Generate implementation photos in grid layout"""
        photos = quote.get('implementation_photos', [])
        if not photos:
            return ''

        # Group by category
        categories = {}
        for photo in photos:
            cat = photo.get('category', 'general')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(photo)

        html = '<div class="section implementation-photos"><h3 class="section-title">🔧 Our Implementation Approach</h3>'

        for category, cat_photos in categories.items():
            html += f'<h4>{category.replace("_", " ").title()}</h4>'
            html += '<div class="photo-grid">'

            for photo in cat_photos:
                # Fetch and embed the image
                file_url = photo.get('file_url', '')
                image_data = self._fetch_image_as_base64(file_url) if file_url else None

                if image_data:
                    html += f'''
                    <div class="photo-item">
                        <img src="{image_data}" style="width: 100%; height: auto;" />
                        <p class="caption">{photo.get('caption', '')}</p>
                    </div>
                    '''

            html += '</div>'

        html += '</div>'
        return html

    def _generate_comparison_photos_section(self, quote: dict) -> str:
        """Generate before/after comparison photos side-by-side"""
        comparisons = quote.get('comparison_photos', [])
        if not comparisons:
            return ''

        html = '<div class="section comparison-photos"><h3 class="section-title">📊 Reference Projects</h3>'
        html += '<p>Similar projects we\'ve completed:</p>'

        for comp in comparisons:
            # Skip incomplete pairs
            if not comp.get('before_photo') or not comp.get('after_photo'):
                continue

            # Fetch and embed both images
            before_url = comp['before_photo'].get('file_url', '')
            after_url = comp['after_photo'].get('file_url', '')

            before_data = self._fetch_image_as_base64(before_url) if before_url else None
            after_data = self._fetch_image_as_base64(after_url) if after_url else None

            if before_data and after_data:
                html += f'''
                <div class="comparison-pair">
                    <div class="before-after">
                        <div class="before">
                            <img src="{before_data}" />
                            <span class="label">Before</span>
                        </div>
                        <div class="after">
                            <img src="{after_data}" />
                            <span class="label">After</span>
                        </div>
                    </div>
                    <p class="scope-description">{comp.get('description', '')}</p>
                    {f'<p class="similarity">Similarity to your project: {comp.get("similarity_score", 0)}%</p>' if comp.get('similarity_score') else ''}
                </div>
                '''

        html += '</div>'
        return html

    def _fetch_image_as_base64(self, url: str) -> Optional[str]:
        """Fetch an image from URL and convert to base64 data URI"""
        try:
            import base64
            from urllib.parse import urlparse
            import re
            from uuid import UUID

            logger.info(f"📸 ========================================")
            logger.info(f"📸 FETCH IMAGE AS BASE64")
            logger.info(f"📸 ========================================")
            logger.info(f"📸 Input URL: {url}")
            logger.info(f"📸 URL Type: {'Internal Media API' if '/api/v1/clients/media/' in url else 'External URL'}")

            # Handle internal media download URLs - access MinIO directly instead of HTTP
            if '/api/v1/clients/media/' in url and '/download' in url:
                logger.info(f"📸 → Processing as internal media download URL")
                # Extract media_id from URL: /api/v1/clients/media/{media_id}/download
                match = re.search(r'/media/([a-f0-9-]+)/download', url)
                if match:
                    media_id_str = match.group(1)
                    logger.info(f"📸 → Extracted media_id: {media_id_str}")

                    try:
                        from uuid import UUID
                        from services.client_media_service import get_client_media_service
                        from services.minio_client import get_minio_client
                        from db.database import AsyncSessionLocal
                        import asyncio

                        media_id = UUID(media_id_str)
                        logger.info(f"📸 → Parsed media_id as UUID: {media_id}")

                        # Get media record from database
                        logger.info(f"📸 → Looking up media record in database...")

                        # Define async function to fetch media
                        async def fetch_media():
                            async with AsyncSessionLocal() as db:
                                media_service = get_client_media_service(db)
                                return await media_service.get_media(media_id)

                        # Run async operation in new event loop
                        logger.info(f"📸 → Running async database query...")
                        media = asyncio.run(fetch_media())

                        if not media:
                            logger.error(f"📸 ✗ FAILED: Media record not found in database")
                            logger.error(f"📸 ✗ Media ID: {media_id}")
                            logger.error(f"📸 ✗ Returning None")
                            return None

                        logger.info(f"📸 ✓ Found media record in database")
                        logger.info(f"📸    - File Name: {media.file_name}")
                        logger.info(f"📸    - MIME Type: {media.mime_type}")
                        logger.info(f"📸    - MinIO Key: {media.minio_object_key}")

                        # Download directly from MinIO
                        logger.info(f"📸 → Downloading from MinIO bucket...")

                        async def fetch_from_minio():
                            minio_client = await get_minio_client()
                            return await minio_client.download_file(media.minio_object_key)

                        # Run async operation in new event loop
                        logger.info(f"📸 → Running async MinIO download...")
                        file_data = asyncio.run(fetch_from_minio())

                        image_size = len(file_data)
                        logger.info(f"📸 ✓ Successfully downloaded from MinIO")
                        logger.info(f"📸    - Bytes received: {image_size:,} bytes ({image_size / 1024:.2f} KB)")

                        # Convert to base64
                        logger.info(f"📸 → Converting to base64...")
                        image_base64 = base64.b64encode(file_data).decode()
                        data_uri_size = len(image_base64)
                        logger.info(f"📸 ✓ Base64 encoding complete")
                        logger.info(f"📸    - Base64 length: {data_uri_size:,} characters")

                        # Return as data URI with proper MIME type
                        content_type = media.mime_type or 'image/svg+xml'
                        logger.info(f"📸 ✓ Creating data URI with content type: {content_type}")
                        logger.info(f"📸 ========================================")
                        logger.info(f"📸 SUCCESS: Image fetched and encoded")
                        logger.info(f"📸 ========================================")
                        return f"data:{content_type};base64,{image_base64}"

                    except Exception as e:
                        logger.error(f"📸 ✗ ========================================")
                        logger.error(f"📸 ✗ EXCEPTION in MinIO fetch path")
                        logger.error(f"📸 ✗ ========================================")
                        logger.error(f"📸 ✗ Error: {str(e)}")
                        logger.error(f"📸 ✗ Error Type: {type(e).__name__}")
                        logger.exception(f"📸 ✗ Full traceback:")
                        return None

            # For external URLs, fall back to HTTP
            import requests
            logger.info(f"📸 → Fetching external URL via HTTP...")
            logger.info(f"📸 → Request timeout: 30 seconds")

            response = requests.get(url, timeout=30)
            logger.info(f"📸 ✓ HTTP request completed")
            logger.info(f"📸    - Status code: {response.status_code}")

            response.raise_for_status()
            logger.info(f"📸 ✓ Status check passed")

            # Detect content type
            content_type = response.headers.get('content-type', 'image/png')
            image_size = len(response.content)
            logger.info(f"📸 ✓ Response received")
            logger.info(f"📸    - Content-Type: {content_type}")
            logger.info(f"📸    - Bytes received: {image_size:,} bytes ({image_size / 1024:.2f} KB)")

            # Convert to base64
            logger.info(f"📸 → Converting to base64...")
            image_base64 = base64.b64encode(response.content).decode()
            data_uri_size = len(image_base64)
            logger.info(f"📸 ✓ Base64 encoding complete")
            logger.info(f"📸    - Base64 length: {data_uri_size:,} characters")

            # Return as data URI
            logger.info(f"📸 ✓ Creating data URI with content type: {content_type}")
            logger.info(f"📸 ========================================")
            logger.info(f"📸 SUCCESS: Image fetched and encoded")
            logger.info(f"📸 ========================================")
            return f"data:{content_type};base64,{image_base64}"
        except Exception as e:
            logger.error(f"📸 ✗ ========================================")
            logger.error(f"📸 ✗ EXCEPTION in image fetch")
            logger.error(f"📸 ✗ ========================================")
            logger.error(f"📸 ✗ URL: {url}")
            logger.error(f"📸 ✗ Error: {str(e)}")
            logger.error(f"📸 ✗ Error Type: {type(e).__name__}")
            logger.exception(f"📸 ✗ Full traceback:")
            return None

    def _generate_qr_code(self, url: str) -> str:
        """Generate QR code as base64 string"""
        try:
            import qrcode
            from io import BytesIO
            import base64

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            return base64.b64encode(buffer.getvalue()).decode()
        except ImportError:
            # qrcode not available, return placeholder
            return ""

    def _get_css(self) -> str:
        """Get CSS styling for the PDF"""
        return """
        @page {
            size: Letter;
            margin: 0.75in;
        }

        body {
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11pt;
            color: #1f2937;
            line-height: 1.5;
        }

        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #0ea5e9;
        }

        .company-name {
            font-size: 32pt;
            font-weight: bold;
            color: #0ea5e9;
            margin: 0;
            margin-bottom: 5px;
        }

        .tagline {
            font-size: 10pt;
            color: #6b7280;
            margin: 0;
        }

        .quote-number {
            font-size: 20pt;
            font-weight: bold;
            color: #1f2937;
            margin: 0;
            margin-bottom: 5px;
        }

        .quote-date,
        .valid-until {
            font-size: 9pt;
            color: #6b7280;
            margin: 2px 0;
        }

        .billing-badge {
            display: inline-block;
            padding: 4px 12px;
            background: #dbeafe;
            color: #1e40af;
            border-radius: 12px;
            font-size: 9pt;
            font-weight: bold;
            margin-top: 8px;
        }

        /* Status Badge */
        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 10pt;
            font-weight: bold;
            margin-bottom: 20px;
            text-transform: uppercase;
        }

        .status-draft {
            background-color: #f3f4f6;
            color: #4b5563;
        }

        .status-sent {
            background-color: #dbeafe;
            color: #1e40af;
        }

        .status-accepted {
            background-color: #dcfce7;
            color: #166534;
        }

        /* Sections */
        .section {
            margin-bottom: 25px;
        }

        .section-title {
            font-size: 14pt;
            font-weight: bold;
            color: #1f2937;
            margin: 0 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 2px solid #e5e7eb;
        }

        .section-description {
            font-size: 9pt;
            color: #6b7280;
            margin: 8px 0 12px 0;
        }

        /* Info Table */
        .info-table {
            width: 100%;
            border-collapse: collapse;
        }

        .info-table td {
            padding: 6px 10px;
        }

        .info-table .label {
            font-weight: bold;
            color: #6b7280;
            width: 20%;
        }

        .info-table .value {
            color: #1f2937;
            width: 30%;
        }

        /* Subscription Table */
        .subscription-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .subscription-table th {
            padding: 10px;
            text-align: left;
            background: #f3f4f6;
            font-size: 9pt;
            font-weight: bold;
            color: #4b5563;
            text-transform: uppercase;
            border-bottom: 2px solid #d1d5db;
        }

        .subscription-table td {
            padding: 12px 10px;
            border-bottom: 1px solid #e5e7eb;
        }

        .service-type {
            font-weight: 600;
            color: #1f2937;
        }

        .tier-badge {
            display: inline-block;
            padding: 4px 12px;
            background: #dcfce7;
            color: #166534;
            border-radius: 12px;
            font-size: 9pt;
            font-weight: bold;
        }

        .subscription-table .total-row {
            background: #f9fafb;
            border-top: 2px solid #1f2937;
        }

        /* Domain Group */
        .domain-group {
            margin: 20px 0;
            page-break-inside: avoid;
        }

        .domain-header {
            font-size: 12pt;
            font-weight: bold;
            color: #1f2937;
            margin: 0 0 10px 0;
            padding: 8px 12px;
            background: #f3f4f6;
            border-left: 4px solid #0ea5e9;
        }

        .products-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
        }

        .products-table th {
            padding: 8px 10px;
            text-align: left;
            background: #f9fafb;
            font-size: 8pt;
            font-weight: bold;
            color: #6b7280;
            border-bottom: 1px solid #e5e7eb;
        }

        .products-table td {
            padding: 8px 10px;
            font-size: 9pt;
            border-bottom: 1px solid #f3f4f6;
        }

        .product-name {
            font-weight: 600;
            color: #1f2937;
        }

        .vendor-name {
            color: #6b7280;
            font-size: 8pt;
        }

        .qty-cell, .price-cell {
            text-align: right;
        }

        .domain-total td {
            background: #f9fafb;
            font-weight: 600;
            border-top: 1px solid #d1d5db;
        }

        /* Hardware Summary */
        .hardware-summary {
            margin-top: 15px;
        }

        /* Installation Table */
        .installation-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .installation-table td {
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
        }

        .install-desc {
            font-weight: 600;
            color: #1f2937;
            width: 50%;
        }

        .install-hours {
            color: #6b7280;
            font-size: 9pt;
            width: 30%;
        }

        .install-price {
            text-align: right;
            font-weight: 600;
            color: #1f2937;
            width: 20%;
        }

        .included-row {
            background: #dcfce7;
        }

        .included-row .install-price {
            color: #166534;
            font-weight: bold;
        }

        .installation-note {
            font-size: 9pt;
            color: #6b7280;
            margin-top: 10px;
            padding: 8px 12px;
            background: #f3f4f6;
            border-left: 3px solid #0ea5e9;
        }

        /* Comprehensive Labor Section */
        .labor-section {
            margin-bottom: 25px;
        }

        .labor-category-group {
            margin: 20px 0;
            page-break-inside: avoid;
        }

        .labor-category-header {
            font-size: 12pt;
            font-weight: bold;
            color: #1f2937;
            margin: 0 0 10px 0;
            padding: 8px 12px;
            background: #f3f4f6;
            border-left: 4px solid #0ea5e9;
        }

        .labor-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 10px;
        }

        .labor-table th {
            padding: 8px 10px;
            text-align: left;
            background: #f9fafb;
            font-size: 8pt;
            font-weight: bold;
            color: #6b7280;
            border-bottom: 2px solid #e5e7eb;
        }

        .labor-table td {
            padding: 10px;
            font-size: 9pt;
            border-bottom: 1px solid #f3f4f6;
            vertical-align: top;
        }

        .labor-task {
            width: 40%;
        }

        .labor-task-name {
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 4px;
        }

        .labor-task-desc {
            font-size: 8pt;
            color: #6b7280;
            line-height: 1.4;
            margin-bottom: 4px;
        }

        .materials-list {
            font-size: 8pt;
            color: #6b7280;
            margin-top: 4px;
            padding: 4px 8px;
            background: #f9fafb;
            border-left: 2px solid #0ea5e9;
        }

        .labor-hours, .labor-rate, .labor-cost, .materials-cost, .total-cost {
            text-align: right;
            color: #1f2937;
        }

        .labor-hours {
            width: 10%;
            font-size: 9pt;
        }

        .labor-rate {
            width: 10%;
            font-size: 9pt;
        }

        .labor-cost {
            width: 12%;
            font-weight: 600;
        }

        .materials-cost {
            width: 12%;
            color: #6b7280;
        }

        .total-cost {
            width: 12%;
            font-weight: 600;
            color: #1f2937;
        }

        .category-total-row {
            background: #f9fafb;
            border-top: 2px solid #d1d5db;
            font-weight: 600;
        }

        .labor-summary {
            margin-top: 15px;
            padding: 15px;
            background: #f9fafb;
            border-left: 4px solid #16a34a;
        }

        /* Grand Total Section */
        .grand-total-section {
            background: linear-gradient(to bottom, #f9fafb, white);
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #0ea5e9;
            margin: 30px 0;
        }

        .savings-callout {
            display: flex;
            align-items: center;
            gap: 15px;
            background: #dcfce7;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #16a34a;
        }

        .savings-icon {
            font-size: 24pt;
        }

        .savings-text {
            font-size: 10pt;
            color: #166534;
        }

        .grand-total-table {
            width: 100%;
            border-collapse: collapse;
        }

        .grand-total-table td {
            padding: 10px;
        }

        .section-header td {
            background: #f3f4f6;
            font-size: 10pt;
            font-weight: bold;
            color: #4b5563;
            padding: 8px 10px;
            border-top: 2px solid #d1d5db;
            border-bottom: 1px solid #d1d5db;
        }

        .subtotal-row {
            background: #f9fafb;
            border-top: 1px solid #e5e7eb;
        }

        .year-1-total, .year-2-total {
            background: #eff6ff;
            border-top: 2px solid #0ea5e9;
            border-bottom: 2px solid #0ea5e9;
        }

        .year-1-total td, .year-2-total td {
            padding: 15px 10px;
        }

        .sublabel {
            font-size: 8pt;
            color: #6b7280;
            font-weight: normal;
            margin-top: 2px;
        }

        /* Summary Table */
        .summary-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        .summary-table td {
            padding: 8px 10px;
        }

        .summary-label {
            text-align: right;
            color: #6b7280;
            width: 70%;
        }

        .summary-value {
            text-align: right;
            font-weight: bold;
            color: #1f2937;
            width: 30%;
        }

        .discount-row .summary-value {
            color: #16a34a;
        }

        .summary-total {
            border-top: 2px solid #1f2937;
            border-bottom: 2px solid #1f2937;
        }

        .summary-total .summary-label,
        .summary-total .summary-value {
            font-size: 12pt;
            padding: 12px 10px;
        }

        /* Device Placement Table */
        .device-placements {
            margin: 20px 0;
        }

        .floor-section {
            margin: 20px 0;
            page-break-inside: avoid;
        }

        .floor-name {
            color: #1f2937;
            font-size: 12pt;
            margin: 15px 0 10px 0;
            padding: 8px 12px;
            background: #f3f4f6;
            border-left: 4px solid #3b82f6;
        }

        .placement-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 9pt;
        }

        .placement-table th {
            background: #3b82f6;
            color: white;
            padding: 8px 6px;
            text-align: left;
            font-weight: bold;
            font-size: 9pt;
        }

        .placement-table td {
            padding: 8px 6px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
        }

        .placement-table tr:hover {
            background: #f9fafb;
        }

        .placement-table .location {
            font-family: 'Courier New', monospace;
            font-size: 8pt;
            color: #6b7280;
        }

        .notes-row {
            background: #fef3c7 !important;
        }

        .device-notes {
            padding: 8px 12px !important;
            font-size: 8pt;
            font-style: italic;
            color: #92400e;
        }

        .badge {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 8pt;
            font-weight: bold;
            white-space: nowrap;
            display: inline-block;
        }

        /* Quality tier badges */
        .badge-good {
            background: #fef3c7;
            color: #92400e;
        }

        .badge-better {
            background: #dbeafe;
            color: #1e40af;
        }

        .badge-best {
            background: #d1fae5;
            color: #065f46;
        }

        .badge-not-specified {
            background: #f3f4f6;
            color: #6b7280;
        }

        /* Priority badges */
        .badge-essential {
            background: #fee2e2;
            color: #991b1b;
            font-weight: bold;
        }

        .badge-good-to-have {
            background: #fed7aa;
            color: #9a3412;
        }

        .badge-extra {
            background: #e0e7ff;
            color: #3730a3;
        }

        /* Notes */
        .notes-text {
            background-color: #fef3c7;
            padding: 15px;
            border-left: 4px solid #f59e0b;
            border-radius: 4px;
            margin: 10px 0;
        }

        /* Terms */
        .terms {
            margin-top: 30px;
            page-break-inside: avoid;
        }

        .terms-text {
            font-size: 9pt;
            color: #6b7280;
            line-height: 1.6;
        }

        /* Footer */
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            font-size: 9pt;
            color: #6b7280;
        }

        .footer p {
            margin: 5px 0;
        }

        .footer-company {
            font-weight: bold;
            font-size: 11pt;
            color: #0ea5e9;
        }

        .footer-thanks {
            font-style: italic;
            margin-top: 10px;
            color: #1f2937;
        }

        /* Visual Assets Sections */
        .floor-plan-page {
            page-break-before: always;
            margin: 20px 0;
        }

        .device-list {
            margin-top: 20px;
            padding: 15px;
            background: #f9fafb;
            border-left: 4px solid #3b82f6;
        }

        .device-list h5 {
            margin: 0 0 10px 0;
            font-size: 11pt;
            color: #1f2937;
        }

        .device-list ul {
            margin: 0;
            padding-left: 20px;
        }

        .device-list li {
            margin: 5px 0;
            font-size: 10pt;
        }

        .polycam-item {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            padding: 20px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }

        .qr-code img {
            width: 150px;
            height: 150px;
        }

        .scan-info {
            flex: 1;
        }

        .scan-info h4 {
            margin: 0 0 10px 0;
            font-size: 12pt;
            color: #1f2937;
        }

        .scan-info p {
            margin: 5px 0;
            font-size: 9pt;
            color: #6b7280;
        }

        .scan-info a {
            color: #0ea5e9;
            text-decoration: none;
        }

        .instructions {
            font-style: italic;
            color: #9ca3af;
        }

        .implementation-photos h4 {
            margin: 20px 0 10px 0;
            font-size: 11pt;
            color: #1f2937;
            text-transform: capitalize;
        }

        .photo-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }

        .photo-item {
            border: 1px solid #e5e7eb;
            padding: 10px;
            border-radius: 4px;
            page-break-inside: avoid;
        }

        .photo-item img {
            width: 100%;
            height: auto;
            border-radius: 4px;
        }

        .caption {
            font-size: 9pt;
            color: #6b7280;
            margin-top: 8px;
            line-height: 1.4;
        }

        .comparison-pair {
            page-break-inside: avoid;
            margin: 30px 0;
            padding: 20px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }

        .before-after {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }

        .before, .after {
            flex: 1;
            text-align: center;
        }

        .before img, .after img {
            width: 100%;
            height: auto;
            border: 2px solid #e5e7eb;
            border-radius: 4px;
        }

        .before .label, .after .label {
            display: block;
            margin-top: 8px;
            font-weight: bold;
            font-size: 10pt;
            color: #1f2937;
        }

        .scope-description {
            font-size: 10pt;
            color: #4b5563;
            margin: 10px 0;
            line-height: 1.5;
        }

        .similarity {
            font-size: 9pt;
            color: #6b7280;
            font-style: italic;
        }
        """

    def _get_default_terms(self) -> str:
        """Get default terms and conditions"""
        return """
        This quote is valid for 30 days from the date of issue. Pricing is subject to change after expiration.
        Services will commence upon signed agreement and receipt of initial payment. Monthly fees are billed in
        advance on the 1st of each month. One-time hardware and installation fees are due upon contract signing.
        Smart home hardware costs are estimates based on provided specifications and may vary based on final
        property assessment. Bulk discounts are automatically applied based on total device count. All prices
        are in USD and exclude applicable taxes. Cancellation requires 30 days written notice. Subscription
        services include ongoing support and system maintenance as specified in the selected tier.
        """

    def _format_currency(self, value) -> str:
        """Format a value as currency"""
        if value is None:
            value = 0

        # Convert to Decimal if not already
        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        # Format with 2 decimal places and thousands separator
        return f"{value:,.2f}"

    def _format_date(self, date_value) -> str:
        """Format a date for display"""
        if not date_value:
            return 'N/A'

        # If it's a string, parse it
        if isinstance(date_value, str):
            try:
                date_value = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except:
                return date_value

        # If it's a datetime, format it
        if isinstance(date_value, datetime):
            return date_value.strftime('%B %d, %Y')

        return str(date_value)


# Utility function for easy import
async def generate_quote_pdf(quote: dict, line_items: list, labor_items: list = None) -> bytes:
    """
    Generate a PDF for a quote

    Args:
        quote: Quote dictionary
        line_items: List of line item dictionaries
        labor_items: List of labor item dictionaries (optional)

    Returns:
        bytes: PDF file content
    """
    generator = QuotePDFGenerator()
    return generator.generate_pdf(quote, line_items, labor_items or [])
