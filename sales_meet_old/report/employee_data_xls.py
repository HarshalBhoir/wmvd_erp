# -*- coding: utf-8 -*-

import calendar
from io import StringIO
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


emp_stages = [('joined', 'Probation'),
              ('grounding', 'Grounding'),
              ('offrole', 'OffRole'),
              ('test_period', 'Test Period'),
              ('employment', 'Employment'),
              ('notice_period', 'Notice Period'),
              ('relieved', 'Resigned'),
              ('terminate', 'Terminated')]

class WpHrEmployeeReport(models.TransientModel):
    _name = "wp.hr.employee.report"
    
    # start_date = fields.Date(string='Start Date',  default=datetime.today().replace(day=1))
    # end_date = fields.Date(string="End Date", default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string="End Date")

    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    hr_employee_data = fields.Char('Name', size=256)
    file_name = fields.Binary('Expense Report', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    emp_state = fields.Selection(emp_stages, string='Status' , index=True , required=True,
                             help="Employee Stages.\nSlap On: Joined\nGrounding: Training\nTest period : Probation")

    company_id = fields.Many2one('res.company', string='Company' , required=True)
    employee_ids = fields.Many2many('hr.employee', 'employee_details_report_hr_employee_rel', string='Employee')

    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]

    @api.multi
    def action_wp_employee_report(self):
        file = StringIO()
        if self.start_date and self.end_date:
            if self.emp_state not in ('notice_period','relieved','terminate') :
                hr_employee = self.env['hr.employee'].search([('date_of_joining', '>=', self.start_date), ('date_of_joining', '<=', self.end_date), 
                                                        ('state', '=', self.emp_state),('company_id','=',self.company_id.id)])
            elif self.emp_state in ('notice_period','relieved','terminate')  :
                hr_employee = self.env['hr.employee'].search([('last_date', '>=', self.start_date), ('last_date', '<=', self.end_date), 
                                                        ('state', '=', self.emp_state),('company_id','=',self.company_id.id)])
        else:
            hr_employee = self.env['hr.employee'].search([('state', '=', self.emp_state),('company_id','=',self.company_id.id)])


        if self.employee_ids:
            employee_id = [employee.id for employee in self.employee_ids]

            hr_employee = self.env['hr.employee'].search([('id','in',employee_id),('state', '=', self.emp_state),('company_id','=',self.company_id.id)])


        self.ensure_one()

        if (not hr_employee):
            raise Warning(_('Record Not Found'))

        # print eeereer
        status = ''
        # self.sudo().unlink()
        if hr_employee :
            order_list = []
            second_heading = ''
            # file_name = self.name + '.xls'
            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet('Employee Report')
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
            base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
            base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
            base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')

          
        #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py

            rep_name = 'Employee Details Report'
            if self.start_date and  self.end_date:
                start_date = datetime.strptime(self.start_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                end_date = datetime.strptime(self.end_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                if self.start_date == self.end_date:
                    rep_name = "Employee Details Report(%s)" % (start_date)
                else:
                    rep_name = "Employee Details Report(%s-%s)"  % (start_date, end_date)
            self.name = rep_name

            
            worksheet.write_merge(0, 1, 0, 10, self.name ,main_style)
            row_index = 2
            
            worksheet.col(1).width = 12000  #'Employee Name'
            worksheet.col(2).width = 2002  #'Grade'
            worksheet.col(3).width = 9000  #'Designation'
            worksheet.col(4).width = 3000  #'Status'
            worksheet.col(5).width = 4000  #'Emp. Id'
            worksheet.col(6).width = 4000  #'Working Mobile'
            worksheet.col(7).width = 7000  #'Location'
            worksheet.col(8).width = 5008  #'State'
            worksheet.col(9).width = 12000  #'Work Mail'
            worksheet.col(10).width = 12000  #'Manager'
            worksheet.col(11).width = 12000  #'Coach'
            worksheet.col(12).width = 6000  #'Company'
            worksheet.col(13).width = 6000  #'Contact No'
            worksheet.col(14).width = 12000  #'Department'
            worksheet.col(15).width = 4000  #'Birthday'
            worksheet.col(16).width = 2016  #'Zone'
            worksheet.col(17).width = 4000  #'Joining Date'
            worksheet.col(18).width = 5000  #'Resignation Date'
            worksheet.col(19).width = 3019  #'Roll'
            worksheet.col(20).width = 12000  #'Father Name'
            worksheet.col(21).width = 12000  #'Personal Email'
            worksheet.col(22).width = 6000  #'State'
            worksheet.col(23).width = 6000  #'Aadhar_No'
            worksheet.col(24).width = 5000  #'Pan_No'
            worksheet.col(25).width = 8000  #'Account_Bank_Id'
            worksheet.col(26).width = 6000  #'Bank_Name'
            worksheet.col(27).width = 5000  #'Ifsc_Code'
            
            # Headers
            header_fields = ['Sr.No','Employee Name','Grade','Designation','Status','Emp. Id','Mobile','Location',
            'State','Work Mail','Manager','Coach','Company','Contact No','Department','Birthday','Zone','Joining Date',
            'Resignation Date','Roll','Father Name','Personal Email','State','Aadhar No','Pan No','Account Bank Id','Bank Name','Ifsc Code']
            row_index += 1
         
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

            count = 0
            for hr_employee_id in hr_employee:
                if hr_employee_id:
                    
                    count +=1
                    worksheet.write(row_index, 0,count, base_style_yellow )
                    worksheet.write(row_index, 1,hr_employee_id.name_related,  base_style_yellow )
                    worksheet.write(row_index, 2,hr_employee_id.grade_id.name  or '',  base_style_yellow )
                    worksheet.write(row_index, 3,hr_employee_id.job_id.name or '',  base_style_yellow )
                    worksheet.write(row_index, 4,hr_employee_id.status or '',  base_style_yellow )
                    worksheet.write(row_index, 5,hr_employee_id.emp_id or '',  base_style_yellow )
                    worksheet.write(row_index, 6,hr_employee_id.mobile_phone or '',  base_style_yellow )
                    worksheet.write(row_index, 7,hr_employee_id.work_location or '',  base_style_yellow )
                    worksheet.write(row_index, 8,hr_employee_id.work_state or '',  base_style_yellow )
                    worksheet.write(row_index, 9,hr_employee_id.work_email or '',  base_style_yellow )
                    worksheet.write(row_index,10,hr_employee_id.parent_id.name_related or '',  base_style_yellow )
                    worksheet.write(row_index,11,hr_employee_id.coach_id.name_related or '',  base_style_yellow )
                    worksheet.write(row_index,12,hr_employee_id.company_id.name or '',  base_style_yellow )
                    worksheet.write(row_index,13,hr_employee_id.work_phone or '',  base_style_yellow )
                    worksheet.write(row_index,14,hr_employee_id.department_id.name or '',  base_style_yellow )
                    worksheet.write(row_index,15,hr_employee_id.birthday or '',  base_style_yellow )
                    worksheet.write(row_index,16,hr_employee_id.zone or '',  base_style_yellow )
                    worksheet.write(row_index,17,hr_employee_id.date_of_joining or '',  base_style_yellow )
                    worksheet.write(row_index,18,hr_employee_id.date_of_resignation or '',  base_style_yellow )
                    worksheet.write(row_index,19,hr_employee_id.roll or '',  base_style_yellow )
                    worksheet.write(row_index,20,hr_employee_id.father_name or '',  base_style_yellow )
                    worksheet.write(row_index,21,hr_employee_id.personal_email or '',  base_style_yellow )
                    worksheet.write(row_index,22,hr_employee_id.state or '',  base_style_yellow )
                    worksheet.write(row_index,23,hr_employee_id.aadhar_no or '',  base_style_yellow )
                    worksheet.write(row_index,24,hr_employee_id.pan_no or '',  base_style_yellow )
                    worksheet.write(row_index,25,hr_employee_id.account_bank_id or '',  base_style_yellow )
                    worksheet.write(row_index,26,hr_employee_id.bank_name or '',  base_style_yellow )
                    worksheet.write(row_index,27,hr_employee_id.ifsc_code or '',  base_style_yellow )


                    
                    row_index += 1

            row_index +=1
            workbook.save(fp)

            out = base64.encodestring(fp.getvalue())

            self.write({'state': 'get','file_name': out,'hr_employee_data':self.name+'.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'wp.hr.employee.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                # 'views': [(False, 'form')],
                'target': 'new',
            }