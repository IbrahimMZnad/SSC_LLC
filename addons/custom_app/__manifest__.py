# -*- coding: utf-8 -*-
{
    'name': 'Custom App',
    'version': '1.0',
    'summary': 'Simple app with Char, Text, and Date fields',
    'description': 'This is a simple custom app with three fields: Name, Description, Date',
    'category': 'Custom',
    'author': 'Ibrahim Alznad',
    'depends': ['base'],
    'data': [
        'views/custom_app_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
