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
        Employee = self.env['x_employeeslist']
        lines = []
        for emp in Employee.search([]):
            lines.append((0, 0, {
                'employee_id': emp.id,
                'attendance_id': emp.x_studio_attendance_id or '',
                'company_id': emp.x_studio_company.id if emp.x_studio_company else False,
                'staff': emp.x_studio_engineeroffice_staff,
                'on_leave': emp.x_studio_on_leave,
            }))
        self.write({'line_ids': lines})

    def _normalize_badge(self, s):
        return re.sub(r'[^A-Za-z0-9]', '', str(s)).upper() if s else ''

    def fetch_bioclock_data(self):
        """
        ✅ يحدث فقط بيانات يوم اليوم
        ✅ يعيد التحديث كل ساعة
        """
        today = fields.Date.context_today(self)

        url = "https://57.biocloud.me:8199/api_gettransctions"
        headers = {
            "token": "fa83e149dabc49d28c477ea557016d03",
            "Content-Type": "application/json"
        }

        Employee = self.env['x_employeeslist']
        badge_map = {
            self._normalize_badge(emp.x_studio_attendance_id): emp
            for emp in Employee.search([('x_studio_attendance_id', '!=', False)])
        }

        attendance = self.search([('date', '=', today)], limit=1)
        if not attendance:
            attendance = self.create({
                'name': str(today),
                'date': today,
                'type': 'Off Day' if today.weekday() == 4 else 'Regular Day'
            })

        start_dt = SERVER_TZ.localize(datetime.combine(today, datetime.min.time()))
        end_dt = SERVER_TZ.localize(datetime.combine(today, datetime.max.time()))

        payload = {
            "StartDate": start_dt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "EndDate": end_dt.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        transactions = data.get("message") or data.get("data") or []

        groups = defaultdict(list)

        for trx in transactions:
            verify_time = trx.get("VerifyTime")
            badge = trx.get("BadgeNumber")
            device = trx.get("DeviceSerialNumber") or ''

            if not verify_time or not badge:
                continue

            dt = datetime.fromisoformat(verify_time)
            if dt.tzinfo is None:
                dt = SERVER_TZ.localize(dt)
            dt_utc = dt.astimezone(pytz.utc)

            groups[self._normalize_badge(badge)].append((dt_utc, device))

        for badge, punches in groups.items():
            employee = badge_map.get(badge)
            if not employee:
                continue

            punches.sort(key=lambda x: x[0])
            first_dt = punches[0][0]
            last_dt = punches[-1][0]

            line = attendance.line_ids.filtered(lambda l: l.employee_id == employee)
            vals = {
                'first_punch': fields.Datetime.to_string(first_dt),
                'last_punch': fields.Datetime.to_string(last_dt),
                'punch_machine_id': punches[-1][1]
            }

            if line:
                line.write(vals)
            else:
                attendance.write({'line_ids': [(0, 0, {
                    'employee_id': employee.id,
                    'attendance_id': employee.x_studio_attendance_id,
                    **vals
                })]})

        return True

    def transfer_to_x_daily_attendance(self):
        """
        ❌ لا ينشئ لاين جديد
        ✅ يحدث فقط الموجود
        """
        Daily = self.env['x_daily_attendance']

        for attendance in self:
            for line in attendance.line_ids:
                parent = Daily.search([
                    ('x_studio_todays_date', '=', attendance.date),
                    ('x_studio_company', '=', line.company_id.id)
                ], limit=1)

                if not parent:
                    continue

                if attendance.type == 'Regular Day':
                    sheet = parent.x_studio_attendance_sheet.filtered(
                        lambda l: l.x_studio_id == line.attendance_id
                    )
                    if sheet:
                        sheet.write({
                            'x_studio_absent': line.absent,
                            'x_studio_project': line.project_id.id if line.project_id else False,
                            'x_studio_overtime_hrs': line.total_ot
                        })

                else:
                    sheet = parent.x_studio_off_days_attendance_sheet.filtered(
                        lambda l: l.x_studio_id == line.attendance_id
                    )
                    if sheet:
                        sheet.write({
                            'x_studio_project': line.project_id.id if line.project_id else False,
                            'x_studio_overtime_hrs': line.total_time + line.total_ot
                        })

        return True


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
    staff = fields.Boolean()
    on_leave = fields.Boolean()

    @api.depends('employee_id')
    def _compute_company(self):
        for r in self:
            r.company_id = r.employee_id.x_studio_company.id if r.employee_id else False

    @api.depends('first_punch', 'last_punch')
    def _compute_total_time(self):
        for r in self:
            if r.first_punch and r.last_punch:
                r.total_time = min((r.last_punch - r.first_punch).total_seconds() / 3600, 8)
            else:
                r.total_time = 0

    @api.depends('first_punch', 'last_punch')
    def _compute_total_ot(self):
        for r in self:
            if r.first_punch and r.last_punch:
                hours = (r.last_punch - r.first_punch).total_seconds() / 3600
                r.total_ot = max(0, hours - 8)
            else:
                r.total_ot = 0

    @api.depends('first_punch')
    def _compute_absent(self):
        for r in self:
            r.absent = not bool(r.first_punch)
