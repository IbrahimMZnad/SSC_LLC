{
    "name": "Store Consumed Report",
    "version": "1.0",
    "author": "Ibrahim Elzenad",
    "website": "https://www.odoo.com",
    "category": "Inventory",
    "summary": "Professional dynamic consumed materials report per store",
    "description": "Generates automatic monthly consumed material reports for each store from x_transaction model.",
    "depends": ["base"],
    "data": [
        "report/store_consumed_report.xml",
        "views/store_consumed_report_menu.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
