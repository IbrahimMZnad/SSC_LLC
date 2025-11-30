from odoo import models, fields, api

class AttendanceReportLine(models.Model):
    _name = 'attendance.report.line'
    _description = 'Attendance Report Line'

    external_id = fields.Many2one('attendance.report', string='Report')
    employee_id = fields.Many2one('x_employeeslist', string='Employee Name')
    employee_att_id = fields.Char(
        string='Employee Att ID', 
        compute='_compute_employee_att_id',
        store=True
    )
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for line in self:
            line.employee_att_id = line.employee_id.x_studio_attendance_id or ''
