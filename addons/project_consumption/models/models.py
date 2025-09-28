from odoo import models, fields, api

class ProjectConsumption(models.Model):
    _name = 'project.consumption'
    _description = 'Project Consumption'

    project_id = fields.Many2one('x_projects_list', string='Project', required=True)

    # Lines
    construction_lines = fields.One2many('project.consumption.line', 'project_consumption_id', string='Construction Materials')
    mep_lines = fields.One2many('project.consumption.line', 'project_consumption_id', string='MEP Materials')


class ProjectConsumptionLine(models.Model):
    _name = 'project.consumption.line'
    _description = 'Project Consumption Line'

    project_consumption_id = fields.Many2one('project.consumption', string='Project Consumption', required=True)
    item_id = fields.Many2one('x_all_items_list', string='Material', required=True)
    
    unit = fields.Char(string='Unit', related='item_id.x_studio_unit', readonly=True)
    x_studio_item_serial_no = fields.Char(string='Item Serial No', related='item_id.x_studio_item_serial_no', readonly=True)
    type_of_material = fields.Many2one('x_all_items_list', string='Type Of Material', related='item_id.x_studio_type_of_material', readonly=True)
    
    quantity_needed = fields.Float(string='Quantity Needed')
    quantity_consumed = fields.Float(string='Quantity Consumed')
    
    quantity_used_over_limit = fields.Float(string='Quantity Used Over Limit', compute='_compute_over_limit', store=True)
    balance = fields.Float(string='Balance', compute='_compute_balance', store=True)

    @api.depends('quantity_needed', 'quantity_consumed')
    def _compute_over_limit(self):
        for rec in self:
            rec.quantity_used_over_limit = rec.quantity_consumed - rec.quantity_needed

    @api.depends('quantity_needed', 'quantity_consumed')
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.quantity_needed - rec.quantity_consumed
