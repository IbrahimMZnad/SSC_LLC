{
    'name': 'SSC Attendance',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Simple attendance tracking',
    'author': 'Ibrahim Alznad',
    'depends': ['base'],
    'data': [
        'data/ssc_attendance_cron.xml',   # Cron job file
        'views/ssc_attendance_views.xml' # Views
    ],
    'installable': True,
    'application': True,
}
