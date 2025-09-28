{
    'name': 'External Attendance',
    'version': '1.0',
    'category': 'HR',
    'summary': 'External Attendance Management',
    'description': """
        Module to track external attendance.
        - Creates daily attendance record automatically.
        - Populates attendance lines for all employees except Engineer Office Staff.
        - Computes total time, total OT, and absent flag.
    """,
    'author': 'Ibrahim Alznad',
    'depends': ['base', 'hr'],
    'data': [
        'views/external_attendance_views.xml',
        'data/external_attendance_cron.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
