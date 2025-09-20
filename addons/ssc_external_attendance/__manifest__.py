{
    'name': 'SSC External Attendance',
    'version': '1.0',
    'summary': 'External Attendance Module for SSC',
    'description': 'Simple external attendance form for automated lines.',
    'author': 'Ibrahim Alznad',
    'category': 'Human Resources',
    'depends': ['base', 'hr'],
    'data': [
        'views/external_attendance_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
