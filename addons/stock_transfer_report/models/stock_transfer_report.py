# -*- coding: utf-8 -*-
from odoo import models, fields

class StockTransferReport(models.Model):
    _name = 'stock.transfer.report'
    _description = 'Stock Transfer Report'

    from_store = fields.Many2one('x_inventory_stores_pro', string="From Store")
    to_store = fields.Many2one('x_inventory_stores_pro', string="To Store")
    company_from = fields.Many2one('res.company', string="Company From", related='from_store.x_studio_company', store=True)
    company_to = fields.Many2one('res.company', string="Company To", related='to_store.x_studio_company', store=True)

    outgoing_lines = fields.One2many('stock.transfer.line', 'transfer_id', string="Outgoing Lines")
    incoming_lines = fields.One2many('stock.transfer.line', 'transfer_id', string="Incoming Lines")

    def fill_lines_from_transactions(self):
        Transaction = self.env['x_transaction']
        for rec in self:
            transactions = Transaction.search([
                ('x_studio_type_of_transaction', '=', 'Transfer'),
                ('x_studio_selection_field_64t_1ipgtrlhm', '=', 'status2'),
                ('x_studio_from_store', '=', rec.from_store.id),
                ('x_studio_store', '=', rec.to_store.id),
            ])
            for tx in transactions:
                for line in tx.x_studio_transfering_details:
                    # Outgoing Line
                    self.env['stock.transfer.line'].create({
                        'transfer_id': rec.id,
                        'description': 'to ' + rec.to_store.name,
                        'item': line.x_studio_item.id,
                        'date': tx.x_studio_date_2,
                    })
                    # Incoming Line
                    self.env['stock.transfer.line'].create({
                        'transfer_id': rec.id,
                        'description': 'from ' + rec.to_store.name,
                        'item': line.x_studio_item.id,
                        'date': tx.x_studio_date_2,
                    })

    def action_fetch_transactions(self):
        """Button action to fetch transactions and fill lines"""
        self.fill_lines_from_transactions()
        return True


class StockTransferLine(models.Model):
    _name = 'stock.transfer.line'
    _description = 'Stock Transfer Line'

    transfer_id = fields.Many2one('stock.transfer.report', string="Transfer")
    description = fields.Char(string="Description")
    item = fields.Many2one('x_all_items_list', string="Item")
    item_serial_no = fields.Char(string="Item Serial No.", related='item.x_studio_item_serial_no', store=True)
    unit = fields.Char(string="Unit", related='item.x_studio_unit', store=True)
    type_of_material = fields.Many2one('x_type_of_material', string="Type Of Material", related='item.x_studio_type_of_material', store=True)
    date = fields.Datetime(string="Date")
