from odoo import models, fields, api, exceptions
from datetime import date

class ExternalAttendance(models.Model):
    _name = "ssc.external.attendance"
    _description = "External Attendance"
    _sql_constraints = [
        ('unique_date', 'unique(date)', 'Attendance record already exists for this date!')
    ]

    name = fields.Char(
        string="Name", 
        required=True, 
        default=lambda self: str(date.today())
    )
    date = fields.Date(
        string="Date", 
        default=fields.Date.context_today
    )
    type = fields.Selection(
        [('Regular Day', 'Regular Day'), ('Off Day', 'Off Day')],
        string="Type",
        default=lambda self: 'Off Day' if date.today().weekday() == 4 else 'Regular Day'
    )
    line_ids = fields.One2many('ssc.external.attendance.line', 'external_id', string="Attendance Lines")

    @api.model
    def create_daily_attendance(self):
        """إنشاء سجل يومي وإضافة الموظفين تلقائياً"""
        today = fields.Date.context_today(self)
        existing = self.search([('date', '=', today)], limit=1)
        if existing:
            return existing

        # إنشاء السجل
        record = self.create({
            'name': str(today),
            'date': today,
            'type': 'Off Day' if today.weekday() == 4 else 'Regular Day'
        })

        # جلب الموظفين من x_employeeslist
        employees = self.env['x_employeeslist'].search([])
        lines = []
        for emp in employees:
            lines.append((0, 0, {
                'employee_id': emp.id,
                'company_id': emp.x_studio_company.id if emp.x_studio_company else False,
                'attendance_id': emp.x_studio_attendance_id or '',
            }))
        record.write({'line_ids': lines})
        return record


class ExternalAttendanceLine(models.Model):
    _name = "ssc.external.attendance.line"
    _description = "External Attendance Line"

    external_id = fields.Many2one('ssc.external.attendance', string="Attendance Reference", ondelete='cascade')
    attendance_id = fields.Char(string="Attendance ID")
    employee_id = fields.Many2one('x_employeeslist', string="Employee", required=True)
    company_id = fields.Many2one('res.company', string="Company", compute="_compute_company", store=True)

    first_punch = fields.Datetime(string="First Punch")
    last_punch = fields.Datetime(string="Last Punch")
    total_time = fields.Float(string="Total Time (Hours)", compute="_compute_total_time", store=True)
    total_ot = fields.Float(string="Total OT (Hours)", compute="_compute_total_ot", store=True)
    absent = fields.Boolean(string="Absent", compute="_compute_absent", store=True)

    @api.constrains('employee_id')
    def _check_employee_company(self):
        """تأكد أن الموظف عنده شركة محددة"""
        for rec in self:
            if rec.employee_id and not rec.employee_id.x_studio_company:
                raise exceptions.ValidationError(
                    f"Employee {rec.employee_id.display_name} has no company assigned!"
                )

    @api.depends('employee_id')
    def _compute_company(self):
        for rec in self:
            rec.company_id = rec.employee_id.x_studio_company.id if rec.employee_id and rec.employee_id.x_studio_company else False

    @api.depends('first_punch', 'last_punch')
    def _compute_total_time(self):
        for rec in self:
            if rec.first_punch and rec.last_punch:
                delta = rec.last_punch - rec.first_punch
                rec.total_time = delta.total_seconds() / 3600
            else:
                rec.total_time = 0.0

    @api.depends('total_time')
    def _compute_total_ot(self):
        for rec in self:
            rec.total_ot = rec.total_time - 8 if rec.total_time > 8 else 0.0

    @api.depends('first_punch')
    def _compute_absent(self):
        for rec in self:
            if not rec.first_punch or rec.first_punch.strftime("%H:%M") == "00:00":
                rec.absent = True
            else:
                rec.absent = False
