from openerp import models, fields, api, _, tools
from openerp.exceptions import UserError, Warning, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

import datetime
from datetime import datetime, timedelta , date
import time
from dateutil import relativedelta
from cStringIO import StringIO
import xlwt
import re
import base64
import pytz

import json
import odoo.http as http
from odoo.http import request
from odoo.addons.web.controllers.main import ExcelExport


class barcode_details_report(models.TransientModel):
    _name = 'barcode.details.report'
    _description = "QR Code Details Report"
    
    name = fields.Char(string="QR Code Detail Report")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    # user_id = fields.Many2one( 'res.users', string="User")
    # user_ids = fields.Many2many('res.users', 'meetings_details_report_res_user_rel', string='Users')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')


    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True


    @api.multi
    def print_report(self):
        
        self.ensure_one()
        if self.date_from and self.date_to:
            if not self.attachment_id:
                pending_order_ids = []
                order_list = []
                # file_name = self.name + '.xls'
                workbook = xlwt.Workbook(encoding='utf-8')
                worksheet = workbook.add_sheet('QR Code Details')
                fp = StringIO()
                
                main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz center; borders: bottom thick, top thick, left thick, right thick')
                sp_style = xlwt.easyxf('font: bold on, height 350;')
                header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
                base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
                base_bold_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; font: bold on')
                base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')
                
                worksheet.write_merge(0, 1, 0, 5, 'QR Code Detail Report' ,main_style)
                barcode_line_ids = self.env['barcode.marketing.line'].sudo().search([])
                barcode_line_checked_ids = self.env['barcode.marketing.line'].sudo().search([('flag','=',True)])

                worksheet.write_merge(2, 3, 0, 1, "QR Code Generated" ,header_style)
                worksheet.write_merge(4, 5, 0, 1, len(barcode_line_ids) ,header_style)

                worksheet.write_merge(2, 3, 2, 3, "QR Code Checked" ,header_style)
                worksheet.write_merge(4, 5, 2, 3, len(barcode_line_checked_ids) ,header_style)

                worksheet.write_merge(2, 3, 4, 5, "QR Code Remaining" ,header_style)
                worksheet.write_merge(4, 5, 4, 5, (len(barcode_line_ids) - len(barcode_line_checked_ids)) ,header_style)
                row_index = 6
                
                worksheet.col(0).width = 3000
                worksheet.col(1).width = 16000
                worksheet.col(2).width = 4000
                worksheet.col(3).width = 4000
                worksheet.col(4).width = 4000
                worksheet.col(5).width = 4000
                worksheet.col(6).width = 4000
                worksheet.col(7).width = 8000
                
                # Headers
                header_fields = ['Sr.No','Partner','Scanned','Rejected','Non QR','Coupon Worth','Total Coupons','Total Amount Payable']
                row_index += 1
                                
                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1


                barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([('date','>=',self.date_from),
                	('date','<=',self.date_to),('state','!=','draft')])
                if (not barcode_check_ids):
                    raise Warning(_('Record Not Found'))

                if barcode_check_ids:
                    count = 0        
                    for barcode_check_id in barcode_check_ids:
                        new_index = row_index
                        if barcode_check_id:
                            total_coupon = (barcode_check_id.count_accepted if barcode_check_id.count_accepted else 0 ) + \
                            (barcode_check_id.manual_count if barcode_check_id.manual_count else 0 )

                            count +=1
                            worksheet.write(row_index, 0,count, base_style)
                            worksheet.write(row_index, 1,barcode_check_id.partner_id.name, base_style)
                            worksheet.write(row_index, 2,barcode_check_id.count_accepted  or '', base_style)
                            worksheet.write(row_index, 3,barcode_check_id.count_rejected or '', base_style)
                            worksheet.write(row_index, 4,barcode_check_id.manual_count or '', base_style)
                            worksheet.write(row_index, 5,barcode_check_id.amount or '', base_style)
                            worksheet.write(row_index, 6,total_coupon or '', base_style)
                            worksheet.write(row_index, 7,barcode_check_id.total_amount or '', base_bold_style)
                            
                            row_index += 1

                row_index +=1
                workbook.save(fp)


            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'name':'QR Code Details (' + self.date_from + ' / '+ self.date_to  + ').xls'})
            # print error
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'barcode.details.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                # 'views': [(False, 'form')],
                'target': 'new',
            }