from odoo import models, fields

# SSC Labours
class SSC_Labours_Attendance_Line(models.Model):
    _name = 'ssc.labours.attendance.line'
    _description = 'SSC Labours Attendance Line'

    report_id = fields.Many2one('attendance.report.per.day', string='Report', ondelete='cascade')
    employee_id = fields.Many2one('x_employeeslist', string='Employee')
    employee_att_id = fields.Char(related='employee_id.x_studio_attendance_id', string='Employee Att ID')
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')


# RA Labours
class RA_Labours_Attendance_Line(models.Model):
    _name = 'ra.labours.attendance.line'
    _description = 'RA Labours Attendance Line'

    report_id = fields.Many2one('attendance.report.per.day', string='Report', ondelete='cascade')
    employee_id = fields.Many2one('x_employeeslist', string='Employee')
    employee_att_id = fields.Char(related='employee_id.x_studio_attendance_id', string='Employee Att ID')
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')


# SSC Staff
class SSC_Staff_Attendance_Line(models.Model):
    _name = 'ssc.staff.attendance.line'
    _description = 'SSC Staff Attendance Line'

    report_id = fields.Many2one('attendance.report.per.day', string='Report', ondelete='cascade')
    employee_id = fields.Many2one('x_employeeslist', string='Employee')
    employee_att_id = fields.Char(related='employee_id.x_studio_attendance_id', string='Employee Att ID')
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')


# RA Staff
class RA_Staff_Attendance_Line(models.Model):
    _name = 'ra.staff.attendance.line'
    _description = 'RA Staff Attendance Line'

    report_id = fields.Many2one('attendance.report.per.day', string='Report', ondelete='cascade')
    employee_id = fields.Many2one('x_employeeslist', string='Employee')
    employee_att_id = fields.Char(related='employee_id.x_studio_attendance_id', string='Employee Att ID')
    first_punch = fields.Datetime(string='First Punch')
    last_punch = fields.Datetime(string='Last Punch')
