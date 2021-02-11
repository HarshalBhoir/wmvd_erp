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


class project_details_report(models.TransientModel):
    _name = 'project.details.report'
    _description = "Project Details Report"


    name = fields.Char(string="ProjectDetailsReport", compute="_get_name")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    user_ids = fields.Many2many('res.users', string='Users')
    lead_id = fields.Many2one('crm.lead', 'Lead')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
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
        rep_name = "Project_Details_Report"
        if self.date_from and self.date_to and  not self.name:
            date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            if self.date_from == self.date_to:
                rep_name = "Project Details Report(%s)" % (date_from,)
            else:
                rep_name = "Project Details Report(%s-%s)" % (date_from, date_to)
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
                worksheet.col(4).width = 6000
                worksheet.col(5).width = 6000
                worksheet.col(6).width = 6000
                worksheet.col(7).width = 8000
                worksheet.col(8).width = 12000
                worksheet.col(9).width = 12000
                worksheet.col(10).width = 8000
                worksheet.col(11).width = 8000
                worksheet.col(12).width = 8000
                worksheet.col(13).width = 18000
                worksheet.col(14).width = 18000
                worksheet.col(15).width = 6000
                worksheet.col(16).width = 18000
                worksheet.col(17).width = 8000
                worksheet.col(18).width = 20000
                worksheet.col(19).width = 8000
                worksheet.col(20).width = 18000
                worksheet.col(21).width = 18000
                worksheet.col(22).width = 6000
                worksheet.col(23).width = 18000
                worksheet.col(24).width = 18000
                worksheet.col(25).width = 16000
                worksheet.col(26).width = 4000
                worksheet.col(27).width = 8000

                
                # Headers
                header_fields = ['Sr.No','Start Date','Close Date','Zone','State','City','Project Source','Type of Project','Project Name','Company Name',
                'Contact Person','Contact Number','Email Id','Handled By','Assisted By','Status','Site Address','Type of Ownership','Site Details',
                'Site Status','Product Offered','Corporate Address','RERA Number','Sales Description','HO Description','Order Details','Quantity (Kgs)','Business Generated']
                row_index += 1
                
            #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
                
                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1

                user_id = [user.id for user in self.user_ids]

                if self.lead_id and not self.user_ids:
                    lead_ids = self.env['crm.lead'].sudo().search([('isproject','=',True),('id','=',self.lead_id.id),('create_date','>=',self.date_from),
                        ('create_date','<=',self.date_to),'|',('active','=',False),('active','=',True)])
                elif not self.lead_id and self.user_ids:
                    lead_ids = self.env['crm.lead'].sudo().search([('isproject','=',True),('user_id','in',user_id),('create_date','>=',self.date_from),
                        ('create_date','<=',self.date_to),'|',('active','=',False),('active','=',True)])
                elif not self.lead_id and not self.user_ids:
                    lead_ids = self.env['crm.lead'].sudo().search([('isproject','=',True),('create_date','>=',self.date_from),('create_date','<=',self.date_to)
                        ,'|',('active','=',False),('active','=',True)])


                
                if (not lead_ids):
                    raise Warning(_('Record Not Found'))

                if lead_ids:

                    count = 0
                    
                    for lead_id in lead_ids:
                        new_index = row_index

                        if lead_id:
                            log_detail = product_name = handledby_name = assistedby_name= ''
                    
                            zone = project_source = project_type = status = ownership_type = ''

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


                            if  lead_id.handledby_ids:
                                handledby_ids = [handledby_id.name.encode("utf-8") for handledby_id in lead_id.handledby_ids]
                                handledby_name = ",".join([str(y) for y in handledby_ids])

                            if  lead_id.assistedby_ids:
                                assistedby_ids = [assistedby_id.name.encode("utf-8") for assistedby_id in lead_id.assistedby_ids]
                                assistedby_name = ",".join([str(z) for z in assistedby_ids])
                            # date_starttime = datetime.strptime(lead_id.start_datetime, "%Y-%m-%d %H:%M:%S") + timedelta(hours=5, minutes=30)
                            # date_start_date = date_starttime.strftime('%d-%m-%Y')
                            # date_start_time = date_starttime.strftime('%H:%M:%S')

                            address = ((lead_id.street + ', ' ) if lead_id.street else '') + ((lead_id.street2  + ', ' ) if lead_id.street2 else '') + \
                                        ((lead_id.city  + ', ' ) if lead_id.city else '') + ((lead_id.state_id.name  + ', ' ) if lead_id.state_id else '') + \
                                        ((lead_id.country_id.name  + ', ' ) if lead_id.country_id else '') + ((lead_id.zip  + ', ' ) if lead_id.zip else '')

                            site_address = ((lead_id.site_street + ', ' ) if lead_id.site_street else '') + ((lead_id.site_street2  + ', ' ) if lead_id.site_street2 else '') + \
                                        ((lead_id.site_city  + ', ' ) if lead_id.site_city else '') + ((lead_id.site_state_id.name  + ', ' ) if lead_id.site_state_id else '') + \
                                        ((lead_id.site_country_id.name  + ', ' ) if lead_id.site_country_id else '') + ((lead_id.site_zip  + ', ' ) if lead_id.site_zip else '')

                            # if lead_id.activity_log_list_one2many:
                            #     log_detail = lead_id.activity_log_list_one2many[-1]

                            count +=1
                            worksheet.write(row_index, 0,count, base_style )
                            worksheet.write(row_index, 1,lead_id.mail_date  or '',  base_style )
                            worksheet.write(row_index, 2,lead_id.date_deadline  or '',  base_style )
                            worksheet.write(row_index, 3,zone or '',  base_style )
                            worksheet.write(row_index, 4,lead_id.state_id.name or '',  base_style )
                            worksheet.write(row_index, 5,lead_id.city or '',  base_style )
                            worksheet.write(row_index, 6,project_source or '',  base_style )
                            worksheet.write(row_index, 7,project_type or '',  base_style )
                            worksheet.write(row_index, 8,lead_id.name or '',  base_style )
                            worksheet.write(row_index, 9,lead_id.partner_name or '',  base_style )
                            worksheet.write(row_index, 10,lead_id.contact_name or '',  base_style )
                            worksheet.write(row_index, 11,lead_id.phone or '',  base_style )
                            worksheet.write(row_index, 12,lead_id.email_from or '',  base_style )
                            worksheet.write(row_index, 13,handledby_name or '',  base_style )
                            worksheet.write(row_index, 14,assistedby_name or '',  base_style )
                            worksheet.write(row_index, 15,status or '',  base_style )
                            worksheet.write(row_index, 16,site_address or '',  base_style )
                            worksheet.write(row_index, 17,ownership_type or '',  base_style )
                            worksheet.write(row_index, 18,lead_id.site_details or '',  base_style )
                            worksheet.write(row_index, 19,lead_id.site_status or '',  base_style )
                            worksheet.write(row_index, 20,product_name or '' ,  base_style )
                            worksheet.write(row_index, 21,address or '',  base_style )
                            worksheet.write(row_index, 22,lead_id.rera_no or '',  base_style )

                            if lead_id.activity_log_list_one2many:
                                log_detail = lead_id.activity_log_list_one2many[-1]
                            

                                worksheet.write(row_index, 23,log_detail.sale_description if log_detail else '',  base_style )
                                worksheet.write(row_index, 24,log_detail.ho_description if log_detail else '',  base_style )
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
                'res_model': 'project.details.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                # 'views': [(False, 'form')],
                'target': 'new',
            }
