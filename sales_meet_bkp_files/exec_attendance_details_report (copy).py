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
    # date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    # date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
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
        # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk"
        self.ensure_one()
        domain = []
        intervals = []
        status = ''
        # self.sudo().unlink()
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
                worksheet = workbook.add_sheet('Meeting Details')
                fp = StringIO()
                
                main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1; borders: bottom thick, top thick, left thick, right thick')
                sp_style = xlwt.easyxf('font: bold on, height 350;')
                header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin ; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
                base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')
                
                worksheet.write_merge(0, 1, 0, 4, rep_name ,main_style)
                row_index = 2
                
                worksheet.col(0).width = 3000
                worksheet.col(1).width = 8000
                worksheet.col(2).width = 4000
                worksheet.col(3).width = 4000
                worksheet.col(4).width = 4000

                # Headers
                header_fields = ['Sr No.','Name','Date','Present','Absent']
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


                print "11111111111111111111111111" , intervals , total_days

                if self.user_ids:
                    user_id = [user.id for user in self.user_ids]
                    # domain.append(('id', '=', user_id))
                    domain.append(user_id)

                user_ids = self.env['res.users'].search(domain)

                count = 0

                for user_id in user_ids.search([('active','=',True)]):
                    present = ''
                    absent = 0
                    

                    # employee_ids = self.env['hr.employee'].sudo().search([
                    #             ('user_id','=',user_id.id), ('department_id','=',42),
                    #             '|',('active','=',False),('active','=',True)])

                    # if employee_ids:

                    for rec in intervals:
                        
                        calendar_ids = self.env['calendar.event'].sudo().search([
                                            ('expense_date','=',rec),
                                            ('user_id','=',user_id.id),
                                            ('company_id','=',self.company_id.id)
                                            ])

                        if calendar_ids:
                            print "wwwwwwww present wwwwwwwww" , user_id.name , present , calendar_ids , len(calendar_ids) , rec , type(rec)
                            present = 'P'
                        else:
                            print "wwwwwwww Absent wwwwwwwww" , user_id.name , absent , calendar_ids , len(calendar_ids) , rec , type(rec)
                            present= 'A'


                        count +=1
                        worksheet.write(row_index, 0,count, base_style)
                        worksheet.write(row_index, 1,user_id.name,  base_style)
                        worksheet.write(row_index, 2,str(rec),  base_style)
                        worksheet.write(row_index, 3,present,  base_style)
                        worksheet.write(row_index, 4,present ,  base_style)


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






    #     print(eroror)


    # @api.multi
    # def print_report(self):
        
    #     self.ensure_one()
    #     status = ''
    #     # self.sudo().unlink()
    #     if self.date_from and self.date_to:
    #         if not self.attachment_id:

    #             rep_name = "Exec Attendance_Details_Report"
    #             if self.date_from and self.date_to and  not self.name:
    #                 date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
    #                 date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
    #                 if self.date_from == self.date_to:
    #                     rep_name = "Exec Attendance Details Report(%s)" % (date_from,)
    #                 else:
    #                     rep_name = "Exec Attendance Details Report(%s|%s)" % (date_from, date_to)
    #             self.name = rep_name + '.xls'

    #             workbook = xlwt.Workbook(encoding='utf-8')
    #             worksheet = workbook.add_sheet('Meeting Details')
    #             fp = StringIO()
                
    #             main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1; borders: bottom thick, top thick, left thick, right thick')
    #             sp_style = xlwt.easyxf('font: bold on, height 350;')
    #             header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin ; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
    #             base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
    #             base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
    #             base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')
                
    #             worksheet.write_merge(0, 1, 0, 19, rep_name ,main_style)
    #             row_index = 2
                
    #             worksheet.col(0).width = 3000
    #             worksheet.col(1).width = 4000
    #             worksheet.col(2).width = 4000
    #             worksheet.col(3).width = 8000
    #             worksheet.col(4).width = 12000
    #             worksheet.col(5).width = 24000
    #             worksheet.col(6).width = 4000
    #             worksheet.col(7).width = 4000
    #             worksheet.col(8).width = 8000
    #             worksheet.col(9).width = 8000
    #             worksheet.col(10).width = 18000
    #             worksheet.col(11).width = 8000
    #             worksheet.col(12).width = 8000
    #             worksheet.col(13).width = 8000
    #             worksheet.col(14).width = 4000
    #             worksheet.col(15).width = 4000
    #             worksheet.col(16).width = 6000
    #             worksheet.col(17).width = 4000
    #             worksheet.col(18).width = 8000
    #             worksheet.col(19).width = 3000
    #             # worksheet.col(20).width = 3000

                
    #             # Headers
    #             header_fields = ['Sr.No','Date','Time','Responsible','Meeting Subject','Address','Distance(Km)','Duration','Lead','Customer','Description',
    #             'Dest Address','Stage','Activity','Latitude','Longitude','Next Activity','Next Date','State','Emp Code']
    #             row_index += 1
                
    #         #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
                
    #             for index, value in enumerate(header_fields):
    #                 worksheet.write(row_index, index, value, header_style)
    #             row_index += 1

    #             user_id = [user.id for user in self.user_ids]

    #             if self.user_id.has_group('sales_meet.group_sales_meet_srexecutive') == True:
    #                 if self.user_ids:
    #                     meeting_ids = self.env['calendar.event'].sudo().search([
    #                         ('user_id','in',user_id),('start_datetime','>=',self.date_from),
    #                         ('start_datetime','<=',self.date_to),
    #                         ('company_id','=',self.company_id.id)
    #                         ,'|',('active','=',False),('active','=',True)])
    #                 elif self.select_all:
    #                     meeting_ids = self.env['calendar.event'].sudo().search([
    #                         ('start_datetime','>=',self.date_from),
    #                         ('start_datetime','<=',self.date_to),
    #                         ('company_id','=',self.company_id.id)
    #                         ,'|',('active','=',False),('active','=',True)])
    #                 else:
    #                     meeting_ids = self.env['calendar.event'].sudo().search([
    #                         ('user_id','=',self.env.uid),
    #                         ('start_datetime','>=',self.date_from),
    #                         ('start_datetime','<=',self.date_to),
    #                         ('company_id','=',self.company_id.id)
    #                         ,'|',('active','=',False),('active','=',True)])
    #             else:
    #                 meeting_ids = self.env['calendar.event'].sudo().search([
    #                     ('user_id','=',self.env.uid),
    #                     ('start_datetime','>=',self.date_from),
    #                     ('start_datetime','<=',self.date_to),
    #                         ('company_id','=',self.company_id.id)
    #                     ,'|',('active','=',False),('active','=',True)])

                
    #             if (not meeting_ids):
    #                 raise Warning(_('Record Not Found'))

    #             if meeting_ids:

    #                 count = 0        
    #                 for meeting_id in meeting_ids:
    #                     po_date = ''
    #                     new_index = row_index

    #                     if meeting_id:

    #                         if meeting_id.ishome or meeting_id.name:
    #                             status = 'complete'
    #                         else:
    #                             status = 'pending'
    #                         date_starttime = datetime.strptime(meeting_id.start_datetime, "%Y-%m-%d %H:%M:%S") + timedelta(hours=5, minutes=30)
    #                         date_start_date = date_starttime.strftime('%d-%m-%Y')
    #                         date_start_time = date_starttime.strftime('%H:%M:%S')

    #                         employee_ids = self.env['hr.employee'].sudo().search([
    #                             ('user_id','=',meeting_id.user_id.id),
    #                             '|',('active','=',False),('active','=',True)])


    #                         count +=1
    #                         worksheet.write(row_index, 0,count, base_style)
    #                         worksheet.write(row_index, 1,date_start_date,  base_style)
    #                         worksheet.write(row_index, 2,date_start_time,  base_style)
    #                         worksheet.write(row_index, 3,meeting_id.user_id.name or '',  base_style)
    #                         worksheet.write(row_index, 4,meeting_id.name or '',  base_style)
    #                         worksheet.write(row_index, 5,meeting_id.reverse_location or '',  base_style)
    #                         worksheet.write(row_index, 6,meeting_id.distance or '',  base_style)
    #                         worksheet.write(row_index, 7,meeting_id.duration or '',  base_style)
    #                         worksheet.write(row_index, 8,meeting_id.lead_id.name or '',  base_style)
    #                         worksheet.write(row_index, 9,meeting_id.partner_id.name or '',  base_style)
    #                         worksheet.write(row_index, 10,meeting_id.description or '',  base_style)
    #                         worksheet.write(row_index, 11,meeting_id.destination or '',  base_style)
    #                         worksheet.write(row_index, 12,meeting_id.stage_id.name or '',  base_style)
    #                         worksheet.write(row_index, 13,meeting_id.categ_id.name or '',  base_style)
    #                         worksheet.write(row_index, 14,meeting_id.checkin_lattitude or '',  base_style)
    #                         worksheet.write(row_index, 15,meeting_id.checkin_longitude or '',  base_style)
    #                         worksheet.write(row_index, 16,meeting_id.next_activity_id.name or '',  base_style)
    #                         worksheet.write(row_index, 17,meeting_id.date_action or '',  base_style)
    #                         # worksheet.write(row_index, 18,meeting_id.title_action or '',  base_style)
    #                         worksheet.write(row_index, 18,employee_ids.state_id.name or employee_ids.work_state or '',  base_style)
    #                         worksheet.write(row_index, 19,employee_ids.emp_id or  '',  base_style)

    #                         #worksheet.write(row_index, 22,meeting_id.user_id.employee_id.state_id.name or meeting_id.user_id.employee_id.work_state or '' ,  base_style)
                            
                            
    #                         row_index += 1

    #             row_index +=1
    #             workbook.save(fp)


    #         out = base64.encodestring(fp.getvalue())
    #         self.write({'state': 'get','report': out,'name':rep_name + '.xls'})
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'exec.attendance.details.report',
    #             'view_mode': 'form',
    #             'view_type': 'form',
    #             'res_id': self.id,
    #             'target': 'new',
    #         }