# __manifest__.py
{
    'name': 'Store Monthly Report',
    'version': '1.0',
    'category': 'Reporting',
    'summary': 'Generate monthly reports for stores from consumed materials',
    'description': 'This module generates monthly store reports using consumed materials.',
    'author': 'Ibrahim Elzenad',
    'depends': ['base'],
    'data': [
        'views/store_monthly_report_views.xml',
        # لو عندك أي security أو data files أضفهم هنا
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
