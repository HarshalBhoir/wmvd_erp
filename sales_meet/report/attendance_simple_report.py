# -*- coding: utf-8 -*-

import time
import xlwt
import base64
import calendar
import odoo.http as http
import dateutil.parser
from cStringIO import StringIO
from datetime import date, datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import api, models, _ , tools, fields
from odoo.exceptions import UserError , Warning, ValidationError

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class attendance_simple_report(models.TransientModel):
    _name = 'attendance.simple.report'
    _description = "Attendance Simple Report"

    name = fields.Char(string="AttendanceSimpleReport")
    date_from = fields.Date(string='Start Date', default=datetime.today().replace(day=1))
    date_to = fields.Date(string="End Date",
        default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))

    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    user_ids = fields.Many2many('res.users', string='Users')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    select_all = fields.Boolean("All User" , default=False )
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('attendance.simple.report'))


    def last_day_of_month(any_day):
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)
  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True

    @api.multi
    def print_attendance(self):
        start = time.time()
        self.ensure_one()
        rep_name = ''

        if not self.attachment_id:
            if not self.name:
                date_from2 = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                date_to2 = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                if date_from2 == date_to2:
                    rep_name = "Daily Attendance Report(%s)" % (date_from2,)
                else:
                    rep_name = "Daily Attendance Report(%s-%s)" % (date_from2, date_to2)
            self.name = rep_name + '.xls'

            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet('Daily Attendance Report', cell_overwrite_ok=True)
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


            worksheet.write_merge(0, 1, 0, 8, rep_name ,main_style)
            row_index = column_index = 2
            
            worksheet.col(0).width = 2000
            worksheet.col(1).width = 3000
            worksheet.col(2).width = 12000
            worksheet.col(3).width  = 6000
            worksheet.col(4).width  = 6000
            worksheet.col(5).width  = 5000
            worksheet.col(6).width = 4000
            worksheet.col(7).width = 5000
            worksheet.col(8).width = 8000
            worksheet.col(9).width = 7000

            # Headers
            header_fields = ['Sr.No','Emp. No.','Employee Name', 'Check In', 'Check Out', 
            'Hours Completed', 'Date', 'Checkout Type','Department', 'Company']

            row_index += 1

            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

            attendance_ids = self.env['hr.attendance'].sudo().search([
                                                            ('attendance_date', '>=', self.date_from), 
                                                            ('attendance_date', '<=', self.date_to)])

            if (not attendance_ids):
                raise Warning(_('Record Not Found'))

            if attendance_ids:
                count = 0
                for ai in attendance_ids:
                    check_in = check_out = ''
                    if ai.checkout_type == 's':
                        checkout_type = 'System'
                    else:
                        checkout_type = 'Manual'

                    if ai.hours_completed <= 4.0:
                        condition = base_style_orange
                    else:
                        condition = base_style_green

                    check_in_date = datetime.strptime(ai.check_in, DATETIME_FORMAT) + timedelta(hours=5, minutes=30)
                    check_in = check_in_date.strftime(DATETIME_FORMAT)

                    if ai.check_out:
                        check_out_date = datetime.strptime(ai.check_out, DATETIME_FORMAT) + timedelta(hours=5, minutes=30)
                        check_out = check_out_date.strftime(DATETIME_FORMAT)
               
                    count +=1
                    worksheet.write(row_index, 0, count, base_style)
                    worksheet.write(row_index, 1, ai.employee_id.emp_id, base_style)
                    worksheet.write(row_index, 2, ai.employee_id.name,  base_style)
                    worksheet.write(row_index, 3 , check_in or '', base_style)
                    worksheet.write(row_index, 4 , check_out or '',  base_style)
                    worksheet.write(row_index, 5 , ai.hours_completed or '',  condition)
                    worksheet.write(row_index, 6 , ai.attendance_date or '',  base_style)
                    worksheet.write(row_index, 7 , checkout_type or '',  base_style)
                    worksheet.write(row_index, 8 , ai.employee_id.department_id.name or '',  base_style)
                    worksheet.write(row_index, 9 , ai.employee_id.company_id.name or '',  base_style)

                    row_index += 1

            row_index +=1
            workbook.save(fp)

        out = base64.encodestring(fp.getvalue())
        self.write({'state': 'get','report': out,'name':rep_name + '.xls'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'attendance.simple.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new',
        }