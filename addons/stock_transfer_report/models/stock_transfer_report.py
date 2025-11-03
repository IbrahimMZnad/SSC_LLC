# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockTransferReport(models.Model):
    _name = 'stock.transfer.report'
    _description = 'Stock Transfer Report'

    store = fields.Many2one('x_inventory_stores_pro', string="Store")
    company = fields.Many2one('res.company', string="Company", related='store.x_studio_company', store=True)
    outgoing_lines = fields.One2many('stock.transfer.line', 'transfer_id', string="Outgoing Lines")
    incoming_lines = fields.One2many('stock.transfer.line', 'transfer_id', string="Incoming Lines")

    @api.model
    def fill_lines_from_transactions(self):
        """Fill or update transfer lines for each store based on x_transaction"""
        Transaction = self.env['x_transaction']
        Store = self.env['x_inventory_stores_pro']

        # حذف السجلات القديمة قبل إعادة إنشائها (اختياري)
        self.search([]).unlink()

        for store in Store.search([]):
            # إنشاء سجل جديد للتقرير الخاص بالمستودع
            report = self.create({'store': store.id})

            # جلب جميع عمليات النقل المتعلقة بهذا المستودع
            transactions = Transaction.search([
                ('x_studio_type_of_transaction', '=', 'Transfer'),
                ('x_studio_selection_field_64t_1ipgtrlhm', '=', 'status2'),
                '|',
                ('x_studio_from_store', '=', store.id),
                ('x_studio_store', '=', store.id),
            ])

            for tx in transactions:
                for line in tx.x_studio_transfering_details:
                    # الحالة 1: المستودع هو المرسل
                    if tx.x_studio_from_store.id == store.id:
                        self.env['stock.transfer.line'].create({
                            'transfer_id': report.id,
                            'description': 'to ' + (tx.x_studio_store.x_name or ''),
                            'item': line.x_studio_item.id,
                            'date': tx.x_studio_date_2,
                            'quantity': line.x_studio_quantity,
                            'notes': tx.x_studio_remarks_4,
                        })

                    # الحالة 2: المستودع هو المستقبل
                    elif tx.x_studio_store.id == store.id:
                        self.env['stock.transfer.line'].create({
                            'transfer_id': report.id,
                            'description': 'from ' + (tx.x_studio_from_store.x_name or ''),
                            'item': line.x_studio_item.id,
                            'date': tx.x_studio_date_2,
                            'quantity': line.x_studio_quantity,
                            'notes': tx.x_studio_remarks_4,
                        })

    def action_fetch_transactions(self):
        """Button to refresh and rebuild all reports"""
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
    quantity = fields.Float(string="Quantity")
    notes = fields.Html(string="Notes")
