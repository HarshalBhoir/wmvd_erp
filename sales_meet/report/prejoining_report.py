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

class WpHrPrejoiningReport(models.TransientModel):
    _name = "wp.hr.prejoining.report"
    
    name = fields.Char('Name', size=256)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string="End Date")
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    file_name = fields.Binary('Prejoining Report', readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')

    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]

    @api.multi
    def action_wp_prejoining_report(self):
        file = StringIO()
        if self.start_date and self.end_date:
            if self.company_id:
                hr_applicant = self.env['wp.employee.prejoining.details'].search([('date_of_joining', '>=', self.start_date), 
                                                            ('date_of_joining', '<=', self.end_date), 
                                                            ('company_id','=',self.company_id.id)])
            else:
                hr_applicant = self.env['wp.employee.prejoining.details'].search([('date_of_joining', '>=', self.start_date), 
                                                            ('date_of_joining', '<=', self.end_date)])
            


        self.ensure_one()

        if (not hr_applicant):
            raise Warning(_('Record Not Found'))

        # self.sudo().unlink()
        if hr_applicant :
            rep_name = 'Applicant Prejoining Details Report'
            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet(rep_name)
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; \
                borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center, vertical center; \
                borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color yellow;' )
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
            worksheet.col(1).width = 8000  # Employee Name
            worksheet.col(2).width = 3002  #DOJ
            worksheet.col(3).width = 8003  #Reporting Manager
            worksheet.col(4).width = 8004  #HOD/ZSM 
            worksheet.col(5).width = 7005  #Designation 
            worksheet.col(6).width = 5006  #Location
            worksheet.col(7).width = 3007  #Domain
            worksheet.col(8).width = 8008  #Buddy Name
            worksheet.col(9).width = 5009  #7 Day Orientation Plan Received on
            worksheet.col(10).width = 3010  #Reminder 1 Sent on 
            worksheet.col(11).width = 3011  #Reminder 2 Sent on 
            worksheet.col(12).width = 3012  #Reminder 3 Sent on 
            worksheet.col(13).width = 3013  #KRA Received 
            worksheet.col(14).width = 5014  #KRA follow up Intimation with BHR
            worksheet.col(15).width = 5015  #Mail to Reporting Manager on
            worksheet.col(16).width = 5016  #Call by Reporting to joinee on
            worksheet.col(17).width = 5017  #Mail & Call to Candidate on
            worksheet.col(18).width = 3018  #Mail to IT on
            worksheet.col(19).width = 4019  #Mail to Admin on
            worksheet.col(20).width = 3020  #SIM Card Request Sent On
            worksheet.col(21).width = 3021  #Name of EL Member
            worksheet.col(22).width = 3022  #Mail to EL Member
            worksheet.col(23).width = 4023  #Call by EL member  to joinee on
            worksheet.col(24).width = 3024  #GIF Shared on 
            worksheet.col(25).width = 3025  #SMS 1
            worksheet.col(26).width = 3026  #SMS 2
            worksheet.col(27).width = 3027  #SMS 3
            worksheet.col(28).width = 5028  #Mail to Reporting Manager on
            worksheet.col(29).width = 3029  #Mail to Candidate on
            worksheet.col(30).width = 3030  #Mail to IT on
            worksheet.col(31).width = 3031  #Mail to Admin on
            worksheet.col(32).width = 3032  #SIM Card Request Sent on 
            worksheet.col(33).width = 3033  #Mail to EL Club Member
            worksheet.col(34).width = 3034  #Photo received on 
            worksheet.col(35).width = 5035  #ID Card Details received on 
            worksheet.col(36).width = 4036  #Bank Details  received on 
            worksheet.col(37).width = 3037  #Welcome Note{Only for HO Mahape and Sanpada}mailed on 09/09/2017
            worksheet.col(38).width = 8038  #Confirmation mail to Admin in cases Sales emplyoee does not join 
            worksheet.col(39).width = 3039  #Lunch
            worksheet.col(40).width = 3040  #Comment if any
            
            # Headers
            header_fields = ['Sr. No',
                            'Employee Name',
                            'DOJ',
                            'Reporting Manager',
                            'HOD/ZSM ',
                            'Designation ',
                            'Location',
                            'Domain',
                            'Buddy Name',
                            '7 Day Orientation Plan Received on',
                            'Reminder 1 Sent on',
                            'Reminder 2 Sent on',
                            'Reminder 3 Sent on',
                            'KRA Received ',
                            'KRA follow up Intimation with BHR',
                            'Mail to Reporting Manager on',
                            'Call by Reporting to joinee on',
                            'Mail & Call to Candidate on',
                            'Mail to IT on',
                            'Mail to Admin on',
                            'SIM Card Request Sent On',
                            'Name of EL Member',
                            'Mail to EL Member',
                            'Call by EL member  to joinee on',
                            'GIF Shared on ',
                            'SMS 1',
                            'SMS 2',
                            'SMS 3',
                            'Mail to Reporting Manager on',
                            'Mail to Candidate on',
                            'Mail to IT on',
                            'Mail to Admin on',
                            'SIM Card Request Sent on ',
                            'Mail to EL Club Member',
                            'Photo received on ',
                            'ID Card Details received on ',
                            'Bank Details  received on ',
                            'Welcome Note',
                            'Confirmation mail to Admin in cases Sales emplyoee does not join ',
                            'Lunch',
                            'Comment if any',

                            ]
            row_index += 1
         
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

            count = 0
            for hr_applicant_id in hr_applicant:
                if hr_applicant_id:
                    
                    count +=1
                    worksheet.write(row_index,0,count,base_style )
                    worksheet.write(row_index,1,hr_applicant_id.applicant_id.name or '', base_style )
                    worksheet.write(row_index,2,hr_applicant_id.date_of_joining  or '', base_style )
                    worksheet.write(row_index,3,hr_applicant_id.parent_id.name_related or '', base_style )
                    worksheet.write(row_index,4,hr_applicant_id.coach_id.name_related or '', base_style )
                    worksheet.write(row_index,5,hr_applicant_id.job_id.name or '', base_style )
                    worksheet.write(row_index,6,hr_applicant_id.work_location or '', base_style )
                    worksheet.write(row_index,7,hr_applicant_id.domain or '', base_style )

                    worksheet.write(row_index,8,hr_applicant_id.buddy_id.name_related or '', base_style )
                    worksheet.write(row_index,9,hr_applicant_id.orientation_plan or '', base_style )
                    worksheet.write(row_index,10,hr_applicant_id.reminder1 or '', base_style )
                    worksheet.write(row_index,11,hr_applicant_id.reminder2 or '', base_style )
                    worksheet.write(row_index,12,hr_applicant_id.reminder3 or '', base_style )
                    worksheet.write(row_index,13,hr_applicant_id.kra_received or '', base_style )
                    worksheet.write(row_index,14,hr_applicant_id.kra_intimation or '', base_style )
                    worksheet.write(row_index,15,hr_applicant_id.reporting_manager_mail or '', base_style )
                    worksheet.write(row_index,16,hr_applicant_id.manager_joinee_call or '', base_style )

                    worksheet.write(row_index,17,hr_applicant_id.mail_call_candidate or '', base_style )
                    worksheet.write(row_index,18,hr_applicant_id.mail_to_it or '', base_style )
                    worksheet.write(row_index,19,hr_applicant_id.mail_to_admin or '', base_style )
                    worksheet.write(row_index,20,hr_applicant_id.sim_request or '', base_style )
                    worksheet.write(row_index,21,hr_applicant_id.el_member_id.name_related or '', base_style )
                    worksheet.write(row_index,22,hr_applicant_id.mail_to_el_member or '', base_style )

                    worksheet.write(row_index,23,hr_applicant_id.el_member_joinee_call or '', base_style )
                    worksheet.write(row_index,24,hr_applicant_id.gif_shared or '', base_style )

                    worksheet.write(row_index,25,hr_applicant_id.sms1 or '', base_style )
                    worksheet.write(row_index,26,hr_applicant_id.sms2 or '', base_style )
                    worksheet.write(row_index,27,hr_applicant_id.sms3 or '', base_style )
                    worksheet.write(row_index,28,hr_applicant_id.reporting_manager_mail2 or '', base_style )
                    worksheet.write(row_index,29,hr_applicant_id.mail_call_candidate2 or '', base_style )
                    worksheet.write(row_index,30,hr_applicant_id.mail_to_it2 or '', base_style )
                    worksheet.write(row_index,31,hr_applicant_id.mail_to_admin2 or '', base_style )
                    worksheet.write(row_index,32,hr_applicant_id.sim_request2 or '', base_style )
                    worksheet.write(row_index,33,hr_applicant_id.mail_to_el_member2 or '', base_style )

                    worksheet.write(row_index,34,hr_applicant_id.photo_received or '', base_style )
                    worksheet.write(row_index,35,hr_applicant_id.id_card_details or '', base_style )
                    worksheet.write(row_index,36,hr_applicant_id.bank_details or '', base_style )
                    worksheet.write(row_index,37,hr_applicant_id.welcome_note or '', base_style )
                    worksheet.write(row_index,38,hr_applicant_id.confirmation_mail_if_joinee_doesnot_join or '', base_style )
                    worksheet.write(row_index,39,hr_applicant_id.lunch or '', base_style )
                    worksheet.write(row_index,40,hr_applicant_id.comment or '', base_style )
                    
                    row_index += 1

            row_index +=1
            workbook.save(fp)

            out = base64.encodestring(fp.getvalue())

            self.write({'state': 'get','file_name': out,'name':self.name+'.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'wp.hr.prejoining.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }