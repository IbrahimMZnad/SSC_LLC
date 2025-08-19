from odoo import models, fields

class CustomApp(models.Model):
    _name = 'custom.app'
    _description = 'Custom App Model'

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
