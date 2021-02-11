from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
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


class invoice_delivery_report(models.TransientModel):
    _name = 'invoice.delivery.report'
    _description = "Invoice Delivery Report"


    name = fields.Char(string="InvoiceDeliveryReport")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    export_file = fields.Char(string="Export")
    status = fields.Selection([
                            ('draft', 'Draft'),
                            ('approved', 'Approved'),
                            ('reverted', 'Reverted')], 
                            string='Status' , default='draft')


  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True


    @api.multi
    def print_report(self):
        
        self.ensure_one()
        status = ''
        # self.sudo().unlink()
        if self.date_from and self.date_to:
            if not self.attachment_id:
                pending_order_ids = []
                order_list = []
                # file_name = self.name + '.xls'


                rep_name = "Invoice_Delivery_Report"
                if self.date_from and self.date_to and  not self.name:
                    date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                    date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                    if self.date_from == self.date_to:
                        rep_name = "Invoice Delivery Details Report(%s)" % (date_from,)
                    else:
                        rep_name = "Invoice Delivery Details Report(%s|%s)" % (date_from, date_to)
                self.name = rep_name


                workbook = xlwt.Workbook(encoding='utf-8')
                worksheet = workbook.add_sheet('Invoice Delivery Details')
                fp = StringIO()
                
                main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
                sp_style = xlwt.easyxf('font: bold on, height 350;')
                header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
                base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
                base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')
                
                worksheet.write_merge(0, 1, 0, 20, self.name ,main_style)
                row_index = 2
                
                worksheet.col(0).width = 3000
                worksheet.col(1).width = 9000
                worksheet.col(2).width = 6000
                worksheet.col(3).width = 6000
                worksheet.col(4).width = 9000
                worksheet.col(5).width = 4000
                worksheet.col(6).width = 2000
                worksheet.col(7).width = 4000
                worksheet.col(8).width = 4000
                worksheet.col(9).width = 4000
                worksheet.col(10).width = 6000
                worksheet.col(11).width = 14000
                worksheet.col(12).width = 6000
                worksheet.col(13).width = 10000
                worksheet.col(14).width = 4000
                worksheet.col(15).width = 8000
                worksheet.col(16).width = 9000
                worksheet.col(17).width = 4000
                worksheet.col(18).width = 4000
                worksheet.col(19).width = 6000
                worksheet.col(20).width = 8000


                
                # Headers
                header_fields = ['Sr.No','Partner','Documentno','Mobile No','Email','Delayed Date','Delay','Lr No','Lr Date',
                'Po Date','Time RML','Delivery Addr','Vhcl No','Trpt Name','Status','Executive','Exec Mail', 'Reverted Date', 
                'Invoice Date' , 'State', 'Business Division']
                row_index += 1
                
            #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
                
                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1

                # user_id = [user.id for user in self.user_ids]

                if self.status :
                    line_ids = self.env['logistic.trail.line'].sudo().search([('condition' ,'=','schedular'),
                                                                                ('dateacct','>=',self.date_from),
                                                                                ('dateacct','<=',self.date_to),
                                                                                ('state','=',self.status)])
                else :
                    line_ids = self.env['logistic.trail.line'].sudo().search([
                                                                                ('condition' ,'=','schedular'),
                                                                                ('dateacct','>=',self.date_from),
                                                                                ('dateacct','<=',self.date_to)])

                
                if (not line_ids):
                    raise Warning(_('Record Not Found'))

                if line_ids:

                    count = 0
                    log_detail = product_name = ''
                    for line_id in line_ids:
                        new_index = row_index

                        if line_id:

                            if line_id.state == 'draft':
                                state = 'Draft'
                            elif line_id.state == 'approved':
                                state = 'Sent To Customer'
                            if line_id.state == 'reverted':
                                state = 'Reverted By Customer'
                   
                            count +=1
                            worksheet.write(row_index, 0,count, base_style )
                            worksheet.write(row_index, 1,line_id.c_bpartner_id  or '',  base_style )
                            worksheet.write(row_index, 2,line_id.documentno  or '',  base_style )
                            worksheet.write(row_index, 3,line_id.mobile or '',  base_style )
                            worksheet.write(row_index, 4,line_id.email or '',  base_style )
                            worksheet.write(row_index, 5,line_id.delayed_date or '',  base_style )
                            worksheet.write(row_index, 6,line_id.delay or '',  base_style )
                            worksheet.write(row_index, 7,line_id.lr_no or '',  base_style )
                            worksheet.write(row_index, 8,line_id.lr_date or '',  base_style )
                            worksheet.write(row_index, 9,line_id.podate or '',  base_style )
                            worksheet.write(row_index, 10,line_id.time_rml or '',  base_style )
                            worksheet.write(row_index, 11,line_id.deliveryadd or '',  base_style )
                            worksheet.write(row_index, 12,line_id.vhcl_no or '',  base_style )
                            worksheet.write(row_index, 13,line_id.trpt_name or '',  base_style )
                            worksheet.write(row_index, 14,state or '',  base_style )
                            worksheet.write(row_index, 15,line_id.sales_exec or '',  base_style )
                            worksheet.write(row_index, 16,line_id.sales_email or '',  base_style )
                            worksheet.write(row_index, 17,line_id.date_reverted or '',  base_style )
                            worksheet.write(row_index, 18,line_id.dateacct or '',  base_style )
                            worksheet.write(row_index, 19,line_id.state_region or '',  base_style )
                            worksheet.write(row_index, 20,line_id.business_division or '',  base_style )

                            row_index += 1

                row_index +=1
                workbook.save(fp)


            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'export_file':self.name+'.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'invoice.delivery.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }
