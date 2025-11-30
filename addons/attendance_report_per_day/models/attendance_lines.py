from odoo import models, fields, api

class AttendanceLines(models.Model):
    _name = 'attendance.lines'
    _description = 'Attendance Lines'

    employee_id = fields.Many2one('x_employeeslist', string='Employee Name')
    employee_att_id = fields.Char(
        string='Employee Att ID', 
        compute='_compute_employee_att_id', store=True)
    
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    # Dummy field لأننا لا نربط بال Main model
    dummy_id = fields.Many2one('attendance.report.per.day')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id if rec.employee_id else ''
