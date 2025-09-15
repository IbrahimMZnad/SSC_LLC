# -*- coding: utf-8 -*-
from odoo import models, api
import logging
import requests
from datetime import date

_logger = logging.getLogger(__name__)

class ZKAttendanceSync(models.Model):
    _name = 'zkteco.attendance.sync'
    _description = 'ZKTeco Cloud Attendance Sync'

    @api.model
    def sync_attendance(self):
        """Cron entry point: fetch from ZKTeco Cloud and update x_daily_attendance."""
        # read config params (set these later in Settings > Technical > System Parameters)
        api_key = self.env['ir.config_parameter'].sudo().get_param('zkteco.api_key')
        base_url = self.env['ir.config_parameter'].sudo().get_param('zkteco.api_url') or 'https://cloud.zkteco.com/api/attendance'

        if not api_key:
            _logger.warning('ZKTeco API key not configured (ir.config_parameter zkteco.api_key). Aborting sync.')
            return

        headers = {'Authorization': f'Bearer {api_key}'}
        try:
            resp = requests.get(base_url, headers=headers, timeout=30)
            resp.raise_for_status()
            attendance_data = resp.json()
        except Exception as e:
            _logger.exception('Failed to fetch attendance from ZKTeco Cloud: %s', e)
            return

        today = date.today()
        # find or create the daily attendance record for today
        Daily = self.env['x_daily_attendance'].sudo()
        daily = Daily.search([('date_field', '=', today)], limit=1)
        if not daily:
            daily = Daily.create({'date_field': today})

        # Example: expecting attendance_data to be a list of dicts like:
        # [{'employee_id': 12, 'first_bunch': '2025-09-14T08:00:00', 'overtime_hours': 2, ...}, ...]
        for rec in attendance_data:
            emp_cloud_id = rec.get('employee_id')
            first_bunch = rec.get('first_bunch')  # None or 0 => absent
            overtime_hrs = rec.get('overtime_hours', 0)

            # find existing line in the one2many by matching many2one employee id
            existing_lines = daily.x_studio_attendance_sheet.filtered(lambda l: l.x_studio_employee and l.x_studio_employee.id == emp_cloud_id)

            vals = {
                'x_studio_absent': True if (not first_bunch) else False,
                'x_studio_overtime_hrs': int(overtime_hrs) if overtime_hrs else 0,
            }
            # optional: get default project id from system params if configured
            proj = self.env['ir.config_parameter'].sudo().get_param('zkteco.default_project_id')
            if proj:
                try:
                    vals['x_studio_project'] = int(proj)
                except Exception:
                    pass

            if existing_lines:
                existing_lines.sudo().write(vals)
            else:
                vals['x_studio_employee'] = emp_cloud_id
                # append new line to the one2many
                daily.sudo().write({'x_studio_attendance_sheet': [(0, 0, vals)]})

        _logger.info('ZKTeco sync finished: processed %d items', len(attendance_data))
