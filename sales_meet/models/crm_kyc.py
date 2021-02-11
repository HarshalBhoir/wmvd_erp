# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import api, fields, models, _, SUPERUSER_ID, tools
import logging
from odoo.exceptions import UserError, ValidationError
from werkzeug import url_encode

todaydate = "{:%d-%b-%y}".format(datetime.now())

class wp_res_partner(models.Model):
	_name = "wp.res.partner"
	_description="WP Res Partner"
	_inherit = 'mail.thread'
	_order	= 'id desc'


	name = fields.Char(string='Distributor')
	street = fields.Char()
	street2 = fields.Char()
	zip = fields.Char(change_default=True)
	city = fields.Char()
	state_id = fields.Many2one("res.country.state", string='State')
	country_id = fields.Many2one('res.country', string='Country')
	partner_group_id = fields.Many2one("res.partner.group", string="Partner Group")
	bp_code = fields.Char('Partner Code')
	pricelist = fields.Char('Pricelist')
	district_id = fields.Many2one("res.state.district", string='District')

	state = fields.Selection([
						('Draft', 'Draft'),
						('Submit', 'Submit'),
						('Approved', 'Approved'),
						('Posted', 'Posted')],default='Draft',
						string='Status',track_visibility='onchange')

	customer = fields.Boolean(string='Is a Customer', default=True)
	supplier = fields.Boolean(string='Is a Vendor')
	employee = fields.Boolean(help="Check this box if this contact is an Employee.")
	active = fields.Boolean(default=True)
	partner_id = fields.Many2one('res.partner', string='Partner', copy=False)
	partner_name = fields.Char(related='partner_id.name', string="Partner Name")

	contact_name = fields.Char(string='Contact Person')
	mobile_no = fields.Char(string='Mobile No', size=10)
	phone_no = fields.Char(string='Phone No')
	gst_no = fields.Char(string='GST No', size=15)
	pan_no = fields.Char(string='PAN No', size=10)
	aadhar_no = fields.Char(string='Aadhar No', size=12)
	email = fields.Char(string='Email')
	user_id = fields.Many2one('res.users', string='Salesperson',required=True, default=lambda self: self._uid)
	company_id = fields.Many2one('res.company', 'Company', 
		default=lambda self: self.env['res.company']._company_default_get('wp.res.partner'))
	bank_name = fields.Char(string='Bank Name')
	security_cheque_details = fields.Char(string='Security Cheque Details')
	security_deposit = fields.Char(string='Security Deposit')
	
	cheque1 = fields.Char(string='Cheque 1')
	amount1 = fields.Float(string='Amount 1')
	cheque2 = fields.Char(string='Cheque 2')
	amount2 = fields.Float(string='Amount 2')
	cheque3 = fields.Char(string='Cheque 3')
	amount3 = fields.Float(string='Amount 3')
	security_deposit_amount = fields.Float(string='SD Amount')
	sd_cheque_no = fields.Char(string='SD Cheque No.')
	credit_limit = fields.Float(string='Credit Limit')
	credit_days = fields.Char(string='Credit Days')

	owner_name = fields.Char(string='Owner Name')
	owner_dob = fields.Date(string='Owner DOB')
	owner_spouse_name = fields.Char(string='Spouse Name')
	owner_spouse_dob = fields.Date(string='Spouse DOB')
	owner_mrg_anvrsry_date = fields.Date(string='Anniversary Date')
	owner_child1_name = fields.Char(string='Child 1 Name')
	owner_child1_dob = fields.Date(string='Child 1 DOB')
	owner_child2_name = fields.Char(string='Child 2 Name')
	owner_child2_dob = fields.Date(string='Child 2 DOB')
	owner_child3_name = fields.Char(string='Child 3 Name')
	owner_child3_dob = fields.Date(string='Child 3 DOB')

	@api.constrains('pan_no')
	def check_pan_no_length(self):
		for rec in self:
			if rec.pan_no and len(rec.pan_no) != 10:
				raise ValidationError(('PAN No must be 10 digits in length'))

	@api.constrains('aadhar_no')
	def check_aadhar_no(self):
		for rec in self:
			if rec.aadhar_no and len(rec.aadhar_no) != 12:
				raise ValidationError(('Aadhar No must be 12 digits in length'))

	@api.constrains('gst_no')
	def check_gst_no(self):
		for rec in self:
			if rec.gst_no and len(rec.gst_no) != 15:
				raise ValidationError(('GST No must be 15 digits in length'))


	@api.constrains('mobile_no')
	def check_mobile_no(self):
		for rec in self:
			if rec.mobile_no and len(rec.mobile_no) != 10:
				raise ValidationError(('Mobile No No must be 10 digits in length'))

	@api.multi
	def action_set_to_approved(self):
		self.write({'state': 'Approved',})
		self.partner_id.unlink()

	@api.onchange('state_id')
	def onchange_state_id(self):
		if self.state_id :
			self.country_id = self.state_id.country_id.id
		else:
			self.country_id = False

	@api.onchange('district_id')
	def onchange_district_id(self):
		if self.district_id :
			self.state_id = self.district_id.state_id.id
			self.country_id  = self.district_id.state_id.country_id.id

		else:
			self.state_id = False
			self.country_id  = False

	def report_check(self):
		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
		report_check = base_url + '/web#%s' % (url_encode({
				'model': self._name,
				'view_type': 'form',
				'id': self.id,
			}))
		rep_check = """
			<br/>
			<td>
				<a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
					font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
					text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
					text-align: center; vertical-align: middle; cursor: pointer; 
					white-space: nowrap; background-image: none; background-color: #337ab7; 
					border: 1px solid #337ab7; margin-right: 10px;">Check Distributor</a>
			</td> 
			"""  % ( report_check)
		return rep_check

	@api.multi
	def action_get_created_partner(self):
		self.ensure_one()
		action = self.env['ir.actions.act_window'].for_xml_id('sales_meet', 'open_view_partner_list')
		action['res_id'] = self.mapped('partner_id').ids[0]
		return action


	@api.multi
	def action_submit(self):

		escalation_ids = self.env['cir.escalation.line'].search([("company_id","=",self.company_id.id),
			("state_id","=",self.state_id.id)],limit=1)
		if not escalation_ids:
			raise ValidationError(('Contact Sales Support team'))

		support_email = [x.login for x in escalation_ids.support_user_ids]
		email_from = self.user_id.login
		email_to = ",".join(support_email)
		email_cc = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).salesupport_mail_id

		subject = "Request for Distributor Approval - %s "  % (todaydate)
		initial_body = """ 
		<p>Hi Team,</p>
			<h3>The following Distributor is created and requires an approval from your end.</h3>"""
		
		self.send_general_mail(initial_body, subject, email_from, email_to, email_cc)
		self.write({'state': 'Submit',})


	@api.multi
	def action_approve(self):

		email_to = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).erp_mail
		email_cc = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).salesupport_mail_id
		email_from = self.env.user.email

		subject = "[Approved] Request for Distributor - %s "  % (todaydate)
		initial_body = """ 
		<p>Hi IT Support Team,</p>
			<h3>The following Distributor is approved from my end.</h3>""" 
		
		self.send_general_mail(initial_body, subject, email_from, email_to, email_cc)
		self.write({'state': 'Approved',})


	@api.multi
	def send_created_mail(self):
		email_cc_list = []

		escalation_ids = self.env['cir.escalation.line'].search([("company_id","=",self.company_id.id),
			("state_id","=",self.state_id.id)],limit=1)

		if not escalation_ids:
			raise ValidationError(('Contact Sales Support team'))

		email_to = self.user_id.email
		email_from = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).erp_mail

		support_mail = self.env['cir.escalation.matrix'].search([("company_id","=",self.company_id.id)]).salesupport_mail_id
		email_cc_list.append(support_mail)
		manager_mail = escalation_ids.manager_id.email
		email_cc_list.append(manager_mail)
		zsm_mail = escalation_ids.zsm_user_id.email
		email_cc_list.append(zsm_mail)

		email_cc = ",".join(email_cc_list)

		main_date = datetime.strptime(str(((self.create_date).split())[0]), 
				tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

		body = """
			<h3>Hi Team,</h3>
			<h3>Distributor is created in CRM and ERP with Following Details</h3>

			<table >
				<tr><th style=" text-align: left;padding: 8px;">Date</td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Distributor </td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Code </td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">State</td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Contact Person</td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Salesperson</td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Company</td><td> : %s</td></tr>
			</table>
		""" % (main_date,self.name, self.bp_code,self.state_id.name,  
			self.contact_name, self.user_id.name, self.company_id.name)


		subject = "[Created] Distributor created by %s - ( %s )"  % (self.user_id.name, todaydate)
		full_body = body + self.report_check()

		self.send_generic_mail(subject, full_body, email_from, email_to, email_cc)


	@api.multi
	def send_general_mail(self, initial_body=False, subject=False, email_from=False, email_to=False, email_cc=False):
		second_body = body = """ """
		main_id = self.id

		print "---------------Start ---------------" , email_from, email_to

		main_date = datetime.strptime(str(((self.create_date).split())[0]), 
				tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

		body = """
			<h3>Kindly take necessary action by clicking the buttons below:</h3>

			<table >
				<tr><th style=" text-align: left;padding: 8px;">Date</td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Distributor </td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">State</td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Contact Person</td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Salesperson</td><td> : %s</td></tr>
				<tr><th style=" text-align: left;padding: 8px;">Company</td><td> : %s</td></tr>
			</table>
		""" % (main_date,self.name, self.state_id.name,  self.contact_name, self.user_id.name, self.company_id.name)

		full_body =  initial_body + body + self.report_check()

		self.send_generic_mail(subject, full_body, email_from, email_to, email_cc)


	@api.multi
	def send_generic_mail(self,subject=False, full_body=False, email_from=False, email_to=False, email_cc=False):
		composed_mail = self.env['mail.mail'].sudo().create({
				'model': self._name,
				'res_id': self.id,
				'email_from': email_from,
				'email_to': email_to,
				'email_cc': email_cc,
				'subject': subject,
				'body_html': full_body,
			})

		composed_mail.send()
		print "--- Mail Sent to ---" , email_to, "---- Mail Sent From ---" , email_from


	@api.multi
	def action_post(self):
		partner = False
		values = {
			'crm_kyc_id' : self.id,
			'name': self.name,
			'user_id': self.user_id.id,
			'phone': self.phone_no,
			'mobile': self.mobile_no,
			'email': self.email,
			'street': self.street,
			'street2': self.street2,
			'zip': self.zip,
			'city': self.city,
			'district_id': self.district_id.id,
			'country_id': self.country_id.id,
			'state_id': self.state_id.id,
			'is_company': True,
			'type': 'contact',

			'bp_code': self.bp_code,
			'partner_group_id': self.partner_group_id.id,
			'pricelist': self.pricelist,
			'so_creditlimit':self.credit_limit,
			'gst_no': self.gst_no,
			'pan_no': self.pan_no,

			'state': 'Created',
			'customer':True,
			'supplier':False,
			'company_id': self.company_id.id,
			'company_type': 'company',

			'cheque1':self.cheque1,
			'amount1':self.amount1,
			'cheque2':self.cheque2,
			'amount2':self.amount2,
			'cheque3':self.cheque3,
			'amount3':self.amount3,
			'security_deposit_amount':self.security_deposit_amount,
			'sd_cheque_no':self.sd_cheque_no,
			'credit_days':self.credit_days,
			'owner_name':self.owner_name,
			'owner_dob':self.owner_dob,
			'owner_spouse_name':self.owner_spouse_name,
			'owner_spouse_dob':self.owner_spouse_dob,
			'owner_mrg_anvrsry_date':self.owner_mrg_anvrsry_date,
			'owner_child1_name':self.owner_child1_name,
			'owner_child1_dob':self.owner_child1_dob,
			'owner_child2_name':self.owner_child2_name,
			'owner_child2_dob':self.owner_child2_dob,
			'owner_child3_name':self.owner_child3_name,
			'owner_child3_dob':self.owner_child3_dob,

		}
		partner =  self.env['res.partner'].sudo().create(values)
		self.sudo().write({'partner_id': partner.id,'state': 'Posted',})

		partner_action = self.env.ref('sales_meet.open_view_partner_list')
		dict_act_window = partner_action.read([])[0]
		if partner:
			dict_act_window['res_id'] = partner.id
		dict_act_window['view_mode'] = 'form,tree'
		return dict_act_window