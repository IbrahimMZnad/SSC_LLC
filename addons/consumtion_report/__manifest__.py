{
    'name': 'Consumption Report',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Report for consumed materials',
    'description': 'Module to generate report of consumed materials based on date, project, company, and items.',
    'author': 'Ibrahim Alznad',
    'depends': ['base', 'x_transaction', 'x_projects_list', 'x_all_items_list'],
    'data': [
        'views/consumtion_report_views.xml',
        'views/consumtion_report_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
