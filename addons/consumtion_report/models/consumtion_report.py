# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime

class ConsumtionReport(models.Model):
    _name = 'consumtion.report'
    _description = 'Consumption Report'

    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    project_ids = fields.Many2many('x_projects_list', string="Projects")
    item_ids = fields.Many2many('x_all_items_list', string="Items")
    all_material_consumed = fields.Many2many('x_transaction', string="All Material Consumed", compute='_compute_consumed', store=False)

    @api.depends('date_from', 'date_to', 'company_id', 'project_ids', 'item_ids')
    def _compute_consumed(self):
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
            matched = self.env['x_transaction'].search(domain)
            rec.all_material_consumed = [(6, 0, matched.ids)]
