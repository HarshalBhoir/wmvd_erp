# -*- coding: utf-8 -*-
import xlwt
import base64
import calendar
from io import StringIO
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime

class SaleOrderReport(models.TransientModel):
    _name = "sale.order.report"
    
    start_date = fields.Date(string='Start Date', required=True, default=datetime.today().replace(day=1))
    end_date = fields.Date(string="End Date", required=True, default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))
    order_state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', default='draft', required=True)
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user, required=True)
    sale_order_data = fields.Char('Name', size=256)
    file_name = fields.Binary('Sale Excel Report', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')

    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]

    @api.multi
    def action_sale_report(self):
        file = StringIO()        
        sale_order = self.env['sale.order'].search([('date_order', '>=', self.start_date), ('date_order', '<=', self.end_date), 
                                                    ('state', '=', self.order_state), ('user_id', '=', self.user_id.id)])
        final_value = {}
        workbook = xlwt.Workbook()                         
        if sale_order:
            for rec in sale_order:
                order_lines = []
                for lines in rec.order_line:
                    product = {
                        'product_id'     : lines.product_id.name,
                        'description'    : lines.name,
                        'product_uom_qty': lines.product_uom_qty,
                        'qty_delivered'  : lines.qty_delivered,
                        'qty_invoiced'   : lines.qty_invoiced,
                        'price_unit'     : lines.price_unit,
                        'price_subtotal' : lines.price_subtotal   
                    }
                    if lines.tax_id:
                        taxes = []
                        for tax_id in lines.tax_id:
                            taxes.append(tax_id.name)
                        product['tax_id'] = taxes
                    order_lines.append(product)
                final_value['partner_id'] = rec.partner_id.name
                final_value['date_order'] = rec.date_order
                final_value['user_id'] = rec.user_id.name
                final_value['name'] = rec.name
                final_value['currency_id'] = rec.currency_id
                final_value['state'] = dict(self.env['sale.order'].fields_get(allfields=['state'])['state']['selection'])[rec.state]
                final_value['payment_term_id'] = rec.payment_term_id.name
                final_value['client_order_ref'] = rec.client_order_ref
                final_value['origin'] = rec.origin
                final_value['amount_untaxed'] = rec.amount_untaxed
                final_value['amount_tax'] = rec.amount_tax
                final_value['amount_total'] = rec.amount_total
                format0 = xlwt.easyxf('font:height 500,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
                format1 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
                format2 = xlwt.easyxf('font:bold True;align: horiz left')
                format3 = xlwt.easyxf('align: horiz left')
                format4 = xlwt.easyxf('align: horiz right')
                format5 = xlwt.easyxf('font:bold True;align: horiz right')
                format6 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz right')
                format7 = xlwt.easyxf('font:bold True;borders:top thick;align: horiz right')
                format8 = xlwt.easyxf('font:bold True;borders:top thick;pattern: pattern solid, fore_colour gray25;align: horiz left')
                sheet = workbook.add_sheet(rec.name)
                sheet.col(0).width = int(30*260)
                sheet.col(1).width = int(30*260)    
                sheet.col(2).width = int(18*260)    
                sheet.col(3).width = int(18*260) 
                sheet.col(4).width = int(15*260)   
                sheet.col(5).width = int(15*260)
                sheet.col(6).width = int(33*260)   
                sheet.write_merge(0, 2, 0, 7, 'Sale Order : ' + final_value['name'] , format0)
                sheet.write(5, 0, "Customer", format1)
                sheet.write(5, 1, final_value['partner_id'], format2)
                sheet.write(5, 3, 'Date', format1)
                sheet.write_merge(5, 5, 4, 5, final_value['date_order'], format3)
                sheet.write(6, 3, 'Payment Term', format1)
                if final_value['payment_term_id']:
                    sheet.write_merge(6, 6, 4, 5, final_value['payment_term_id'], format3)
                else:
                    sheet.write_merge(6, 6, 4, 5, "No Payment Terms Defined", format3)
                sheet.write(7, 3, 'Customer Reference', format1)
                if final_value['client_order_ref']:
                    sheet.write_merge(7, 7, 4, 5, final_value['client_order_ref'], format3)
                else:
                    sheet.write_merge(7, 7, 4, 5, "No Customer Reference Defined", format3)
                sheet.write(8, 3, "State", format1)
                sheet.write_merge(8, 8, 4, 5, final_value['state'], format3)
                sheet.write(10, 0, "Salesperson", format1)
                sheet.write(11, 0, final_value['user_id'], format3)
                sheet.write(15, 0, 'PRODUCT', format1)
                sheet.write(15, 1, 'DESCRIPTION', format1)
                sheet.write(15, 2, 'QUANTITY', format6)        
                sheet.write(15, 3, 'DELIVERED', format6)        
                sheet.write(15, 4, 'INVOICED', format6)        
                sheet.write(15, 5, 'UNIT PRICE', format6)
                sheet.write(15, 6, 'TAXES', format1) 
                sheet.write(15, 7, 'SUBTOTAL', format6)
                row = 16
                for rec in order_lines:
                    sheet.write(row, 0, rec.get('product_id'), format3)
                    sheet.write(row, 1, rec.get('description'), format3)
                    sheet.write(row, 2, rec.get('product_uom_qty'), format4)
                    sheet.write(row, 3, rec.get('qty_delivered'), format4)
                    sheet.write(row, 4, rec.get('qty_invoiced'), format4)
                    sheet.write(row, 5, rec.get('price_unit'), format4)
                    if rec.get('tax_id'):
                        sheet.write(row, 6, ",".join(rec.get('tax_id')), format4)
                    else:
                        sheet.write(row, 6, 0, format4)
                    if final_value['currency_id'].position == "before":
                        sheet.write(row, 7, final_value['currency_id'].symbol + str(rec.get('price_subtotal')), format4)
                    else:
                        sheet.write(row, 7, str(rec.get('price_subtotal')) + final_value['currency_id'].symbol, format4)
                    row += 1
                row += 2
                sheet.write(row, 6, 'UNTAXED AMOUNT', format8)
                if final_value['currency_id'].position == "before":
                    sheet.write(row, 7, final_value['currency_id'].symbol + str(final_value['amount_untaxed']), format7)
                else:
                    sheet.write(row, 7, str(final_value['amount_untaxed']) + final_value['currency_id'].symbol, format7)    
                sheet.write(row+1, 6, 'TAXES', format8)
                if final_value['currency_id'].position == "before":
                    sheet.write(row+1, 7, final_value['currency_id'].symbol + str(final_value['amount_tax']), format7)
                else:
                    sheet.write(row+1, 7, str(final_value['amount_tax']) + final_value['currency_id'].symbol, format7)
                sheet.write(row+2, 6, 'TOTAL', format8)
                if final_value['currency_id'].position == "before":
                    sheet.write(row+2, 7, final_value['currency_id'].symbol + str(final_value['amount_total']), format7)
                else:
                    sheet.write(row+2, 7, str(final_value['amount_total']) + final_value['currency_id'].symbol, format7)
        else:
            raise Warning("Currently No Sales Order For This Data!!")
        filename = ('Sale Order Report'+ '.xls')
        workbook.save(filename)
        file = open(filename, "rb")
        file_data = file.read()
        out = base64.encodestring(file_data)
        self.write({'state': 'get', 'file_name': out, 'sale_order_data':'Sale Order Report.xls'})
        return {
           'type': 'ir.actions.act_window',
           'res_model': 'sale.order.report',
           'view_mode': 'form',
           'view_type': 'form',
           'res_id': self.id,
           'target': 'new',
        }          