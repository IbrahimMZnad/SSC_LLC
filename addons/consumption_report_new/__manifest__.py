# -*- coding: utf-8 -*-
{
    'name': 'Consumption Material New',
    'version': '1.0',
    'category': 'Reports',
    'summary': 'Consumption Material Report Module New',
    'description': """
Generate and filter consumed materials based on company, project, date range, and items.
""",
    'author': 'Ibrahim Alznad',
    'depends': ['base'],
    'data': [
        'views/consumption_report_new_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
