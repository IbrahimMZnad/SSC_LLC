from odoo import models, fields, api

class AttendanceReportPerDay(models.Model):
    _name = 'attendance.report.per.day'
    _description = 'Attendance Report Per Day'

    project_id = fields.Many2one('x_projects_list', string='Project', required=True)
    date = fields.Date(string='Date', required=True)
    name = fields.Char(string='Name')

    show_ssc_labours_attendance = fields.Boolean(string='Show SSC Labours Attendance')
    show_ra_labours_attendance = fields.Boolean(string='Show RA Labours Attendance')
    show_ssc_staff_attendance = fields.Boolean(string='Show SSC Staff Attendance')
    show_ra_staff_attendance = fields.Boolean(string='Show RA Staff Attendance')

    ssc_labours_attendance_ids = fields.One2many('ssc.labours.attendance.lines', 'report_id')
    ra_labours_attendance_ids = fields.One2many('ra.labours.attendance.lines', 'report_id')
    ssc_staff_attendance_ids = fields.One2many('ssc.staff.attendance.lines', 'report_id')
    ra_staff_attendance_ids = fields.One2many('ra.staff.attendance.lines', 'report_id')


class SSCLaboursAttendanceLines(models.Model):
    _name = 'ssc.labours.attendance.lines'
    _description = 'SSC Labours Attendance Lines'

    report_id = fields.Many2one('attendance.report.per.day')
    employee_id = fields.Many2one('x_employeeslist', string='Employee')
    employee_att_id = fields.Char(compute='_compute_employee_att_id', store=True)
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id or False


class RALaboursAttendanceLines(models.Model):
    _name = 'ra.labours.attendance.lines'
    _description = 'RA Labours Attendance Lines'

    report_id = fields.Many2one('attendance.report.per.day')
    employee_id = fields.Many2one('x_employeeslist', string='Employee')
    employee_att_id = fields.Char(compute='_compute_employee_att_id', store=True)
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id or False


class SSCStaffAttendanceLines(models.Model):
    _name = 'ssc.staff.attendance.lines'
    _description = 'SSC Staff Attendance Lines'

    report_id = fields.Many2one('attendance.report.per.day')
    employee_id = fields.Many2one('x_employeeslist', string='Employee')
    employee_att_id = fields.Char(compute='_compute_employee_att_id', store=True)
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id or False


class RAStaffAttendanceLines(models.Model):
    _name = 'ra.staff.attendance.lines'
    _description = 'RA Staff Attendance Lines'

    report_id = fields.Many2one('attendance.report.per.day')
    employee_id = fields.Many2one('x_employeeslist', string='Employee')
    employee_att_id = fields.Char(compute='_compute_employee_att_id', store=True)
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')

    @api.depends('employee_id')
    def _compute_employee_att_id(self):
        for rec in self:
            rec.employee_att_id = rec.employee_id.x_studio_attendance_id or False
