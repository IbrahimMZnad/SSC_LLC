# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
import calendar


class MaterialsReceivedReport(models.Model):
    _name = 'materials.received.report'
    _description = 'Materials Received Report'

    name = fields.Char(string="Report Name", compute='_compute_name', store=True)
    report_type = fields.Selection([
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
    receipt_ids = fields.Many2many('x_material_receipt', string="Material Receipts", compute='_compute_receipts', store=False)

    @api.depends('month', 'year')
    def _compute_name(self):
        for rec in self:
            month_name = calendar.month_name[int(rec.month)] if rec.month else ''
            rec.name = f"Materials Received on {month_name} {rec.year}"

    @api.depends('month', 'year', 'company_id', 'project_ids')
    def _compute_receipts(self):
        for rec in self:
            if not (rec.month and rec.year and rec.company_id and rec.project_ids):
                rec.receipt_ids = [(5, 0, 0)]
                continue

            month_int = int(rec.month)
            year_int = rec.year
            first_day = datetime(year_int, month_int, 1).date()
            last_day = datetime(year_int, month_int, calendar.monthrange(year_int, month_int)[1]).date()

            matched_receipts = self.env['x_material_receipt'].search([
                ('x_studio_company', '=', rec.company_id.id),
                ('x_studio_project', 'in', rec.project_ids.ids)
            ])

            valid_ids = []
            for r in matched_receipts:
                for line in r.x_studio_items_ordered:
                    if not line.x_studio_date:
                        continue
                    date_value = fields.Date.to_date(line.x_studio_date)
                    if first_day <= date_value <= last_day:
                        valid_ids.append(r.id)
                        break

            rec.receipt_ids = [(6, 0, list(set(valid_ids)))]

    # ✅ الكرون: إنشاء تقارير لجميع أشهر 2024 وحتى الشهر الحالي
    @api.model
    def create_monthly_report_auto(self):
        """يتم استدعاؤها يومياً لإنشاء تقارير لكل أشهر 2024 حتى الشهر الحالي."""
        today = datetime.today()
        current_year = today.year
        current_month = today.month

        cron_user = self.env.user

        companies = self.env['res.company'].search([])
        for company in companies:
            for year in [2024, current_year]:
                start_month = 1 if year < current_year else 1
                end_month = 12 if year < current_year else current_month

                for month in range(start_month, end_month + 1):
                    month_str = str(month)
                    existing = self.search([
                        ('month', '=', month_str),
                        ('year', '=', year),
                        ('company_id', '=', company.id)
                    ], limit=1)

                    if not existing:
                        projects = self.env['x_projects_list'].search([])
                        new_report = self.create({
                            'month': month_str,
                            'year': year,
                            'company_id': company.id,
                            'project_ids': [(6, 0, projects.ids)],
                        })

                        message = _("✅ Monthly Materials Received Report created automatically for %s (%s %s) by Scheduled Action user: %s") % (
                            company.name,
                            calendar.month_name[month],
                            year,
                            cron_user.name
                        )
                        new_report.message_post(body=message)
                        self.env.cr.commit()
                        _logger = self.env['ir.logging']
                        _logger.create({
                            'name': 'Materials Received Report Cron',
                            'type': 'server',
                            'dbname': self._cr.dbname,
                            'level': 'INFO',
                            'message': message,
                            'path': 'materials.received.report',
                            'func': 'create_monthly_report_auto',
                            'line': 0,
                        })
