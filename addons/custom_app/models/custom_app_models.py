# -*- coding: utf-8 -*-
from odoo import models, fields

class CustomApp(models.Model):
    _name = 'custom.app'
    _description = 'Custom App'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    date = fields.Date(string='Date')
