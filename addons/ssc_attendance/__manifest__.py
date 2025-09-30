{
    'name': 'SSC Attendance',
    'version': '1.0',
    'summary': 'Daily Attendance Management',
    'description': 'Custom attendance module for daily attendance with projects and punch machine tracking.',
    'author': 'SSC',
    'depends': ['base'],
    'data': [
        'views/ssc_attendance_views.xml',
        'data/ssc_attendance_cron.xml',
    ],
    'installable': True,
    'application': True,
}
