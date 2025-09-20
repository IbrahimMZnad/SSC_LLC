from odoo import models, fields
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

    line_ids = fields.One2many(
        "ssc.external.attendance.line",  # موديل الـ lines
        "dummy_id",                       # field dummy فقط لتجنب FK
        string="Attendance Lines"
    )


class ExternalAttendanceLine(models.Model):
    _name = "ssc.external.attendance.line"
    _description = "External Attendance Line"

    attendance_id = fields.Char(string="Attendance ID")
    dummy_id = fields.Char()  # هذا موجود فقط لتفادي FK
