from odoo import models, fields, api
from datetime import date

class ExternalAttendanceLine(models.Model):
    _name = 'ssc.external.attendance.line'
    _description = 'External Attendance Line'

    name = fields.Char(string="Name")
    attendance_id = fields.Char(string="Attendance ID")
    attendance_ref = fields.Many2one('ssc.external.attendance', string="Attendance Reference")


class ExternalAttendance(models.Model):
    _name = 'ssc.external.attendance'
    _description = 'External Attendance'

    name = fields.Char(string="Name")
    date_field = fields.Date(string="Date", default=date.today)
    day_type = fields.Selection(
        [('regular', 'Regular Day'), ('off', 'Off Day')],
        string="Day Type",
        default='regular'
    )
    att_record = fields.One2many('ssc.external.attendance.line', 'attendance_ref', string="Attendance Records")

    @api.model
    def create(self, vals):
        # لو التاريخ جمعة -> Off Day
        dt = vals.get('date_field') or date.today()
        if isinstance(dt, str):
            dt = fields.Date.from_string(dt)
        vals['day_type'] = 'off' if dt.weekday() == 4 else 'regular'
        return super().create(vals)
