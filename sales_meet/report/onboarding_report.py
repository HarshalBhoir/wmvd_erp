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

class WpHrOnboardingReport(models.TransientModel):
    _name = "wp.hr.onboarding.report"
    
    name = fields.Char('Name', size=256)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string="End Date")
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    file_name = fields.Binary('Onboarding Report', readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')

    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]

    @api.multi
    def action_wp_onboarding_report(self):
        file = StringIO()
        if self.start_date and self.end_date:
            if self.company_id:
                onboarding = self.env['wp.employee.onboarding.details'].search([('date_of_joining', '>=', self.start_date), 
                                                            ('date_of_joining', '<=', self.end_date), 
                                                            ('company_id','=',self.company_id.id)])
            else:
                onboarding = self.env['wp.employee.onboarding.details'].search([('date_of_joining', '>=', self.start_date), 
                                                            ('date_of_joining', '<=', self.end_date)])
            


        self.ensure_one()

        if (not onboarding):
            raise Warning(_('Record Not Found'))

        # self.sudo().unlink()
        if onboarding :
            rep_name = 'Onboarding Details Report'
            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet(rep_name)
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; \
                borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center, vertical center; \
                borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color green;' )
            base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
            base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
            base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color yellow;')

            if self.start_date and  self.end_date:
                start_date = datetime.strptime(self.start_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                end_date = datetime.strptime(self.end_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                if self.start_date == self.end_date:
                    rep_name2 = rep_name + " (%s)" % (start_date)
                else:
                    rep_name2 = rep_name + " (%s-%s)"  % (start_date, end_date)
            self.name = rep_name2

            
            worksheet.write_merge(0, 1, 0, 8, self.name ,main_style)
            row_index = 2

            worksheet.row(3).height = 1000   #Sr No

            worksheet.col(0).width = 3000  #Sr. No
            worksheet.col(1).width = 3001  #Emp No
            worksheet.col(2).width = 8002  #Employee Name
            worksheet.col(3).width = 6003  #Designation
            worksheet.col(4).width = 6004  #Department
            worksheet.col(5).width = 3005  #Domain
            worksheet.col(6).width = 3006  #Grade
            worksheet.col(7).width = 5007  #Location
            worksheet.col(8).width = 3008  #DOJ (DD/MM/YY)
            worksheet.col(9).width = 5009  #Offer Letter Issued On (TAT 1 days)
            worksheet.col(10).width = 4010  #Acceptance Documented
            worksheet.col(11).width = 5011  #Appointment Letter Issued On (TAT 1 days)
            worksheet.col(12).width = 4012  #Reason if release delayed
            worksheet.col(13).width = 5013  #AL Acceptance Documented
            worksheet.col(14).width = 5014  #ID CARD Request Sent to Admin (TAT 1 day)
            worksheet.col(15).width = 7015  #ID Card Issued on (TAT 5 days) (Weekly MIS sent by admin to HR)
            worksheet.col(16).width = 5016  #Visiting Card Request Sent to Admin (TAT  0 day)
            worksheet.col(17).width = 7017  #Visiting Card Issued on (TAT 5 days) (Weekly MIS sent by admin to HR)
            worksheet.col(18).width = 7018  #Joining KIT  issued on (TAT 0 day) (Weekly MIS sent by Admin to HR)
            worksheet.col(19).width = 8019  #Joining Booklet issued on (TAT 0 day) (Weekly MIS sent by Admin to HR)
            worksheet.col(20).width = 4020  #Joining Booklet Received on
            worksheet.col(21).width = 8021  #Sim Card Issued on (TAT 0 day) (Weekly MIS sent by admin to HR)
            worksheet.col(22).width = 7022  #Bank Letter Request to payroll sent on (TAT 1 days)
            worksheet.col(23).width = 8023  #Bank Letter Issued On (TAT 1 days) (Weekly MIS sent by payroll to HR)
            worksheet.col(24).width = 8024  #Reason if NO
            worksheet.col(25).width = 6025  #File Issued to payroll on (TAT 1-9 days)
            worksheet.col(26).width = 8026  #Saral entry done on (TAT 2-10 days) (Weekly MIS sent by payroll to HR)
            worksheet.col(27).width = 7027  #Portal link sent on (6-13days) (Weekly MIS sent by Pooja to HR)
            worksheet.col(28).width = 7028  #Portal Induction by Pooja (Weekly MIS sent by Pooja to HR)
            worksheet.col(29).width = 4029  #HR Tele - INDUCTION 
            worksheet.col(30).width = 7030  #HR F2F joining Induction (Weekly MIS sent by Nayan to HR)
            worksheet.col(31).width = 8031  #Mediclaim Induction by Pooja (TAT 0) (Weekly MIS sent by Pooja to HR)
            worksheet.col(32).width = 7032  #Travel Policy induction by Varad (mail sent to Varad on)
            worksheet.col(33).width = 5033  #7Day Orientation Booklet Issued on
            worksheet.col(34).width = 6034  #7Day Orientation Booklet Received on
            worksheet.col(35).width = 5035  #Relieving & Experience Letter Received on
            worksheet.col(36).width = 4036  #R&E Reminder 1 (30days from DOJ)
            worksheet.col(37).width = 5037  #R&E Reminder 2 (45 days from DOJ)
            worksheet.col(38).width = 4038  #Emp Declaration Letter (Y/N)
            worksheet.col(39).width = 4039  #Salary  on Hold 

            
            # Headers
            header_fields = [
                    'Sr. No',
                    'Emp No',
                    'Employee Name',
                    'Designation',
                    'Department',
                    'Domain',
                    'Grade',
                    'Location',
                    'DOJ',
                    'Offer Letter Issued On (TAT 1 days)',
                    'Acceptance Documented',
                    'Appointment Letter Issued On (TAT 1 days)',
                    'Reason if release delayed',
                    'AL Acceptance Documented',
                    'ID CARD Request Sent to Admin (TAT 1 day)',
                    'ID Card Issued on (TAT 5 days) (Weekly MIS sent by admin to HR)',
                    'Visiting Card Request Sent to Admin (TAT 0 day)',
                    'Visiting Card Issued on (TAT 5 days) (Weekly MIS sent by admin to HR)',
                    'Joining KIT  issued on (TAT 0 day) (Weekly MIS sent by Admin to HR)',
                    'Joining Booklet issued on (TAT 0 day) (Weekly MIS sent by Admin to HR)',
                    'Joining Booklet Received on',
                    'Sim Card Issued on (TAT 0 day) (Weekly MIS sent by admin to HR)',
                    'Bank Letter Request to payroll sent on (TAT 1 days)',
                    'Bank Letter Issued On (TAT 1 days) (Weekly MIS sent by payroll to HR)',
                    'Reason if NO',
                    'File Issued to payroll on (TAT 1-9 days)',
                    'Saral entry done on (TAT 2-10 days) (Weekly MIS sent by payroll to HR)',
                    'Portal link sent on (6-13days) (Weekly MIS sent to HR)',
                    'Portal Induction (Weekly MIS sent to HR)',
                    'HR Tele - INDUCTION ',
                    'HR F2F joining Induction (Weekly MIS sent to HR)',
                    'Mediclaim Induction (TAT 0) (Weekly MIS sent to HR)',
                    'Travel Policy induction',
                    '7Day Orientation Booklet Issued on',
                    '7Day Orientation Booklet Received on',
                    'Relieving & Experience Letter Received on',
                    'R&E Reminder 1 (30days from DOJ)',
                    'R&E Reminder 2 (45 days from DOJ)',
                    'Emp Declaration Letter',
                    'Salary on Hold ',

                ]
            row_index += 1
         
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

            count = 0
            for onboarding_id in onboarding:
                if onboarding_id:
                    
                    count +=1
                    worksheet.write(row_index,0,count,base_style )
                    worksheet.write(row_index,1,onboarding_id.employee_id.emp_id or '', base_style )
                    worksheet.write(row_index,2,onboarding_id.employee_id.name_related  or '', base_style )
                    worksheet.write(row_index,3,onboarding_id.job_id.name or '', base_style )
                    worksheet.write(row_index,4,onboarding_id.department_id.name or '', base_style )
                    worksheet.write(row_index,5,onboarding_id.domain or '', base_style )
                    worksheet.write(row_index,6,onboarding_id.grade_id.name or '', base_style )
                    worksheet.write(row_index,7,onboarding_id.work_location or '', base_style )

                    worksheet.write(row_index,8,onboarding_id.date_of_joining or '', base_style )
                    worksheet.write(row_index,9,onboarding_id.offer_issued_tat1_date or '', base_style )
                    worksheet.write(row_index,10,onboarding_id.acceptance_documented or '', base_style )
                    worksheet.write(row_index,11,onboarding_id.appointment_letter_issued_tat1_date or '', base_style )
                    worksheet.write(row_index,12,onboarding_id.delayed_reason or '', base_style )
                    worksheet.write(row_index,13,onboarding_id.al_acceptance_documented or '', base_style )
                    worksheet.write(row_index,14,onboarding_id.id_card_request or '', base_style )
                    worksheet.write(row_index,15,onboarding_id.id_card_issued or '', base_style )
                    worksheet.write(row_index,16,onboarding_id.visiting_card_request or '', base_style )

                    worksheet.write(row_index,17,onboarding_id.visiting_card_issued or '', base_style )
                    worksheet.write(row_index,18,onboarding_id.joining_kit_issued or '', base_style )
                    worksheet.write(row_index,19,onboarding_id.joining_booklet_issued or '', base_style )
                    worksheet.write(row_index,20,onboarding_id.joining_booklet_received or '', base_style )
                    worksheet.write(row_index,21,onboarding_id.sim_card_issued or '', base_style )
                    worksheet.write(row_index,22,onboarding_id.bank_letter_request_payroll or '', base_style )

                    worksheet.write(row_index,23,onboarding_id.bank_letter_issued or '', base_style )
                    worksheet.write(row_index,24,onboarding_id.reason_if_no or '', base_style )

                    worksheet.write(row_index,25,onboarding_id.file_issued_to_payroll or '', base_style )
                    worksheet.write(row_index,26,onboarding_id.saral_entry or '', base_style )
                    worksheet.write(row_index,27,onboarding_id.portal_link_sent or '', base_style )
                    worksheet.write(row_index,28,onboarding_id.portal_induction or '', base_style )
                    worksheet.write(row_index,29,onboarding_id.hr_tele_induction or '', base_style )
                    worksheet.write(row_index,30,onboarding_id.hr_f2f_joining_induction or '', base_style )
                    worksheet.write(row_index,31,onboarding_id.mediclaim_induction or '', base_style )
                    worksheet.write(row_index,32,onboarding_id.travel_policy_induction or '', base_style )
                    worksheet.write(row_index,33,onboarding_id.orientation_booklet_issued or '', base_style )

                    worksheet.write(row_index,34,onboarding_id.orientation_booklet_received or '', base_style )
                    worksheet.write(row_index,35,onboarding_id.relieving_experience_letter_received or '', base_style )
                    worksheet.write(row_index,36,onboarding_id.re_reminder1 or '', base_style )
                    worksheet.write(row_index,37,onboarding_id.re_reminder2 or '', base_style )
                    worksheet.write(row_index,38,onboarding_id.emp_declaration_letter or '', base_style )
                    worksheet.write(row_index,39,onboarding_id.salary_on_hold or '', base_style )
                    
                    row_index += 1

            row_index +=1
            workbook.save(fp)

            out = base64.encodestring(fp.getvalue())

            self.write({'state': 'get','file_name': out,'name':self.name+'.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'wp.hr.onboarding.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }