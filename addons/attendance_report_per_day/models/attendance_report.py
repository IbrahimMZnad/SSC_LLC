from odoo import models, fields

class AttendanceReport(models.Model):
    _name = 'attendance.report'
    _description = 'Attendance Report'

    project_id = fields.Many2one('x_projects_list', string='Project')
    date = fields.Date(string='Date')
    name = fields.Char(string='Name')

    show_ssc_labours = fields.Boolean(string='Show SSC Labours Attendance')
    show_ra_labours = fields.Boolean(string='Show RA Labours Attendance')
    show_ssc_staff = fields.Boolean(string='Show SSC Staff Attendance')
    show_ra_staff = fields.Boolean(string='Show RA Staff Attendance')

    ssc_labours_lines = fields.One2many(
        'attendance.report.line', 'external_id', string='SSC Labours Attendance'
    )
    ra_labours_lines = fields.One2many(
        'attendance.report.line', 'external_id', string='RA Labours Attendance'
    )
    ssc_staff_lines = fields.One2many(
        'attendance.report.line', 'external_id', string='SSC Staff Attendance'
    )
    ra_staff_lines = fields.One2many(
        'attendance.report.line', 'external_id', string='RA Staff Attendance'
    )
