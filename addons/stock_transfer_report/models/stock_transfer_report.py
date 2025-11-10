# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockTransferReport(models.Model):
    _name = 'stock.transfer.report'
    _description = 'Stock Transfer Report'

    store = fields.Many2one('x_inventory_stores_pro', string="Store")
    company = fields.Many2one('res.company', string="Company", related='store.x_studio_company', store=True)
    outgoing_lines = fields.One2many('stock.transfer.line', 'transfer_out_id', string="Outgoing Lines")
    incoming_lines = fields.One2many('stock.transfer.line', 'transfer_in_id', string="Incoming Lines")

    def fill_lines_from_transactions(self):
        Transaction = self.env['x_transaction']
        Store = self.env['x_inventory_stores_pro']

        # استخرج عمليات Transfer بالحالة المطلوبة
        transactions = Transaction.search([
            ('x_studio_type_of_transaction', '=', 'Transfer'),
            ('x_studio_selection_field_64t_1ipgtrlhm', '=', 'status2')
        ])

        if not transactions:
            return

        # استخرج المخازن المشاركة
        involved_stores = Store.search([
            '|',
            ('id', 'in', transactions.mapped('x_studio_store').ids),
            ('id', 'in', transactions.mapped('x_studio_from_store').ids)
        ])

        for store in involved_stores:

            report = self.search([('store', '=', store.id)], limit=1)

            if not report:
                report = self.create({'store': store.id})

            store_transactions = transactions.filtered(
                lambda t: t.x_studio_store.id == store.id or t.x_studio_from_store.id == store.id
            )

            # ✅ إضافة السطور بدون تكرار
            for tx in store_transactions:
                for line in tx.x_studio_transfering_details:

                    vals = {
                        'item': line.x_studio_item.id,
                        'date': tx.x_studio_date_2,
                        'quantity': line.x_studio_quantity,
                        'notes': tx.x_studio_remarks_4,
                    }

                    # خروج من المخزن
                    if tx.x_studio_from_store.id == store.id:
                        vals.update({
                            'transfer_out_id': report.id,
                            'description': 'to ' + (tx.x_studio_store.x_name or ''),
                        })

                        existing = self.env['stock.transfer.line'].search([
                            ('transfer_out_id', '=', report.id),
                            ('item', '=', line.x_studio_item.id),
                            ('date', '=', tx.x_studio_date_2),
                            ('quantity', '=', line.x_studio_quantity),
                            ('description', '=', 'to ' + (tx.x_studio_store.x_name or '')),
                        ], limit=1)

                        if not existing:
                            self.env['stock.transfer.line'].create(vals)

                    # دخول إلى المخزن
                    elif tx.x_studio_store.id == store.id:
                        vals.update({
                            'transfer_in_id': report.id,
                            'description': 'from ' + (tx.x_studio_from_store.x_name or ''),
                        })

                        existing = self.env['stock.transfer.line'].search([
                            ('transfer_in_id', '=', report.id),
                            ('item', '=', line.x_studio_item.id),
                            ('date', '=', tx.x_studio_date_2),
                            ('quantity', '=', line.x_studio_quantity),
                            ('description', '=', 'from ' + (tx.x_studio_from_store.x_name or '')),
                        ], limit=1)

                        if not existing:
                            self.env['stock.transfer.line'].create(vals)


class StockTransferLine(models.Model):
    _name = 'stock.transfer.line'
    _description = 'Stock Transfer Line'

    transfer_out_id = fields.Many2one('stock.transfer.report', string="Outgoing Transfer")
    transfer_in_id = fields.Many2one('stock.transfer.report', string="Incoming Transfer")
    description = fields.Char(string="Description")
    item = fields.Many2one('x_all_items_list', string="Item")
    item_serial_no = fields.Char(string="Item Serial No.", related='item.x_studio_item_serial_no', store=True)
    unit = fields.Char(string="Unit", related='item.x_studio_unit', store=True)
    type_of_material = fields.Many2one('x_type_of_material', string="Type Of Material", related='item.x_studio_type_of_material', store=True)
    date = fields.Datetime(string="Date")
    quantity = fields.Float(string="Quantity")
    notes = fields.Html(string="Notes")
