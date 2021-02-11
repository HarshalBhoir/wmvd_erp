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


class sampling_details_report(models.TransientModel):
    _name = 'sampling.details.report'
    _description = "sampling Details Report"


    name = fields.Char(string="samplingDetailsReport", compute="_get_name")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    user_ids = fields.Many2many('res.users', 'sampling_details_report_res_user_rel', string='Users')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    partner_id = fields.Many2one('res.partner',string="Distributor / Retailer" )

  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True
    
    @api.depends('date_from','date_to')
    @api.multi
    def _get_name(self):
        rep_name = "sampling_Details_Report"
        if self.date_from and self.date_to and  not self.name:
            date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            if self.date_from == self.date_to:
                rep_name = "Sampling Details Report(%s).xls" % (date_from,)
            else:
                rep_name = "Sampling Details Report(%s|%s).xls" % (date_from, date_to)
        self.name = rep_name

    @api.multi
    def print_report(self):
        
        self.ensure_one()
        status = ''
        # self.sudo().unlink()
        if self.date_from and self.date_to:
        # if not self.attachment_id:

            # file_name = self.name + '.xls'
            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet('Sampling Details')
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1; borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
            base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
            base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
            base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')
            
            worksheet.write_merge(0, 1, 0, 16, self.name ,main_style)
            row_index = 2
            
            worksheet.col(0).width = 3000
            worksheet.col(1).width = 4000
            worksheet.col(2).width = 4000
            worksheet.col(3).width = 8000
            worksheet.col(4).width = 12000
            worksheet.col(5).width = 20000
            worksheet.col(6).width = 4000
            worksheet.col(7).width = 4000
            worksheet.col(8).width = 8000
            worksheet.col(9).width = 8000
            worksheet.col(10).width = 8000
            worksheet.col(11).width = 18000
            worksheet.col(12).width = 18000
            worksheet.col(13).width = 18000
            worksheet.col(14).width = 18000
            worksheet.col(15).width = 8000
            worksheet.col(16).width = 8000
            # worksheet.col(17).width = 4000
            # worksheet.col(18).width = 4000
            # worksheet.col(19).width = 6000
            # worksheet.col(20).width = 4000
            # worksheet.col(21).width = 8000
            # worksheet.col(22).width = 8000

            
            # Headers
            header_fields = [
                            'Sr.No',
                            'Sample No',
                            'Partner Code',
                            'Distributer / Retailer',

                            'Dateordered',
                            'Documentno',
                            'Product Code',
                            'Product',
                            'UOM',
                            'Quantity(Kg)',
                            'Grandtotal',
                            'Deliveryadd',
                            'User',
                            'Business Partner',
                            
                            ]
            row_index += 1
            
        #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
            
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

            # user_id = [user.id for user in self.user_ids]


            if self.partner_id:
                sample_issuance_id = self.env['sample.issuance'].sudo().search([
                        ('partner_id','=',self.partner_id.id),
                        # ('dateordered','>=',self.date_from),
                        # ('dateordered','<=',self.date_to)
                        ])

            else:
                sample_issuance_id = self.env['sample.issuance'].sudo().search([
                        # ('dateordered','>=',self.date_from),
                        # ('dateordered','<=',self.date_to)
                        ])



            print "lllllllllllllllllllllllllllllllllllllllllllllllllllllll" , sample_issuance_id

            # print erroror

            
            if (not sample_issuance_id):
                raise Warning(_('Records Not Found'))

            if sample_issuance_id:

                count = 0        
                for rec in sample_issuance_id:
                    po_date = ''
                    new_index = row_index

                    if rec:
                        # employee_ids = self.env['hr.employee'].sudo().search([
                        #     ('user_id','=',meeting_id.user_id.id),'|',('active','=',False),('active','=',True)])
                        if rec.sample_issuance_line_one2many:


                            count +=1
                            worksheet.write(row_index, 0,count, base_style )
                            worksheet.write(row_index, 1,rec.name  or '',  base_style )
                            worksheet.write(row_index, 2,rec.partner_id.bp_code  or '',  base_style )
                            worksheet.write(row_index, 3,rec.partner_id.name or '',  base_style )

                            # if rec.sample_issuance_line_one2many:
                                # log_detail = rec.activity_log_list_one2many[-1]
                                # for record in rec.sample_issuance_line_one2many:
                            for record in rec.sample_issuance_line_one2many.search([
                                ('sample_issuance_id','=',rec.id),
                                ('dateordered','>=',self.date_from),
                                ('dateordered','<=',self.date_to)]):

                                print "KKKKKKKKKKKKKKKKKKKK" , record.dateordered , self.date_from , self.date_to , type(record.dateordered), type(self.date_from), type(self.date_to)

                                worksheet.write(row_index, 4,record.dateordered or '',  base_style )
                                worksheet.write(row_index, 5,record.documentno or '',  base_style )
                                worksheet.write(row_index, 6,record.product_id.value or '',  base_style )
                                worksheet.write(row_index, 7,record.product_id.name or '',  base_style )
                                worksheet.write(row_index, 8,record.product_id.uom_id.name or '',  base_style )
                                worksheet.write(row_index, 9,record.quantity or '',  base_style )
                                worksheet.write(row_index, 10,record.grandtotal or '',  base_style )
                                worksheet.write(row_index, 11,record.deliveryadd or '',  base_style )
                                worksheet.write(row_index, 12,record.user_id.name or '',  base_style )
                                worksheet.write(row_index, 13,record.user_id.name or '',  base_style )
                        
                                row_index += 1

                            row_index += 1


            row_index +=1
            workbook.save(fp)


        out = base64.encodestring(fp.getvalue())
        self.write({'state': 'get','report': out,'name':'Sampling.xls'})
        # print error
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sampling.details.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            # 'views': [(False, 'form')],
            'target': 'new',
        }
