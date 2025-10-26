# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, timedelta, datetime
import requests
import re
from collections import defaultdict
import pytz
import logging

_logger = logging.getLogger(__name__)

SERVER_TZ = pytz.timezone('Asia/Dubai')


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
    # Normalize badge number
    # -------------------------
    def _normalize_badge(self, s):
        if not s:
            return ''
        return re.sub(r'[^A-Za-z0-9]', '', str(s)).upper()

    # -------------------------
    # Fetch BioCloud Data for all existing ssc.attendance records
    # -------------------------
    def fetch_bioclock_data(self):
        """
        Fetch transactions from BioCloud for all existing ssc.attendance records
        based on their attendance.date
        """
        url = "https://57.biocloud.me:8199/api_gettransctions"
        token = "fa83e149dabc49d28c477ea557016d03"
        headers = {"token": token, "Content-Type": "application/json"}

        synced_count = 0
        total_records = 0
        matched_attendance = 0
        matched_employee = 0
        errors = []

        Employee = self.env['x_employeeslist']
        # Build badge map once for performance
        badge_map = {}
        for emp in Employee.search([('x_studio_attendance_id', '!=', False)]):
            badge_map[self._normalize_badge(emp.x_studio_attendance_id or '')] = emp

        # Loop over all existing attendance records
        for attendance in self.search([]):
            start_dt_utc = datetime.combine(attendance.date, datetime.min.time()).replace(tzinfo=pytz.utc)
            end_dt_utc = datetime.combine(attendance.date, datetime.max.time()).replace(tzinfo=pytz.utc)
            payload = {
                "StartDate": start_dt_utc.strftime("%Y-%m-%d %H:%M:%S"),
                "EndDate": end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")
            }

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code != 200:
                    errors.append(f"Error fetching data for {attendance.date}: {response.status_code} - {response.text}")
                    continue
                data = response.json()
                if "result" in data and data["result"] not in ("Success", "OK"):
                    errors.append(f"Unexpected response for {attendance.date}: {data.get('message', '')}")
                    continue
                transactions = data.get("message") or data.get("data") or []
                if transactions is None:
                    transactions = []

                groups = defaultdict(list)

                for trx in transactions:
                    total_records += 1
                    verify_type = (trx.get("VerifyType") or '').strip()
                    if verify_type and verify_type.lower() == 'interruption':
                        continue
                    verify_time_str = trx.get("VerifyTime") or trx.get("VerifyDate")
                    badge_number = trx.get("BadgeNumber")
                    device_serial = trx.get("DeviceSerialNumber") or trx.get("DeviceSerial")
                    if not (verify_time_str and badge_number):
                        errors.append(f"Missing VerifyTime or BadgeNumber: {trx}")
                        continue

                    # parse verify_time_str into a datetime
                    verify_dt = None
                    try:
                        verify_dt = datetime.fromisoformat(verify_time_str)
                    except Exception:
                        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                            try:
                                verify_dt = datetime.strptime(verify_time_str, fmt)
                                break
                            except Exception:
                                continue
                    if not verify_dt:
                        errors.append(f"Unparseable VerifyTime: {verify_time_str}")
                        continue

                    # If naive, assume SERVER_TZ (Asia/Dubai); if tz-aware, respect it
                    if verify_dt.tzinfo is None:
                        try:
                            verify_dt = SERVER_TZ.localize(verify_dt)
                        except Exception:
                            verify_dt = pytz.utc.localize(verify_dt)
                    else:
                        try:
                            verify_dt = verify_dt.astimezone(pytz.utc).astimezone(verify_dt.tzinfo)
                        except Exception:
                            verify_dt = pytz.utc.localize(verify_dt.replace(tzinfo=None))

                    verify_dt_server = verify_dt.astimezone(SERVER_TZ)
                    verify_date = verify_dt_server.date()
                    verify_dt_utc = verify_dt.astimezone(pytz.utc)
                    badge_clean = self._normalize_badge(badge_number)
                    if not badge_clean:
                        errors.append(f"Empty badge after normalize: {badge_number}")
                        continue
                    groups[(badge_clean, verify_date)].append((verify_dt_utc, device_serial or '', trx))

                attendance_cache = {attendance.date: attendance}
                employee_cache = {}

                for (badge_clean, v_date), events in groups.items():
                    try:
                        events_sorted = sorted(events, key=lambda x: x[0])
                        if len(events_sorted) == 1:
                            first_dt_utc = last_dt_utc = events_sorted[0][0]
                        else:
                            first_dt_utc = events_sorted[0][0]
                            last_dt_utc = events_sorted[-1][0]

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
                            chosen_device = max(
                                device_spans.items(),
                                key=lambda x: (x[1], max(device_events[x[0]]) if device_events[x[0]] else datetime.min)
                            )[0]
                        else:
                            chosen_device = ''

                        employee = employee_cache.get(badge_clean)
                        if not employee:
                            emp_found = badge_map.get(badge_clean)
                            if emp_found:
                                employee_cache[badge_clean] = emp_found
                                employee = emp_found

                        if not employee:
                            errors.append(f"No employee match for badge {badge_clean} on {v_date}")
                            continue
                        matched_employee += 1

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
                            try:
                                existing_first_dt = fields.Datetime.from_string(existing_line.first_punch) if existing_line.first_punch else None
                            except Exception:
                                existing_first_dt = None
                            try:
                                existing_last_dt = fields.Datetime.from_string(existing_line.last_punch) if existing_line.last_punch else None
                            except Exception:
                                existing_last_dt = None

                            chosen_first_dt = min([d for d in (existing_first_dt, first_dt_utc) if d is not None])
                            chosen_last_dt = max([d for d in (existing_last_dt, last_dt_utc) if d is not None])

                            existing_line.write({
                                'first_punch': fields.Datetime.to_string(chosen_first_dt) if chosen_first_dt else False,
                                'last_punch': fields.Datetime.to_string(chosen_last_dt) if chosen_last_dt else False,
                                'punch_machine_id': chosen_device or (existing_line.punch_machine_id or ''),
                                'error_note': None
                            })
                        else:
                            attendance.write({'line_ids': [(0, 0, line_vals)]})
                        synced_count += 1
                    except Exception as sub_e:
                        errors.append(f"Error processing group {badge_clean} {v_date}: {sub_e}")
                        _logger.exception("Error processing group %s %s: %s", badge_clean, v_date, sub_e)
                        continue

            except Exception as e:
                errors.append(f"Error fetching BioCloud data for {attendance.date}: {e}")
                _logger.exception("Error fetching BioCloud data for %s: %s", attendance.date, e)
                continue

        _logger.info('BioCloud Sync: %s records synced. Total received: %s Matched attendance days: %s Matched employees: %s Errors: %s',
                     synced_count, total_records, matched_attendance, matched_employee, len(errors))

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

    # -------------------------
    # Transfer to x_daily_attendance
    # -------------------------
    def transfer_to_x_daily_attendance(self):
        """
        Transfer lines from ssc.attendance -> x_daily_attendance according to:
        - find x_daily_attendance where x_studio_todays_date == attendance.date
        - and company match: company_id in line == x_studio_company in x_daily_attendance
        - if type == 'Regular Day' -> transfer to x_studio_attendance_sheet
            * match/compare x_studio_id with attendance_id
            * set x_studio_absent, x_studio_project, x_studio_overtime_hrs = total_ot
        - if type == 'Off Day' -> transfer to x_studio_off_days_attendance_sheet
            * match x_studio_id with attendance_id
            * set x_studio_project, x_studio_overtime_hrs = total_time + total_ot
        """
        Daily = self.env['x_daily_attendance']
        for attendance in self:
            for line in attendance.line_ids:
                if not line.company_id:
                    continue
                parent = Daily.search([
                    ('x_studio_todays_date', '=', attendance.date),
                    ('x_studio_company', '=', line.company_id.id)
                ], limit=1)
                if not parent:
                    continue

                if attendance.type == 'Regular Day':
                    existing_sheet = parent.x_studio_attendance_sheet.filtered(lambda l: l.x_studio_id == (line.attendance_id or ''))
                    vals = {
                        'x_studio_id': line.attendance_id or '',
                        'x_studio_absent': bool(line.absent),
                        'x_studio_project': line.project_id.id if line.project_id else False,
                        'x_studio_overtime_hrs': line.total_ot if line.total_ot else 0.0,
                    }
                    if existing_sheet:
                        existing_sheet.write(vals)
                    else:
                        parent.write({'x_studio_attendance_sheet': [(0, 0, vals)]})

                elif attendance.type == 'Off Day':
                    existing_sheet = parent.x_studio_off_days_attendance_sheet.filtered(lambda l: l.x_studio_id == (line.attendance_id or ''))
                    vals = {
                        'x_studio_id': line.attendance_id or '',
                        'x_studio_project': line.project_id.id if line.project_id else False,
                        'x_studio_overtime_hrs': (line.total_time + line.total_ot) if (line.total_time or line.total_ot) else 0.0,
                    }
                    if existing_sheet:
                        existing_sheet.write(vals)
                    else:
                        parent.write({'x_studio_off_days_attendance_sheet': [(0, 0, vals)]})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Transfer Finished',
                'message': 'Transfer to x_daily_attendance completed.',
                'type': 'success',
                'sticky': False,
            }
        }


class SSCAttendanceLine(models.Model):
    _name = "ssc.attendance.line"
    _description = "Attendance Line"

    external_id = fields.Many2one('ssc.attendance', string="Attendance Reference", ondelete='cascade')
    employee_id = fields.Many2one('x_employeeslist', string="Employee", required=False)
    company_id = fields.Many2one('res.company', string="Company", compute="_compute_company", store=True)
    attendance_id = fields.Char(string="Attendance ID")
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

    @api.depends('punch_machine_id')
    def _compute_project(self):
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
                if hours > 1.0:
                    hours = hours - 1.0
                rec.total_time = hours if hours <= 8 else 8.0
            else:
                rec.total_time = 0.0

    @api.depends('total_time')
    def _compute_total_ot(self):
        for rec in self:
            if rec.total_time:
                rec.total_ot = rec.total_time - 8.0 if rec.total_time > 8.0 else 0.0
            else:
                rec.total_ot = 0.0

    @api.depends('first_punch', 'employee_id')
    def _compute_absent(self):
        for rec in self:
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
