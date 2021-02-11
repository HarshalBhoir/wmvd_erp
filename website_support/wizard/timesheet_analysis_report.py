# -*- coding: utf-8 -*-
##############################################################################
#
#    odoo, Open Source Management Solution
#    Copyright (C) 2018 BroadTech IT Solutions Pvt Ltd 
#    (<http://broadtech-innovations.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, _
import xlwt
from cStringIO import StringIO
import base64
from xlwt import easyxf
import datetime
import math

class TimesheetAnalysisReport(models.TransientModel):
    _name = "timesheet.analyis.report"
    
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    analysis_report = fields.Binary('Analysis Report')
    file_name = fields.Char('File Name')
    project_report_printed = fields.Boolean('Project Report Printed')
    user_id = fields.Many2one('res.users', string='User')
    
    @api.multi
    def action_print_timesheet_analysis_report(self):
        workbook = xlwt.Workbook()
        amount_tot = 0
        column_heading_style = easyxf('font:height 210;font:bold True;')
        worksheet = workbook.add_sheet('Timesheet Analysis Report')
        if self.user_id:
            worksheet.write(2, 2, self.user_id.name or '', easyxf('font:height 230;font:bold True;align: horiz center;'))
        worksheet.write(4, 2, self.from_date + '   ' + 'To' + '   ' + self.to_date,easyxf('font:height 200;font:bold True;align: horiz center;'))
        worksheet.write(6, 0, _('Date'), column_heading_style)
        worksheet.write(6, 1, _('Project'), column_heading_style) 
        worksheet.write(6, 2, _('Task Summary'), column_heading_style)
        worksheet.write(6, 3, _('Work Summary'), column_heading_style)
        worksheet.write(6, 4, _('Time Spent in Hrs'), column_heading_style)
        worksheet.col(0).width = 4500
        worksheet.col(1).width = 8500
        worksheet.col(2).width = 9000
        worksheet.col(3).width = 9000
        worksheet.col(4).width = 4500
        user_dict = {}
        row = 8
        for wizard in self:
            heading =  'TIMESHEET ANALYSIS REPORT'
            worksheet.write_merge(0, 0, 0, 4, heading, easyxf('font:height 210; align: horiz center;pattern: pattern solid, fore_color black; font: color white; font:bold True;' "borders: top thin,bottom thin"))
            if wizard.user_id:
                domain = [('date','>=',wizard.from_date),('date','<=',wizard.to_date),('user_id','=',wizard.user_id.id)]
            else:
                domain = [('date','>=',wizard.from_date),('date','<=',wizard.to_date)]
            task_ids = self.env['account.analytic.line'].search(domain)
            total = 0
            for task in task_ids:
                if task.user_id not in user_dict:
                    user_dict.update({task.user_id : [task]})
                else:
                    task_obj = user_dict[task.user_id] + [task]
                    user_dict.update({task.user_id : task_obj})
                amount = round(task.unit_amount,2)
                duration_time = float(amount)
                total += duration_time
                if wizard.user_id:
                    worksheet.write(row-1, 0, task.date, easyxf('font:height 200; align: horiz left;'))
                    worksheet.write(row-1, 1, task.task_id.project_id and task.task_id.project_id.name or '', easyxf('font:height 200;align: horiz left;'))
                    worksheet.write(row-1, 2, task.task_id.name or '', easyxf('font:height 200;align: horiz left;'))
                    worksheet.write(row-1, 3, task.name, easyxf('font:height 200;align: horiz left;'))
                    worksheet.write(row-1, 4, duration_time, easyxf('font:height 200;align: horiz left;'))
                    row += 1
            if not wizard.user_id:
                for user in user_dict:
                    worksheet.write(row, 0, user.name, easyxf('font:height 200;font:bold True; align: horiz left;'))
                    for user_vals in user_dict[user]:
                        amount = round(user_vals.unit_amount,2)
                        duration_time = float(amount)
                        row += 1
                        worksheet.write(row, 0, user_vals.date, easyxf('font:height 200; align: horiz left;'))
                        worksheet.write(row, 1, user_vals.task_id.project_id and user_vals.task_id.project_id.name or '', easyxf('font:height 200;align: horiz left;'))
                        worksheet.write(row, 2, user_vals.task_id.name or '', easyxf('font:height 200;align: horiz left;'))
                        worksheet.write(row, 3, user_vals.name, easyxf('font:height 200;align: horiz left;'))
                        worksheet.write(row, 4, duration_time, easyxf('font:height 200;align: horiz left;'))
                    row += 1
            amount_tot = total
            worksheet.write(row+1, 4, format(amount_tot,'.2f'), easyxf('font:height 200;font:bold True;align: horiz right;'))
            fp = StringIO()
            workbook.save(fp)
            excel_file = base64.encodestring(fp.getvalue())
            wizard.analysis_report = excel_file
            wizard.file_name = 'Timesheet Analysis Report.xls'
            wizard.project_report_printed = True
            fp.close()
            return {
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'res_model': 'timesheet.analyis.report',
                    'view_type': 'form',
                    'type': 'ir.actions.act_window',
                    'context': self.env.context,
                    'target': 'new',
                       }
        