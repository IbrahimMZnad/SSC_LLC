from odoo import models, fields

class SscTestSimple(models.Model):
    _name = "ssc.test.simple"
    _description = "Simple Test Menu"

    name = fields.Char(string="Name", required=True)  # إضافة حقل name
    date_field = fields.Date(string="Date")
    is_checked = fields.Boolean(string="Checked")
