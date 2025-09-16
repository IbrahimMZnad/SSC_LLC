from odoo import models, fields

class CustomModel(models.Model):
    _name = 'custom.app'
    _description = 'Custom App'

    name = fields.Char(string='Name')
    date_field = fields.Date(string='Date')
