from odoo import models, fields, api
from datetime import date, timedelta
import requests
import logging

_logger = logging.getLogger(__name__)

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

    # =============================================================
    # ✅ Fetch Attendance Data from BioCloud API with Date Comparison
    # =============================================================
    def fetch_bioclock_data(self):
        """Fetch and update attendance data from ZK BioCloud with date comparison"""
        api_url = "https://api.zkbiocloud.com/v1/attendance"
        headers = {
            "Authorization": "Token fa83e149dabc49d28c477ea557016d03",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(api_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                _logger.info(f"✅ Successfully fetched {len(data)} records from BioCloud.")

                for item in data:
                    emp_code = item.get('employee_id')
                    punch_time_str = item.get('punch_time')
                    device_id = item.get('device_id')
                    status = item.get('status')

                    if not punch_time_str:
                        continue

                    # 🕒 Convert punch_time to date for comparison
                    punch_date = fields.Date.to_date(punch_time_str.split('T')[0])

                    # 🔍 Find or create attendance record for that date
                    today_rec = self.search([('date', '=', punch_date)], limit=1)
                    if not today_rec:
                        today_rec = self.create({
                            'date': punch_date,
                            'name': str(punch_date),
                            'type': 'Off Day' if punch_date.weekday() == 4 else 'Regular Day'
                        })

                    # 🧍 Match employee by BioCloud employee_id
                    employee = self.env['x_employeeslist'].search([
                        ('x_studio_attendance_id', '=', emp_code)
                    ], limit=1)

                    if employee:
                        line = self.env['ssc.attendance.line'].search([
                            ('employee_id', '=', employee.id),
                            ('external_id', '=', today_rec.id)
                        ], limit=1)

                        # ✅ Update or create attendance line
                        if line:
                            if status.lower() == "checkin":
                                line.first_punch = punch_time_str
                            elif status.lower() == "checkout":
                                line.last_punch = punch_time_str
                            line.punch_machine_id = device_id
                        else:
                            self.env['ssc.attendance.line'].create({
                                'external_id': today_rec.id,
                                'employee_id': employee.id,
                                'attendance_id': emp_code,
                                'punch_machine_id': device_id,
                                'first_punch': punch_time_str if status.lower() == "checkin" else False,
                                'last_punch': punch_time_str if status.lower() == "checkout" else False,
                            })

                _logger.info("✅ BioCloud Sync Completed Successfully.")
            else:
                _logger.warning(f"⚠️ BioCloud API returned {response.status_code}: {response.text}")
        except Exception as e:
            _logger.error(f"❌ Error fetching BioCloud data: {e}")


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
