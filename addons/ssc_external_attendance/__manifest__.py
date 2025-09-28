{
    'name': 'External Attendance',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Simple external attendance tracking',
    'author': 'Ibrahim Alznad',
    'depends': ['base'],
    'data': [
        'data/external_attendance_cron.xml',   # Cron job file
        'views/external_attendance_views.xml' # Views
    ],
    'installable': True,
    'application': True,
}
