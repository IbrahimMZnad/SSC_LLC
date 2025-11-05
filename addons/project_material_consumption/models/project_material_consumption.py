# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProjectMaterialConsumption(models.Model):
    _name = 'project.material.consumption'
    _description = 'Project Material Consumption'

    name = fields.Many2one('x_projects_list', string='Project', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)

    line_ids = fields.One2many(
        'project.material.consumption.line',
        'consumption_id',
        string='Lines',
    )

    boq_line_ids = fields.One2many(
        'project.material.consumption.boq.line',
        'consumption_id',
        string='BOQ Lines',
    )

    @api.model
    def add_all_items_daily(self):
        """Add items according to conditions:
        - If item exists in x_studio_items_needed → add to BOQ lines (only there)
        - Else if item appears in transactions/orders → add to regular lines
        """
        Transactions = self.env['x_transaction']
        PurchaseOrders = self.env['purchase.order']
        ItemModel = self.env['x_all_items_list']

        for rec in self.search([]):
            # ===== 1) اجمع كل المواد المَطلوبة (Needed) =====
            needed_item_ids = []
            needed_records = self.env['x_quantities_summary'].search([
                ('x_studio_project', '=', rec.name.id)
            ])
            for n in needed_records:
                if hasattr(n, 'x_studio_items_needed'):
                    for line in n.x_studio_items_needed:
                        item_id = None
                        if hasattr(line, 'x_item') and line.x_item:
                            item_id = line.x_item.id
                        elif hasattr(line, 'x_name') and line.x_name:
                            item_obj = ItemModel.search([('x_name', '=', line.x_name)], limit=1)
                            if item_obj:
                                item_id = item_obj.id
                        if item_id:
                            needed_item_ids.append(item_id)
            needed_item_ids = list(set(needed_item_ids))

            # ===== 2) اجمع المواد من Transactions و Purchase Orders =====
            consumed_items = Transactions.search([
                ('x_studio_project', '=', rec.name.id),
                ('x_studio_type_of_transaction', '=', 'Consumed'),
                ('x_studio_company', '=', rec.company_id.id)
            ]).mapped('x_studio_item_1')
            consumed_ids = consumed_items.ids

            ordered_ids = []
            orders = PurchaseOrders.search([
                ('x_studio_project', '=', rec.name.id),
                ('company_id', '=', rec.company_id.id)
            ])
            for order in orders:
                ordered_ids += [ln.x_studio_item.id for ln in order.order_line if ln.x_studio_item]
            ordered_ids = list(set(ordered_ids))

            consumed_or_ordered_ids = list(set(consumed_ids + ordered_ids))

            # ===== 3) أضف المواد المَطلوبة فقط إلى BOQ Lines =====
            for item_id in needed_item_ids:
                if not rec.boq_line_ids.filtered(lambda l: l.item.id == item_id):
                    self.env['project.material.consumption.boq.line'].create({
                        'consumption_id': rec.id,
                        'item': item_id,
                    })

            # ===== 4) أضف المواد الأخرى (غير المَطلوبة) إلى Lines العادية =====
            for item_id in consumed_or_ordered_ids:
                if item_id in needed_item_ids:
                    continue  # تخطى المواد المضافة مسبقاً في BOQ
                if not rec.line_ids.filtered(lambda l: l.item.id == item_id):
                    self.env['project.material.consumption.line'].create({
                        'consumption_id': rec.id,
                        'item': item_id,
                    })


# =====================================================================
#                              LINE MODEL
# =====================================================================

class ProjectMaterialConsumptionLine(models.Model):
    _name = 'project.material.consumption.line'
    _description = 'Project Material Consumption Line'

    consumption_id = fields.Many2one(
        'project.material.consumption',
        string='Consumption Reference',
        ondelete='cascade'
    )

    item = fields.Many2one('x_all_items_list', string='Item', required=True)

    quantity_needed = fields.Float(
        string='Quantity Needed',
        compute='_compute_quantity_needed',
        inverse='_inverse_quantity_needed',
        store=True,
        readonly=False,
    )

    quantity_consumed = fields.Float(string='Quantity Consumed', compute='_compute_quantity_consumed', store=True)
    quantity_ordered = fields.Float(string='Quantity Ordered', compute='_compute_quantity_ordered', store=True)
    balance_to_order = fields.Float(string='Balance to Order', compute='_compute_balance_to_order', store=True)
    balance_to_use = fields.Float(string='Balance to Use', compute='_compute_balance_to_use', store=True)
    stock = fields.Float(string='Stock', compute='_compute_stock', store=True)

    # ===== Related Fields =====
    unit = fields.Char(related='item.x_studio_unit', string='Unit')
    type_of_material = fields.Many2one('x_type_of_material', related='item.x_studio_type_of_material', string='Type of Material')

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_needed(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name:
                needed_records = self.env['x_quantities_summary'].search([
                    ('x_studio_project', '=', rec.consumption_id.name.id)
                ])
                for n in needed_records:
                    if hasattr(n, 'x_studio_items_needed'):
                        for line in n.x_studio_items_needed:
                            if hasattr(line, 'x_name') and hasattr(line, 'x_studio_quantity'):
                                if hasattr(line, 'x_item') and line.x_item and line.x_item.id == rec.item.id:
                                    qty_sum += line.x_studio_quantity
                                elif line.x_name and line.x_name == rec.item.x_name:
                                    qty_sum += line.x_studio_quantity
            rec.quantity_needed = qty_sum

    def _inverse_quantity_needed(self):
        pass

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_consumed(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name and rec.consumption_id.company_id:
                consumed_records = self.env['x_transaction'].search([
                    ('x_studio_project', '=', rec.consumption_id.name.id),
                    ('x_studio_type_of_transaction', '=', 'Consumed'),
                    ('x_studio_item_1', '=', rec.item.id),
                    ('x_studio_company', '=', rec.consumption_id.company_id.id)
                ])
                if consumed_records:
                    qty_sum = sum(getattr(r, 'x_studio_quantity', 0) or 0 for r in consumed_records)
            rec.quantity_consumed = qty_sum

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_ordered(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name and rec.consumption_id.company_id:
                orders = self.env['purchase.order'].search([
                    ('x_studio_project', '=', rec.consumption_id.name.id),
                    ('company_id', '=', rec.consumption_id.company_id.id),
                    ('state', 'in', ['purchase', 'done'])
                ])
                for order in orders:
                    if hasattr(order, 'order_line'):
                        for line in order.order_line:
                            if hasattr(line, 'x_studio_item') and line.x_studio_item and line.x_studio_item.id == rec.item.id:
                                qty_sum += getattr(line, 'product_qty', 0) or 0
            rec.quantity_ordered = qty_sum

    @api.depends('quantity_needed', 'quantity_ordered')
    def _compute_balance_to_order(self):
        for rec in self:
            if not rec.quantity_needed:
                rec.balance_to_order = 0
            else:
                value = (rec.quantity_needed or 0) - (rec.quantity_ordered or 0)
                rec.balance_to_order = value if value > 0 else 0

    @api.depends('quantity_needed', 'quantity_consumed')
    def _compute_balance_to_use(self):
        for rec in self:
            if not rec.quantity_needed:
                rec.balance_to_use = 0
            else:
                value = (rec.quantity_needed or 0) - (rec.quantity_consumed or 0)
                rec.balance_to_use = value if value > 0 else 0


    @api.depends('item', 'consumption_id.name')
    def _compute_stock(self):
        Inventory = self.env['x_inventory_stores_pro']
        for rec in self:
            total_stock = 0
            inv_records = Inventory.search([
                ('x_studio_project_1', '=', rec.consumption_id.name.id),
                ('x_studio_company', '=', rec.consumption_id.company_id.id)
            ])
            for inv in inv_records:
                if hasattr(inv, 'x_studio_one2many_field_113_1if9packl'):
                    for line in inv.x_studio_one2many_field_113_1if9packl:
                        if line.x_studio_item and line.x_studio_item.id == rec.item.id:
                            total_stock += line.x_studio_available_quantity or 0
            rec.stock = total_stock


# =====================================================================
#                           BOQ LINE MODEL
# =====================================================================

class ProjectMaterialConsumptionBoqLine(models.Model):
    _name = 'project.material.consumption.boq.line'
    _description = 'Project Material Consumption BOQ Line'

    consumption_id = fields.Many2one(
        'project.material.consumption',
        string='Consumption Reference',
        ondelete='cascade'
    )

    item = fields.Many2one('x_all_items_list', string='Item', required=True)

    quantity_needed = fields.Float(
        string='Quantity Needed',
        compute='_compute_quantity_needed',
        store=True,
        readonly=False,
    )

    quantity_consumed = fields.Float(string='Quantity Consumed', compute='_compute_quantity_consumed', store=True)
    quantity_ordered = fields.Float(string='Quantity Ordered', compute='_compute_quantity_ordered', store=True)
    balance_to_order = fields.Float(string='Balance to Order', compute='_compute_balance_to_order', store=True)
    balance_to_use = fields.Float(string='Balance to Use', compute='_compute_balance_to_use', store=True)
    stock = fields.Float(string='Stock', compute='_compute_stock', store=True)

    # ===== Related Fields =====
    unit = fields.Char(related='item.x_studio_unit', string='Unit')
    type_of_material = fields.Many2one('x_type_of_material', related='item.x_studio_type_of_material', string='Type of Material')

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_needed(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name:
                needed_records = self.env['x_quantities_summary'].search([
                    ('x_studio_project', '=', rec.consumption_id.name.id)
                ])
                for n in needed_records:
                    if hasattr(n, 'x_studio_items_needed'):
                        for line in n.x_studio_items_needed:
                            item_id = None
                            if hasattr(line, 'x_item') and line.x_item:
                                item_id = line.x_item.id
                            elif hasattr(line, 'x_name'):
                                item_obj = self.env['x_all_items_list'].search([('x_name', '=', line.x_name)], limit=1)
                                if item_obj:
                                    item_id = item_obj.id
                            if item_id and item_id == rec.item.id:
                                qty_sum += getattr(line, 'x_studio_quantity', 0) or 0
            rec.quantity_needed = qty_sum

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_consumed(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name and rec.consumption_id.company_id:
                consumed_records = self.env['x_transaction'].search([
                    ('x_studio_project', '=', rec.consumption_id.name.id),
                    ('x_studio_type_of_transaction', '=', 'Consumed'),
                    ('x_studio_item_1', '=', rec.item.id),
                    ('x_studio_company', '=', rec.consumption_id.company_id.id)
                ])
                qty_sum = sum(getattr(r, 'x_studio_quantity', 0) or 0 for r in consumed_records)
            rec.quantity_consumed = qty_sum

    @api.depends('item', 'consumption_id.name')
    def _compute_quantity_ordered(self):
        for rec in self:
            qty_sum = 0
            if rec.item and rec.consumption_id.name and rec.consumption_id.company_id:
                orders = self.env['purchase.order'].search([
                    ('x_studio_project', '=', rec.consumption_id.name.id),
                    ('company_id', '=', rec.consumption_id.company_id.id)
                ])
                for order in orders:
                    if hasattr(order, 'order_line'):
                        for line in order.order_line:
                            if hasattr(line, 'x_studio_item') and line.x_studio_item and line.x_studio_item.id == rec.item.id:
                                qty_sum += getattr(line, 'product_qty', 0) or 0
            rec.quantity_ordered = qty_sum

    @api.depends('quantity_needed', 'quantity_ordered')
    def _compute_balance_to_order(self):
        for rec in self:
            if not rec.quantity_needed:
                rec.balance_to_order = 0
            else:
                value = (rec.quantity_needed or 0) - (rec.quantity_ordered or 0)
                rec.balance_to_order = value if value > 0 else 0

    @api.depends('quantity_needed', 'quantity_consumed')
    def _compute_balance_to_use(self):
        for rec in self:
            if not rec.quantity_needed:
                rec.balance_to_use = 0
            else:
                value = (rec.quantity_needed or 0) - (rec.quantity_consumed or 0)
                rec.balance_to_use = value if value > 0 else 0


    @api.depends('item', 'consumption_id.name')
    def _compute_stock(self):
        Inventory = self.env['x_inventory_stores_pro']
        for rec in self:
            total_stock = 0
            inv_records = Inventory.search([
                ('x_studio_project_1', '=', rec.consumption_id.name.id),
                ('x_studio_company', '=', rec.consumption_id.company_id.id)
            ])
            for inv in inv_records:
                if hasattr(inv, 'x_studio_one2many_field_113_1if9packl'):
                    for line in inv.x_studio_one2many_field_113_1if9packl:
                        if line.x_studio_item and line.x_studio_item.id == rec.item.id:
                            total_stock += line.x_studio_available_quantity or 0
            rec.stock = total_stock
