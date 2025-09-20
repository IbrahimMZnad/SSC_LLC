from odoo import models, fields, api
from datetime import date

class ExternalAttendanceLine(models.Model):
    _name = 'ssc.external.attendance.line'
    _description = 'External Attendance Line'

    name = fields.Char(string="Name")
    attendance_id = fields.Char(string="Attendance ID")
    external_attendance_id = fields.Many2one('ssc.external.attendance', string="Attendance Reference")

class ExternalAttendance(models.Model):
    _name = 'ssc.external.attendance'
    _description = 'External Attendance'

    name = fields.Char(string="Name")
    date_field = fields.Date(string="Date", default=date.today())
    day_type = fields.Selection([('regular','Regular Day'),('off','Off Day')], string="Day Type", default='regular')
    att_record = fields.One2many('ssc.external.attendance.line', 'external_attendance_id', string="Attendance Records")

    @api.model
    def create(self, vals):
        if 'date_field' in vals and vals['date_field']:
            dt = vals['date_field']
        else:
            dt = date.today()
        if dt.weekday() == 4:  # الجمعة
            vals['day_type'] = 'off'
        else:
            vals['day_type'] = 'regular'
        return super().create(vals)
