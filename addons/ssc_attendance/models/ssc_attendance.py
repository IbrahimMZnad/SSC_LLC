# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta, datetime
import requests
import re
from collections import defaultdict
import pytz

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
            # بالعربي (عامي): بحسب اسم اليوم من التاريخ
            # EN: compute day name from date
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
    # Override create to populate lines if not provided
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
    # دالة fetch من BioCloud مع handling مضبوط للـ timezone
    # -------------------------
    def fetch_bioclock_data(self):
        """
        الخوارزمية العامة (ملخّص):
        1) نجيب كل transactions من API.
        2) نتجاهل سجلات Interruption أو الناقصة.
        3) نحوّل كل VerifyTime لِـ timezone-aware datetime (نفترض UTC لو ما في tz).
        4) نجمّع البصمات حسب (badge_clean, local_date) — local_date بحساب tz المستخدم.
        5) نحسب first/last ونختار الجهاز ذو أكبر span، ثم نحدّث أو نضيف سطر attendance.line.
        6) نرجع ملخّص.
        """
        url = "https://57.biocloud.me:8199/api_gettransctions"
        token = "fa83e149dabc49d28c477ea557016d03"
        headers = {"token": token, "Content-Type": "application/json"}
        # الفترة: آخر 24 ساعة — هذا منطقك الأصلي
        end_date = datetime.now(pytz.utc)
        start_date = end_date - timedelta(days=1)
        payload = {
            "StartDate": start_date.strftime("%Y-%m-%d 00:00:00"),
            "EndDate": end_date.strftime("%Y-%m-%d 23:59:59")
        }

        synced_count = 0
        total_records = 0
        matched_attendance = 0
        matched_employee = 0
        errors = []

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                raise Exception(f"Error fetching data: {response.status_code} - {response.text}")
            data = response.json()
            if "result" in data and data["result"] not in ("Success", "OK"):
                raise Exception(data.get("message", "Unexpected response from BioCloud"))
            transactions = data.get("message") or data.get("data") or []
            if transactions is None:
                transactions = []

            # 2) نجمع البصمات حسب badge_clean + verify_date (local date)
            groups = defaultdict(list)  # key = (badge_clean, date), value = list of (dt_utc, device, raw_trx)
            Employee = self.env['x_employeeslist']

            # حدد tz المستخدم (fallback لـ UTC) — حتى نحسب التاريخ المحلي بطريقة صحيحة
            user_tz = self.env.context.get('tz') or (self.env.user.tz if self.env.user else None) or 'UTC'
            try:
                tz_obj = pytz.timezone(user_tz)
            except Exception:
                tz_obj = pytz.utc

            for trx in transactions:
                total_records += 1
                # استبعاد أنواع غير ضرورية أو ناقصة
                verify_type = (trx.get("VerifyType") or '').strip()
                if verify_type and verify_type.lower() == 'interruption':
                    # تخطّي سجلات الانقطاع
                    continue
                verify_time_str = trx.get("VerifyTime") or trx.get("VerifyDate")
                badge_number = trx.get("BadgeNumber")
                device_serial = trx.get("DeviceSerialNumber") or trx.get("DeviceSerial")
                if not (verify_time_str and badge_number):
                    errors.append(f"Missing VerifyTime or BadgeNumber: {trx}")
                    continue

                verify_dt = None
                # حاول parse بعدة طرق
                try:
                    # محاولة fromisoformat أولاً (قد يرجع naive أو مع tz)
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

                # --- IMPORTANT: Normalize timezone handling ---
                # If incoming verify_dt has no tzinfo, assume it's UTC (most BioCloud APIs return UTC timestamps).
                # Make it timezone-aware in UTC, then convert to user's timezone to get the local date for grouping.
                if verify_dt.tzinfo is None:
                    verify_dt = pytz.utc.localize(verify_dt)
                else:
                    # ensure it's normalized to UTC-aware
                    try:
                        verify_dt = verify_dt.astimezone(pytz.utc)
                    except Exception:
                        verify_dt = pytz.utc.localize(verify_dt.replace(tzinfo=None))

                # compute local datetime in user's tz for grouping by date
                try:
                    local_dt = verify_dt.astimezone(tz_obj)
                except Exception:
                    local_dt = verify_dt.astimezone(pytz.utc)

                verify_date = local_dt.date()
                badge_clean = self._normalize_badge(badge_number)
                if not badge_clean:
                    errors.append(f"Empty badge after normalize: {badge_number}")
                    continue

                # append the UTC-aware datetime (verify_dt) and device
                groups[(badge_clean, verify_date)].append((verify_dt, device_serial or '', trx))

            # caches لتقليل الاستعلامات
            attendance_cache = {}
            employee_cache = {}

            # 4) نُعالج كل مجموعة
            for (badge_clean, v_date), events in groups.items():
                try:
                    # ترتيب التايمستامب
                    events_sorted = sorted(events, key=lambda x: x[0])
                    first_dt_utc = events_sorted[0][0]   # aware UTC
                    last_dt_utc = events_sorted[-1][0]   # aware UTC

                    # اختيار الجهاز الذي يعطي أكبر مدة span لنفس الموظف في ذلك اليوم
                    device_events = defaultdict(list)
                    for dt, device, _ in events_sorted:
                        device_key = device or ''
                        device_events[device_key].append(dt)

                    device_spans = {}
                    for dev, dts in device_events.items():
                        if not dts:
                            device_spans[dev] = timedelta(0)
                        else:
                            device_spans[dev] = max(dts) - min(dts)

                    chosen_device = ''
                    if device_spans:
                        # ترتيب بحسب span ثم بحسب آخر ظهور للتعادل
                        chosen_device = max(
                            device_spans.items(),
                            key=lambda x: (x[1], max(device_events[x[0]]) if device_events[x[0]] else datetime.min)
                        )[0]
                    else:
                        chosen_device = ''

                    # الآن نبحث عن employee عبر badge_clean (cache)
                    employee = employee_cache.get(badge_clean)
                    if not employee:
                        emp_found = None
                        # البحث بمطابقة الحقل x_studio_attendance_id بعد normalize
                        for emp in Employee.search([('x_studio_attendance_id', '!=', False)]):
                            emp_badge = self._normalize_badge(emp.x_studio_attendance_id or '')
                            if emp_badge == badge_clean:
                                emp_found = emp
                                break
                        if emp_found:
                            employee_cache[badge_clean] = emp_found
                            employee = emp_found

                    if not employee:
                        errors.append(f"No employee match for badge {badge_clean} on {v_date}")
                        continue
                    matched_employee += 1

                    # الحصول على attendance للسنة/الشهر/اليوم هذا (cache)
                    attendance = attendance_cache.get(v_date)
                    if not attendance:
                        attendance = self.search([('date', '=', v_date)], limit=1)
                        if not attendance:
                            attendance = self.create({
                                'name': str(v_date),
                                'date': v_date,
                                'type': 'Off Day' if v_date.weekday() == 4 else 'Regular Day'
                            })
                        attendance_cache[v_date] = attendance
                        matched_attendance += 1

                    # نجهز قيم السطر النهائي
                    # IMPORTANT: fields.Datetime expects string in UTC (to store correctly).
                    # نستخدم fields.Datetime.to_string لتأمين الشكل المناسب
                    first_punch_str = fields.Datetime.to_string(first_dt_utc)
                    last_punch_str = fields.Datetime.to_string(last_dt_utc)

                    line_vals = {
                        'employee_id': employee.id,
                        'attendance_id': employee.x_studio_attendance_id or '',
                        'company_id': employee.x_studio_company.id if getattr(employee, 'x_studio_company', False) else False,
                        'staff': employee.x_studio_engineeroffice_staff,
                        'on_leave': employee.x_studio_on_leave,
                        'first_punch': first_punch_str,
                        'last_punch': last_punch_str,
                        'punch_machine_id': chosen_device or '',
                        'error_note': None
                    }

                    existing_line = attendance.line_ids.filtered(lambda l: l.employee_id and l.employee_id.id == employee.id)
                    if existing_line:
                        # حدث القيم الأساسية بس بدون تغيير الباقي
                        existing_line.write({
                            'first_punch': min(existing_line.first_punch or first_punch_str, first_punch_str),
                            'last_punch': max(existing_line.last_punch or last_punch_str, last_punch_str),
                            'punch_machine_id': chosen_device or (existing_line.punch_machine_id or ''),
                            'error_note': None
                        })
                    else:
                        attendance.write({'line_ids': [(0, 0, line_vals)]})
                    synced_count += 1

                except Exception as sub_e:
                    errors.append(f"Error processing group {badge_clean} {v_date}: {sub_e}")
                    continue

            # ملخّص
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
    # Project field made computed according to punch_machine_id as requested
    project_id = fields.Many2one('x_projects_list', string="Project", compute="_compute_project", store=True)
    punch_machine_id = fields.Char(string="Punch Machine ID")
    first_punch = fields.Datetime(string="First Punch")
    last_punch = fields.Datetime(string="Last Punch")
    total_time = fields.Float(string="Total Time (Hours)", compute="_compute_total_time", store=True)
    total_ot = fields.Float(string="Total OT (Hours)", compute="_compute_total_ot", store=True)
    absent = fields.Boolean(string="Absent", compute="_compute_absent", store=True)
    staff = fields.Boolean(string="Staff", compute="_compute_staff", store=True)
    on_leave = fields.Boolean(string="On Leave", compute="_compute_on_leave", store=True)
    error_note = fields.Text(string="Error Note")

    # -------------------------
    # حساب الـ project بناء على punch_machine_id
    # -------------------------
    @api.depends('punch_machine_id')
    def _compute_project(self):
        """
        خريطة الأجهزة للمشاريع:
        - VDE2252100257 أو VDE2252100409 => "47 G+1 Villa Arjan (Townhouses) - 6727777"
        - VDE2252100345 أو VDE2252100359 => "Al Khan G + 15 - 211"
        بنبحث داخل model x_projects_list على السجل اللي x_name == الاسم ثم نربطه.
        """
        mapping = {
            'VDE2252100257': '47 G+1 Villa Arjan (Townhouses) - 6727777',
            'VDE2252100409': '47 G+1 Villa Arjan (Townhouses) - 6727777',
            'VDE2252100345': 'Al Khan G + 15 - 211',
            'VDE2252100359': 'Al Khan G + 15 - 211',
        }
        Project = self.env['x_projects_list']
        for rec in self:
            if rec.punch_machine_id:
                target_name = mapping.get(rec.punch_machine_id)
                if target_name:
                    proj = Project.search([('x_name', '=', target_name)], limit=1)
                    rec.project_id = proj.id if proj else False
                    if not proj:
                        # لو ما لقى المشروع نحط ملاحظة خطأ صغيرة (ما توقف التنفيذ)
                        rec.error_note = (rec.error_note or '') + f"\nProject not found for name: {target_name}"
                else:
                    rec.project_id = False
            else:
                rec.project_id = False

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
            # بالعربي: لو الموظف على اجازة => absent False
            # أو لو اليوم جمعة => False
            if rec.on_leave:
                rec.absent = False
            elif rec.external_id and rec.external_id.date and rec.external_id.date.weekday() == 4:
                rec.absent = False
            else:
                rec.absent = not bool(rec.first_punch)

    @api.depends('employee_id')
    def _compute_staff(self):
        for rec in self:
            rec.staff = rec.employee_id.x_studio_engineeroffice_staff if rec.employee_id else False

    @api.depends('employee_id')
    def _compute_on_leave(self):
        for rec in self:
            rec.on_leave = rec.employee_id.x_studio_on_leave if rec.employee_id else False
