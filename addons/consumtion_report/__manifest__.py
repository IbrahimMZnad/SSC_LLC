{
    'name': 'Consumption Report',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Report for consumed materials',
    'description': 'Module to generate report of consumed materials based on date, project, company, and items.',
    'author': 'Ibrahim Alznad',
    'depends': ['base'],
    'data': [
        'views/consumtion_report_views.xml',
        'views/consumtion_report_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
