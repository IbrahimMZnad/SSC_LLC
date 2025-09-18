from odoo import models, fields

class SSC_TestModel(models.Model):
    _name = 'ssc.test.model'
    _description = 'SSC Test Model'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
