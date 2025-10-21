# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta, datetime
import requests
import re
from collections import defaultdict

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
    # شرح مفصّل داخل الكومنتس بالعربي عشان تكون القراءة واضحة
    # -------------------------
    def fetch_bioclock_data(self):
        """
        الخوارزمية العامة:
        1) نجيب كل transactions من API (تحت 'message' أو 'data').
        2) نتجاهل سجلات انقطاع الجهاز (VerifyType == 'Interruption') أو السجلات الناقصة.
        3) نجمع البصمات في dict حسب (badge_clean, verify_date) => list of (dt, device)
        4) بعد جمع كل البصمات نمرّ على كل مجموعة:
           - نحسب first_punch = min(dt) و last_punch = max(dt)
           - نختار punch_machine_id بناءً على الجهاز الذي لديه أكبر span (max(timestamp) - min(timestamp)) ضمن ذلك الـ badge/day
           - نجد attendance record لذلك التاريخ (أو ننشئه) ونحدّث أو ننشئ سطر الـ attendance.line عبر attendance.write({'line_ids': [...]})
        5) نرجع تقرير مبسّط بعد الانتهاء.
        """

        url = "https://57.biocloud.me:8199/api_gettransctions"
        token = "fa83e149dabc49d28c477ea557016d03"
        headers = {"token": token, "Content-Type": "application/json"}

        # الفترة: آخر 24 ساعة — هذا منطقك الأصلي
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

        payload = {
            "StartDate": start_date.strftime("%Y-%m-%d 00:00:00"),
            "EndDate": end_date.strftime("%Y-%m-%d 23:59:59")
        }

        # عدادات وتقارير
        synced_count = 0
        total_records = 0
        matched_attendance = 0
        matched_employee = 0
        errors = []

        try:
            # 1) استدعاء API
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

            data = response.json()

            # API ممكن ترجع النتائج تحت 'message' أو 'data'
            if "result" in data and data["result"] not in ("Success", "OK"):
                # لو النتيجة غير ناجحة نرفع استثناء
                raise Exception(data.get("message", "Unexpected response from BioCloud"))

            transactions = data.get("message") or data.get("data") or []
            if transactions is None:
                transactions = []

            # 2) نجمع البصمات حسب badge_clean + verify_date
            groups = defaultdict(list)  # key = (badge_clean, date), value = list of (dt, device, raw_trx)
            Employee = self.env['x_employeeslist']

            for trx in transactions:
                total_records += 1
                # استبعاد أنواع غير ضرورية أو ناقصة
                verify_type = (trx.get("VerifyType") or '').strip()
                if verify_type and verify_type.lower() == 'interruption':
                    # تخطّي سجلات الـ Interruption لأنها ليست بصمات موظف
                    continue

                verify_time_str = trx.get("VerifyTime") or trx.get("VerifyDate")
                badge_number = trx.get("BadgeNumber")
                device_serial = trx.get("DeviceSerialNumber") or trx.get("DeviceSerial")

                if not (verify_time_str and badge_number):
                    errors.append(f"Missing VerifyTime or BadgeNumber: {trx}")
                    continue

                # تحويل VerifyTime إلى datetime عبر محاولات لعدة صيغ
                verify_dt = None
                # غالباً يأتي بتنسيق ISO مثل 2025-10-20T05:52:52
                # نحاول fromisoformat أولاً ثم نجرّب فورماتات شائعة كـ fallback
                try:
                    # Python fromisoformat يتعامل مع 'YYYY-MM-DDTHH:MM:SS'
                    verify_dt = datetime.fromisoformat(verify_time_str)
                except Exception:
                    # fallback formats
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
                badge_clean = self._normalize_badge(badge_number)
                if not badge_clean:
                    errors.append(f"Empty badge after normalize: {badge_number}")
                    continue

                # اجمع البصمات في المجموعة المناسبة
                groups[(badge_clean, verify_date)].append((verify_dt, device_serial or '', trx))

            # 3) نجهز caches لتقليل الاستعلامات DB
            attendance_cache = {}
            employee_cache = {}

            # 4) نُعالج كل مجموعة (كل موظف لكل يوم مرة واحدة)
            for (badge_clean, v_date), events in groups.items():
                # events: list of (dt, device, trx)
                try:
                    # ترتيب التايمستامب
                    events_sorted = sorted(events, key=lambda x: x[0])
                    first_dt = events_sorted[0][0]
                    last_dt = events_sorted[-1][0]

                    # اختيار الجهاز الذي يعطي أكبر مدة span لنفس الموظف في ذلك اليوم
                    # نحسب span لكل جهاز: max(dt) - min(dt) داخل هذا اليوم لذلك الجهاز
                    device_events = defaultdict(list)
                    for dt, device, _ in events_sorted:
                        device_key = device or ''
                        device_events[device_key].append(dt)

                    # حساب span لكل جهاز
                    device_spans = {}
                    for dev, dts in device_events.items():
                        if not dts:
                            device_spans[dev] = timedelta(0)
                        else:
                            device_spans[dev] = max(dts) - min(dts)

                    # نختار الجهاز ذو أعلى span. لو كلهم صفر نأخذ الجهاز الأخير الموجود.
                    chosen_device = ''
                    if device_spans:
                        # ترتيب بحسب span ثم بحسب آخر ظهور للتعادل
                        chosen_device = max(device_spans.items(), key=lambda x: (x[1], max(device_events[x[0]]) if device_events[x[0]] else datetime.min))[0]
                    else:
                        chosen_device = ''

                    # الآن نبحث عن employee عبر badge_clean
                    employee = employee_cache.get(badge_clean)
                    if not employee:
                        # استعلام واحد شامل قد يكون مكلفاً لو فيه آلاف، لكن نستخدم search محدد
                        # نبحث بين الموظفين الذين لديهم قيمة attendance id
                        emp_found = None
                        for emp in Employee.search([('x_studio_attendance_id', '!=', False)]):
                            emp_badge = self._normalize_badge(emp.x_studio_attendance_id or '')
                            if emp_badge == badge_clean:
                                emp_found = emp
                                break
                        if emp_found:
                            employee_cache[badge_clean] = emp_found
                            employee = emp_found

                    if not employee:
                        # لا يوجد موظف مطابق — نضيف لملاحظات ونكمل
                        errors.append(f"No employee match for badge {badge_clean} on {v_date}")
                        continue
                    matched_employee += 1

                    # الحصول على attendance للسنة/الشهر/اليوم هذا (cache)
                    attendance = attendance_cache.get(v_date)
                    if not attendance:
                        attendance = self.search([('date', '=', v_date)], limit=1)
                        if not attendance:
                            # لو مش موجود ننشئ record جديد (منطقك موجود أصلاً)
                            attendance = self.create({
                                'name': str(v_date),
                                'date': v_date,
                                'type': 'Off Day' if v_date.weekday() == 4 else 'Regular Day'
                            })
                        attendance_cache[v_date] = attendance
                    matched_attendance += 1

                    # الآن نجهز قيم السطر النهائي
                    line_vals = {
                        'employee_id': employee.id,
                        'attendance_id': employee.x_studio_attendance_id or '',
                        'company_id': employee.x_studio_company.id if getattr(employee, 'x_studio_company', False) else False,
                        'staff': employee.x_studio_engineeroffice_staff,
                        'on_leave': employee.x_studio_on_leave,
                        'first_punch': first_dt,
                        'last_punch': last_dt,
                        'punch_machine_id': chosen_device or '',
                        'error_note': None
                    }

                    # نتحقق لو في سطر موجود ونحدّثه أو نضيف جديد عبر write على line_ids
                    existing_line = attendance.line_ids.filtered(lambda l: l.employee_id and l.employee_id.id == employee.id)
                    if existing_line:
                        # نكتب فقط الحقول الضرورية لتحديث البصمات والأجهزة
                        existing_line.write({
                            'first_punch': min(existing_line.first_punch or first_dt, first_dt),
                            'last_punch': max(existing_line.last_punch or last_dt, last_dt),
                            'punch_machine_id': chosen_device or (existing_line.punch_machine_id or ''),
                            'error_note': None
                        })
                    else:
                        attendance.write({'line_ids': [(0, 0, line_vals)]})

                    synced_count += 1

                except Exception as sub_e:
                    errors.append(f"Error processing group {badge_clean} {v_date}: {sub_e}")
                    continue

            # 5) بعد الانتهاء نعرض ملخص
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
