# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
from odoo import tools, api
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


BOOLEAN_STATE = [('YES', 'YES'), ('NO', 'NO'), ('NA', 'NA')]

RECEIVED_STATE = [('RECEIVED', 'RECEIVED'),('NOT RECEIVED', 'NOT RECEIVED')]

DEACTIVATED_STATE = [('DEACTIVATED', 'DEACTIVATED'), ('N/A', 'N/A'), ('OTHER', 'OTHER')]

class wp_exit_process_automation(models.Model):
	""" WP Exit Process Automation """
	_name = "wp.exit.process.automation"
	_inherit = 'mail.thread'
	_description = "Exit Process"

	#Basic Details
	name = fields.Char(string='Name')
	employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade')
	emp_id = fields.Char(string='EmpID')
	job_id = fields.Many2one('hr.job', 'Designation')
	grade_id = fields.Many2one("grade.master", string="Grade")
	department_id = fields.Many2one('hr.department', 'Department')
	company_id = fields.Many2one('res.company', 'Company')
	employment_status = fields.Selection([
				('CONTRACT', 'CONTRACT'),
				('CONFIRMED', 'CONFIRMED'),
				('PROBATION', 'PROBATION')],
				string='Employment Status',track_visibility='onchange')

	domain = fields.Selection([
				('Plant', 'Plant'),
				('HO', 'HO'),
				('Sales', 'Sales')], string='Domain', copy=False)

	location = fields.Char(string='Location')
	doj = fields.Date(string='DOJ')
	other_resignation = fields.Char(string='Comments(In Case of Others)')
	fnf_status = fields.Selection([
				('CLOSED', 'CLOSED'),
				('EXIT DOCUMENTS PENDING', 'EXIT DOCUMENTS PENDING'),
				('CLEARANCE PENDING WITH STAKEHOLDER', 'CLEARANCE PENDING WITH STAKEHOLDER'),
				('CLEARANCE PENDING WITH HR', 'CLEARANCE PENDING WITH HR'),
				('CLEARANCE PENDING WITH STAKEHOLDER- SUNIL BHAKRE', 'CLEARANCE PENDING WITH STAKEHOLDER- SUNIL BHAKRE'),
				('CURRENTLY SERVING NOTICE PERIOD', 'CURRENTLY SERVING NOTICE PERIOD'),
				('RECOVERY PENDING : ACTION BY HR', 'RECOVERY PENDING : ACTION BY HR'),
				('RECOVERY PENDING : ACTION BY HR COMPLIANCE', 'RECOVERY PENDING : ACTION BY HR COMPLIANCE'),
				('PENDING WITH PAYROLL', 'PENDING WITH PAYROLL'),
				('ABSCONDING', 'ABSCONDING'),
				('TERMINATE', 'TERMINATE'),
				('RESIGNATION WITHDRAWN', 'RESIGNATION WITHDRAWN'),
				('OTHERS', 'OTHERS')],
				string='FnF Status',track_visibility='onchange')

	other_status = fields.Char(string='Comments(In Case of Others)')

	#Resignation Details

	dor = fields.Date(string='DOR')
	resignation_intimation_to_hr_or_admin_and_it = fields.Date(string='Resignation intimation to HR/ Admin & IT')
	hold_expenses_and_salary = fields.Date(string='Hold Expenses & Salary')
	type_of_resignation = fields.Selection([
				('SELF', 'SELF'),
				('ENABLED', 'ENABLED'),
				('TERMINATE', 'TERMINATE'),
				('ABSCOND', 'ABSCOND'),
				('OTHER', 'OTHER')],
				string='Resignation Type',track_visibility='onchange')

	date_on_which_acceptance_mail_sent  = fields.Date(string='Date on which Acceptance mail sent')
	last_working_day = fields.Date(string='Last working day')
	last_working_day_hod = fields.Date(string='Last Working Day (HOD)')
	last_working_day_attendance = fields.Date(string='Last Working Day (Attendance)')
	early_release = fields.Selection(BOOLEAN_STATE, string='Early Release',track_visibility='onchange')
	early_release_reason = fields.Char(string='Early Release Reason')

	#Exit Documents

	exit_documents_received = fields.Selection(BOOLEAN_STATE, string='Exit Documents Received')
	exit_documents_submitted_by_employee_on  = fields.Date(string='Exit documents submitted by employee on')
	exit_documents_reminder1  = fields.Date(string='Exit Documents Reminder 1')
	exit_documents_received1 = fields.Selection(BOOLEAN_STATE, string='Exit Documents Received after 1st Reminder')

	exit_documents_reminder2  = fields.Date(string='Exit Documents Reminder 2')
	exit_documents_received2 = fields.Selection(BOOLEAN_STATE, string='Exit Documents Received after 2nd Reminder')

	exit_documents_reminder3  = fields.Date(string='Exit Documents Reminder 3')
	exit_documents_received3 = fields.Selection(BOOLEAN_STATE, string='Exit Documents Received after 3rd Reminder')

	exit_documents_reminder_to_employees_after_last_day = fields.Text(string='Exit Documents Reminder to employees after last day')
	exit_documents_comments = fields.Char(string='Comments')

	#Clearance from Stakeholders

	clearance_pending_with = fields.Selection([
				('ADMIN DEPARTMENT', 'ADMIN DEPARTMENT'),
				('IT DEPARTMENT', 'IT DEPARTMENT'),
				('ACCOUNTS DEPARTMENT', 'ACCOUNTS DEPARTMENT'),
				('SALES SUPPORT TEAM', 'SALES SUPPORT TEAM')],
				string='Clearance pending with (Name of person) (on Hold)',track_visibility='onchange')

	clearance_pending_it = fields.Selection(BOOLEAN_STATE, string='Clearance From IT')
	clearance_pending_admin = fields.Selection(BOOLEAN_STATE, string='Clearance From Admin')
	clearance_pending_sales_support = fields.Selection(BOOLEAN_STATE, string='Clearance From Sales Support')
	clearance_pending_accounts = fields.Selection(BOOLEAN_STATE, string='Clearance From Accounts')
	clearance_pending_hod_zsm = fields.Selection(BOOLEAN_STATE, string='Clearance From HOD/ZSM')

	comments_it = fields.Char(string='Comments From IT')
	comments_admin = fields.Char(string='Comments From Admin')
	comments_sales_support = fields.Char(string='Comments From Sales Support')
	comments_accounts = fields.Char(string='Comments From Accounts')
	comments_hod_zsm = fields.Char(string='Comments From HOD/ZSM')

	email_id_deactivated  = fields.Selection(DEACTIVATED_STATE, string='Email-id Deactivated')
	comments_email = fields.Char(string='Comments - Email Status')

	sim_card_status = fields.Selection(DEACTIVATED_STATE, string='SIM Card Status')
	comments_sim = fields.Char(string='Comments - SIM Status')


	#Farewell

	eligible_farewell_lunch = fields.Selection(BOOLEAN_STATE, string='Eligible for Farewell Lunch')
	mail_to_manager_sent_on = fields.Date(string='Mail to Manager Sent on')
	bill_sent_to_admin_on = fields.Date(string='Bill Sent to Admin On')
	amount_paid_on_by_admin = fields.Date(string='Amount paid on')

	eligible_farewell_gift = fields.Selection(BOOLEAN_STATE, string='Eligible for Farewell Gift')
	mail_to_admin_on  = fields.Date(string='Mail to Admin on')
	farwell_gift_sent_on = fields.Date(string='Farwell Gift Sent on')

	eligible_farewell_ecard = fields.Selection(BOOLEAN_STATE, string='Eligible for Farewell E-Card')
	farwell_ecard_sent_on = fields.Date(string='Farwell E-Card Sent on')

	eligible_farewell_skype = fields.Selection(BOOLEAN_STATE, string='Eligible for Farewell Skype Call')
	farewell_skype = fields.Date(string='Farewell Skype Call Mail to the Team')
	farewell_skype_date = fields.Date(string='Date on which Skype call was conducted')

	eligible_bhr_exit_interview = fields.Selection(BOOLEAN_STATE, string='Eligible for BHR exit Interview')
	mail_to_bhr = fields.Date(string='Mail to BHR for Exit Interview')
	exit_interview_date = fields.Date(string='Date on Which Exit Interview was conducted')

	# FNF Input Sheet

	fnf_input_forwarded_to_payroll = fields.Selection(BOOLEAN_STATE, string='FnF input  forwarded to payroll')
	fnf_input_forwarded_to_payroll_on = fields.Date(string='FnF input forwarded to payroll on')
	file_handover_payroll = fields.Selection(BOOLEAN_STATE, string='File Handover to Payroll')
	file_handover_payroll_on = fields.Date(string='File Handover to Payroll on')
	fnf_released = fields.Selection(BOOLEAN_STATE, string='FnF released')
	fnf_released_on = fields.Date(string='FnF released on')
	file_handover_mail_to = fields.Date(string='File Handover Mail to Payroll')

	# Relieving
	eligible_experience_letter = fields.Selection(BOOLEAN_STATE, string='Eligible for Relieving & Experience Letter')
	acceptance_received = fields.Selection(BOOLEAN_STATE, string='Acceptance received on Relieving & Experience')
	relieving_and_experience_letter_given_on = fields.Date(string='Relieving & Experience letter given on')
	relieving_and_experience_acceptance_on = fields.Date(string='Relieving & Experience acceptance on')
	remarks = fields.Text(string='Remarks')


	# Recovery

	notice_period_recovery = fields.Char(string='Notice Period Recovery')
	notice_period_payment = fields.Char(string='Notice Period Payment')
	clearance_pending_since = fields.Date(string='Clearance Pending since')
	clearance_received_from_zsm_and_hod_on_mail = fields.Date(string='Clearance Received from ZSM & HOD on mail')

	
	
	
	recovery_in_case_any = fields.Selection([
									('YES', 'YES'),
									('NO', 'NO'),
									('HR COMPLIANCE', 'HR COMPLIANCE')],
									string='Recovery in any case',track_visibility='onchange')

	recovery_reason = fields.Text(string='Recovery Reason')
	recovery_amount = fields.Char(string='Recovery Amount')

	recovery_intimation_mail_to_ex_employee  = fields.Date(string='Recovery intimation mail to ex employee')
	
	recovery_amount_received = fields.Selection(RECEIVED_STATE, string='Recovery Amount Received')
	recovery_amount_received1 = fields.Selection(RECEIVED_STATE, string='Recovery Amount Received After 1st Reminder')

	recovery_reminder_mail_1  = fields.Date(string='Recovery Reminder mail 1')
	recovery_amount_received2 = fields.Selection(RECEIVED_STATE, string='Recovery Amount Received After 2nd Reminder')

	recovery_reminder_mail_2  = fields.Date(string='Recovery Reminder mail 2')
	recovery_amount_received3 = fields.Selection(RECEIVED_STATE, string='Recovery Amount Received After 3rd Reminder')
	recovery_reminder_mail_3  = fields.Date(string='Recovery Reminder mail 3')

	first_recovery_letter_via_registered = fields.Selection(BOOLEAN_STATE, string='1st Recovery Letter via registered post shared')
	first_recovery_letter_via_registered_post  = fields.Date(string='1st Recovery Letter via registered post')
	first_recovery_letter_recipt_received_on  = fields.Date(string='1st Recovery Letter Receipt received on')
	second_recovery_letter_via_registered = fields.Selection(BOOLEAN_STATE, string='2nd Recovery Letter via registered post shared')

	second_recovery_letter  = fields.Date(string='2nd Recovery Letter')
	second_recovery_letter_recipt_received_on  = fields.Date(string='2nd Recovery Letter Receipt received on')
	third_recovery_letter_via_registered = fields.Selection(BOOLEAN_STATE, string='3rd Recovery Letter via registered post shared')

	third_recovery_letter  = fields.Date(string='3rd Recovery Letter')
	third_recovery_letter_recipt_received_on  = fields.Date(string='3rd Recovery Letter Receipt received on')
	recovery_letter_recipt_received_on  = fields.Date(string='Recovery Letter Receipt received on')

	recovery_status = fields.Selection(RECEIVED_STATE, string='Recovery Status')
	recovery_received_amount_date  = fields.Date(string='Recovery Received amount')

	recovery_forwardedto_cmpl_date  = fields.Date(string='RCase Forwaded to HR compliance')

	case_fwd_hr_cmpl = fields.Selection(BOOLEAN_STATE, string='Case Forwaded to HR compliance')
	case_fwd_hr_cmpl_on = fields.Date(string='Case Forwaded to HR compliance On')


	recovery_amount_hr_cmpl = fields.Char(string='Recovery Amount')
	recovery_reason_hr_cmpl = fields.Char(string='Recovery Reason')
	legal_notice_sent_cmpl_team1  = fields.Date(string='Legal Notice sent by Compliance Team 1')
	legal_notice_sent_cmpl_team2  = fields.Date(string='Legal Notice sent by Compliance Team 2')
	legal_notice_sent_cmpl_team3  = fields.Date(string='Legal Notice sent by Compliance Team 3')
	legal_notice_sent_ext_lawyer  = fields.Date(string='Legal Notice sent through External Lawyer')
	reason_closure = fields.Char(string='Reason for closure ')


	@api.model
	def create(self, vals):
		result = super(wp_exit_process_automation, self).create(vals)
		result.name = "EP/" + str(result.company_id.short_name)  +"/"  + str(result.id).zfill(5)
		return result	


	@api.onchange('employee_id')
	def onchange_employee_id(self):
		if self.employee_id :
			self.department_id = self.employee_id.department_id.id
			self.company_id = self.employee_id.company_id.id
			self.domain = self.employee_id.domain
			self.job_id = self.employee_id.job_id.id
			self.location = self.employee_id.work_location
			self.grade_id = self.employee_id.grade_id.id
			self.doj = self.employee_id.date_of_joining
			self.emp_id = self.employee_id.emp_id
		else:
			self.department_id = False
			self.company_id = False
			self.domain = False
			self.job_id = False
			self.location = False
			self.grade_id = False
			self.doj = False
			self.emp_id = False

	@api.onchange('early_release')
	def onchange_early_release(self):
		if self.early_release in ('NO','NA') :
			self.early_release_reason = 'NA'
		else:
			self.early_release_reason = ''





	


