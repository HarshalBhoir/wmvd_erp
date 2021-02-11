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

class WpHrApplicantReport(models.TransientModel):
    _name = "wp.hr.applicant.report"
    
    name = fields.Char('Name', size=256)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string="End Date")
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    file_name = fields.Binary('Applicant Report', readonly=True)
    company_id = fields.Many2one('res.company', string='Company')
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')

    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]

    @api.multi
    def action_wp_applicant_report(self):
        file = StringIO()
        if self.start_date and self.end_date:
            if self.company_id:
                hr_applicant = self.env['hr.applicant'].sudo().search([('requisition_date', '>=', self.start_date), 
                                                            ('requisition_date', '<=', self.end_date), 
                                                            ('company_id','=',self.company_id.id)])
            else:
                hr_applicant = self.env['hr.applicant'].sudo().search([('requisition_date', '>=', self.start_date), 
                                                            ('requisition_date', '<=', self.end_date)])
            


        self.ensure_one()

        if (not hr_applicant):
            raise Warning(_('Record Not Found'))

        # print eeereer
        status = ''
        # self.sudo().unlink()
        if hr_applicant :
            order_list = []
            second_heading = ''
            # file_name = self.name + '.xls'
            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet('Applicant Report')
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

          
        #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py

            rep_name = 'Applicant Details Report'
            if self.start_date and  self.end_date:
                start_date = datetime.strptime(self.start_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                end_date = datetime.strptime(self.end_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                if self.start_date == self.end_date:
                    rep_name = "Applicant Details Report(%s)" % (start_date)
                else:
                    rep_name = "Applicant Details Report(%s-%s)"  % (start_date, end_date)
            self.name = rep_name

            
            worksheet.write_merge(0, 1, 0, 5, self.name ,main_style)
            row_index = 2

            worksheet.row(3).height = 1000   #Sr No
                        
            worksheet.col(1).width = 3000   #Sr No
            worksheet.col(2).width = 8000   #Recruiter
            worksheet.col(3).width = 8000   #Position Name
            worksheet.col(4).width = 6000   #Requisition Date
            worksheet.col(5).width = 6000   #Requisition Code
            worksheet.col(6).width = 6000   #Allocation date
            worksheet.col(7).width = 6000   #Requisition Aeging(Req date to till date)
            worksheet.col(8).width = 6000   #Allocation Aeging to till date
            worksheet.col(9).width = 8000   #Candidate name
            worksheet.col(10).width = 8000   #Designation offered
            worksheet.col(11).width = 5000   #CTC  offered (in lacs)
            worksheet.col(12).width = 5000   #Location
            worksheet.col(13).width = 4000   #Domain
            worksheet.col(14).width = 6000   #Dept
            worksheet.col(15).width = 6000   #Company
            worksheet.col(16).width = 8000   #Hiring Manager
            worksheet.col(17).width = 6000   #Type of requisition (New replacement)
            worksheet.col(18).width = 8000   #Replacement Name
            worksheet.col(19).width = 7000   #Designation of ex employee
            worksheet.col(20).width = 5000   #CTC of ex employee
            worksheet.col(21).width = 5000   #CTC range in requisition form
            worksheet.col(22).width = 4000   #Status . 
            worksheet.col(23).width = 5000   #Mention name if cancelled/transferred
            worksheet.col(24).width = 6000   #Offer accepted On(TAT 1 day)
            worksheet.col(25).width = 5000   #Resignation received on
            worksheet.col(26).width = 6000   #Resignation Acceptance received on 
            worksheet.col(27).width = 6000   #Reminder 1(TAT 2 days after offer release)
            worksheet.col(28).width = 6000   #Reminder 2(TAT 4 days after offer release)
            worksheet.col(29).width = 6000   #Reminder 3 (TAT 7 days after offer release)
            worksheet.col(30).width = 6000   #Final reminder (TAT 10 days after offer release)
            worksheet.col(31).width = 6000   #Offer withdrawal Intimation (TAT 12days after offer release)
            worksheet.col(32).width = 4000   #CV Shared On
            worksheet.col(33).width = 5000   #Source Type
            worksheet.col(34).width = 5000   #Source Name
            worksheet.col(35).width = 5000   #Selection Date
            worksheet.col(36).width = 4000   #Offer Date
            worksheet.col(37).width = 8000   #Offer Released by
            worksheet.col(38).width = 4000   #DOJ
            worksheet.col(39).width = 5000   #Reference Check 1(Date)
            worksheet.col(40).width = 5000   #Reference Check 2(Date)
            worksheet.col(41).width = 5000   #Reference Check Sent to HR
            worksheet.col(42).width = 5000   #HR Reference Received(Date)
            worksheet.col(43).width = 5000   #HR Reference Check Sent to Reporting Manager(Date)
            worksheet.col(44).width = 5000   #HR Reference Check received - Reporting Manager(Date)
            worksheet.col(45).width = 4000   #Type of Aptitude Test conducted for HO Candidates
            worksheet.col(46).width = 4000   #Aptitude Test Scores
            worksheet.col(47).width = 4000   #Type of TechnicalTest conducted for HO Candidates
            worksheet.col(48).width = 4000   #Technical Test Score
            worksheet.col(49).width = 4000   #Test Result
            worksheet.col(50).width = 8000   #Name of Buddy Assigned if applicable
            worksheet.col(51).width = 5000   #Total CVs sent to hiring manager
            worksheet.col(52).width = 5000   #CV's Shared today
            worksheet.col(53).width = 5000   #Total Candidate Lined up for interview 
            worksheet.col(54).width = 5000   #Total interviews with Hiring Manager
            worksheet.col(55).width = 5000   #Time taken to close position
            worksheet.col(56).width = 5000   #Comment
            worksheet.col(57).width = 5000   #Current Status
            worksheet.col(58).width = 5000   #24 HRS / 48 HRS CV
            worksheet.col(59).width = 5000   #Backup CVs

            
            # Headers
            header_fields = ['Sr No',
                            'Recruiter',
                            'Position Name',
                            'Requisition Date',
                            'Requisition Code',
                            'Allocation date',
                            'Requisition Aeging',
                            'Allocation Aeging to till date',
                            'Candidate name',
                            'Designation offered',
                            'CTC offered (in lacs)',
                            'Location',
                            'Domain',
                            'Dept',
                            'Company',
                            'Hiring Manager',
                            'Type of requisition (New replacement)',
                            'Replacement Name',
                            'Designation of ex employee',
                            'CTC of ex employee',
                            'CTC range in requisition form',
                            'Status',
                            'Mention name if cancelled/transferred',
                            'Offer accepted On(TAT 1 day)',
                            'Resignation received on',
                            'Resignation Acceptance received on ',
                            'Reminder 1(TAT 2 days after offer release)',
                            'Reminder 2(TAT 4 days after offer release)',
                            'Reminder 3 (TAT 7 days after offer release)',
                            'Final reminder (TAT 10 days after offer release)',
                            'Offer withdrawal Intimation (TAT 12days after offer release)',
                            'CV Shared On',
                            'Source Type (Job Portal/Consultant/Reference)',
                            'Source Name',
                            'Selection Date',
                            'Offer Date',
                            'Offer Released by',
                            'DOJ',
                            'Reference Check 1(Date)',
                            'Reference Check 2(Date)',
                            'Reference Check Sent to HR',
                            'HR Reference Received(Date)',
                            'HR Reference Check Sent to Reporting Manager(Date)',
                            'HR Reference Check received - Reporting Manager(Date)',
                            'Type of Aptitude Test conducted for HO Candidates',
                            'Aptitude Test Scores',
                            'Type of TechnicalTest conducted for HO Candidates',
                            'Technical Test Score',
                            'Test Result',
                            'Name of Buddy Assigned if applicable',
                            'Total CVs sent to hiring manager',
                            'CVs Shared today',
                            'Total Candidate Lined up for interview ',
                            'Total interviews with Hiring Manager',
                            'Time taken to close position',
                            'Comment',
                            'Current Status',
                            '24 HRS / 48 HRS CV',
                            'Backup CVs',
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
                    worksheet.write(row_index,1,hr_applicant_id.user_id.name, base_style )
                    worksheet.write(row_index,2,hr_applicant_id.job_id.name  or '', base_style )
                    worksheet.write(row_index,3,hr_applicant_id.requisition_date or '', base_style )
                    worksheet.write(row_index,4,hr_applicant_id.requisition_code or '', base_style )
                    worksheet.write(row_index,5,hr_applicant_id.allocation_date or '', base_style )
                    worksheet.write(row_index,6,hr_applicant_id.requisition_aeging or '', base_style )
                    worksheet.write(row_index,7,hr_applicant_id.allocation_aeging or '', base_style )

                    worksheet.write(row_index,8,hr_applicant_id.name or '', base_style )
                    worksheet.write(row_index,9,hr_applicant_id.job_id.name or '', base_style )
                    worksheet.write(row_index,10,hr_applicant_id.salary_proposed or '', base_style )
                    worksheet.write(row_index,11,hr_applicant_id.location or '', base_style )
                    worksheet.write(row_index,12,hr_applicant_id.domain or '', base_style )
                    worksheet.write(row_index,13,hr_applicant_id.department_id.name or '', base_style )
                    worksheet.write(row_index,14,hr_applicant_id.company_id.name or '', base_style )
                    worksheet.write(row_index,15,hr_applicant_id.hiring_id.name or '', base_style )
                    worksheet.write(row_index,16,hr_applicant_id.requisition_type or '', base_style )

                    worksheet.write(row_index,17,hr_applicant_id.replacement_id.name_related or '', base_style )
                    worksheet.write(row_index,18,hr_applicant_id.replacement_job_id.name or '', base_style )
                    worksheet.write(row_index,19,hr_applicant_id.ex_emp_ctc or '', base_style )
                    worksheet.write(row_index,20,hr_applicant_id.salary_expected or '', base_style )
                    worksheet.write(row_index,21,hr_applicant_id.stage_id.name or '', base_style )
                    worksheet.write(row_index,22,hr_applicant_id.mention_cancel or '', base_style )

                    worksheet.write(row_index,23,hr_applicant_id.offer_accepted_tat1_date or '', base_style )
                    worksheet.write(row_index,24,hr_applicant_id.resignation_received_date or '', base_style )

                    worksheet.write(row_index,25,hr_applicant_id.resignation_acceptance_date or '', base_style )
                    worksheet.write(row_index,26,hr_applicant_id.reminder_1tat2_date or '', base_style )
                    worksheet.write(row_index,27,hr_applicant_id.reminder_2tat4_date or '', base_style )
                    worksheet.write(row_index,28,hr_applicant_id.reminder_3tat7_date or '', base_style )
                    worksheet.write(row_index,29,hr_applicant_id.final_reminder_tat10_date or '', base_style )
                    worksheet.write(row_index,30,hr_applicant_id.offer_withdrawal_intimation_date or '', base_style )
                    worksheet.write(row_index,31,hr_applicant_id.cv_shared_date or '', base_style )
                    worksheet.write(row_index,32,hr_applicant_id.source_id.name or '', base_style )
                    worksheet.write(row_index,33,hr_applicant_id.medium_id.name or '', base_style )
                    worksheet.write(row_index,34,hr_applicant_id.selection_date or '', base_style )
                    worksheet.write(row_index,35,hr_applicant_id.offer_date or '', base_style )
                    worksheet.write(row_index,36,hr_applicant_id.offer_released_id.name_related or '', base_style )
                    worksheet.write(row_index,37,hr_applicant_id.joining_date or '', base_style )
                    worksheet.write(row_index,38,hr_applicant_id.ref_check1_date or '', base_style )
                    worksheet.write(row_index,39,hr_applicant_id.ref_check2_date or '', base_style )
                    worksheet.write(row_index,40,hr_applicant_id.ref_check_hr_date or '', base_style )
                    worksheet.write(row_index,41,hr_applicant_id.hr_ref_received_date or '', base_style )
                    worksheet.write(row_index,42,hr_applicant_id.hr_ref_sent_repmanager_date or '', base_style )
                    worksheet.write(row_index,43,hr_applicant_id.hr_ref_received_repmanager_date or '', base_style )
                    worksheet.write(row_index,44,hr_applicant_id.aptitude_test or '', base_style )
                    worksheet.write(row_index,45,hr_applicant_id.aptitude_test_scores or '', base_style )
                    worksheet.write(row_index,46,hr_applicant_id.technical_test or '', base_style )
                    worksheet.write(row_index,47,hr_applicant_id.technical_test_scores or '', base_style )
                    worksheet.write(row_index,48,hr_applicant_id.test_result or '', base_style )
                    worksheet.write(row_index,49,hr_applicant_id.buddy_id.name_related or '', base_style )
                    worksheet.write(row_index,50,hr_applicant_id.total_cv_sent or '', base_style )
                    worksheet.write(row_index,51,hr_applicant_id.cv_shared_today or '', base_style )
                    worksheet.write(row_index,52,hr_applicant_id.total_candidate_lined or '', base_style )
                    worksheet.write(row_index,53,hr_applicant_id.total_interview_with_hiring_manager or '', base_style )
                    worksheet.write(row_index,54,hr_applicant_id.time_taken_close_position or '', base_style )
                    worksheet.write(row_index,55,hr_applicant_id.description or '', base_style )
                    worksheet.write(row_index,56,hr_applicant_id.current_status or '', base_style )
                    worksheet.write(row_index,57,hr_applicant_id.hrs24_48_cv or '', base_style )
                    worksheet.write(row_index,58,hr_applicant_id.backup_cv or '', base_style )


                    
                    row_index += 1

            row_index +=1
            workbook.save(fp)

            out = base64.encodestring(fp.getvalue())

            self.write({'state': 'get','file_name': out,'name':self.name+'.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'wp.hr.applicant.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                # 'views': [(False, 'form')],
                'target': 'new',
            }