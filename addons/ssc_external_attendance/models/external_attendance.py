from odoo import models, fields, api
from datetime import date

class ExternalAttendance(models.Model):
    _name = "ssc.external.attendance"
    _description = "External Attendance"

    name = fields.Char(string="Name", default=lambda self: f"Today's Date ({date.today()})")
    date_field = fields.Date(string="Date", default=fields.Date.context_today)
    day_type = fields.Selection(
        [
            ("regular", "Regular Day"),
            ("off", "Off Day"),
        ],
        string="Day Type",
        default="regular"
    )

    # One2many to attendance lines
    line_ids = fields.One2many("ssc.external.attendance.line", "attendance_ref", string="Attendance Lines")


class ExternalAttendanceLine(models.Model):
    _name = "ssc.external.attendance.line"
    _description = "External Attendance Line"

    name = fields.Char(string="Name")
    attendance_id = fields.Char(string="Attendance ID")

    attendance_ref = fields.Many2one("ssc.external.attendance", string="Attendance Reference")
