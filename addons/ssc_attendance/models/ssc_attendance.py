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

    name = fields.Char(string="Name", required=True, default=lambda self: str(date.today()))
    date = fields.Date(string="Date", default=fields.Date.context_today)
    type = fields.Selection(
        [('Regular Day', 'Regular Day'), ('Off Day', 'Off Day')],
        string="Type",
        default=lambda self: 'Off Day' if date.today().weekday() == 4 else 'Regular Day'
    )
    day_name = fields.Char(string="Day Name", compute="_compute_day_name", store=True)
    line_ids = fields.One2many('ssc.attendance.line', 'external_id', string="Attendance Lines")

    @api.depends('date')
    def _compute_day_name(self):
        for rec in self:
            rec.day_name = rec.date.strftime('%A') if rec.date else ''

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

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if not vals.get('line_ids'):
            record._populate_lines()
        return record

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

    def _normalize_badge(self, s):
        if not s:
            return ''
        return re.sub(r'[^A-Za-z0-9]', '', str(s)).upper()

    # ✅ Fixed Indentation Error Here
    def transfer_to_x_daily_attendance(self):
        for rec in self.line_ids:
            if not rec.employee_id or not rec.external_id.date:
                continue

            daily_attendance = self.env['x_daily_attendance'].search([
                ('x_studio_employee', '=', rec.employee_id.id),
                ('x_studio_date', '=', rec.external_id.date)
            ], limit=1)

            vals = {
                'x_studio_employee': rec.employee_id.id,
                'x_studio_date': rec.external_id.date,
                'x_studio_total_time': getattr(rec, 'total_time', False),
                'x_studio_total_ot': getattr(rec, 'total_ot', False),
                'x_studio_absent': getattr(rec, 'absent', False),
            }

            if daily_attendance:
                daily_attendance.write(vals)
            else:
                self.env['x_daily_attendance'].create(vals)

    def fetch_bioclock_data(self):
        """Fetch transactions from BioCloud only for today's date"""
        url = "https://57.biocloud.me:8199/api_gettransctions"
        token = "fa83e149dabc49d28c477ea557016d03"
        headers = {"token": token, "Content-Type": "application/json"}

        today = fields.Date.context_today(self)
        attendance_records = self.search([('date', '=', today)])

        synced_count = 0
        total_records = 0
        matched_attendance = 0
        matched_employee = 0
        errors = []

        Employee = self.env['x_employeeslist']
        badge_map = {self._normalize_badge(emp.x_studio_attendance_id or ''): emp
                     for emp in Employee.search([('x_studio_attendance_id', '!=', False)])}

        for attendance in attendance_records:
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

                    if verify_dt.tzinfo is None:
                        try:
                            verify_dt = SERVER_TZ.localize(verify_dt)
                        except Exception:
                            verify_dt = pytz.utc.localize(verify_dt)
                    else:
                        verify_dt = verify_dt.astimezone(pytz.utc)

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
                        first_dt_utc = events_sorted[0][0]
                        last_dt_utc = events_sorted[-1][0] if len(events_sorted) > 1 else first_dt_utc

                        device_events = defaultdict(list)
                        for dt, device, _ in events_sorted:
                            device_events[device or ''].append(dt)

                        device_spans = {dev: max(dts) - min(dts) if dts else timedelta(0)
                                        for dev, dts in device_events.items()}

                        chosen_device = max(device_spans.items(),
                                            key=lambda x: (x[1], max(device_events[x[0]]) if device_events[x[0]] else datetime.min))[0] \
                            if device_spans else ''

                        employee = employee_cache.get(badge_clean) or badge_map.get(badge_clean)
                        if employee:
                            employee_cache[badge_clean] = employee
                            matched_employee += 1
                        else:
                            errors.append(f"No employee match for badge {badge_clean} on {v_date}")
                            continue

                        attendance = attendance_cache.get(v_date) or self.search([('date', '=', v_date)], limit=1)
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
                            existing_line.write(line_vals)
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
                if rec.last_punch.hour >= 14:
                    hours -= 1.0
                rec.total_time = 8.0 if hours > 8.0 else hours
            else:
                rec.total_time = 0.0

    @api.depends('first_punch', 'last_punch')
    def _compute_total_ot(self):
        for rec in self:
            if rec.first_punch and rec.last_punch:
                delta = rec.last_punch - rec.first_punch
                hours = delta.total_seconds() / 3600.0
                if rec.last_punch.hour >= 14:
                    hours -= 1.0
                rec.total_ot = hours - 8.0 if hours > 8.0 else 0.0
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
            rec.staff = getattr(rec.employee_id, 'x_studio_engineeroffice_staff', False)

    @api.depends('employee_id')
    def _compute_on_leave(self):
        for rec in self:
            rec.on_leave = getattr(rec.employee_id, 'x_studio_on_leave', False)
