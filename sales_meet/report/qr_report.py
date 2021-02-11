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


class qr_details_report(models.TransientModel):
    _name = 'qr.details.report'
    _description = "QR Code Details Report"

    name = fields.Char(string="QR Scan Detail Report")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    # user_id = fields.Many2one( 'res.users', string="User")
    partner_ids = fields.Many2many('res.partner',  string="Partners")
    user_ids = fields.Many2many('res.users', string='Users')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    check_state = fields.Selection([('draft', 'Draft'),
                                ('create', 'Created'),
                                ('update', 'Updated'),
                                ('reject', 'Rejected'),
                                ('cn_raised', 'CN Raised'),])


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

                worksheet.write_merge(0, 1, 0, 5, 'Coupon Scan Detail Report (' + self.date_from + ' - '+ self.date_to  + ')' ,main_style)
                row_index = 2
                # barcode_line_ids = self.env['barcode.marketing.line'].sudo().search([])
                # barcode_line_checked_ids = self.env['barcode.marketing.line'].sudo().search([('flag','=',True),('mobile_bool','=',True)])


                worksheet.col(0).width = 2000
                worksheet.col(1).width = 3000
                worksheet.col(2).width = 8000
                worksheet.col(3).width = 4000
                worksheet.col(4).width = 5000
                worksheet.col(5).width = 6000
                worksheet.col(6).width = 6000
                worksheet.col(7).width = 6000
                worksheet.col(8).width = 6000
                worksheet.col(9).width = 3000
                worksheet.col(10).width = 8000
                worksheet.col(11).width = 4000
                worksheet.col(12).width = 4000
                worksheet.col(13).width = 4000

                # Headers
                header_fields = ['Sr.No','Cust Code','Customer','Date','State','Accepted Count',
                'Rejected Count','Duplicated Count', 'Previously Scanned','EMP Code',
                'Salesperson', 'Net Amount', 'Total Amount', 'Status']
                row_index += 1

                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1

                user_id = [user.id for user in self.user_ids]
                partner_id = [partner.id for partner in self.partner_ids]


                if self.user_ids:
                    if self.partner_ids and not self.check_state:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('user_id','in',user_id),
                                                    ('partner_id','in',partner_id)])

                    elif not self.partner_ids and self.check_state:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('user_id','in',user_id),
                                                    ('state','=',self.check_state)])

                    elif not self.partner_ids and not self.check_state:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('user_id','in',user_id)])


                if self.partner_ids:
                    if self.user_ids and not self.check_state:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('user_id','in',user_id),
                                                    ('partner_id','in',partner_id)])

                    elif not self.user_ids and self.check_state:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('partner_id','in',partner_id),
                                                    ('state','=',self.check_state)])

                    elif not self.user_ids and not self.check_state:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('partner_id','in',partner_id)])

                if self.check_state:
                    if not self.user_ids and self.partner_ids:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('state','=',self.check_state),
                                                    ('partner_id','in',partner_id)])

                    elif not self.partner_ids and self.user_ids:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('user_id','in',user_id),
                                                    ('state','=',self.check_state)])

                    elif not self.user_ids and not self.partner_ids:
                        barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True),
                                                    ('state','=',self.check_state)])

                if not self.partner_ids and not self.user_ids and not self.check_state:
                    barcode_check_ids = self.env['barcode.marketing.check'].sudo().search([
                                                    ('date','>=',self.date_from),
                                                    ('date','<=',self.date_to),
                                                    ('mobile_bool','=',True)])



                if (not barcode_check_ids):
                    raise Warning(_('Record Not Found'))


                if barcode_check_ids:
                    count = 0
                    for barcode_check_id in barcode_check_ids:
                        new_index = row_index
                        check_state = False
                        if barcode_check_id:

                            employee_ids = self.env['hr.employee'].sudo().search([
                                ('user_id','=',barcode_check_id.user_id.id),
                                '|',('active','=',False),('active','=',True)])

                            print "dddddddddd" , barcode_check_id.state


                            if barcode_check_id.state == 'draft':
                                check_state = 'Draft'
                            elif barcode_check_id.state == 'create':
                                check_state = 'Created'
                            elif barcode_check_id.state == 'update':
                                check_state = 'Updated'
                            elif barcode_check_id.state == 'reject':
                                check_state = 'Rejected'
                            elif barcode_check_id.state == 'cn_raised':
                                check_state = 'CN Raised'
                            # else:
                            #     check_state = False

                            count +=1
                            worksheet.write(row_index, 0,count, base_style)
                            worksheet.write(row_index, 1,barcode_check_id.partner_id.bp_code, base_style)
                            worksheet.write(row_index, 2,barcode_check_id.partner_id.name  or '', base_style)
                            worksheet.write(row_index, 3,barcode_check_id.date or '', base_style)
                            worksheet.write(row_index, 4,barcode_check_id.partner_id.state_id.name or '', base_style)
                            worksheet.write(row_index, 5,barcode_check_id.count_accepted or '', base_style)
                            worksheet.write(row_index, 6,barcode_check_id.count_rejected or '', base_style)
                            worksheet.write(row_index, 7,barcode_check_id.count_duplicated or '', base_bold_style)

                            worksheet.write(row_index, 8,barcode_check_id.count_previously_scanned or '', base_style)
                            worksheet.write(row_index, 9,employee_ids.emp_id or '', base_style)
                            worksheet.write(row_index, 10,barcode_check_id.user_id.name  or '', base_style)
                            worksheet.write(row_index, 11,barcode_check_id.net_amount or '', base_style)
                            worksheet.write(row_index, 12,barcode_check_id.total_amount or '', base_style)
                            worksheet.write(row_index, 13,check_state or '', base_style)

                            row_index += 1

                row_index +=1
                workbook.save(fp)


            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'name':'QR Code Details (' + self.date_from + ' - '+ self.date_to  + ').xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'qr.details.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                # 'views': [(False, 'form')],
                'target': 'new',
            }
