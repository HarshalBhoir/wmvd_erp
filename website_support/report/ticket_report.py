# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta , date
import time
from cStringIO import StringIO
import xlwt
import base64

class ticket_report(models.TransientModel):
    _name = 'ticket.report'
    _description = "Ticket Report"

    name = fields.Char(string="Ticket Report")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    category = fields.Many2one('website.support.ticket.categories', string="Category")
  
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

                rep_name = "Ticket_Report"
                if self.date_from and self.date_to and  not self.name:
                    date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                    date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                    if self.date_from == self.date_to:
                        rep_name = "Ticket Report(%s)" % (date_from,)
                    else:
                        rep_name = "Ticket Report(%s|%s)" % (date_from, date_to)
                self.name = rep_name + '.xls'

                workbook = xlwt.Workbook(encoding='utf-8')
                worksheet = workbook.add_sheet(rep_name)
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
                    pattern: pattern fine_dots, fore_color white, back_color light_green;')

                worksheet.write_merge(0, 1, 0, 8, rep_name ,main_style)
                row_index = 2

                worksheet.row(3).height = 700
                
                worksheet.col(0).width = 2000
                worksheet.col(1).width = 6000
                worksheet.col(2).width = 12000
                worksheet.col(3).width = 20000
                worksheet.col(4).width = 20000
                worksheet.col(5).width = 6000
                worksheet.col(6).width = 4000
                worksheet.col(7).width = 12000
                worksheet.col(8).width = 12000
                worksheet.col(9).width = 12000
                worksheet.col(10).width = 18000
                worksheet.col(11).width = 5000
                worksheet.col(12).width = 5000
                worksheet.col(13).width = 9000
                worksheet.col(14).width = 6000
                worksheet.col(15).width = 6000
                worksheet.col(16).width = 6000
                worksheet.col(17).width = 4000
                worksheet.col(18).width = 5000
                worksheet.col(19).width = 5000
                worksheet.col(20).width = 8000
                worksheet.col(21).width = 6000
                worksheet.col(22).width = 6000
                worksheet.col(23).width = 8000
                
                # Headers
                header_fields = ['Sr.No',
                                'Date',
                                'Created By',
                                'Subject',
                                'Description',
                                'Category',
                                'Priority',
                                'Requistion',
                                'Assigned User',
                                'Delegated User',
                                'Close Comment',
                                'State',
                                'Stage',
                                'Company',
                                'Initiated on',
                                'Target Closure Date',
                                'Close Time',
                                'Time to close (seconds)',
                                'Estimated Hours',
                                'Actual Hours',
                                'Asset',
                                'Approx Cost',
                                'Project']
                row_index += 1
                
                
                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1

                ticket_ids = self.env['website.support.ticket'].sudo().search([
                            ('create_date','>=',self.date_from),
                            ('create_date','<=',self.date_to)])

                if self.user_id:
                    ticket_ids = ticket_ids.sudo().search([('create_user_id','=',self.user_id.id)])

                if self.category:
                    ticket_ids = ticket_ids.sudo().search([('category','=',self.category.id)])
              
                if (not ticket_ids):
                    raise Warning(_('Record Not Found'))

                if ticket_ids:
                    count = 0
                    for ticket_id in ticket_ids:
                        if ticket_id:
                            condition = base_style_green if ticket_id.status =='completed' else base_style 

                            count +=1
                            worksheet.write(row_index, 0,count, condition)
                            worksheet.write(row_index, 1,ticket_id.create_date,  condition)
                            worksheet.write(row_index, 2,ticket_id.create_user_id.name,  condition)
                            worksheet.write(row_index, 3,ticket_id.subject or '',  condition)
                            worksheet.write(row_index, 4,ticket_id.description or '',  condition)
                            worksheet.write(row_index, 5,ticket_id.category.name or '',  condition)
                            worksheet.write(row_index, 6,ticket_id.priority_id.name or '',  condition)
                            worksheet.write(row_index, 7,ticket_id.requisition_id.name or '',  condition)
                            worksheet.write(row_index, 8,ticket_id.user_id.name or '',  condition)
                            worksheet.write(row_index, 9,ticket_id.closed_by_id.name or '',  condition)
                            worksheet.write(row_index, 10,ticket_id.close_comment or '',  condition)
                            worksheet.write(row_index, 11,ticket_id.status or '',  condition)
                            worksheet.write(row_index, 12,ticket_id.state.name or '',  condition)
                            worksheet.write(row_index, 13,ticket_id.company_id.name or '',  condition)
                            worksheet.write(row_index, 14,ticket_id.start_time or '',  condition)
                            worksheet.write(row_index, 15,ticket_id.target_closure_date or '',  condition)
                            worksheet.write(row_index, 16,ticket_id.close_time or '',  condition)
                            worksheet.write(row_index, 17,ticket_id.time_to_close or '',  condition)
                            worksheet.write(row_index, 18,ticket_id.estimated_hours or '',  condition)
                            worksheet.write(row_index, 19,ticket_id.actual_hours or  '',  condition)
                            worksheet.write(row_index, 20,ticket_id.asset_id.name or  '',  condition)
                            worksheet.write(row_index, 21,ticket_id.approx_cost or  '',  condition)
                            worksheet.write(row_index, 22,ticket_id.project_id.name or  '',  condition)
                          
                            row_index += 1

                row_index +=1
                workbook.save(fp)

            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'name':rep_name + '.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'ticket.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }