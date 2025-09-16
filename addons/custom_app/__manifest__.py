{
    'name': 'Custom App',
    'version': '1.0',
    'summary': 'Simple app with date and text field',
    'description': 'A simple Odoo module with only two fields',
    'author': 'Ibrahim',
    'category': 'Custom',
    'depends': ['base'],
    'data': [
        'views/custom_view.xml',
    ],
    'installable': True,
    'application': True,
}
