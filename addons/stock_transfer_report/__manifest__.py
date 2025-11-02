# -*- coding: utf-8 -*-
{
    'name': 'Stock Transfer Report',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Report of materials transferred between stores',
    'description': 'Tracks outgoing and incoming materials between stores',
    'depends': ['base'],
    'data': [
        'views/stock_transfer_report_views.xml',
    ],
    'installable': True,
    'application': True,
}
