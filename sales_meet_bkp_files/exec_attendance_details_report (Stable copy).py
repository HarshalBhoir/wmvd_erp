# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta , date
import time
from dateutil import relativedelta
from cStringIO import StringIO
import xlwt
import re
import base64
import pytz
import calendar
import json
import odoo.http as http
from odoo.http import request
from odoo.addons.web.controllers.main import ExcelExport
import dateutil.parser

from odoo import models, fields, api
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo import api, models, _ , tools
from odoo.exceptions import UserError , Warning, ValidationError
from odoo.addons.report_xlsx.report.report_xlsx import ReportXlsx


format_date = '%Y-%m-%d'

class exec_attendance_details_report(models.TransientModel):
    _name = 'exec.attendance.details.report'
    _description = "Exec Attendance Details Report"


    name = fields.Char(string="ExecAttendanceDetailsReport")
    date_from = fields.Date(string='Start Date', required=True, default=datetime.today().replace(day=1))
    date_to = fields.Date(string="End Date", required=True, default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))

    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    user_ids = fields.Many2many('res.users', 'exec_attendance_details_report_res_user_rel', string='Users')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    select_all = fields.Boolean("All User" , default=False )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('exec.attendance.details.report'))

  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True




    @api.multi
    def update_attendance(self):
        self.ensure_one()
        domain = []
        intervals = []
        status = ''
        if self.date_from and self.date_to:
            if not self.attachment_id:
                rep_name = "Exec Attendance Details Report"
                if self.date_from and self.date_to and  not self.name:
                    date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                    date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                    if self.date_from == self.date_to:
                        rep_name = "Exec Attendance Details Report(%s)" % (date_from,)
                    else:
                        rep_name = "Exec Attendance Details Report(%s|%s)" % (date_from, date_to)
                self.name = rep_name + '.xls'

                workbook = xlwt.Workbook(encoding='utf-8')
                worksheet = workbook.add_sheet('Attendance Details', cell_overwrite_ok=True)
                fp = StringIO()

                main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1; borders: bottom thick, top thick, left thick, right thick; pattern: pattern fine_dots, fore_color white, back_color light_green;')
                sp_style = xlwt.easyxf('font: bold on, height 350;')
                header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin ; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
                base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')
                base_style_green = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color green;')

                #CCFFCC
                
                worksheet.write_merge(0, 1, 0, 23, rep_name ,main_style)
                row_index = 2

                column_index = 1
                
                worksheet.col(0).width = 3000
                worksheet.col(1).width = 8000
                worksheet.col(2).width  = 1000
                worksheet.col(3).width  = 1000
                worksheet.col(4).width  = 1000
                worksheet.col(5).width  = 1000
                worksheet.col(6).width  = 1000
                worksheet.col(7).width  = 1000
                worksheet.col(8).width  = 1000
                worksheet.col(9).width  = 1000
                worksheet.col(10).width  = 1000
                worksheet.col(11).width  = 1000
                worksheet.col(12).width  = 1000
                worksheet.col(13).width  = 1000
                worksheet.col(14).width  = 1000
                worksheet.col(15).width  = 1000
                worksheet.col(16).width  = 1000
                worksheet.col(17).width  = 1000
                worksheet.col(18).width  = 1000
                worksheet.col(19).width  = 1000
                worksheet.col(20).width  = 1000
                worksheet.col(21).width  = 1000
                worksheet.col(22).width  = 1000
                worksheet.col(23).width  = 1000
                worksheet.col(24).width  = 1000
                worksheet.col(25).width  = 1000
                worksheet.col(26).width  = 1000
                worksheet.col(27).width  = 1000
                worksheet.col(28).width  = 1000
                worksheet.col(29).width  = 1000
                worksheet.col(30).width  = 1000
                worksheet.col(31).width  = 1000
                worksheet.col(32).width  = 1000
                worksheet.col(33).width  = 3000
                worksheet.col(34).width  = 4000


                # Headers
                header_fields = ['Emp. No.','Employee Name','1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29','30','31','Total Days']
                row_index += 1

                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1


                date_from = dateutil.parser.parse(self.date_from).date()
                date_to = dateutil.parser.parse(self.date_to).date()

                delta = date_to - date_from
                total_days = delta.days + 1


                for days in range(total_days):
          
                    intervals.append(date_from)
                    date_from += timedelta(days=1)

                if self.user_ids:
                    user_id = [user.id for user in self.user_ids]
                    domain.append(user_id)

                user_ids = self.env['res.users'].search(domain)
                
               

                for user_id in user_ids.search([('active','=',True),('wp_salesperson','=',True)]):
                    present = ''
                    present_bool = False
                    total_present_days = 0

                    employee_ids = self.env['hr.employee'].sudo().search([
                                ('user_id','=',user_id.id),
                                '|',('active','=',False),('active','=',True)])
                    

                    for rec in intervals:                        
                        calendar_ids = self.env['calendar.event'].sudo().search([
                                            ('expense_date','=',rec),
                                            ('user_id','=',user_id.id),
                                            ('company_id','=',self.company_id.id)
                                            ])

                        if calendar_ids:
                            present = 'P'
                            present_bool = True
                            total_present_days += 1

                        worksheet.write(row_index, 0,employee_ids.emp_id, base_style)
                        worksheet.write(row_index, 1,user_id.name,  base_style)
                        worksheet.write(row_index, column_index + int(rec.day) ,present or '', base_style_green if present_bool == True else base_style )
                        worksheet.write(row_index, 33 , total_present_days or '',  base_style_gray)


                    row_index += 1

                row_index +=1
                workbook.save(fp)


            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'name':rep_name + '.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'exec.attendance.details.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }