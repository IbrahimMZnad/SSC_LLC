{
    'name': 'Project Consumption',
    'version': '1.0',
    'summary': 'Track consumed materials per project',
    'description': 'This module tracks project materials consumption using x_all_items_list.',
    'author': 'Ibrahim Alznad',
    'category': 'Project',
    'depends': ['base', 'project'],
    'data': [
        'views/project_consumption_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
