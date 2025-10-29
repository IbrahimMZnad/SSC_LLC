# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ConsumtionMaterial(models.Model):
    _name = 'consumtion.material'
    _description = 'Consumption Material Report'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    company_id = fields.Many2one('res.company', string='Company')
    project_ids = fields.Many2many('x_projects_list', string='Projects')
    item_ids = fields.Many2many('x_all_items_list', string='Items')

    all_material_consumed = fields.Many2many(
        'x_transaction',
        string='All Material Consumed',
        compute='_compute_consumed_records',
        store=False,
    )

    @api.depends('date_from', 'date_to', 'company_id', 'project_ids', 'item_ids')
    def _compute_consumed_records(self):
        Transaction = self.env['x_transaction']
        for record in self:
            domain = [
                ('x_studio_type_of_transaction', '=', 'Consumed'),
            ]
            # Filter by Company
            if record.company_id:
                domain.append(('x_studio_company', '=', record.company_id.id))
            # Filter by Projects
            if record.project_ids:
                domain.append(('x_studio_project', 'in', record.project_ids.ids))
            # Filter by Date range
            if record.date_from:
                domain.append(('x_studio_date_2', '>=', record.date_from))
            if record.date_to:
                domain.append(('x_studio_date_2', '<=', record.date_to))
            # Filter by Items (optional)
            if record.item_ids:
                domain.append(('x_studio_item_1', 'in', record.item_ids.ids))

            transactions = Transaction.search(domain)
            record.all_material_consumed = transactions

    @api.depends('date_from', 'date_to', 'company_id', 'project_ids')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.company_id:
                parts.append(rec.company_id.name)
            if rec.date_from and rec.date_to:
                parts.append('%s → %s' % (rec.date_from, rec.date_to))
            rec.name = ' - '.join(parts) or 'Consumption Report'
