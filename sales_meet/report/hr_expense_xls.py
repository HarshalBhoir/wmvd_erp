# -*- coding: utf-8 -*-

import calendar
from io import StringIO
from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from datetime import datetime, timedelta , date
import time
from cStringIO import StringIO
import xlwt
import re
import base64

class WpHrExpenseReport(models.TransientModel):
    _name = "wp.hr.expense.sheet.report"
    
    start_date = fields.Date(string='Start Date', required=True, default=datetime.today().replace(day=1))
    end_date = fields.Date(string="End Date", required=True, 
        default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))

    expense_state = fields.Selection([('submit', 'Submitted'),
          ('manager_approve', 'Manager Approved'),
          ('approve', 'Approved'),
          ('post', 'Posted'),
          ('done', 'Paid'),
          ('cancel', 'Refused')
          ], string='Status', index=True)


    user_id = fields.Many2one('res.users', string='Salesperson')
    hr_expense_data = fields.Char('Name', size=256)
    file_name = fields.Binary('Expense Report', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')

    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]

    @api.multi
    def action_expense_report(self):
        self.ensure_one()
        fp = StringIO()
        if self.user_id:
            hr_expense = self.env['hr.expense.sheet'].sudo().search([('create_date', '>=', self.start_date), 
                                                                    ('create_date', '<=', self.end_date), 
                                                                    ('state', '=', self.expense_state), 
                                                                    ('create_uid', '=', self.user_id.id)])
        else:
            hr_expense = self.env['hr.expense.sheet'].sudo().search([('create_date', '>=', self.start_date), 
                                                ('create_date', '<=', self.end_date), 
                                                ('state', '=', self.expense_state)],order="create_uid, create_date asc")

        if (not hr_expense):
            raise Warning(_('Record Not Found'))
        
        rep_name = 'Expense Details Report'
        second_heading = approval_status = ''
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet(rep_name)
        
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

        start_date = datetime.strptime(self.start_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
        end_date = datetime.strptime(self.end_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
        if self.start_date == self.end_date:
            rep_name = rep_name + "(%s)" % (start_date)
        else:
            rep_name = rep_name + "(%s|%s)"  % (start_date, end_date)

        worksheet.write_merge(0, 1, 0, 12, rep_name ,main_style)
        row_index = 2
        
        worksheet.col(0).width = 2000
        worksheet.col(1).width = 12000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 12000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 12000
        for tt in range(6,13):
            worksheet.col(tt).width  = 6000
        
        # Headers
        header_fields = ['S.No','Employee','Date','Expense','Meeting Date', 'Meeting', 'Allocated','Claimed',
        'Manager','Grade','State','Manager Approval','Emp ID']
        row_index += 1
     
        for index, value in enumerate(header_fields):
            worksheet.write(row_index, index, value, header_style)
        row_index += 1

        count = 0
        for hr_expense_id in hr_expense:
            if hr_expense_id and len(hr_expense_id.expense_line_ids) > 0:
                expense_id = hr_expense_id.expense_line_ids[0]

                if expense_id.total_amount > expense_id.grade_amount and expense_id.grade_amount !=0:
                    approval_status = 'Needed'
                else:
                    approval_status = ''

                count +=1
                worksheet.write(row_index, 0,count, base_style_yellow )
                worksheet.write(row_index, 1,hr_expense_id.employee_id.name,  base_style_yellow )
                worksheet.write(row_index, 2,hr_expense_id.create_date,  base_style_yellow )
                worksheet.write(row_index, 3,hr_expense_id.name or '',  base_style_yellow )
                worksheet.write(row_index, 4,hr_expense_id.expense_meeting_id.expense_date or '',  base_style_yellow )
                worksheet.write(row_index, 5,hr_expense_id.expense_meeting_id.name or '',  base_style_yellow )
                worksheet.write(row_index, 6,expense_id.grade_amount or '',  base_style_yellow )
                worksheet.write(row_index, 7,expense_id.total_amount or '',  base_style_yellow )
                worksheet.write(row_index, 8,expense_id.manager_id.name or '',  base_style_yellow )
                worksheet.write(row_index, 9,expense_id.grade_id.name or '',  base_style_yellow )
                worksheet.write(row_index, 10,hr_expense_id.state or '',  base_style_yellow )
                worksheet.write(row_index, 11,approval_status or '',  base_style_yellow )
                worksheet.write(row_index, 12,hr_expense_id.employee_id.emp_id or '',  base_style_yellow )

                row_index += 1

        row_index +=1
        workbook.save(fp)
        out = base64.encodestring(fp.getvalue())

        self.write({'state': 'get','file_name': out,'hr_expense_data':rep_name +'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wp.hr.expense.sheet.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new',
        }