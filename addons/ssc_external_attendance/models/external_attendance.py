from odoo import models, fields, api
from datetime import date

class SolO2M(models.Model):
    _name = "ssc.external.attendance.line"
    _description = "External Attendance Line"

    name = fields.Char(string="Name")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    attendance_id = fields.Char(string="Attendance ID")  # تم تعديل النوع Char

class ExternalAttendance(models.Model):
    _name = "ssc.external.attendance"
    _description = "External Attendance"

    name = fields.Char(string="Name", default=lambda self: date.today().strftime('%Y-%m-%d'))
    date_field = fields.Date(string="Date", default=date.today)
    day_type = fields.Selection([
        ('regular', 'Regular Day'),
        ('off', 'Off Day')
    ], string="Day Type", default='regular')

    line_one_ids = fields.One2many('ssc.external.attendance.line', 'attendance_id', string="Line One")
    line_two_ids = fields.One2many('ssc.external.attendance.line', 'attendance_id', string="Line Two")

    @api.model
    def create(self, vals):
        today = date.today()
        if today.weekday() == 4:  # الجمعة weekday=4
            vals['day_type'] = 'off'
        else:
            vals['day_type'] = 'regular'
        if 'name' not in vals or not vals['name']:
            vals['name'] = today.strftime('%Y-%m-%d')
        if 'date_field' not in vals or not vals['date_field']:
            vals['date_field'] = today
        return super().create(vals)
