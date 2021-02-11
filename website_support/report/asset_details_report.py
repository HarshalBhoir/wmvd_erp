# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta , date
from cStringIO import StringIO
import xlwt
import base64

class asset_details_report(models.TransientModel):
    _name = 'asset.details.report'
    _description = "Asset Details Report"


    name = fields.Char(string="AssetDetailsReport")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    employee_ids = fields.Many2many('hr.employee', 'assets_details_report_hr_employee_rel', string='Employee')
    repname = fields.Char(string="AssetDetailsReport")
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    condition = fields.Selection([('Employee', 'Employee'), 
                                ('Department', 'Department'), 
                                ('Location', 'Location'), 
                                ('Company', 'Company')], string='Condition')
    current_loc_id = fields.Many2one('bt.asset.location', string="Location")
    company_id = fields.Many2one('res.company', string="Company")
    department_id = fields.Many2one('hr.department', string="Department")

  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True
    

    @api.multi
    def print_report(self):
        self.ensure_one()
        if not self.attachment_id:
            order_list = []
            second_heading = ''
            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet('Asset Details')
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; \
            borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center, vertical center; \
                borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
            base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
            base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
            base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color yellow;')
            base_style_green = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color green;')
            base_style_orange = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color orange;')

            asset_ids = self.env['bt.asset'].sudo().search([
                            ('purchase_date','>=',self.date_from),
                            ('purchase_date','<=',self.date_to)],order="company_id , department_id , current_loc_id  asc")

            if not self.condition:
                second_heading = 'ALL Data'

            elif self.condition == 'Employee':
                employee_id = [employee.id for employee in self.employee_ids]
                second_heading = 'Employee'
                asset_ids = asset_ids.sudo().search([('name','in',employee_id)])

            elif self.condition == 'Department':
                second_heading = self.department_id.name
                asset_ids = asset_ids.sudo().search([('department_id','=',self.department_id.id)])

            elif self.condition == 'Company':
                second_heading = self.company_id.name
                asset_ids = asset_ids.sudo().search([('company_id','=',self.company_id.id)])
                
            elif self.condition == 'Location':
                second_heading = self.current_loc_id.name 
                asset_ids = asset_ids.sudo().search([('current_loc_id','=',self.current_loc_id.id)])

            rep_name = ''
            date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            if self.date_from == self.date_to:
                rep_name = "Assets Details Report(%s) - %s" % (date_from,second_heading)
            else:
                rep_name = "Assets Details Report(%s|%s) - %s"  % (date_from, date_to,second_heading)
            self.name = rep_name

            
            worksheet.write_merge(0, 1, 0, 12, self.name ,main_style)
            row_index = 2
            
            worksheet.col(0).width = 2000
            worksheet.col(1).width = 12000
            worksheet.col(2).width = 8000
            worksheet.col(3).width = 8000
            worksheet.col(4).width = 8000
            worksheet.col(5).width = 8000
            worksheet.col(6).width = 6000
            worksheet.col(7).width = 6000
            worksheet.col(8).width = 6000
            worksheet.col(9).width = 4000
            worksheet.col(10).width = 8000
            worksheet.col(11).width = 8000
            worksheet.col(12).width = 4000
            
            # Headers
            header_fields = ['S.No','User Name','Asset Code','Asset Type','Brand & Model','Serial Number',
            'Physical Location','Department','Company','Purchase Date','Component','Model/Capacity','State']
            row_index += 1
         
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

           
            if (not asset_ids):
                raise Warning(_('Record Not Found'))


            count = 0        
            for asset_id in asset_ids:
                if asset_id:
                    
                    count +=1
                    worksheet.write(row_index, 0,count, base_style_yellow )
                    worksheet.write(row_index, 1,asset_id.asset_name,  base_style_yellow )
                    worksheet.write(row_index, 2,asset_id.asset_code,  base_style_yellow )
                    worksheet.write(row_index, 3,asset_id.category_id.name or '',  base_style_yellow )
                    worksheet.write(row_index, 4,asset_id.model_name or '',  base_style_yellow )
                    worksheet.write(row_index, 5,asset_id.serial_no or '',  base_style_yellow )
                    worksheet.write(row_index, 6,asset_id.current_loc_id.name or '',  base_style_yellow )
                    worksheet.write(row_index, 7,asset_id.department_id.name or '',  base_style_yellow )
                    worksheet.write(row_index, 8,asset_id.company_id.name or '',  base_style_yellow )
                    worksheet.write(row_index, 9,asset_id.purchase_date or '',  base_style_yellow )
                    worksheet.write(row_index, 10,'',  base_style_yellow )
                    worksheet.write(row_index, 11,'',  base_style_yellow )
                    worksheet.write(row_index, 12,'',  base_style_yellow )
                    
                    row_index += 1

                    for line in asset_id.component_ids:
                        worksheet.write(row_index, 0,'' )
                        worksheet.write(row_index, 10,line.name.name or '', base_style)
                        worksheet.write(row_index, 11,line.model_name, base_style)
                        worksheet.write(row_index, 12,line.state, base_style)

                        row_index += 1
                    row_index += 1

            row_index +=1
            workbook.save(fp)


            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'repname':self.name+'.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'asset.details.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }