from odoo import models, fields

class AttendanceReport(models.Model):
    _name = 'attendance.report'
    _description = 'Attendance Report Per Day'

    project_id = fields.Many2one('x_projects_list', string='Project')
    date = fields.Date(string='Date')
    name = fields.Char(string='Name')

    show_ssc_labours = fields.Boolean(string='Show SSC Labours Attendance')
    show_ra_labours = fields.Boolean(string='Show RA Labours Attendance')
    show_ssc_staff = fields.Boolean(string='Show SSC Staff Attendance')
    show_ra_staff = fields.Boolean(string='Show RA Staff Attendance')

    # One2many lines بدون Many2one عكسي
    ssc_labours_lines = fields.One2many('attendance.report.line', string='SSC Labours Attendance')
    ra_labours_lines = fields.One2many('attendance.report.line', string='RA Labours Attendance')
    ssc_staff_lines = fields.One2many('attendance.report.line', string='SSC Staff Attendance')
    ra_staff_lines = fields.One2many('attendance.report.line', string='RA Staff Attendance')
