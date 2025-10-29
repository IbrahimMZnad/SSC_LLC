# -*- coding: utf-8 -*-
{
    'name': 'Consumption Material',
    'version': '1.0',
    'category': 'Reports',
    'summary': 'Consumption Material Report Module',
    'description': """
Generate and filter consumed materials based on company, project, date range, and items.
""",
    'author': 'Ibrahim Alznad',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/consumtion_material_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
