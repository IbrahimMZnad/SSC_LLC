{
    "name": "WorkSite Analytics - Store Reports",
    "version": "1.0",
    "summary": "Generates professional store reports with monthly tabs for Consumed Materials",
    "description": """
        Generates reports for each store with monthly tabs (January 2024 onwards),
        showing Materials Consumed data from x_transaction.
    """,
    "author": "Ibrahim Elzenad",
    "depends": ["base", "x_inventory_stores_pro"],
    "data": [
        "views/store_report_views.xml",
        "reports/store_report_templates.xml",
        "data/cron_generate_store_reports.xml"
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
