from odoo import models, fields, api
from datetime import date, timedelta, datetime
import requests
import re

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
    # مساعدة: تنظيف badge (إزالة أي رموز غير أرقام/حروف) / Normalize badge
    # -------------------------
    def _normalize_badge(self, s):
        if not s:
            return ''
        # keep only alphanumeric characters, uppercase
        return re.sub(r'[^A-Za-z0-9]', '', str(s)).upper()

    # -------------------------
    # جلب بيانات BioCloud / Fetch attendance data from BioCloud API
    # -------------------------
    def fetch_bioclock_data(self):
        url = "https://57.biocloud.me:8199/api_gettransctions"
        token = "fa83e149dabc49d28c477ea557016d03"
        headers = {"token": token, "Content-Type": "application/json"}

        # الفترة التي نطلبها من الـ API (آخر 24 ساعة) — منطقك نفسه
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        payload = {
            "StartDate": start_date.strftime("%Y-%m-%d 00:00:00"),
            "EndDate": end_date.strftime("%Y-%m-%d 23:59:59")
        }

        # عدادات وـ logs للمساعدة في التتبع
        synced_count = 0
        total_records = 0
        matched_attendance = 0
        matched_employee = 0
        errors = []

        try:
            # استدعاء API
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

            data = response.json()

            # بعض نسخ الـ API ترجع data تحت "message" وبعضها تحت "data"
            if "result" in data and data["result"] not in ("Success", "OK"):
                raise Exception(data.get("message", "Unexpected response from BioCloud"))

            transactions = data.get("message") or data.get("data") or []
            if transactions is None:
                transactions = []

            Employee = self.env['x_employeeslist']

            # نمر على كل عملية
            for trx in transactions:
                total_records += 1
                line_obj = None  # سنتيحها للتسجيل في حالة حدوث استثناء لاحق

                try:
                    # استخراج الحقول الأساسية
                    verify_time_str = trx.get("VerifyTime") or trx.get("VerifyDate")
                    badge_number = trx.get("BadgeNumber")
                    device_serial = trx.get("DeviceSerialNumber") or trx.get("DeviceSerial")

                    if not (verify_time_str and badge_number):
                        errors.append(f"Missing VerifyTime or BadgeNumber: {trx}")
                        continue

                    # محاولة تحويل VerifyTime إلى datetime بأكثر من صيغة محتملة
                    verify_dt = None
                    try:
                        # عادة يأتي بصيغة ISO: 2025-10-20T05:52:52
                        verify_dt = datetime.fromisoformat(verify_time_str)
                    except Exception:
                        # fallback إلى صيغ شائعة
                        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                            try:
                                verify_dt = datetime.strptime(verify_time_str, fmt)
                                break
                            except Exception:
                                continue
                    if not verify_dt:
                        errors.append(f"Unparseable VerifyTime: {verify_time_str}")
                        continue

                    verify_date = verify_dt.date()

                    # البحث عن سجل attendance لذلك اليوم أو إنشاؤه (منطقك لم يتغير)
                    attendance = self.search([('date', '=', verify_date)], limit=1)
                    if not attendance:
                        attendance = self.create({
                            'name': str(verify_date),
                            'date': verify_date,
                            'type': 'Off Day' if verify_date.weekday() == 4 else 'Regular Day'
                        })
                    matched_attendance += 1

                    # تطبيع الـ badge (إزالة الشرطات، المسافات، تحويل لأحرف كبيرة)
                    badge_clean = self._normalize_badge(badge_number)
                    employee = None

                    # البحث عن الموظف بحيث نقارن القيم بعد التطبيع
                    for emp in Employee.search([('x_studio_attendance_id', '!=', False)]):
                        emp_badge_raw = emp.x_studio_attendance_id or ''
                        emp_badge = self._normalize_badge(emp_badge_raw)
                        if emp_badge and emp_badge == badge_clean:
                            employee = emp
                            break

                    if not employee:
                        # لا يوجد موظف مطابق — نسجل الخطأ وننتقل
                        errors.append(f"No employee match for badge {badge_number}")
                        continue
                    matched_employee += 1

                    # الآن نجهز قيم السطر
                    line_vals = {
                        'employee_id': employee.id,
                        'attendance_id': employee.x_studio_attendance_id or '',
                        'company_id': employee.x_studio_company.id if getattr(employee, 'x_studio_company', False) else False,
                        'staff': employee.x_studio_engineeroffice_staff,
                        'on_leave': employee.x_studio_on_leave,
                        'first_punch': verify_dt,
                        'last_punch': verify_dt,
                        'punch_machine_id': device_serial or '',
                        'error_note': None
                    }

                    # إن وجد سطر لنفس الموظف في نفس الـ attendance نحدّثه، وإلا نضيفه عبر write على line_ids
                    existing_line = attendance.line_ids.filtered(lambda l: l.employee_id and l.employee_id.id == employee.id)
                    if existing_line:
                        existing_line.write(line_vals)
                        line_obj = existing_line
                    else:
                        # كتابة في attendance.line_ids لضمان ظهور الـ One2many في الواجهة
                        attendance.write({'line_ids': [(0, 0, line_vals)]})
                        # الحصول على السطر الذي أُنشئ حديثًا (نبحث عنه الآن)
                        new_line = attendance.line_ids.filtered(lambda l: l.employee_id and l.employee_id.id == employee.id)
                        if new_line:
                            line_obj = new_line[0]

                    synced_count += 1

                except Exception as sub_e:
                    # تسجيل الخطأ وتخزينه في سطر (إذا كان موجودًا)
                    err_msg = f"Error processing Badge {trx.get('BadgeNumber')}: {sub_e}"
                    errors.append(err_msg)
                    try:
                        if line_obj:
                            line_obj.error_note = err_msg
                    except Exception:
                        # لا نفشل العملية الرئيسية بسبب خطأ في تسجيل الملاحظة
                        pass
                    continue

            # نهاية معالجة كل السجلات — نعرض ملخص
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'BioCloud Sync',
                    'message': f'{synced_count} records synced. Total received: {total_records} '
                               f'Matched attendance days: {matched_attendance} Matched employees: {matched_employee} '
                               f'Errors: {len(errors)}',
                    'type': 'success' if synced_count > 0 else 'warning',
                    'sticky': False,
                }
            }

        except Exception as e:
            # في حال فشل شامل نعرض رسالة مفصلة
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sync Error',
                    'message': f"Error: {str(e)}",
                    'type': 'danger',
                    'sticky': True,
                }
            }


class SSCAttendanceLine(models.Model):
    _name = "ssc.attendance.line"
    _description = "Attendance Line"

    external_id = fields.Many2one('ssc.attendance', string="Attendance Reference", ondelete='cascade')
    employee_id = fields.Many2one('x_employeeslist', string="Employee", required=False)
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
    error_note = fields.Text(string="Error Note")

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

    @api.depends('first_punch', 'employee_id')
    def _compute_absent(self):
        for rec in self:
            # إذا الموظف على إجازة => absent = False
            if rec.on_leave:
                rec.absent = False
            # الجمعة considered off day
            elif rec.external_id and rec.external_id.date and rec.external_id.date.weekday() == 4:
                rec.absent = False
            else:
                # الغياب يحسب فقط بناءً على وجود أول بصمة
                rec.absent = not bool(rec.first_punch)

    @api.depends('employee_id')
    def _compute_staff(self):
        for rec in self:
            rec.staff = rec.employee_id.x_studio_engineeroffice_staff if rec.employee_id else False

    @api.depends('employee_id')
    def _compute_on_leave(self):
        for rec in self:
            rec.on_leave = rec.employee_id.x_studio_on_leave if rec.employee_id else False
