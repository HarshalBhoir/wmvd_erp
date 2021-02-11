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

class attendance_details_report(models.TransientModel):
    _name = 'attendance.details.report'
    _description = "Attendance Details Report"

    name = fields.Char(string="AttendanceDetailsReport")
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
        default=lambda self: self.env['res.company']._company_default_get('attendance.details.report'))
    year = fields.Char(size=4, default=datetime.now().year)
    month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')], string="Month")


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
    def update_attendance(self):
        start = time.time()
        self.ensure_one()
        intervals = []
        rep_name = ''
        if not self.year.isdigit():
            raise ValidationError("Year Must be entered in numbers")

        if self.month and self.year:
            month = int(self.month)
            year =  int(self.year)
            _, num_days = calendar.monthrange(year, month)
            first_day = datetime(year, month, 1)
            last_day = datetime(year, month, num_days)
            date_from2 = first_day.strftime('%Y-%m-%d')
            date_to2 = last_day.strftime('%Y-%m-%d')

            if not self.attachment_id:
                if not self.name:
                    date_from3 = datetime.strptime(date_from2, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                    date_to3 = datetime.strptime(date_to2, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                    if date_from2 == date_to2:
                        rep_name = "Attendance Details Report(%s)" % (date_from3,)
                    else:
                        rep_name = "Attendance Details Report(%s-%s)" % (date_from3, date_to3)
                self.name = rep_name + '.xls'

                workbook = xlwt.Workbook(encoding='utf-8')
                worksheet = workbook.add_sheet('Attendance Details', cell_overwrite_ok=True)
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


                worksheet.write_merge(0, 1, 0, 11, rep_name ,main_style)
                row_index = column_index = 2
                month_days = num_days+2
                
                worksheet.col(0).width = 2000
                worksheet.col(1).width = 3000
                worksheet.col(2).width = 12000
                for tt in range(3,month_days):
                    worksheet.col(tt).width  = 2000
                worksheet.col(month_days+1).width  = 4000
                worksheet.col(month_days+2).width = 8000
                worksheet.col(month_days+3).width = 8000

                # Headers
                num_days
                days_list = [str(ee) for ee in range(1,num_days+1)]
                total_days_str = ['Total Days','Department', 'Company']
                header_fields = ['Sr.No','Emp. No.','Employee Name']
                header_fields.extend(days_list)
                header_fields.extend(total_days_str)

                row_index += 1

                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1

                date_from = dateutil.parser.parse(date_from2).date()
                date_to = dateutil.parser.parse(date_to2).date()

                delta = date_to - date_from
                total_days = delta.days + 1

                for days in range(total_days):
                    intervals.append(date_from)
                    date_from += timedelta(days=1)

                present = full_day = half_day = attendance_status = ''
                present_bool = False
                present_days = count = 0

                category_id = self.env['hr.employee.category'].sudo().search([('name','=','HO')], limit=1)
                employee_ids = self.env['hr.employee'].sudo().search([('category_ids_many2one','=',category_id.id),('active','=',True)])

                for employee in employee_ids:
                    emp_id = employee.emp_id
                    employee_name = employee.name
                    dept_name = employee.department_id.name
                    company_name = employee.company_id.name

                    total_present_days= 0
                    count +=1

                    for rec in intervals:
                        status = ''

                        attendance_ids = self.env['hr.attendance'].sudo().search([('attendance_date','=',rec),
                            ('employee_id','=',employee.id)])

                        if attendance_ids:
                            if len(attendance_ids) > 1:
                                hours_completed = sum([attendance.hours_completed for attendance in attendance_ids])
                                attendance_status = str(hours_completed)

                                if hours_completed >= 8:
                                    status = 'P'
                                    present_days = 1

                                elif hours_completed >= 4 and hours_completed < 7 :
                                    status = 'H'
                                    present_days = 0.5

                                else:
                                    status = 'L'
                                    present_days = 0

                            else:
                                hours_completed = attendance_ids.hours_completed
                                attendance_status = str(hours_completed)
                                
                                if attendance_ids.hours_completed >= 8:
                                    status = 'P'
                                    present_days = 1

                                elif attendance_ids.hours_completed >= 4 and attendance_ids.hours_completed < 7 :
                                    status = 'H'
                                    present_days = 0.5

                                else:
                                    status = 'L'
                                    present_days = 0

                            total_present_days += present_days

                        else:
                            attendance_status = ''
                        
                        worksheet.write(row_index, 0, count, base_style_gray)
                        worksheet.write(row_index, 1, emp_id, base_style_gray)
                        worksheet.write(row_index, 2, employee_name,  base_style_gray)
                        worksheet.write(row_index, column_index + int(rec.day) , attendance_status or '', base_style_green if status == 'P' \
                         else (base_style_yellow if status == 'H'  else (base_style_orange if status == 'L'  else base_style)) )
                        worksheet.write(row_index, month_days+1 , total_present_days or '',  base_style_gray)
                        worksheet.write(row_index, month_days+2 , dept_name or '',  base_style_gray)
                        worksheet.write(row_index, month_days+3 , company_name or '',  base_style_gray)


                    row_index += 1

                row_index +=1
                workbook.save(fp)

            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'name':rep_name + '.xls'})

            end = time.time()
            print "2222222222222222222 End of Report 22222222222222222" , end - start
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'attendance.details.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }

        