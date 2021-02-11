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

    @api.depends('check_in', 'check_out')
    @api.multi
    def _compute_duration(self):
        for attendance in self:
            if attendance.check_out:
                delta = datetime.strptime(attendance.check_out, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(
                    attendance.check_in, DEFAULT_SERVER_DATETIME_FORMAT)
                attendance.hours_completed = delta.total_seconds() / 3600.0
                print "vvvvvvvvvvvvvvvvvvvv_compute_duration vvvvvvvvvvvvvvvvvvvvvvvvv" , attendance.hours_completed


    def _compute_attendance_count(self):
        print "11111111111111111"
        status_attendance = ''
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                delta = datetime.strptime(attendance.check_out, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(
                    attendance.check_in, DEFAULT_SERVER_DATETIME_FORMAT)
                hours_completed = delta.total_seconds() / 3600.0
                print "hhhhhhhhhhhhhhhhhhhh _compute_attendance_count hhhhhhhhhhhhhhhhhhhhhhhhh" , hours_completed

                if hours_completed >= 8:
                    attendance.attendance_count = 1
                if hours_completed <= 4:
                    attendance.attendance_count = 0.5
            else:
                attendance.attendance_count = 0

    attendance_status = fields.Selection([('lop', 'Loss Of Pay'),('half_day', 'Half Day'),
                                        ('full_day', 'Full Day'),], string='Attendance Status', copy=False, index=True)

    meeting_count = fields.Integer(string="Meeting Count")
    attendance_count = fields.Float(string="Attendance Count", compute=_compute_attendance_count, store=True, digits=(16, 2))
    hours_completed = fields.Float(string="Hours Completed", compute=_compute_duration, store=True, digits=(16, 2))
    attendance_date = fields.Date(string="Date" , default=lambda self: fields.datetime.now())
    checkout_type = fields.Selection([('s', 'System'), 
                                      ('m', 'Manual')], default='m', string='Checkout Type')

    @api.multi
    def autoclose_attendance(self):
        # self.ensure_one()
        # vals = {'check_out': datetime.now(), 'checkout_type': 's'}
        self.write({'check_out': datetime.now(), 'checkout_type': 's'})

    @api.model
    def check_for_incomplete_attendances(self):
        # stale_attendances = self.search([('check_out', '=', False),('attendance_date', '=', date.today())])
        # print "aaaaaaaaaaaaaaaaaaaaaa" , stale_attendances, date.today()
        # for att in stale_attendances:
        #     # att.autoclose_attendance()
        #     att.write({'check_out': datetime.now(), 'checkout_type': 's'})


        self._cr.execute("""update hr_attendance set check_out = attendance_date + interval '16h 30m' , \
         checkout_type = 's' , \
        hours_completed = cast( (to_char((attendance_date + interval '16h 30m' - check_in ), 'HH24.MI') ) as float) \
        where check_out is null and check_in < (attendance_date + interval '16h 30m') """)


    @api.model
    @api.multi
    def process_calculate_attendance_scheduler(self):
        today = datetime.now() - timedelta(days=1)
        # daymonth = today.strftime( "%Y-%m-%d")
        daymonth = '2019-09-10'

        for user_id in self.env['res.users'].sudo().search([('active','=',True),('wp_salesperson','=',True)]):
            attendance_status = ''
            employee_ids = self.env['hr.employee'].sudo().search([
                                ('user_id','=',user_id.id),'|',('active','=',False),('active','=',True)])
                    
            calendar_ids = self.env['calendar.event'].sudo().search([
                                ('expense_date','=',daymonth), ('user_id','=',user_id.id), ('company_id','=',3)])

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








