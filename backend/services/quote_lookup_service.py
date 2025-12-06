"""
Automated Quote Lookup Service

Automatically finds and contacts contractors when no in-house resources available:
1. Search Yelp API for local contractors by category
2. Search Google Places API for additional contractors
3. Extract contact information (email, phone)
4. Send automated quote requests via n8n workflow (email templates)
5. Track responses and parse quotes
6. Use LocalAI to analyze and rank quotes
7. Present best options for human approval

Integrates with:
- Yelp Fusion API
- Google Places API
- n8n for email automation
- LocalAI for quote analysis
- contractor_manager for contractor database
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import httpx
import uuid
import os

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ============================================================================
# QUOTE LOOKUP SERVICE
# ============================================================================

class QuoteLookupService:
    """
    Automatically discover and contact contractors for quotes
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # API Configuration
        self.yelp_api_key = os.getenv('YELP_API_KEY', '')
        self.google_places_api_key = os.getenv('GOOGLE_PLACES_API_KEY', '')

        # Service URLs (Kubernetes service discovery)
        self.n8n_url = os.getenv('N8N_URL', 'http://n8n.automation.svc.cluster.local:5678')
        self.localai_url = os.getenv('LOCALAI_URL', 'http://localai.ai.svc.cluster.local:8080')

        # Quote request configuration
        self.default_quote_deadline_hours = 48
        self.max_contractors_to_contact = 10
        self.preferred_search_radius_miles = 25

    # ========================================================================
    # MAIN QUOTE CAMPAIGN WORKFLOW
    # ========================================================================

    async def start_quote_campaign(
        self,
        campaign_id: uuid.UUID,
        work_order_id: uuid.UUID,
        service_category: str,
        service_description: str,
        property_id: uuid.UUID,
        unit_id: Optional[uuid.UUID],
        urgency: str,
        target_quote_count: int = 3,
        deadline_hours: int = 48
    ) -> Dict[str, Any]:
        """
        Start automated quote gathering campaign

        Workflow:
        1. Search for contractors online (Yelp + Google)
        2. Check existing contractor database
        3. Score and rank potential contractors
        4. Send automated quote requests (email via n8n)
        5. Track responses
        6. Analyze quotes with AI
        7. Notify manager when quotes ready
        """
        logger.info(f"Starting quote campaign {campaign_id} for work order {work_order_id}")

        results = {
            'campaign_id': str(campaign_id),
            'contractors_found': 0,
            'quote_requests_sent': 0,
            'errors': []
        }

        try:
            # Step 1: Discover contractors
            contractors = await self._discover_contractors(
                service_category=service_category,
                property_id=property_id,
                search_radius_miles=self.preferred_search_radius_miles
            )

            results['contractors_found'] = len(contractors)
            logger.info(f"Found {len(contractors)} potential contractors")

            if not contractors:
                logger.warning("No contractors found - campaign may fail")
                results['errors'].append("No contractors discovered")
                return results

            # Step 2: Rank contractors by relevance and quality
            ranked_contractors = await self._rank_contractors(
                contractors=contractors,
                service_category=service_category,
                urgency=urgency
            )

            # Step 3: Select top contractors to contact
            contractors_to_contact = ranked_contractors[:min(len(ranked_contractors), target_quote_count * 2)]

            # Step 4: Send quote requests via n8n
            for contractor in contractors_to_contact:
                try:
                    quote_id = await self._send_quote_request(
                        campaign_id=campaign_id,
                        work_order_id=work_order_id,
                        contractor_info=contractor,
                        service_description=service_description,
                        urgency=urgency,
                        deadline_hours=deadline_hours
                    )

                    if quote_id:
                        results['quote_requests_sent'] += 1
                        logger.info(f"Quote request sent to {contractor['name']}")

                except Exception as e:
                    logger.error(f"Failed to send quote request to {contractor['name']}: {e}")
                    results['errors'].append(f"Failed to contact {contractor['name']}")

                # Rate limiting - don't spam
                await asyncio.sleep(2)

            logger.info(
                f"Quote campaign {campaign_id} initiated: "
                f"{results['quote_requests_sent']} requests sent"
            )

        except Exception as e:
            logger.error(f"Quote campaign {campaign_id} failed: {e}", exc_info=True)
            results['errors'].append(str(e))

        return results

    # ========================================================================
    # CONTRACTOR DISCOVERY
    # ========================================================================

    async def _discover_contractors(
        self,
        service_category: str,
        property_id: uuid.UUID,
        search_radius_miles: int
    ) -> List[Dict[str, Any]]:
        """
        Discover contractors via Yelp and Google APIs

        Returns list of contractors with contact info
        """
        contractors = []

        # Get property location for geo-search
        property_location = await self._get_property_location(property_id)

        if not property_location:
            logger.error(f"Could not get location for property {property_id}")
            return []

        # Search Yelp
        if self.yelp_api_key:
            try:
                yelp_results = await self._search_yelp(
                    category=service_category,
                    latitude=property_location['latitude'],
                    longitude=property_location['longitude'],
                    radius_miles=search_radius_miles
                )
                contractors.extend(yelp_results)
                logger.info(f"Found {len(yelp_results)} contractors on Yelp")
            except Exception as e:
                logger.error(f"Yelp search failed: {e}")

        # Search Google Places
        if self.google_places_api_key:
            try:
                google_results = await self._search_google_places(
                    category=service_category,
                    latitude=property_location['latitude'],
                    longitude=property_location['longitude'],
                    radius_miles=search_radius_miles
                )
                contractors.extend(google_results)
                logger.info(f"Found {len(google_results)} contractors on Google")
            except Exception as e:
                logger.error(f"Google Places search failed: {e}")

        # Deduplicate by name/phone
        contractors = self._deduplicate_contractors(contractors)

        logger.info(f"Total unique contractors discovered: {len(contractors)}")

        return contractors

    async def _get_property_location(self, property_id: uuid.UUID) -> Optional[Dict[str, float]]:
        """Get property latitude/longitude for geo-search"""
        # TODO: Query properties table for address, geocode if needed
        # Placeholder - in production, fetch from database and geocode
        return {
            'latitude': 34.0522,  # Los Angeles example
            'longitude': -118.2437
        }

    async def _search_yelp(
        self,
        category: str,
        latitude: float,
        longitude: float,
        radius_miles: int
    ) -> List[Dict[str, Any]]:
        """
        Search Yelp Fusion API for contractors

        https://www.yelp.com/developers/documentation/v3/business_search
        """
        if not self.yelp_api_key:
            return []

        # Map our service categories to Yelp categories
        category_mapping = {
            'plumbing': 'plumbing',
            'electrical': 'electricians',
            'hvac': 'hvac',
            'general_maintenance': 'handyman',
            'carpentry': 'carpenters',
            'painting': 'painters',
            'appliance_repair': 'appliancerepair'
        }

        yelp_category = category_mapping.get(category, 'contractors')

        url = 'https://api.yelp.com/v3/businesses/search'
        headers = {
            'Authorization': f'Bearer {self.yelp_api_key}'
        }
        params = {
            'categories': yelp_category,
            'latitude': latitude,
            'longitude': longitude,
            'radius': int(radius_miles * 1609),  # Convert miles to meters
            'limit': 20,
            'sort_by': 'rating'
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        contractors = []
        for business in data.get('businesses', []):
            contractors.append({
                'name': business['name'],
                'phone': business.get('phone', ''),
                'email': None,  # Yelp doesn't provide email
                'address': self._format_address(business.get('location', {})),
                'rating': business.get('rating', 0.0),
                'review_count': business.get('review_count', 0),
                'categories': [cat['title'] for cat in business.get('categories', [])],
                'url': business.get('url', ''),
                'source': 'yelp',
                'source_id': business['id']
            })

        return contractors

    async def _search_google_places(
        self,
        category: str,
        latitude: float,
        longitude: float,
        radius_miles: int
    ) -> List[Dict[str, Any]]:
        """
        Search Google Places API for contractors

        https://developers.google.com/maps/documentation/places/web-service/search-nearby
        """
        if not self.google_places_api_key:
            return []

        # Map our categories to Google Places types
        type_mapping = {
            'plumbing': 'plumber',
            'electrical': 'electrician',
            'hvac': 'electrician',  # No specific HVAC type
            'general_maintenance': 'general_contractor',
            'carpentry': 'general_contractor',
            'painting': 'painter'
        }

        place_type = type_mapping.get(category, 'general_contractor')

        url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
        params = {
            'location': f'{latitude},{longitude}',
            'radius': int(radius_miles * 1609),  # Convert miles to meters
            'type': place_type,
            'key': self.google_places_api_key
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        contractors = []
        for place in data.get('results', []):
            # Get additional details (phone, website)
            details = await self._get_place_details(place['place_id'])

            contractors.append({
                'name': place['name'],
                'phone': details.get('formatted_phone_number', ''),
                'email': None,  # Google doesn't provide email
                'address': place.get('vicinity', ''),
                'rating': place.get('rating', 0.0),
                'review_count': place.get('user_ratings_total', 0),
                'categories': place.get('types', []),
                'url': details.get('website', ''),
                'source': 'google',
                'source_id': place['place_id']
            })

        return contractors

    async def _get_place_details(self, place_id: str) -> Dict[str, Any]:
        """Get detailed place information from Google"""
        url = 'https://maps.googleapis.com/maps/api/place/details/json'
        params = {
            'place_id': place_id,
            'fields': 'formatted_phone_number,website',
            'key': self.google_places_api_key
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        return data.get('result', {})

    def _deduplicate_contractors(self, contractors: List[Dict]) -> List[Dict]:
        """Remove duplicate contractors based on phone number or name"""
        seen = set()
        unique = []

        for contractor in contractors:
            # Use phone as primary dedup key
            phone = contractor.get('phone', '').replace('-', '').replace('(', '').replace(')', '').replace(' ', '')
            name = contractor.get('name', '').lower()

            key = phone if phone else name

            if key and key not in seen:
                seen.add(key)
                unique.append(contractor)

        return unique

    def _format_address(self, location: Dict) -> str:
        """Format Yelp location object into address string"""
        parts = []
        if 'address1' in location:
            parts.append(location['address1'])
        if 'city' in location:
            parts.append(location['city'])
        if 'state' in location:
            parts.append(location['state'])
        if 'zip_code' in location:
            parts.append(location['zip_code'])

        return ', '.join(parts)

    # ========================================================================
    # CONTRACTOR RANKING
    # ========================================================================

    async def _rank_contractors(
        self,
        contractors: List[Dict],
        service_category: str,
        urgency: str
    ) -> List[Dict]:
        """
        Rank contractors by quality score

        Factors:
        - Rating (Yelp/Google)
        - Number of reviews (more = more reliable)
        - Distance (closer = better)
        - Response time (if available)
        - Past performance (if in our database)
        """
        for contractor in contractors:
            score = 0.0

            # Rating component (0-50 points)
            rating = contractor.get('rating', 0.0)
            score += (rating / 5.0) * 50

            # Review count component (0-30 points)
            # Logarithmic scale: 10 reviews = 15pts, 100 reviews = 30pts
            import math
            review_count = contractor.get('review_count', 0)
            if review_count > 0:
                score += min(30, math.log10(review_count) * 15)

            # Availability component (0-20 points)
            # If we have historical data, use it
            # For now, assume all equally available
            score += 10

            contractor['quality_score'] = round(score, 2)

        # Sort by quality score
        contractors.sort(key=lambda x: x.get('quality_score', 0), reverse=True)

        return contractors

    # ========================================================================
    # QUOTE REQUEST SENDING
    # ========================================================================

    async def _send_quote_request(
        self,
        campaign_id: uuid.UUID,
        work_order_id: uuid.UUID,
        contractor_info: Dict,
        service_description: str,
        urgency: str,
        deadline_hours: int
    ) -> Optional[uuid.UUID]:
        """
        Send quote request to contractor via n8n workflow

        n8n workflow will:
        1. Send professional email with quote request
        2. Include work details, deadline, contact info
        3. Track email opens/clicks
        4. Parse responses and create contractor_quotes records
        """
        quote_id = uuid.uuid4()

        # Create quote record (status: requested)
        # TODO: Insert into contractor_quotes table

        # Prepare n8n webhook payload
        payload = {
            'quote_id': str(quote_id),
            'campaign_id': str(campaign_id),
            'work_order_id': str(work_order_id),
            'contractor': {
                'name': contractor_info['name'],
                'email': contractor_info.get('email'),
                'phone': contractor_info['phone'],
                'source': contractor_info.get('source')
            },
            'service': {
                'description': service_description,
                'urgency': urgency,
                'deadline_hours': deadline_hours
            },
            'callback_url': f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/api/quotes/{quote_id}/response"
        }

        # If contractor has email, send email request
        if contractor_info.get('email'):
            try:
                await self._trigger_n8n_workflow(
                    workflow_name='quote-request-email',
                    payload=payload
                )
                logger.info(f"Email quote request sent to {contractor_info['email']}")
                return quote_id

            except Exception as e:
                logger.error(f"Failed to send email quote request: {e}")

        # If no email but has phone, send SMS request
        elif contractor_info.get('phone'):
            try:
                await self._trigger_n8n_workflow(
                    workflow_name='quote-request-sms',
                    payload=payload
                )
                logger.info(f"SMS quote request sent to {contractor_info['phone']}")
                return quote_id

            except Exception as e:
                logger.error(f"Failed to send SMS quote request: {e}")

        else:
            logger.warning(f"No contact method for contractor {contractor_info['name']}")
            return None

    async def _trigger_n8n_workflow(
        self,
        workflow_name: str,
        payload: Dict
    ) -> Dict:
        """Trigger n8n workflow via webhook"""
        url = f"{self.n8n_url}/webhook/{workflow_name}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    # ========================================================================
    # QUOTE ANALYSIS WITH AI
    # ========================================================================

    async def analyze_quotes_with_ai(
        self,
        work_order_id: uuid.UUID,
        quotes: List[Dict]
    ) -> Dict[str, Any]:
        """
        Use LocalAI to analyze and compare quotes

        AI will consider:
        - Price competitiveness
        - Contractor reputation
        - Timeline reasonableness
        - Scope completeness
        - Red flags in quote text
        """
        from services.localai_client import get_localai_client

        if not quotes:
            return {'recommendation': None, 'analysis': 'No quotes to analyze'}

        # Build AI prompt
        quote_summaries = []
        for i, quote in enumerate(quotes, 1):
            quote_summaries.append(f"""
Quote {i}:
- Contractor: {quote['contractor_name']} (Rating: {quote.get('contractor_rating', 'N/A')})
- Price: ${quote.get('quoted_amount', 0.0):.2f}
- Timeline: {quote.get('estimated_completion_date', 'Not specified')}
- Breakdown: {quote.get('quote_breakdown', {})}
""")

        prompt = f"""
You are analyzing contractor quotes for a property maintenance work order.

Work Description:
{quotes[0].get('service_description', 'N/A')}

Quotes Received:
{''.join(quote_summaries)}

Please analyze these quotes and provide:
1. Which quote offers the best value (not just cheapest)
2. Any red flags or concerns
3. Recommendation with reasoning

Format your response as JSON:
{{
  "recommended_quote_number": 1,
  "reasoning": "...",
  "red_flags": ["..."],
  "value_analysis": "..."
}}
"""

        try:
            localai = get_localai_client()
            analysis = await localai.chat_completion(
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.3
            )

            # Parse JSON response
            import json
            analysis_json = json.loads(analysis)

            return analysis_json

        except Exception as e:
            logger.error(f"AI quote analysis failed: {e}", exc_info=True)
            return {
                'recommended_quote_number': None,
                'error': str(e)
            }


# ============================================================================
# SINGLETON HELPER
# ============================================================================

_quote_lookup_instance = None

def get_quote_lookup_service(db: AsyncSession) -> QuoteLookupService:
    """Get singleton instance of QuoteLookupService"""
    global _quote_lookup_instance
    if _quote_lookup_instance is None:
        _quote_lookup_instance = QuoteLookupService(db)
    return _quote_lookup_instance
