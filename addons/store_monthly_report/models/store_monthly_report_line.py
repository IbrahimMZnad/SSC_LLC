from odoo import models, fields, api

class StoreMonthlyReportLine(models.Model):
    _name = 'store.monthly.report.line'
    _description = 'Store Monthly Report Line'

    report_id = fields.Many2one('store.monthly.report', string='Report', required=True)
    month_year = fields.Char('Month Year')
    item = fields.Many2one('x_all_items_list', string='Item')
    quantity = fields.Float('Quantity')
    unit = fields.Char('Unit')
    type_of_material = fields.Many2one('x_type_of_material', string='Type of Material')
    date = fields.Date('Date')
    day = fields.Char('Day', compute='_compute_day', store=True)
    sector = fields.Many2one('x_sectorss', string='Sector')
    transaction_id = fields.Many2one('x_transaction', string='Transaction')

    @api.depends('date')
    def _compute_day(self):
        for record in self:
            record.day = record.date.strftime('%A') if record.date else ''
