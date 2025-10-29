# -*- coding: utf-8 -*-
{
    'name': "Consumtion Material",
    'version': "1.0",
    'category': "Custom",
    'summary': "Report of all consumed materials",
    'description': "Module to generate Consumption Material report based on filters",
    'depends': ['base', 'x_transaction', 'x_projects_list', 'x_all_items_list'],
    'data': [
        'views/consumtion_material_views.xml',
    ],
    'installable': True,
    'application': True,
}
