# -*- coding: utf-8 -*-
from odoo import models, fields
from datetime import date

class ExternalAttendance(models.Model):
    _name = 'ssc.external.attendance'
    _description = 'External Attendance'

    name = fields.Char(string='Name')
    date_field = fields.Date(string='Date', default=fields.Date.context_today)
    day_type = fields.Selection(
        [('Regular Day', 'Regular Day'), ('Off Day', 'Off Day')],
        string='Day Type',
        default=lambda self: 'Off Day' if date.today().weekday() == 4 else 'Regular Day'
    )

    att_record = fields.One2many(
        'ssc.external.attendance.line', 
        'parent_id', 
        string='Attendance Lines'
    )


class ExternalAttendanceLine(models.Model):
    _name = 'ssc.external.attendance.line'
    _description = 'Attendance Line'

    name = fields.Char(string='Name')
    attendance_id = fields.Char(string='Attendance ID')
    parent_id = fields.Many2one('ssc.external.attendance', string='Parent Attendance')
