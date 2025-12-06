#!/usr/bin/env python3
"""
Seed subscription tier data for Service Hours, Smart Actions, and Analytics
"""

SUBSCRIPTION_TIERS = {
    "service_hours": [
        {
            "tier_name": "Pay Per Hour",
            "tier_level": 0,
            "tier_type": "service_hours",
            "monthly_price": 0,
            "hourly_rate": 150,
            "included_hours": 0,
            "overage_rate": 150,
            "features": [
                "No monthly commitment",
                "Billed monthly for hours used",
                "15-minute minimum increments",
                "Standard support response time"
            ],
            "support_level": "Email (24-48hr)",
            "active": True
        },
        {
            "tier_name": "Starter",
            "tier_level": 1,
            "tier_type": "service_hours",
            "monthly_price": 599,
            "annual_price": 5990,
            "annual_savings": 1188,
            "annual_credit": 500,
            "included_hours": 5,
            "overage_rate": 120,
            "features": [
                "5 hours/month included",
                "$120/hr for additional hours",
                "Email & chat support",
                "2-business-day response time",
                "Basic automations included"
            ],
            "support_level": "Email & Chat",
            "active": True
        },
        {
            "tier_name": "Professional",
            "tier_level": 2,
            "tier_type": "service_hours",
            "monthly_price": 999,
            "annual_price": 9990,
            "annual_savings": 1998,
            "annual_credit": 1000,
            "included_hours": 10,
            "overage_rate": 100,
            "features": [
                "10 hours/month included",
                "$100/hr for additional hours",
                "Priority phone & email support",
                "4-hour response time",
                "Advanced automations",
                "Monthly strategy review"
            ],
            "support_level": "Priority (Phone + Email)",
            "most_popular": True,
            "active": True
        },
        {
            "tier_name": "Enterprise",
            "tier_level": 3,
            "tier_type": "service_hours",
            "monthly_price": 1799,
            "annual_price": 17990,
            "annual_savings": 3598,
            "annual_credit": 2000,
            "included_hours": 20,
            "overage_rate": 90,
            "features": [
                "20 hours/month included",
                "$90/hr for additional hours",
                "24/7 dedicated support line",
                "1-hour response time",
                "Custom automations included",
                "Dedicated account manager",
                "Quarterly business reviews"
            ],
            "support_level": "White-Glove (Dedicated Manager)",
            "active": True
        }
    ],
    "smart_actions": [
        {
            "tier_name": "Basic",
            "tier_level": 1,
            "tier_type": "smart_actions",
            "monthly_price": 99,
            "annual_price": 990,
            "annual_savings": 198,
            "max_devices": 10,
            "features": [
                "Up to 10 devices monitored",
                "Connectivity & health checks",
                "30-minute response time",
                "Email alerts",
                "Business hours support"
            ],
            "response_time": "30 minutes",
            "active": True
        },
        {
            "tier_name": "Standard",
            "tier_level": 2,
            "tier_type": "smart_actions",
            "monthly_price": 249,
            "annual_price": 2490,
            "annual_savings": 498,
            "max_devices": 25,
            "features": [
                "Up to 25 devices monitored",
                "Real-time health monitoring",
                "15-minute response time",
                "SMS & email alerts",
                "Automated contractor dispatch",
                "24/7 monitoring dashboard"
            ],
            "response_time": "15 minutes",
            "active": True
        },
        {
            "tier_name": "Premium",
            "tier_level": 3,
            "tier_type": "smart_actions",
            "monthly_price": 499,
            "annual_price": 4990,
            "annual_savings": 998,
            "max_devices": 50,
            "features": [
                "Up to 50 devices monitored",
                "Advanced predictive monitoring",
                "5-minute response time",
                "Priority contractor dispatch",
                "Multi-channel alerts (SMS, email, app)",
                "Weekly health reports",
                "Device lifecycle tracking"
            ],
            "response_time": "5 minutes",
            "most_popular": True,
            "active": True
        },
        {
            "tier_name": "Enterprise",
            "tier_level": 4,
            "tier_type": "smart_actions",
            "monthly_price": 999,
            "annual_price": 9990,
            "annual_savings": 1998,
            "max_devices": None,  # Unlimited
            "features": [
                "Unlimited devices monitored",
                "AI-powered predictive analytics",
                "Immediate response (< 2 min)",
                "Dedicated contractor team",
                "Custom alerting rules",
                "24/7 dedicated monitoring team",
                "Monthly strategy & optimization",
                "SLA guarantees"
            ],
            "response_time": "< 2 minutes",
            "active": True
        }
    ],
    "analytics": [
        {
            "tier_name": "Essential",
            "tier_level": 1,
            "tier_type": "analytics",
            "monthly_price": 199,
            "annual_price": 1990,
            "annual_savings": 398,
            "features": [
                "Monthly energy reports",
                "Basic utility cost tracking",
                "Usage trend visualization",
                "PDF report delivery",
                "12-month data retention"
            ],
            "reporting_frequency": "Monthly",
            "data_retention_months": 12,
            "active": True
        },
        {
            "tier_name": "Professional",
            "tier_level": 2,
            "tier_type": "analytics",
            "monthly_price": 399,
            "annual_price": 3990,
            "annual_savings": 798,
            "features": [
                "Weekly energy reports",
                "Advanced cost optimization insights",
                "Peak demand analysis",
                "Anomaly detection alerts",
                "Interactive dashboards",
                "24-month data retention"
            ],
            "reporting_frequency": "Weekly",
            "data_retention_months": 24,
            "active": True
        },
        {
            "tier_name": "Advanced",
            "tier_level": 3,
            "tier_type": "analytics",
            "monthly_price": 799,
            "annual_price": 7990,
            "annual_savings": 1598,
            "features": [
                "Real-time energy monitoring",
                "Predictive usage forecasting (ML-powered)",
                "Device-level consumption breakdown",
                "Custom data science models",
                "API access for integrations",
                "Unlimited data retention",
                "Quarterly optimization reviews"
            ],
            "reporting_frequency": "Real-time",
            "data_retention_months": None,  # Unlimited
            "most_popular": True,
            "active": True
        },
        {
            "tier_name": "Enterprise",
            "tier_level": 4,
            "tier_type": "analytics",
            "monthly_price": 1499,
            "annual_price": 14990,
            "annual_savings": 2998,
            "features": [
                "Multi-property analytics suite",
                "AI-powered cost optimization",
                "Carbon footprint tracking & ESG reporting",
                "Dedicated data scientist support",
                "Custom model development",
                "White-label reporting",
                "24/7 data engineering support",
                "SLA guarantees & data security compliance"
            ],
            "reporting_frequency": "Real-time + Custom",
            "data_retention_months": None,  # Unlimited
            "active": True
        }
    ]
}


# Add-on services (one-time projects)
ADD_ON_SERVICES = [
    {
        "service_name": "Custom Automation",
        "service_type": "one_time_project",
        "starting_price": 2500,
        "description": "Tailored automation workflows designed for your specific needs",
        "features": [
            "Discovery & requirements gathering",
            "Custom workflow design & implementation",
            "Testing & deployment",
            "30 days of post-deployment support",
            "Documentation & training"
        ],
        "notes": "Does not count against service hours. Billed separately as a project."
    },
    {
        "service_name": "Specialized Software",
        "service_type": "one_time_project",
        "starting_price": 10000,
        "description": "Custom software solutions built to your exact specifications",
        "features": [
            "Full requirements analysis",
            "Architecture & UI/UX design",
            "Full-stack development",
            "Testing, deployment & hosting",
            "90 days of post-launch support",
            "Complete documentation & training"
        ],
        "notes": "Priced per project based on scope. Ongoing maintenance available through service hours."
    }
]
