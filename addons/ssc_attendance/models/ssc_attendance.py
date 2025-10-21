from odoo import models, fields, api
from datetime import date, timedelta, datetime
import requests

class SSCAttendance(models.Model):
    _name = "ssc.attendance"
    _description = "SSC Attendance"

    _sql_constraints = [
        ('unique_date', 'unique(date)', 'Attendance record already exists for this date!')
    ]

    # -------------------------
    # الحقول الأساسية / Main Fields
    # -------------------------
    name = fields.Char(string="Name", required=True, default=lambda self: str(date.today()))
    date = fields.Date(string="Date", default=fields.Date.context_today)
    type = fields.Selection(
        [('Regular Day', 'Regular Day'), ('Off Day', 'Off Day')],
        string="Type",
        default=lambda self: 'Off Day' if date.today().weekday() == 4 else 'Regular Day'
    )
    day_name = fields.Char(string="Day Name", compute="_compute_day_name", store=True)
    line_ids = fields.One2many('ssc.attendance.line', 'external_id', string="Attendance Lines")

    # -------------------------
    # دالة لحساب اسم اليوم / Compute day name
    # -------------------------
    @api.depends('date')
    def _compute_day_name(self):
        for rec in self:
            rec.day_name = rec.date.strftime('%A') if rec.date else ''

    # -------------------------
    # إنشاء سجل يومي تلقائي / Auto-create daily attendance
    # -------------------------
    @api.model
    def create_daily_attendance(self):
        today = fields.Date.context_today(self)
        last_record = self.search([], order="date desc", limit=1)
        start_date = last_record.date if last_record else today
        if not start_date:
            start_date = today

        current_date = start_date
        while current_date <= today:
            existing = self.search([('date', '=', current_date)], limit=1)
            if not existing:
                vals = {
                    'name': str(current_date),
                    'date': current_date,
                    'type': 'Off Day' if current_date.weekday() == 4 else 'Regular Day'
                }
                self.create(vals)
            current_date += timedelta(days=1)

    # -------------------------
    # إعادة كتابة دالة create لإضافة الخطوط تلقائي / Override create to populate lines
    # -------------------------
    @api.model
    def create(self, vals):
        record = super().create(vals)
        if not vals.get('line_ids'):
            record._populate_lines()
        return record

    # -------------------------
    # تعبئة خطوط الحضور تلقائي للموظفين / Populate attendance lines for employees
    # -------------------------
    def _populate_lines(self):
        self.ensure_one()
        Employee = self.env['x_employeeslist']
        employees = Employee.search([])
        lines = []
        for emp in employees:
            lines.append((0, 0, {
                'employee_id': emp.id,
                'attendance_id': emp.x_studio_attendance_id or '',
                'company_id': emp.x_studio_company.id if getattr(emp, 'x_studio_company', False) else False,
                'staff': emp.x_studio_engineeroffice_staff,
                'on_leave': emp.x_studio_on_leave,
            }))
        if lines:
            self.write({'line_ids': lines})

    # -------------------------
    # جلب بيانات BioCloud / Fetch BioCloud data
    # -------------------------
    def fetch_bioclock_data(self):
        """جلب بيانات الحضور من BioCloud / Fetch attendance data from BioCloud API"""
        url = "https://57.biocloud.me:8199/api_gettransctions"
        token = "fa83e149dabc49d28c477ea557016d03"
        headers = {
            "token": token,
            "Content-Type": "application/json"
        }

        # تحديد فترة جلب البيانات (اليوم السابق واليوم الحالي) / Define date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        payload = {
            "StartDate": start_date.strftime("%Y-%m-%d 00:00:00"),
            "EndDate": end_date.strftime("%Y-%m-%d 23:59:59")
        }

        try:
            # استدعاء API / Call API
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

            data = response.json()
            if "result" in data and data["result"] != "OK":
                raise Exception(data.get("message", "Unexpected response"))

            transactions = data.get("data", [])
            Employee = self.env['x_employeeslist']

            synced_count = 0  # عداد السجلات المتزامنة / Counter

            for trx in transactions:
                try:
                    verify_time_str = trx.get("VerifyTime")
                    badge_number = trx.get("BadgeNumber")
                    device_serial = trx.get("DeviceSerialNumber")

                    if not (verify_time_str and badge_number):
                        continue

                    # تحويل VerifyTime إلى datetime / Convert VerifyTime to datetime
                    verify_dt = datetime.fromisoformat(verify_time_str)
                    verify_date = verify_dt.date()  # استخدام اليوم فقط للمقارنة / Use only date

                    # البحث عن سجل attendance في نفس اليوم / Search attendance record by date
                    attendance = self.search([('date', '=', verify_date)], limit=1)
                    if not attendance:
                        continue

                    # البحث عن الموظف المطابق للـ BadgeNumber / Search employee by BadgeNumber
                    employee = Employee.search([('x_studio_attendance_id', '=', badge_number)], limit=1)
                    if not employee:
                        continue

                    # البحث عن سطر الموظف في attendance line / Search employee line
                    line = attendance.line_ids.filtered(lambda l: l.employee_id == employee)
                    if not line:
                        continue
                    line = line[0]

                    # تعبئة الحقول المطلوبة / Fill punch data
                    if not line.first_punch:
                        line.first_punch = verify_dt
                    line.last_punch = verify_dt
                    line.punch_machine_id = device_serial

                    synced_count += 1

                except Exception as sub_e:
                    # تجاوز الخطأ في السطر الواحد / Skip single line errors
                    continue

            # إظهار عدد السجلات المتزامنة / Display synced count
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'BioCloud Sync',
                    'message': f'{synced_count} records synced successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sync Error',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }


class SSCAttendanceLine(models.Model):
    _name = "ssc.attendance.line"
    _description = "Attendance Line"

    external_id = fields.Many2one('ssc.attendance', string="Attendance Reference", ondelete='cascade')
    employee_id = fields.Many2one('x_employeeslist', string="Employee", required=True)
    company_id = fields.Many2one('res.company', string="Company", compute="_compute_company", store=True)
    attendance_id = fields.Char(string="Attendance ID")
    project_id = fields.Many2one('x_projects_list', string="Project")
    punch_machine_id = fields.Char(string="Punch Machine ID")
    first_punch = fields.Datetime(string="First Punch")
    last_punch = fields.Datetime(string="Last Punch")
    total_time = fields.Float(string="Total Time (Hours)", compute="_compute_total_time", store=True)
    total_ot = fields.Float(string="Total OT (Hours)", compute="_compute_total_ot", store=True)
    absent = fields.Boolean(string="Absent", compute="_compute_absent", store=True)
    staff = fields.Boolean(string="Staff", compute="_compute_staff", store=True)
    on_leave = fields.Boolean(string="On Leave", compute="_compute_on_leave", store=True)

    @api.depends('employee_id')
    def _compute_company(self):
        for rec in self:
            rec.company_id = rec.employee_id.x_studio_company.id if rec.employee_id and getattr(rec.employee_id, 'x_studio_company', False) else False

    @api.depends('first_punch', 'last_punch')
    def _compute_total_time(self):
        for rec in self:
            if rec.first_punch and rec.last_punch:
                delta = rec.last_punch - rec.first_punch
                hours = delta.total_seconds() / 3600.0
                rec.total_time = hours if hours <= 8 else 8.0
            else:
                rec.total_time = 0.0

    @api.depends('first_punch', 'last_punch')
    def _compute_total_ot(self):
        for rec in self:
            if rec.first_punch and rec.last_punch:
                delta = rec.last_punch - rec.first_punch
                hours = delta.total_seconds() / 3600.0
                rec.total_ot = hours - 8.0 if hours > 8.0 else 0.0
            else:
                rec.total_ot = 0.0

    @api.depends('first_punch')
    def _compute_absent(self):
        for rec in self:
            if rec.external_id.date and rec.external_id.date.weekday() == 4:
                rec.absent = False
            else:
                rec.absent = not rec.first_punch

    @api.depends('employee_id')
    def _compute_staff(self):
        for rec in self:
            rec.staff = rec.employee_id.x_studio_engineeroffice_staff if rec.employee_id else False

    @api.depends('employee_id')
    def _compute_on_leave(self):
        for rec in self:
            rec.on_leave = rec.employee_id.x_studio_on_leave if rec.employee_id else False
