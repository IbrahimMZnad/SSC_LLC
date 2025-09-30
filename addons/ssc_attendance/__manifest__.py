{
    'name': 'SSC Attendance',
    'version': '1.0',
    'summary': 'Daily Attendance Management',
    'description': 'Custom attendance module for daily attendance with projects and punch machine tracking.',
    'author': 'SSC',
    'depends': ['base'],
    'data': [
    'data/ssc_attendance_cron.xml',
    'views/ssc_attendance_views.xml',
    'views/ssc_attendance_menu.xml',],

    'installable': True,
    'application': True,
}
