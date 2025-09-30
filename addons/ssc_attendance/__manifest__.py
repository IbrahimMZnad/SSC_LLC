{
    'name': 'SSC Attendance',
    'version': '1.0',
    'category': 'HR',
    'summary': 'Manage daily attendance',
    'author': 'Ibrahim Elzenad',
    'depends': ['base'],
    'data': [
        'views/ssc_attendance_views.xml',
        'views/ssc_attendance_menu.xml',
        'data/ssc_attendance_cron.xml',
    ],
    'installable': True,
    'application': True,
}
