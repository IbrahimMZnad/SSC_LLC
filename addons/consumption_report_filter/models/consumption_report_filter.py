# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ConsumptionMaterialReport(models.Model):
    _name = 'consumption.material.report'
    _description = 'Consumption Material Report'

    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")
    company_id = fields.Many2one('res.company', string="Company")
    project_ids = fields.Many2many('x_projects_list', string="Projects")
    item_ids = fields.Many2many('x_all_items_list', string="Items Filter")

    consumed_transaction_ids = fields.Many2many(
        'x_transaction',
        string="All Material Consumed",
        compute="_compute_consumed_transactions",
        store=False
    )

    @api.depends('date_from', 'date_to', 'company_id', 'project_ids', 'item_ids')
    def _compute_consumed_transactions(self):
        for record in self:
            domain = [('x_studio_type_of_transaction', '=', 'Consumed')]

            if record.date_from and record.date_to:
                domain += [
                    ('x_studio_date_2', '>=', record.date_from),
                    ('x_studio_date_2', '<=', record.date_to)
                ]
            if record.company_id:
                domain.append(('x_studio_company', '=', record.company_id.id))
            if record.project_ids:
                domain.append(('x_studio_project', 'in', record.project_ids.ids))
            if record.item_ids:
                domain.append(('x_studio_item_1', 'in', record.item_ids.ids))

            transactions = self.env['x_transaction'].search(domain)
            record.consumed_transaction_ids = [(6, 0, transactions.ids)]
