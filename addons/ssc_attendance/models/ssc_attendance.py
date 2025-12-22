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
            if not self.search([('date', '=', current_date)], limit=1):
                self.create({
                    'name': str(current_date),
                    'date': current_date,
                    'type': 'Off Day' if current_date.weekday() == 4 else 'Regular Day'
                })
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
        lines = []
        for emp in Employee.search([]):
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
        return re.sub(r'[^A-Za-z0-9]', '', str(s)).upper() if s else ''

    def fetch_bioclock_data(self):
        url = "https://57.biocloud.me:8199/api_gettransctions"
        token = "fa83e149dabc49d28c477ea557016d03"
        headers = {"token": token, "Content-Type": "application/json"}

        synced_count = total_records = matched_attendance = matched_employee = 0
        errors = []

        Employee = self.env['x_employeeslist']
        badge_map = {
            self._normalize_badge(emp.x_studio_attendance_id): emp
            for emp in Employee.search([('x_studio_attendance_id', '!=', False)])
        }

        for attendance in self.search([]):

            # ✅ cache السطور الموجودة (بدون حذف)
            existing_lines = {
                line.employee_id.id: line
                for line in attendance.line_ids
                if line.employee_id
            }

            start_dt = datetime.combine(attendance.date, datetime.min.time()).replace(tzinfo=pytz.utc)
            end_dt = datetime.combine(attendance.date, datetime.max.time()).replace(tzinfo=pytz.utc)

            try:
                response = requests.post(url, headers=headers, json={
                    "StartDate": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "EndDate": end_dt.strftime("%Y-%m-%d %H:%M:%S")
                }, timeout=30)

                if response.status_code != 200:
                    continue

                transactions = response.json().get("message") or response.json().get("data") or []
                groups = defaultdict(list)

                for trx in transactions:
                    total_records += 1
                    if (trx.get("VerifyType") or '').lower() == 'interruption':
                        continue

                    verify_time = trx.get("VerifyTime") or trx.get("VerifyDate")
                    badge = self._normalize_badge(trx.get("BadgeNumber"))
                    device = trx.get("DeviceSerialNumber") or trx.get("DeviceSerial")

                    if not verify_time or not badge:
                        continue

                    try:
                        verify_dt = datetime.fromisoformat(verify_time)
                    except Exception:
                        continue

                    if verify_dt.tzinfo is None:
                        verify_dt = SERVER_TZ.localize(verify_dt)

                    verify_dt_utc = verify_dt.astimezone(pytz.utc)
                    verify_date = verify_dt.astimezone(SERVER_TZ).date()
                    groups[(badge, verify_date)].append((verify_dt_utc, device or ''))

                for (badge, v_date), events in groups.items():
                    events.sort(key=lambda x: x[0])
                    employee = badge_map.get(badge)
                    if not employee:
                        continue

                    matched_employee += 1
                    matched_attendance += 1

                    line_vals = {
                        'employee_id': employee.id,
                        'attendance_id': employee.x_studio_attendance_id or '',
                        'company_id': employee.x_studio_company.id if getattr(employee, 'x_studio_company', False) else False,
                        'staff': employee.x_studio_engineeroffice_staff,
                        'on_leave': employee.x_studio_on_leave,
                        'first_punch': fields.Datetime.to_string(events[0][0]),
                        'last_punch': fields.Datetime.to_string(events[-1][0]),
                        'punch_machine_id': events[0][1],
                        'error_note': None
                    }

                    line = existing_lines.get(employee.id)
                    if line:
                        line.write(line_vals)
                    else:
                        attendance.write({'line_ids': [(0, 0, line_vals)]})

                    synced_count += 1

            except Exception as e:
                errors.append(str(e))
                _logger.exception(e)

        _logger.info("BioCloud Sync Done | %s synced | %s errors", synced_count, len(errors))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'BioCloud Sync',
                'message': f'Synced: {synced_count} | Errors: {len(errors)}',
                'type': 'success',
                'sticky': False,
            }
        }

    def transfer_to_x_daily_attendance(self):
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
                    sheet = parent.x_studio_attendance_sheet.filtered(
                        lambda l: l.x_studio_id == (line.attendance_id or '')
                    )
                    if sheet:
                        sheet.write({
                            'x_studio_project': line.project_id.id if line.project_id else False,
                            'x_studio_overtime_hrs': line.total_ot or 0.0,
                            'x_studio_absent': bool(line.absent)
                        })

                elif attendance.type == 'Off Day':
                    sheet = parent.x_studio_off_days_attendance_sheet.filtered(
                        lambda l: l.x_studio_id == (line.attendance_id or '')
                    )
                    if sheet:
                        sheet.write({
                            'x_studio_project': line.project_id.id if line.project_id else False,
                            'x_studio_overtime_hrs': (line.total_time + line.total_ot) or 0.0
                        })


# ------------------------------------------------------------
# Attendance Line
# ------------------------------------------------------------
class SSCAttendanceLine(models.Model):
    _name = "ssc.attendance.line"
    _description = "Attendance Line"

    external_id = fields.Many2one('ssc.attendance', ondelete='cascade')
    employee_id = fields.Many2one('x_employeeslist')
    company_id = fields.Many2one('res.company', compute="_compute_company", store=True)
    attendance_id = fields.Char()
    project_id = fields.Many2one('x_projects_list', compute="_compute_project", store=True)
    punch_machine_id = fields.Char()
    first_punch = fields.Datetime()
    last_punch = fields.Datetime()
    total_time = fields.Float(compute="_compute_total_time", store=True)
    total_ot = fields.Float(compute="_compute_total_ot", store=True)
    absent = fields.Boolean(compute="_compute_absent", store=True)
    staff = fields.Boolean(compute="_compute_staff", store=True)
    on_leave = fields.Boolean(compute="_compute_on_leave", store=True)
    error_note = fields.Text()

    @api.depends('employee_id')
    def _compute_company(self):
        for rec in self:
            rec.company_id = rec.employee_id.x_studio_company.id if rec.employee_id else False

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
            name = mapping.get(rec.punch_machine_id)
            rec.project_id = Project.search([('x_name', '=', name)], limit=1).id if name else False

    @api.depends('first_punch', 'last_punch')
    def _compute_total_time(self):
        for rec in self:
            if rec.first_punch and rec.last_punch:
                delta = rec.last_punch - rec.first_punch
                hours = delta.total_seconds() / 3600.0

                # خصم ساعة بريك إذا الدوام بعد 14
                if rec.last_punch.hour >= 14:
                    hours -= 1.0

                # حماية من القيم السالبة
                hours = max(hours, 0.0)

                # دوام عادي حد أقصى 8 ساعات
                rec.total_time = min(hours, 8.0)
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

                hours = max(hours, 0.0)

                # أي شي فوق 8 يعتبر OT
                rec.total_ot = max(hours - 8.0, 0.0)
            else:
                rec.total_ot = 0.0


    @api.depends('first_punch', 'on_leave', 'external_id')
    def _compute_absent(self):
        for rec in self:
            if rec.on_leave:
                rec.absent = False
            elif rec.external_id and rec.external_id.date.weekday() == 4:
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
