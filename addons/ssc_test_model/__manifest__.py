{
    'name': 'SSC Test Model',
    'version': '1.0',
    'summary': 'Simple test model for SSC',
    'description': 'This is a test module to verify menu and dashboard visibility.',
    'author': 'Ibrahim Alznad',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        'views/test_model_views.xml',
        'views/test_model_menu.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
