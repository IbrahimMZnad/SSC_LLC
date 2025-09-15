{
    'name': 'ZKTeco Cloud Sync',
    'version': '1.0',
    'summary': 'Sync attendance data from ZKTeco Cloud to Odoo',
    'description': 'Fetch attendance logs from ZKTeco Cloud and update x_daily_attendance.',
    'author': 'Ibrahim MZnad',
    'website': 'https://yourcompany.com',
    'category': 'Human Resources',
    'depends': ['base', 'hr'],
    'data': [
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
}
