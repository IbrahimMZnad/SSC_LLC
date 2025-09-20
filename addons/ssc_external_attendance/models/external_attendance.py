from odoo import models, fields, api
from datetime import date

class SscExternalAttendance(models.Model):
    _name = "ssc.external.attendance"
    _description = "External Attendance"

    name = fields.Char(string="Name", default=lambda self: str(date.today()))
    date_field = fields.Date(string="Date", default=fields.Date.today)
    day_type = fields.Selection([
        ('regular', 'Regular Day'),
        ('off', 'Off Day')
    ], string="Day Type", default='regular')

    line_one_ids = fields.One2many('ssc.external.attendance.line', 'attendance_id_main', string="Line One")
    line_two_ids = fields.One2many('ssc.external.attendance.line', 'attendance_id_main', string="Line Two")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if date.today().weekday() == 4:  # Friday
            res['day_type'] = 'off'
        else:
            res['day_type'] = 'regular'
        return res

class SscExternalAttendanceLine(models.Model):
    _name = "ssc.external.attendance.line"
    _description = "External Attendance Line"

    name = fields.Char(string="Name")
    attendance_id = fields.Char(string="Attendance ID")
    attendance_id_main = fields.Many2one('ssc.external.attendance', string="Attendance Reference")
