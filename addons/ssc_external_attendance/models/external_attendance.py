from odoo import models, fields, api
from datetime import date

class ExternalAttendance(models.Model):
    _name = "ssc.external.attendance"
    _description = "External Attendance"

    name = fields.Char(string="Name", required=True, default=lambda self: str(date.today()))
    date = fields.Date(string="Date", default=fields.Date.context_today)
    type = fields.Selection(
        [('Regular Day', 'Regular Day'), ('Off Day', 'Off Day')],
        string="Type",
        default=lambda self: 'Off Day' if date.today().weekday() == 4 else 'Regular Day'  # الجمعة = 4
    )
    line_ids = fields.One2many('ssc.external.attendance.line', 'external_id', string="Attendance Lines")


class ExternalAttendanceLine(models.Model):
    _name = "ssc.external.attendance.line"
    _description = "External Attendance Line"

    external_id = fields.Many2one('ssc.external.attendance', string="Attendance Reference", ondelete='cascade')
    attendance_id = fields.Char(string="Attendance ID")
