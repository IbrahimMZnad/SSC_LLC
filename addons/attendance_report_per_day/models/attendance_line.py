# attendance_report_per_day/models/attendance_line.py
from odoo import models, fields, api

# ========= SSC Labours =========
class SSCLaboursAttendanceLines(models.Model):
    _name = 'ssc.labours.attendance.lines'
    _description = 'SSC Labours Attendance Lines'

    attendance_id = fields.Many2one('attendance.report.per.day', string='Attendance Report')
    employee_id = fields.Many2one('x_employeeslist', string='Employee Name')
    employee_att_id = fields.Char(string='Employee Att ID', compute='_compute_employee_att_id', store=True)
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id if rec.employee_id else ''

# ========= RA Labours =========
class RALaboursAttendanceLines(models.Model):
    _name = 'ra.labours.attendance.lines'
    _description = 'RA Labours Attendance Lines'

    attendance_id = fields.Many2one('attendance.report.per.day', string='Attendance Report')
    employee_id = fields.Many2one('x_employeeslist', string='Employee Name')
    employee_att_id = fields.Char(string='Employee Att ID', compute='_compute_employee_att_id', store=True)
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id if rec.employee_id else ''

# ========= SSC Staff =========
class SSCStaffAttendanceLines(models.Model):
    _name = 'ssc.staff.attendance.lines'
    _description = 'SSC Staff Attendance Lines'

    attendance_id = fields.Many2one('attendance.report.per.day', string='Attendance Report')
    employee_id = fields.Many2one('x_employeeslist', string='Employee Name')
    employee_att_id = fields.Char(string='Employee Att ID', compute='_compute_employee_att_id', store=True)
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id if rec.employee_id else ''

# ========= RA Staff =========
class RAStaffAttendanceLines(models.Model):
    _name = 'ra.staff.attendance.lines'
    _description = 'RA Staff Attendance Lines'

    attendance_id = fields.Many2one('attendance.report.per.day', string='Attendance Report')
    employee_id = fields.Many2one('x_employeeslist', string='Employee Name')
    employee_att_id = fields.Char(string='Employee Att ID', compute='_compute_employee_att_id', store=True)
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id if rec.employee_id else ''
