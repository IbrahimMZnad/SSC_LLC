from odoo import models, fields, api
from datetime import datetime

class ExternalAttendance(models.Model):
    _name = 'ssc.external.attendance'
    _description = 'External Attendance'

    name = fields.Char(string="Name", default=lambda self: "Today's Date (%s)" % fields.Date.today())
    date_field = fields.Date(string="Date", default=fields.Date.today)
    day_type = fields.Selection(
        [('regular', 'Regular Day'), ('off', 'Off Day')],
        string="Type",
        default=lambda self: 'off' if datetime.today().strftime('%A') == 'Friday' else 'regular'
    )

    attendance_sheet = fields.One2many('ssc.external.attendance.line', 'attendance_id', string="Attendance Sheet")

class ExternalAttendanceLine(models.Model):
    _name = 'ssc.external.attendance.line'
    _description = 'External Attendance Line'

    attendance_id = fields.Many2one('ssc.external.attendance', string="Attendance")
    name = fields.Char(string="Attendance ID")
