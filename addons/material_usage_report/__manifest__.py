# -*- coding: utf-8 -*-
{
    'name': 'Material Usage Reporting',
    'version': '1.0',
    'category': 'Reporting',
    'summary': 'Generate reports for material usage filtered by company, projects, and period',
    'description': """
This module allows users to generate material usage reports
based on selected company, projects, and date range.
""",
    'author': 'Ibrahim Alznad',
    'depends': ['base'],
    'data': [
        'views/material_usage_report_views.xml',
    ],
    'installable': True,
    'application': False,
}
