from odoo import models, fields

class ExternalAttendance(models.Model):
    _name = 'ssc.external.attendance'
    _description = 'External Attendance'

    name = fields.Char(string="Reference")
    date = fields.Date(string="Date")
    note = fields.Text(string="Note")

    line_ids = fields.One2many(
        'ssc.external.attendance.line',
        'attendance_id',
        string="Attendance Lines"
    )


class ExternalAttendanceLine(models.Model):
    _name = 'ssc.external.attendance.line'
    _description = 'External Attendance Line'

    attendance_id = fields.Many2one(
        'ssc.external.attendance',
        string="Attendance"
    )
    employee = fields.Char(string="Employee Name")
    hours = fields.Float(string="Worked Hours")
