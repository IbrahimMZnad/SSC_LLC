from odoo import models, fields
from datetime import date

class ExternalAttendance(models.Model):
    _name = "ssc.external.attendance"
    _description = "External Attendance"

    name = fields.Char(string="Name", default=lambda self: date.today().strftime('%Y-%m-%d'))
    date_field = fields.Date(string="Date", default=date.today)
    day_type = fields.Selection([
        ('regular', 'Regular Day'),
        ('off', 'Off Day')
    ], string="Day Type", default=lambda self: 'off' if date.today().weekday() == 4 else 'regular')

    line_one_ids = fields.One2many('ssc.external.attendance.line', 'attendance_id', string="Line One")
    line_two_ids = fields.One2many('ssc.external.attendance.line', 'attendance_id', string="Line Two")

class ExternalAttendanceLine(models.Model):
    _name = "ssc.external.attendance.line"
    _description = "External Attendance Line"

    name = fields.Char(string="Name")
    employee_id = fields.Char(string="Employee ID")
    attendance_id = fields.Char(string="Attendance ID")
    parent_attendance = fields.Many2one('ssc.external.attendance', string="Attendance Parent")
