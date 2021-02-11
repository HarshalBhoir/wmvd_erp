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


class lead_details_report(models.TransientModel):
    _name = 'lead.details.report'
    _description = "lead Details Report"


    name = fields.Char(string="leadDetailsReport", compute="_get_name")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    user_ids = fields.Many2many('res.users', 'lead_details_report_res_user_rel', string='Users')
    lead_id = fields.Many2one('crm.lead', 'Lead')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    export_file = fields.Char(string="Export")
    status = fields.Selection([
            ('first_order','First-Order'),
            ('re_order','Re-Order'),
            ('incorrect','Incorrect'),
            ('lost','Lost'),
            ('open','Open'),
            ('regret','Regret'),
        ], string='Status')


  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True
    
    @api.depends('date_from','date_to')
    @api.multi
    def _get_name(self):
        rep_name = "Lead_Details_Report"
        if self.date_from and self.date_to and  not self.name:
            date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            if self.date_from == self.date_to:
                rep_name = "Lead Details Report(%s)" % (date_from,)
            else:
                rep_name = "Lead Details Report(%s|%s)" % (date_from, date_to)
        self.name = rep_name


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
                workbook = xlwt.Workbook(encoding='utf-8')
                worksheet = workbook.add_sheet('Lead Details')
                fp = StringIO()
                
                main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
                sp_style = xlwt.easyxf('font: bold on, height 350;')
                header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
                base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
                base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')
                
                worksheet.write_merge(0, 1, 0, 27, self.name ,main_style)
                row_index = 2
                
                worksheet.col(0).width = 3000
                worksheet.col(1).width = 6000
                worksheet.col(2).width = 6000
                worksheet.col(3).width = 6000
                worksheet.col(4).width = 4000
                worksheet.col(5).width = 4000
                worksheet.col(6).width = 12000
                worksheet.col(7).width = 8000
                worksheet.col(8).width = 8000
                worksheet.col(9).width = 8000
                worksheet.col(10).width = 6000
                worksheet.col(11).width = 6000
                worksheet.col(12).width = 8000
                worksheet.col(13).width = 8000
                worksheet.col(14).width = 18000
                worksheet.col(15).width = 18000
                worksheet.col(16).width = 6000
                worksheet.col(17).width = 12000
                worksheet.col(18).width = 18000
                worksheet.col(19).width = 18000
                worksheet.col(20).width = 6000
                worksheet.col(21).width = 6000
                worksheet.col(22).width = 6000
                worksheet.col(23).width = 4000
                worksheet.col(24).width = 8000
                worksheet.col(25).width = 12000
                worksheet.col(26).width = 4000
                worksheet.col(27).width = 8000

                
                # Headers
                header_fields = ['Sr.No','Source','Enquiry Type','Enquiry Date','Month','Zone','Company Name','Sales Representative','Contact Name',
                'Job Position','Mobile No.','Phone','Email ID','Group','Product Info','Address','Log Create Date','Sales Log','Sales Description',
                'Ho Description','Status','Next Follow Up Date','Closed Date','Month','Delay Reason','Order Details','Quantity (Kg)','Business Generated']
                row_index += 1
                
            #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
                
                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1

                user_id = [user.id for user in self.user_ids]

                if self.lead_id and not self.user_ids:
                    lead_ids = self.env['crm.lead'].sudo().search([('id','=',self.lead_id.id),('create_date','>=',self.date_from),
                        ('create_date','<=',self.date_to),'|',('active','=',False),('active','=',True)])
                elif not self.lead_id and self.user_ids:
                    lead_ids = self.env['crm.lead'].sudo().search([('user_id','in',user_id),('create_date','>=',self.date_from),
                        ('create_date','<=',self.date_to),'|',('active','=',False),('active','=',True)])
                elif not self.lead_id and not self.user_ids:
                    print "jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj"
                    lead_ids = self.env['crm.lead'].sudo().search([('create_date','>=',self.date_from),('create_date','<=',self.date_to)
                        ,'|',('active','=',False),('active','=',True)])

                if self.status:
                    print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk"
                    lead_ids = lead_ids.sudo().search([('status','=',self.status)])





                
                if (not lead_ids):
                    raise Warning(_('Record Not Found'))

                if lead_ids:

                    count = 0
                    log_detail = product_name = ''
                    for lead_id in lead_ids:
                        new_index = row_index

                        if lead_id:
                            log_detail = product_name = handledby_name = assistedby_name= ''
                    
                            zone = project_source = project_type = status = ownership_type = ''
                            print "lllllllllllllllllllllllllllllllll" , lead_id.zone

                            if lead_id.zone:
                                if lead_id.zone == 'north':
                                    zone = 'North'
                                if lead_id.zone == 'east':
                                    zone = 'East'
                                if lead_id.zone == 'central':
                                    zone = 'Central'
                                if lead_id.zone == 'west':
                                    zone = 'West'
                                if lead_id.zone == 'south':
                                    zone = 'South'
                                if lead_id.zone == 'export':
                                    zone = 'Export'


                            if lead_id.project_source:
                                if lead_id.project_source == 'ho':
                                    project_source = 'HO'
                                if lead_id.project_source == 'self_visit':
                                    project_source = 'Self-Visit'

                            if lead_id.project_type:
                                if lead_id.project_type == 'commercial':
                                    project_type = 'Commercial'
                                if lead_id.project_type == 'residential':
                                    project_type = 'Residential'
                                if lead_id.project_type == 'industrial':
                                    project_type = 'Industrial'
                                if lead_id.project_type == 'government':
                                    project_type = 'Government'


                            if lead_id.status:
                                if lead_id.status == 'first_order':
                                    status = 'First-Order'
                                if lead_id.status == 're_order':
                                    status = 'Re-Order'
                                if lead_id.status == 'incorrect':
                                    status = 'Incorrect'
                                if lead_id.status == 'lost':
                                    status = 'Lost'
                                if lead_id.status == 'open':
                                    status = 'Open'
                                if lead_id.status == 'regret':
                                    status = 'Regret'

                            if lead_id.ownership_type:
                                if lead_id.ownership_type == 'government':
                                    ownership_type = 'Government'
                                if lead_id.ownership_type == 'private':
                                    ownership_type = 'Private'
                                if lead_id.ownership_type == 'charitable':
                                    ownership_type = 'Charitable'


                            if  lead_id.product_id:

                                product_ids = [product.name.encode("utf-8") for product in lead_id.product_id]
                                product_name = ",".join([str(x) for x in product_ids])
                            # date_starttime = datetime.strptime(lead_id.start_datetime, "%Y-%m-%d %H:%M:%S") + timedelta(hours=5, minutes=30)
                            # date_start_date = date_starttime.strftime('%d-%m-%Y')
                            # date_start_time = date_starttime.strftime('%H:%M:%S')

                            address = ((lead_id.street + ', ' ) if lead_id.street else '') + ((lead_id.street2  + ', ' ) if lead_id.street2 else '') + \
                                        ((lead_id.city  + ', ' ) if lead_id.city else '') + ((lead_id.state_id.name  + ', ' ) if lead_id.state_id else '') + \
                                        ((lead_id.country_id.name  + ', ' ) if lead_id.country_id else '') + ((lead_id.zip  + ', ' ) if lead_id.zip else '')

                            # if lead_id.activity_log_list_one2many:
                            #     log_detail = lead_id.activity_log_list_one2many[-1]

                            count +=1
                            worksheet.write(row_index, 0,count, base_style )
                            worksheet.write(row_index, 1,lead_id.source_id.name  or '',  base_style )
                            worksheet.write(row_index, 2,lead_id.enquiry_type_id.name  or '',  base_style )
                            worksheet.write(row_index, 3,lead_id.enquiry_date or '',  base_style )
                            worksheet.write(row_index, 4,lead_id.enquiry_month or '',  base_style )
                            worksheet.write(row_index, 5,lead_id.zone or '',  base_style )
                            worksheet.write(row_index, 6,lead_id.partner_name or '',  base_style )
                            worksheet.write(row_index, 7,lead_id.sales_user_id.name or '',  base_style )
                            worksheet.write(row_index, 8,lead_id.contact_name or '',  base_style )
                            worksheet.write(row_index, 9,lead_id.function or '',  base_style )
                            worksheet.write(row_index, 10,lead_id.mobile or '',  base_style )
                            worksheet.write(row_index, 11,lead_id.phone or '',  base_style )
                            worksheet.write(row_index, 12,lead_id.email_from or '',  base_style )
                            worksheet.write(row_index, 13,lead_id.partner_group_id.name or '',  base_style )
                            worksheet.write(row_index, 14,product_name or '',  base_style )
                            worksheet.write(row_index, 15,address or '',  base_style )

                            if lead_id.activity_log_list_one2many:
                                log_detail = lead_id.activity_log_list_one2many[-1]
                            

                                worksheet.write(row_index, 16,log_detail.create_date if log_detail else '',  base_style )
                                worksheet.write(row_index, 17,log_detail.user_id.name if log_detail else '',  base_style )
                                worksheet.write(row_index, 18,log_detail.sale_description if log_detail else '',  base_style )
                                worksheet.write(row_index, 19,log_detail.ho_description if log_detail else '',  base_style )
                                worksheet.write(row_index, 20,log_detail.status if log_detail else '',  base_style )
                                worksheet.write(row_index, 21,log_detail.followup_date if log_detail else '',  base_style )
                                worksheet.write(row_index, 22,log_detail.date_deadline if log_detail else '',  base_style )
                                worksheet.write(row_index, 23,log_detail.closed_month if log_detail else '',  base_style )
                                worksheet.write(row_index, 24,log_detail.delay_reason if log_detail else '',  base_style )
                                worksheet.write(row_index, 25,log_detail.order_details if log_detail else '',  base_style )
                                worksheet.write(row_index, 26,log_detail.quantity if log_detail else '',  base_style )
                                worksheet.write(row_index, 27,log_detail.business_generated if log_detail else '',  base_style )
                            
                            
                            row_index += 1

                row_index +=1
                workbook.save(fp)


            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'export_file':self.name+'.xls'})
            # print error
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'lead.details.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                # 'views': [(False, 'form')],
                'target': 'new',
            }
