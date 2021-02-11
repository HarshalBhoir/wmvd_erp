# -*- coding: utf-8 -*-


from odoo.tools.translate import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import dateutil.parser

from odoo.exceptions import UserError , ValidationError


class hr_attendance_extension(models.Model):
    _inherit = "hr.attendance"


    attendance_status = fields.Selection([
        ('lop', 'Loss Of Pay'),
        ('half_day', 'Half Day'),
        ('full_day', 'Full Day'),
        ], string='Attendance Status', copy=False, index=True)

    meeting_count = fields.Integer(string="Meeting Count")
    hours_completed = fields.Float(string="Hours Completed")
    # today_date = fields.Date(string="Hours Completed")


    @api.model
    @api.multi
    def process_calculate_attendance_scheduler(self):
        print "hhhhhhhhhhhhhhhhhhhhhhhhhh"
        today = datetime.now() - timedelta(days=1)
        # daymonth = today.strftime( "%Y-%m-%d")
        daymonth = '2019-09-10'
                

        for user_id in self.env['res.users'].sudo().search([('active','=',True),('wp_salesperson','=',True)]):
            attendance_status = ''
            employee_ids = self.env['hr.employee'].sudo().search([
                                ('user_id','=',user_id.id),
                                '|',('active','=',False),('active','=',True)])
                    

            calendar_ids = self.env['calendar.event'].sudo().search([
                                ('expense_date','=',daymonth),
                                ('user_id','=',user_id.id),
                                ('company_id','=',3)
                                ])


            if calendar_ids:
                if len(calendar_ids) >=8:
                    attendance_status = 'full_day'
                elif len(calendar_ids) >= 4 :
                    attendance_status = 'half_day'
                else:
                    attendance_status = 'lop'


                start_datetime = date_to = dateutil.parser.parse(calendar_ids[-1].start_datetime)
                end_datetime = date_to = dateutil.parser.parse(calendar_ids[0].start_datetime)

                diff = end_datetime - start_datetime

                diff_hours = diff.total_seconds()/3600

                vals_line = {
                            'employee_id':employee_ids.id,
                            'check_out': calendar_ids[0].start_datetime,
                            'check_in': calendar_ids[-1].start_datetime,
                            'attendance_status': attendance_status,
                            'meeting_count': len(calendar_ids),
                            'hours_completed' : diff_hours,
                                                        
                        }
                create_attendance = self.env['hr.attendance'].sudo().create(vals_line)








