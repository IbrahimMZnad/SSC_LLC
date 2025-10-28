# -*- coding: utf-8 -*-
{
    'name': 'Materials Received Report',
    'version': '1.0',
    'author': 'Ibrahim M. Elznad',
    'category': 'Warehouse',
    'summary': 'Generate monthly and daily materials received reports by project and company',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/materials_received_report_views.xml',
    ],
    'application': True,
    'installable': True,
}
