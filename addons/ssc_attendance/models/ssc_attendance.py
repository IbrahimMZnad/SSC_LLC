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
        employees = Employee.search([])

        lines = []
        for emp in employees:
            lines.append((0, 0, {
                'employee_id': emp.id,
                'attendance_id': emp.x_studio_attendance_id or '',
                'company_id': emp.x_studio_company.id if emp.x_studio_company else False,
                'staff': emp.x_studio_engineeroffice_staff,
                'on_leave': emp.x_studio_on_leave,
            }))
        if lines:
            self.write({'line_ids': lines})

    def _normalize_badge(self, s):
        if not s:
            return ''
        return re.sub(r'[^A-Za-z0-9]', '', str(s)).upper()

    def fetch_bioclock_data(self):
        url = "https://57.biocloud.me:8199/api_gettransctions"
        token = "fa83e149dabc49d28c477ea557016d03"
        headers = {"token": token, "Content-Type": "application/json"}

        Employee = self.env['x_employeeslist']
        badge_map = {
            self._normalize_badge(emp.x_studio_attendance_id or ''): emp
            for emp in Employee.search([('x_studio_attendance_id', '!=', False)])
        }

        for attendance in self.search([]):

            # ✅ Cache للأسطر الموجودة
            existing_lines = {
                line.employee_id.id: line
                for line in attendance.line_ids
                if line.employee_id
            }

            start_dt_utc = datetime.combine(attendance.date, datetime.min.time()).replace(tzinfo=pytz.utc)
            end_dt_utc = datetime.combine(attendance.date, datetime.max.time()).replace(tzinfo=pytz.utc)

            payload = {
                "StartDate": start_dt_utc.strftime("%Y-%m-%d %H:%M:%S"),
                "EndDate": end_dt_utc.strftime("%Y-%m-%d %H:%M:%S")
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            data = response.json()
            transactions = data.get("message") or data.get("data") or []

            groups = defaultdict(list)

            for trx in transactions:
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

                groups[(badge, verify_date)].append((verify_dt_utc, device))

            for (badge, v_date), events in groups.items():
                if v_date != attendance.date:
                    continue

                employee = badge_map.get(badge)
                if not employee:
                    continue

                events = sorted(events, key=lambda x: x[0])
                first_dt = events[0][0]
                last_dt = events[-1][0]
                chosen_device = events[-1][1]

                line_vals = {
                    'employee_id': employee.id,
                    'attendance_id': employee.x_studio_attendance_id or '',
                    'company_id': employee.x_studio_company.id if employee.x_studio_company else False,
                    'staff': employee.x_studio_engineeroffice_staff,
                    'on_leave': employee.x_studio_on_leave,
                    'first_punch': fields.Datetime.to_string(first_dt),
                    'last_punch': fields.Datetime.to_string(last_dt),
                    'punch_machine_id': chosen_device or '',
                }

                line = existing_lines.get(employee.id)
                if line:
                    line.write(line_vals)
                else:
                    attendance.write({'line_ids': [(0, 0, line_vals)]})

        return True

    def transfer_to_x_daily_attendance(self):
        Daily = self.env['x_daily_attendance']
        today = fields.Date.context_today(self)

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
                    if not sheet:
                        continue

                    vals = {
                        'x_studio_id': line.attendance_id or '',
                        'x_studio_project': line.project_id.id if line.project_id else False,
                        'x_studio_overtime_hrs': line.total_ot or 0.0,
                        'x_studio_absent': True if (attendance.date < today and line.absent) else False
                    }
                    sheet.write(vals)

                elif attendance.type == 'Off Day':
                    sheet = parent.x_studio_off_days_attendance_sheet.filtered(
                        lambda l: l.x_studio_id == (line.attendance_id or '')
                    )
                    if not sheet:
                        continue

                    sheet.write({
                        'x_studio_id': line.attendance_id or '',
                        'x_studio_project': line.project_id.id if line.project_id else False,
                        'x_studio_overtime_hrs': (line.total_time + line.total_ot) or 0.0,
                    })

        return True


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

    @api.depends('employee_id')
    def _compute_company(self):
        for rec in self:
            rec.company_id = rec.employee_id.x_studio_company.id if rec.employee_id and rec.employee_id.x_studio_company else False

    @api.depends('first_punch', 'last_punch')
    def _compute_total_time(self):
        for rec in self:
            if rec.first_punch and rec.last_punch:
                rec.total_time = min((rec.last_punch - rec.first_punch).total_seconds() / 3600.0, 8.0)
            else:
                rec.total_time = 0.0

    @api.depends('first_punch', 'last_punch')
    def _compute_total_ot(self):
        for rec in self:
            if rec.first_punch and rec.last_punch:
                hours = (rec.last_punch - rec.first_punch).total_seconds() / 3600.0
                rec.total_ot = max(hours - 8.0, 0.0)
            else:
                rec.total_ot = 0.0

    @api.depends('first_punch', 'on_leave', 'external_id.date')
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
