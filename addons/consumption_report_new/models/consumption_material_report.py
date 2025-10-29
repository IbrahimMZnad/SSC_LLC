# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime


class ConsumptionMaterialReport(models.Model):
    _name = 'consumption.material.report'
    _description = 'Consumption Material Report'

    name = fields.Char(string="Report Name", compute='_compute_name', store=True)
    
    date_from = fields.Date(string="From Date", required=True, default=lambda self: datetime.today().replace(day=1))
    date_to = fields.Date(string="To Date", required=True, default=lambda self: datetime.today())
    
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    project_ids = fields.Many2many('x_projects_list', string="Projects")
    item_ids = fields.Many2many('x_all_items_list', string="Items")
    
    transaction_ids = fields.Many2many(
        'x_transaction',
        string="All Material Consumed",
        compute='_compute_transactions',
        store=False
    )

    @api.depends('date_from', 'date_to', 'company_id', 'project_ids', 'item_ids')
    def _compute_transactions(self):
        for rec in self:
            domain = [
                ('x_studio_type_of_transaction', '=', 'Consumed'),
                ('x_studio_company', '=', rec.company_id.id),
                ('x_studio_project', 'in', rec.project_ids.ids),
                ('x_studio_date_2', '>=', rec.date_from),
                ('x_studio_date_2', '<=', rec.date_to),
            ]
            if rec.item_ids:
                domain.append(('x_studio_item_1', 'in', rec.item_ids.ids))

            transactions = self.env['x_transaction'].search(domain)
            rec.transaction_ids = [(6, 0, transactions.ids)]

    @api.depends('date_from', 'date_to', 'company_id', 'project_ids', 'item_ids')
    def _compute_name(self):
        for rec in self:
            from_str = rec.date_from.strftime('%d-%m-%Y') if rec.date_from else ''
            to_str = rec.date_to.strftime('%d-%m-%Y') if rec.date_to else ''
            rec.name = f"Consumption Report {from_str} to {to_str}"
