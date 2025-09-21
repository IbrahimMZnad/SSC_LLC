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

    # الحقول الجديدة
    employee_name = fields.Char(string="Employee Name")
    first_punch = fields.Datetime(string="First Punch")
    last_punch = fields.Datetime(string="Last Punch")
    total_time = fields.Float(string="Total Time (Hours)", compute="_compute_total_time", store=True)
    total_ot = fields.Float(string="Total OT (Hours)", compute="_compute_total_ot", store=True)
    absent = fields.Boolean(string="Absent", compute="_compute_absent", store=True)

    @api.depends('first_punch', 'last_punch')
    def _compute_total_time(self):
        for rec in self:
            if rec.first_punch and rec.last_punch:
                delta = rec.last_punch - rec.first_punch
                rec.total_time = delta.total_seconds() / 3600
            else:
                rec.total_time = 0.0

    @api.depends('total_time')
    def _compute_total_ot(self):
        for rec in self:
            rec.total_ot = rec.total_time - 8 if rec.total_time > 8 else 0.0

    @api.depends('first_punch')
    def _compute_absent(self):
        for rec in self:
            if not rec.first_punch or rec.first_punch.strftime("%H:%M") == "00:00":
                rec.absent = True
            else:
                rec.absent = False
