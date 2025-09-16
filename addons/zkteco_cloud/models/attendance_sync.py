from odoo import models, fields, api

class ZKTecoAttendanceSync(models.Model):
    _name = 'zkteco.attendance.sync'
    _description = 'ZKTeco Attendance Sync'

    name = fields.Char(string='Record Name')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    check_in = fields.Datetime(string='Check In')
    check_out = fields.Datetime(string='Check Out')

    @api.model
    def sync_zkteco_attendance(self):
        # هنا راح تحط الكود لاحقًا لسحب البيانات من الجهاز أو الكلاود
        return True
