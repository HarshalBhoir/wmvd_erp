from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import datetime
from datetime import datetime, timedelta , date
import time
from cStringIO import StringIO
import xlwt
import base64
from collections import Counter

class pending_distributer_stock_report(models.TransientModel):
    _name = 'pending.distributer.stock.report'
    _description = "Pending Distributer Stock Report"


    name = fields.Char(string="Pending Distributer Stock Report")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    partner_ids = fields.Many2many('res.partner', 'pending_distributer_stock_res_partner_rel', string='Distributers')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')

  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True
    

    @api.multi
    def print_report(self):
        
        self.ensure_one()
        filtered_list = []
        filtered_list3 = {}
        product_list = []
        new_quant = 0
        vals = []
        # self.sudo().unlink()
        if self.date_from and self.date_to:

            rep_name = self._description
            if  not self.name:
                date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                if self.date_from == self.date_to:
                    rep_name = "Pending Distributer Stock Report(%s)" % (date_from,)
                else:
                    rep_name = "Pending Distributer Stock Report(%s|%s)" % (date_from, date_to)
            self.name = rep_name

            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet('Pending Distributer Stock Report')
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1; borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
            base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
            base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
            base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')
                
            
            worksheet.write_merge(0, 1, 0, 8, self.name ,main_style)
            row_index = 2
            
            worksheet.col(0).width = 3000
            worksheet.col(1).width = 4000
            worksheet.col(2).width = 4000
            worksheet.col(3).width = 12000
            worksheet.col(4).width = 4000
            worksheet.col(5).width = 5000
            worksheet.col(6).width = 12000
            worksheet.col(7).width = 4000
            worksheet.col(8).width = 5000

            
            # Headers
            header_fields = [
                            'Sr.No',
                            'Sample No',
                            'Partner Code',
                            'Distributer / Retailer',
                            'State',
                            'Product Code',
                            'Product',
                            'UOM',
                            'Quantity(Kg)',                            
                            ]
            row_index += 1

        #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
            
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

            partner_id = [partner.id for partner in self.partner_ids]

            if self.partner_ids:
                sample_issuance_id = self.env['sample.issuance'].sudo().search([('partner_id','in',partner_id)])
            else:
                sample_issuance_id = self.env['sample.issuance'].sudo().search([])
            
            if (not sample_issuance_id):
                raise Warning(_('Records Not Found'))

            if sample_issuance_id:

                count = 0        
                for rec in sample_issuance_id:
                    new_index = row_index

                    if rec:
                        issuance_lines = rec.sample_issuance_line_one2many.sudo().search([
                                ('sample_issuance_id','=',rec.id),
                                # ('sample_requisition_id','=',False),
                                ('dateordered','>=',self.date_from),
                                ('dateordered','<=',self.date_to)])

                        filtered_list3 = {}
                        filtered_list = []

                        if issuance_lines:

                            count +=1
                            worksheet.write(row_index, 0,count, base_style_gray )
                            worksheet.write(row_index, 1,rec.name  or '',  base_style_gray )
                            worksheet.write(row_index, 2,rec.partner_id.bp_code  or '',  base_style_gray )
                            worksheet.write(row_index, 3,rec.partner_id.name or '',  base_style_gray )
                            worksheet.write(row_index, 4,rec.partner_id.state_id.name or '',  base_style_gray )

                            for record2 in issuance_lines:
                                filtered_list.append(record2.product_id.id)

                            filtered_list3 = dict(Counter(filtered_list))

                            vals = []
                            product_id = ''
                            for product_id, value in filtered_list3.iteritems():
                                new_quant = 0
                                new_list =[]


                                for rec in issuance_lines:
                                    if int(product_id) == int(rec.product_id.id):
                                        if value > 1:
                                            new_quant += rec.quantity
                                        else:
                                            new_quant = rec.quantity

                                new_list = (new_quant)
                                

                                vals.append((product_id,new_list))

                            for rem in vals:
                                product_rec = self.env['product.product'].sudo().search([('id','=',rem[0])])
                            
                                worksheet.write(row_index, 5,product_rec.value or '',  base_style_yellow )
                                worksheet.write(row_index, 6,product_rec.name or '',  base_style_yellow )
                                worksheet.write(row_index, 7,product_rec.uom_id.name or '',  base_style_yellow )
                                worksheet.write(row_index, 8,rem[1] or '',  base_style_yellow )

                                row_index += 1

                            # row_index += 1


            row_index +=1
            workbook.save(fp)


        out = base64.encodestring(fp.getvalue())
        self.write({'state': 'get','report': out,'name':rep_name+'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new',
        }
