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

class WpHrExpenseReport(models.TransientModel):
    _name = "wp.hr.expense.sheet.report"
    
    start_date = fields.Date(string='Start Date', required=True, default=datetime.today().replace(day=1))
    end_date = fields.Date(string="End Date", required=True, default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))


    expense_state = fields.Selection([('submit', 'Submitted'),
          ('manager_approve', 'Manager Approved'),
          ('approve', 'Approved'),
          ('post', 'Posted'),
          ('done', 'Paid'),
          ('cancel', 'Refused')
          ], string='Status', index=True)


    user_id = fields.Many2one('res.users', string='Salesperson') #, default=lambda self: self.env.user
    hr_expense_data = fields.Char('Name', size=256)
    file_name = fields.Binary('Expense Report', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')

    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]

    @api.multi
    def action_expense_report(self):
        file = StringIO()
        if self.user_id:
            hr_expense = self.env['hr.expense.sheet'].sudo().search([('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date), 
                                                    ('state', '=', self.expense_state), ('create_uid', '=', self.user_id.id)])
        else:
            hr_expense = self.env['hr.expense.sheet'].sudo().search([('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date), 
                                                    ('state', '=', self.expense_state)],order="create_uid, create_date asc")

        self.ensure_one()
        status = ''
        # self.sudo().unlink()
        if self.start_date and self.end_date :
            second_heading = approval_status = ''
            # file_name = self.name + '.xls'
            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet('Expense Report')
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
            base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
            base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
            base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')

          
        #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py

            rep_name = ''
            start_date = datetime.strptime(self.start_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            end_date = datetime.strptime(self.end_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            if self.start_date == self.end_date:
                rep_name = "Expense Details Report(%s)" % (start_date)
            else:
                rep_name = "Expense Details Report(%s|%s)"  % (start_date, end_date)
            self.name = rep_name

            
            worksheet.write_merge(0, 1, 0, 12, self.name ,main_style)
            row_index = 2
            
            worksheet.col(0).width = 2000
            worksheet.col(1).width = 12000
            worksheet.col(2).width = 6000
            worksheet.col(3).width = 12000
            worksheet.col(4).width = 6000
            worksheet.col(5).width = 12000
            worksheet.col(6).width = 6000
            worksheet.col(7).width = 6000
            worksheet.col(8).width = 6000
            worksheet.col(9).width = 6000
            worksheet.col(10).width = 6000
            worksheet.col(11).width = 6000
            worksheet.col(12).width = 6000

            
            # Headers
            header_fields = ['S.No','Employee','Date','Expense','Meeting Date', 'Meeting', 'Allocated','Claimed','Manager','Grade','State','Manager Approval','Emp ID']
            row_index += 1
         
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

           
            if (not hr_expense):
                raise Warning(_('Record Not Found'))

            if hr_expense:

                count = 0
                for hr_expense_id in hr_expense:

                    # if hr_expense_id:
                    if hr_expense_id and len(hr_expense_id.expense_line_ids) > 0:

                        if hr_expense_id.expense_line_ids[0].total_amount > hr_expense_id.expense_line_ids[0].grade_amount \
                                    and hr_expense_id.expense_line_ids[0].grade_amount !=0:
                            approval_status = 'Needed'
                        else:
                            approval_status = ''

                        
                        count +=1
                        worksheet.write(row_index, 0,count, base_style_yellow )
                        # worksheet.write_merge(row_index, row_index+len(hr_expense_id.component_ids), 1, 1, hr_expense_id.asset_name,  base_style_yellow)
                        worksheet.write(row_index, 1,hr_expense_id.employee_id.name,  base_style_yellow )
                        worksheet.write(row_index, 2,hr_expense_id.create_date,  base_style_yellow )
                        worksheet.write(row_index, 3,hr_expense_id.name or '',  base_style_yellow )
                        worksheet.write(row_index, 4,hr_expense_id.expense_meeting_id.expense_date or '',  base_style_yellow )
                        worksheet.write(row_index, 5,hr_expense_id.expense_meeting_id.name or '',  base_style_yellow )
                        worksheet.write(row_index, 6,hr_expense_id.expense_line_ids[0].grade_amount or '',  base_style_yellow )
                        worksheet.write(row_index, 7,hr_expense_id.expense_line_ids[0].total_amount or '',  base_style_yellow )
                        worksheet.write(row_index, 8,hr_expense_id.expense_line_ids[0].manager_id.name or '',  base_style_yellow )
                        worksheet.write(row_index, 9,hr_expense_id.expense_line_ids[0].grade_id.name or '',  base_style_yellow )
                        worksheet.write(row_index, 10,hr_expense_id.state or '',  base_style_yellow )
                        worksheet.write(row_index, 11,approval_status or '',  base_style_yellow )
                        worksheet.write(row_index, 12,hr_expense_id.employee_id.emp_id or '',  base_style_yellow )

                        
                        row_index += 1

                        # for line in hr_expense_id.component_ids:
                        #     worksheet.write(row_index, 0,'' )
                        #     worksheet.write(row_index, 10,line.name.name or '', base_style)
                        #     worksheet.write(row_index, 11,line.model_name, base_style)
                        #     worksheet.write(row_index, 12,line.state, base_style)

                        #     row_index += 1
                        # row_index += 1

            row_index +=1
            workbook.save(fp)


            out = base64.encodestring(fp.getvalue())

            # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , out
            self.write({'state': 'get','file_name': out,'hr_expense_data':self.name+'.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'wp.hr.expense.sheet.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                # 'views': [(False, 'form')],
                'target': 'new',
            }