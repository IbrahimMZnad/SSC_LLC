{
    'name': 'SSC Attendance',
    'version': '1.0',
    'summary': 'Daily Attendance Management',
    'description': 'Custom attendance module for daily attendance with projects and punch machine tracking.',
    'author': 'SSC',
    'depends': ['base'],
    'data': [
    'data/attendance_cron.xml',
    'views/attendance_views.xml',
    'views/attendance_menu.xml',],

    'installable': True,
    'application': True,
}
