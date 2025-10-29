# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MaterialUsageReport(models.Model):
    _name = 'material.usage.report'
    _description = 'Material Usage Report'

    title = fields.Char(string="Report Title", compute='_compute_title', store=True)
    company_ref = fields.Many2one('res.company', string="Company", required=True)
    start_period = fields.Date(string="Start Date", required=True)
    end_period = fields.Date(string="End Date", required=True)
    selected_projects = fields.Many2many('project.project', string="Projects")
    usage_entries = fields.One2many('material.usage.report.entry', 'report_ref', string="Usage Entries")

    def generate_usage(self):
        self.ensure_one()
        # حذف السجلات السابقة
        self.usage_entries = [(5, 0, 0)]

        # بناء شرط البحث
        criteria = [
            ('company_id', '=', self.company_ref.id),
            ('project_id', 'in', self.selected_projects.ids),
            ('consumption_date', '>=', self.start_period),
            ('consumption_date', '<=', self.end_period)
        ]
        usage_records = self.env['x_consumed_materials'].search(criteria)

        # إنشاء السجلات الجديدة للخطوط
        entries = []
        for rec in usage_records:
            entries.append((0, 0, {
                'material_label': rec.material_name,
                'amount_used': rec.quantity,
                'unit_type': rec.unit,
                'project_link': rec.project_id.id,
                'date_used': rec.consumption_date,
            }))
        self.usage_entries = entries

    @api.depends('company_ref', 'start_period', 'end_period')
    def _compute_title(self):
        for rec in self:
            rec.title = f"Material Usage Report {rec.start_period} - {rec.end_period}"

class MaterialUsageReportEntry(models.Model):
    _name = 'material.usage.report.entry'
    _description = 'Material Usage Report Entry'

    report_ref = fields.Many2one('material.usage.report', string="Report")
    material_label = fields.Char(string="Material Name")
    amount_used = fields.Float(string="Quantity")
    unit_type = fields.Char(string="Unit")
    project_link = fields.Many2one('project.project', string="Project")
    date_used = fields.Date(string="Date of Usage")
