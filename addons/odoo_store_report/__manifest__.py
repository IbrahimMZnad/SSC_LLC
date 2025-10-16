{
    'name': 'Odoo Store Report',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Monthly store reports from transactions',
    'description': """
        This module generates monthly reports for each store
        and imports data from x_transaction into store.report.
    """,
    'author': 'Ibrahim Elzenad',
    'website': 'https://www.example.com',
    'depends': ['base', 'stock'],  # أضف أي موديل آخر يعتمد عليه
    'data': [
        'views/store_report_views.xml',
        'data/store_report_cron.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
