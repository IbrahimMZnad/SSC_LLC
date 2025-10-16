from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class StoreMonthlyReport(models.Model):
    _name = 'store.monthly.report'
    _description = 'Monthly Report for Stores'

    name = fields.Many2one('x_inventory_stores_pro', string='Store', required=True)
    project = fields.Many2one('x_projects_list', string='Project', related='name.x_studio_project_1', store=True)
    report_lines = fields.One2many('store.monthly.report.line', 'report_id', string='Monthly Report Lines')

    # كرون 1: إنشاء تقارير لكل الاستورات
    def _create_reports_for_all_stores(self):
        stores = self.env['x_inventory_stores_pro'].search([])
        for store in stores:
            if not self.search([('name','=',store.id)]):
                self.create({'name': store.id})

    # كرون 2: تعبئة البيانات من x_transaction
    def _fill_lines_from_transactions(self):
        for report in self.search([]):
            transactions = self.env['x_transaction'].search([
                ('x_studio_store','=',report.name.id),
                ('x_studio_project','=',report.project.id)
            ])
            for trans in transactions:
                month_year = trans.x_studio_date_2.strftime('%B %Y') if trans.x_studio_date_2 else 'Unknown'
                # تحقق من تكرار السطر قبل الإضافة
                if not self.env['store.monthly.report.line'].search([
                    ('report_id','=',report.id),
                    ('transaction_id','=',trans.id)
                ]):
                    self.env['store.monthly.report.line'].create({
                        'report_id': report.id,
                        'month_year': month_year,
                        'item': trans.x_studio_item_1.id,
                        'quantity': trans.x_studio_quantity,
                        'unit': trans.x_studio_unit_1,
                        'type_of_material': trans.x_studio_type_of_material.id,
                        'date': trans.x_studio_date_2,
                        'sector': trans.x_studio_sector.id,
                        'transaction_id': trans.id
                    })
