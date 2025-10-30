# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProjectMaterialConsumption(models.Model):
    _name = 'project.material.consumption'
    _description = 'Project Material Consumption'

    name = fields.Many2one('x_projects_list', string='Project', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    line_ids = fields.One2many('project.material.consumption.line', 'consumption_id', string='Lines')


class ProjectMaterialConsumptionLine(models.Model):
    _name = 'project.material.consumption.line'
    _description = 'Project Material Consumption Line'

    consumption_id = fields.Many2one('project.material.consumption', string='Consumption Reference', ondelete='cascade')
    item = fields.Many2one('x_all_items_list', string='Item', required=True)

    quantity_needed = fields.Float(string='Quantity Needed', compute='_compute_quantity_needed', store=True)
    quantity_consumed = fields.Float(string='Quantity Consumed', compute='_compute_quantity_consumed', store=True)
    quantity_ordered = fields.Float(string='Quantity Ordered', compute='_compute_quantity_ordered', store=True)
    balance_to_order = fields.Float(string='Balance to Order', compute='_compute_balance_to_order', store=True)
    balance_to_use = fields.Float(string='Balance to Use', compute='_compute_balance_to_use', store=True)

    # --------------------------------------------------
    # COMPUTE FIELDS
    # --------------------------------------------------

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_needed(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name:
                needed_records = self.env['x_quantities_summary'].search([
                    ('x_studio_project.id', '=', rec.consumption_id.name.id),
                    ('x_studio_company.id', '=', rec.consumption_id.company_id)
                ])
                for n in needed_records:
                    for line in n.x_studio_items_needed:
                        if line.x_name == rec.item.name:
                            qty_sum += line.x_studio_quantity
            rec.quantity_needed = qty_sum

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_consumed(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name:
                consumed_records = self.env['x_transaction'].search([
                    ('x_studio_project.id', '=', rec.consumption_id.name.id),
                    ('x_studio_type_of_transaction', '=', 'Consumed'),
                    ('x_studio_item_1.id', '=', rec.item.id),
                    ('x_studio_company.id', '=', rec.consumption_id.company_id)
                ])
                qty_sum = sum(consumed_records.mapped('x_studio_quantity'))
            rec.quantity_consumed = qty_sum

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_ordered(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name:
                orders = self.env['purchase.order'].search([
                    ('x_studio_project.id', '=', rec.consumption_id.name.id),
                    ('company_id.id', '=', rec.consumption_id..company_id)
                ])
                for order in orders:
                    for line in order.order_line:
                        if line.x_studio_item.id == rec.item.id:
                            qty_sum += line.product_qty
            rec.quantity_ordered = qty_sum

    @api.depends('quantity_needed', 'quantity_ordered')
    def _compute_balance_to_order(self):
        for rec in self:
            rec.balance_to_order = rec.quantity_needed - rec.quantity_ordered

    @api.depends('quantity_needed', 'quantity_consumed')
    def _compute_balance_to_use(self):
        for rec in self:
            rec.balance_to_use = rec.quantity_needed - rec.quantity_consumed
