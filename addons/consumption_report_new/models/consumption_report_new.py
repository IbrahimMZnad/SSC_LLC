# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime
import calendar

class ConsumptionMaterialReport(models.Model):
    _name = 'consumption.material.report'
    _description = 'Consumption Material Report'

    name = fields.Char(string="Report Name", compute='_compute_name', store=True)
    report_type = fields.Selection([
        ('daily', 'Daily'),
        ('monthly', 'Monthly')
    ], string="Report Type", default='monthly')

    month = fields.Selection(
        [(str(i), calendar.month_name[i]) for i in range(1, 13)],
        string="Month",
        default=lambda self: str(datetime.today().month)
    )

    year = fields.Integer(string="Year", default=lambda self: datetime.today().year)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    project_ids = fields.Many2many('x_projects_list', string="Projects")
    item_ids = fields.Many2many('x_all_items_list', string="Items")
    consumption_ids = fields.Many2many('x_transaction', string="All Material Consumed", compute='_compute_consumed', store=False)

    @api.depends('month', 'year', 'company_id', 'project_ids', 'item_ids')
    def _compute_consumed(self):
        for rec in self:
            if not (rec.month and rec.year and rec.company_id):
                rec.consumption_ids = [(5, 0, 0)]
                continue

            # حدد أول وآخر يوم للشهر
            month_int = int(rec.month)
            year_int = rec.year
            first_day = datetime(year_int, month_int, 1).date()
            last_day = datetime(year_int, month_int, calendar.monthrange(year_int, month_int)[1]).date()

            domain = [
                ('x_studio_type_of_transaction', '=', 'Consumed'),
                ('x_studio_company', '=', rec.company_id.id),
                ('x_studio_project', 'in', rec.project_ids.ids) if rec.project_ids else ('id', '!=', 0),
                ('x_studio_item_1', 'in', rec.item_ids.ids) if rec.item_ids else ('id', '!=', 0),
            ]

            all_transactions = self.env['x_transaction'].search(domain)
            valid_ids = []
            for tr in all_transactions:
                if not tr.x_studio_date_2:
                    continue
                date_value = fields.Date.to_date(tr.x_studio_date_2)
                if first_day <= date_value <= last_day:
                    valid_ids.append(tr.id)
            rec.consumption_ids = [(6, 0, valid_ids)]

    @api.depends('month', 'year')
    def _compute_name(self):
        for rec in self:
            month_name = calendar.month_name[int(rec.month)] if rec.month else ''
            rec.name = f"Consumption Material Report: {month_name} {rec.year}"
