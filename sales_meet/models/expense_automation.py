from odoo.tools.translate import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _, tools, SUPERUSER_ID
import logging
from io import StringIO
from time import gmtime, strftime
from odoo.exceptions import UserError, Warning, ValidationError
import dateutil.parser
from werkzeug import url_encode
import calendar
import xlwt
import re
import base64
from cStringIO import StringIO
from collections import Counter
import requests
import psycopg2

headers = {'content-type': 'text/xml'}

class expense_automation(models.Model):
	_name = 'expense.automation'
	_description = "Expense Automation"
	_inherit = ['mail.thread', 'ir.needaction_mixin']
	_order = 'create_date desc'


	@api.multi
	def _get_config(self):
		config = self.env['external.db.configuration'].search([('state', '=', 'connected')], limit=1)
		if config:
			config_id = config.id
		else:
			config = self.env['external.db.configuration'].search([('id', '!=',0)], limit=1)
			config_id = config.id
		return config_id
	
	name = fields.Char(string = "Expense")
	company_id = fields.Many2one('res.company', 'Company', 
		default=lambda self: self.env['res.company']._company_default_get('expense.automation'))

	attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
	datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
	expense_automation_line_one2many = fields.One2many('expense.automation.line','expense_automation_id')
	start_date = fields.Date(string='Start Date', required=True, default=datetime.today().replace(day=1))
	end_date = fields.Date(string="End Date", required=True, 
		default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))

	expense_state = fields.Selection([
		  ('submit', 'Submitted'),
		  ('manager_approve', 'Manager Approved'),
		  ('approve', 'Approved'),
		  ('post', 'Posted'),
		  ('done', 'Paid'),
		  ('cancel', 'Refused')
		  ], string='Status', index=True)

	user_id = fields.Many2one('res.users', string='User')
	hr_expense_data = fields.Char('Name', size=256)
	file_name = fields.Binary('Expense Report', readonly=True)
	state = fields.Selection([
		('draft', 'Draft'),
		('done', 'Done'),
		('posted', 'Posted'),
		('cancel', 'Cancelled'),
		], string='Status', readonly=True,
		copy=False, index=True, track_visibility='always', default='draft')

	ad_org_id = fields.Many2one('org.master', string='Organisation', 
		domain="[('company_id','=',company_id),('default','=',True)]" )
	filter_rep_bool = fields.Boolean('Filter Rep Generated' , default=False)
	new_year_bool = fields.Boolean('New Server' , default=False)
	dateacct = fields.Date(string='Accounting Date', required=True,default=datetime.today())

	# c_period_id = fields.Many2one('wp.c.period', string='CN To')
	c_elementvalue_id = fields.Many2one('wp.c.elementvalue', string='Cost Center')

	cnfromperiod = fields.Many2one('wp.c.period', string='CN From' ,  domain="[('company_id','=',company_id)]")
	cntoperiod = fields.Many2one('wp.c.period', string='CN To' ,  domain="[('company_id','=',company_id)]")
	user1_id = fields.Many2one('wp.c.elementvalue', string='Business Division' ,
		domain="[('company_id','=',company_id),('c_element_id','in',('1000005','1000008'))]")
	user2_id = fields.Many2one('wp.c.elementvalue', string='Functions' , 
		domain="[('company_id','=',company_id),('c_element_id','in',('1000013','1000017'))]")

	dateordered2 = fields.Date(string='Exp Period From', required=True, default=datetime.today().replace(day=1))
	dateordered3 = fields.Date(string='Exp Period To', required=True, default=datetime.today().replace(day=1))

	config_id = fields.Many2one('external.db.configuration', string='Database', default=_get_config )


	_sql_constraints = [
			('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
	]

	@api.onchange('dateacct')
	def _onchange_dateacct(self):
		if self.dateacct :
			dateacct = dateutil.parser.parse(self.dateacct).date()
			tt = datetime.today().strftime( "%Y-%m-%d")
			today = dateutil.parser.parse(tt).date() 
			back_date = today - timedelta(days=30 )
			if back_date > dateacct:
				raise UserError(_('You can only enter Account Date within 30 days'))
	
	
	@api.multi
	def unlink(self):
		for order in self:
			if order.state != 'draft':
				raise UserError(_('You can only delete Draft Entries'))
		return super(expense_automation, self).unlink()
	

	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('expense.automation')
		result = super(expense_automation, self).create(vals)
		return result

	@api.multi
	def select_all(self):
		for record in self.expense_automation_line_one2many:
			if record.selection == True:
				record.selection = False

			elif record.selection == False:
				record.selection = True

	@api.multi
	def approve_all(self):
		for res in self.expense_automation_line_one2many:
			if res.selection:
				res.expense_name.approve_expense_sheets()
				res.state = res.expense_name.state
				res.approved_bool = True
				res.selection = False
				print "8888888888888888888888 approve_all Expenses 8888888888888888"


		
	@api.multi
	def action_expense_report(self):
		self.expense_automation_line_one2many.unlink()
		result = []
		sale_name = invoice_number = dc_no = location = rep_name = ''
		# file = StringIO()
		if self.user_id:
			hr_expense = self.env['hr.expense.sheet'].sudo().search([('create_date', '>=', self.start_date), 
								('create_date', '<=', self.end_date), 
								('state', '=', self.expense_state), 
								('create_uid', '=', self.user_id.id)],order="create_uid, create_date asc")
		else:
			hr_expense = self.env['hr.expense.sheet'].sudo().search([('create_date', '>=', self.start_date), 
								('create_date', '<=', self.end_date), 
								('state', '=', self.expense_state)],order="create_uid, create_date asc")

		
		start_date = datetime.strptime(self.start_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
		end_date = datetime.strptime(self.end_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
		if self.start_date == self.end_date:
			rep_name = "Expense Details Report(%s)" % (start_date)
		else:
			rep_name = "Expense Details Report(%s-%s)"  % (start_date, end_date)
		self.name = rep_name


		if (not hr_expense):
			raise Warning(_('Record Not Found'))

		count = 0
		for hr_expense_id in hr_expense:
			if hr_expense_id and len(hr_expense_id.expense_line_ids) > 0:

				if hr_expense_id.expense_line_ids[0].total_amount > hr_expense_id.expense_line_ids[0].grade_amount \
							and hr_expense_id.expense_line_ids[0].grade_amount !=0:
					approval_status = 'Needed'
				else:
					approval_status = ''

				vals = {
						'employee_id' : hr_expense_id.employee_id.id,
						'date' : hr_expense_id.create_date,
						'expense_name' : hr_expense_id.id , 
						'meeting_date' : hr_expense_id.expense_meeting_id.expense_date,
						'expense_meeting_id' : hr_expense_id.expense_meeting_id.id ,
						'grade_amount' : hr_expense_id.expense_line_ids[0].grade_amount,
						'total_amount' : hr_expense_id.expense_line_ids[0].total_amount,
						'manager_id' : hr_expense_id.expense_line_ids[0].manager_id.name,
						'grade_id' : hr_expense_id.expense_line_ids[0].grade_id.name,
						'state' : hr_expense_id.state,
						'approval_status' : approval_status,
						'meeting_address' : hr_expense_id.expense_meeting_id.reverse_location,

					}

				result.append(vals)
		self.state = 'done'
		self.expense_automation_line_one2many = result
		
		
			
	@api.multi
	def expense_automation_report(self):
		file = StringIO()		
		today_date = str(date.today())
		self.ensure_one()

		order_list = []
		second_heading = approval_status = status = ''
		workbook = xlwt.Workbook(encoding='utf-8')
		worksheet = workbook.add_sheet('Expense Report')
		fp = StringIO()
		row_index = 0

		main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; \
			borders: bottom thick, top thick, left thick, right thick')
		sp_style = xlwt.easyxf('font: bold on, height 350;')
		header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; \
			borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
		base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
		base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
			pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
		base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
			pattern: pattern fine_dots, fore_color white, back_color yellow;')

		worksheet.col(0).width = 6000
		worksheet.col(1).width = 12000
		worksheet.col(2).width = 6000
		worksheet.col(3).width = 12000
		worksheet.col(4).width = 6000
		worksheet.col(5).width = 12000
		worksheet.col(6).width = 6000
		worksheet.col(7).width = 6000
		worksheet.col(8).width = 6000
		worksheet.col(9).width = 6000
		worksheet.col(10).width = 6000
		worksheet.col(11).width = 6000
		worksheet.col(12).width = 6000
		worksheet.col(13).width = 6001
		worksheet.col(14).width = 6002
		worksheet.col(15).width = 6003
		worksheet.col(16).width = 6004
		worksheet.col(17).width = 6005
		worksheet.col(18).width = 6006
		worksheet.col(19).width = 6007
		worksheet.col(20).width = 6008

		# Headers
		header_fields = ['AD_Org_ID[Name]',
						'C_DocType_ID[Name]',
						'DocumentNo',
						'IsSOTrx',
						'Description',
						'SalesRep_ID[Name]',
						'C_Currency_ID',
						'M_PriceList_ID[Name]',
						'C_PaymentTerm_ID[Value]',
						'C_BPartner_ID[Value]',
						'C_Region_ID[Name]',
						'CountryCode',
						'C_Country_ID[Name]',
						'DateInvoiced',
						'DateAcct',
						'C_Charge_ID[Name]',
						'QtyOrdered',
						'PriceActual',
						'LineDescription',
						'C_Tax_ID[Name]',
						]
		# row_index += 1
	 
		for index, value in enumerate(header_fields):
			worksheet.write(row_index, index, value, base_style)
		row_index += 1

		for res in self.expense_automation_line_one2many:
			if res.approved_bool or res.expense_automation_id.expense_state == 'approve':

				worksheet.write(row_index, 0,'Head Office', base_style )
				worksheet.write(row_index, 1,'AP Expense Invoice', base_style )
				worksheet.write(row_index, 2,res.documentno, base_style )
				worksheet.write(row_index, 3,'N', base_style )
				worksheet.write(row_index, 4,res.expense_automation_id.name, base_style )
				worksheet.write(row_index, 5,'WalplastAdmin', base_style )
				worksheet.write(row_index, 6,'304', base_style )
				worksheet.write(row_index, 7,'Purchase PL', base_style )
				worksheet.write(row_index, 8,'Immediate', base_style )
				worksheet.write(row_index, 9,res.expense_name.expense_line_ids[0].employee_id.emp_id or '', base_style )
				worksheet.write(row_index, 10,'OR', base_style )
				worksheet.write(row_index, 11,'N', base_style )
				worksheet.write(row_index, 12,'India', base_style )
				worksheet.write(row_index, 13,today_date, base_style )
				worksheet.write(row_index, 14,today_date, base_style )
				worksheet.write(row_index, 15,res.expense_name.expense_line_ids[0].product_id.charge_name or '', base_style )
				worksheet.write(row_index, 16,'1', base_style )
				worksheet.write(row_index, 17,res.total_amount, base_style )
				worksheet.write(row_index, 18,res.expense_name.name or '', base_style )
				worksheet.write(row_index, 19,'Tax Exempt', base_style )
		
				row_index += 1

		row_index +=1
		workbook.save(fp)
		out = base64.encodestring(fp.getvalue())
		self.sudo().write({'file_name': out,'hr_expense_data':self.name+'.xls'})


	@api.multi
	def expense_automation_webservice(self):
		filtered_list = []
		filter_dict = {}
		vals = []
		commit_bool = False
		c_bpartner_id = documentno_log = crm_description2 = crm_description = C_Tax_ID = documentno = ''

		expense_invoice_filter = self.expense_automation_line_one2many.sudo().search([("expense_automation_id","=",self.id),
																					  ("state","=",'approve')])

		partner_ids = list(set([ x.employee_id.c_bpartner_id for x in expense_invoice_filter]))

		if  len(expense_invoice_filter) < 1:
			raise ValidationError(_('No Records Selected or No approved expense detected'))

		user_ids = self.env['wp.erp.credentials'].sudo().search([("wp_user_id","=",self.env.uid),("company_id","=",self.company_id.id)])

		if len(user_ids) < 1:
			raise ValidationError(_("User's ERP Credentials not found. Kindly Contact IT Helpdesk"))

		for rec in expense_invoice_filter:

			c_charge_id2 = rec.expense_name.expense_line_ids[0].product_id
			for c_charge in c_charge_id2:
				if c_charge and len(c_charge.erp_charge_one2many) > 0:
					for rescharge in  c_charge.erp_charge_one2many.sudo().search([('product_charge_id',"=",c_charge.id),
																				("company_id","=",self.company_id.id)]):
						# c_charge_id = c_charge.erp_charge_one2many[0].c_charge_id
						c_charge_id = rescharge.c_charge_id
				else:
					raise ValidationError(_("Charge not found. Kindly Contact IT Helpdesk"))

			filtered_list.append((rec.employee_id,c_charge_id))

		filtered_list3 = dict(Counter(filtered_list))

		for beneficiary_name, value in filtered_list3.iteritems():
			total_amount = 0
			c_charge_id = beneficiary_name[1]
			employee_id = beneficiary_name[0].id
			for record in expense_invoice_filter :
				c_charge_id_rec = self.env['wp.erp.charge'].sudo().search([
										("product_charge_id","=",record.expense_name.expense_line_ids.product_id.id),
										("company_id","=",self.company_id.id)]).c_charge_id

				if not c_charge_id_rec:
					raise ValidationError(_("Charge not found. Kindly Contact IT Helpdesk"))

				if beneficiary_name[0].id == record.employee_id.id and c_charge_id == c_charge_id_rec :
					if value > 1:
						total_amount += record.total_amount
						crm_description += record.expense_name.name + ',   '
					else:
						total_amount = record.total_amount
						crm_description = record.expense_name.name

					date_filter = self.create_date
					if record.employee_id and record.employee_id.c_bpartner_id:
						c_bpartner_id = record.employee_id.c_bpartner_id #(str(record.employee_id.c_bpartner_id).split('.'))[0]
					else:
						raise ValidationError(_("Employee ID not found. Kindly Contact IT Helpdesk"))
					#c_bpartner_id = record.employee_id.c_bpartner_id #(str(record.employee_id.c_bpartner_id).split('.'))[0]
					filter_id = record.id


			# if c_bpartner_id == '':

			# 	print "aaaaaaaaaaaaaaaaaaaaaaaaaaa" , c_bpartner_id
			# 	raise ValidationError(_("Employee ID not found. Kindly Contact IT Helpdesk"))
			# else:
			new_list = (c_bpartner_id, abs(total_amount), c_charge_id, filter_id, crm_description)
			vals.append(new_list)



		for partner in partner_ids:

			for records in vals:
				if partner == records[0]:
					crm_description2 += records[4] + ',   '

			line_body = body = upper_body  = payment_body = lower_body = """ """
			
			commit_bool = False

			print "#-------------Select --TRY----------------------#"
			conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
				password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
			pg_cursor = conn_pg.cursor()
			

			query = "select LCO_TaxPayerType_ID from adempiere.C_BPartner where  C_BPartner_ID = %s \
			and ad_client_id= %s  " % (c_bpartner_id,self.company_id.ad_client_id)

			pg_cursor.execute(query)
			record_query = pg_cursor.fetchall()

			if record_query[0][0] == None:
				print "------------------------------ commit_bool ----------------------2" , record_query
				commit_bool = True

			# daymonth = datetime.today().strftime( "%Y-%m-%d 00:00:00")
			daymonth = self.dateacct + ' 00:00:00'
			dateordered2 = self.dateordered2 + ' 00:00:00'
			dateordered3 = self.dateordered3 + ' 00:00:00'
			# daynow = datetime.now()
			daynow  = datetime.now().strftime( "%y%m%d%H%M%S")

			if self.company_id.ad_client_id == '1000000':
				C_DocType_ID = C_DocTypeTarget_ID = 1000235
				C_Tax_ID = 1000193
				M_PriceList_ID = 1000014
				
			elif self.company_id.ad_client_id == '1000001':
				C_DocType_ID = 1000056
			elif self.company_id.ad_client_id == '1000002':
				C_DocType_ID = 1000103
			elif self.company_id.ad_client_id == '1000003':
				C_DocType_ID = C_DocTypeTarget_ID = 1000237
				C_Tax_ID = 1000370
				M_PriceList_ID = 1000041

			else:
				raise UserError(" Select proper company " )


			upper_body = """
			<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:_0="http://idempiere.org/ADInterface/1_0">
				<soapenv:Header />
				<soapenv:Body>
					<_0:compositeOperation>
						<!--Optional:-->
						<_0:CompositeRequest>
							<_0:ADLoginRequest>
								<_0:user>%s</_0:user>
								<_0:pass>%s</_0:pass>
								<_0:ClientID>%s</_0:ClientID>
								<_0:RoleID>%s</_0:RoleID>
								<_0:OrgID>0</_0:OrgID>
								<_0:WarehouseID>0</_0:WarehouseID>
								<_0:stage>0</_0:stage>
							</_0:ADLoginRequest>
							<_0:serviceType>CreateCompleteExpInv</_0:serviceType>
							""" % (user_ids.erp_user, user_ids.erp_pass, self.company_id.ad_client_id, user_ids.erp_roleid )


			payment_body = """
				<_0:operations>
					<_0:operation preCommit="false" postCommit="false">
						<_0:TargetPort>createData</_0:TargetPort>
						<_0:ModelCRUD>
							<_0:serviceType>CreateExpInvoice</_0:serviceType>
							<_0:TableName>C_Invoice</_0:TableName>
							<_0:DataRow>
								<!--Zero or more repetitions:-->
								<_0:field column="AD_Org_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="C_DocTypeTarget_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="C_DocType_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="DateInvoiced">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="DateAcct">
									<_0:val>%s</_0:val>
								</_0:field>
								
								<_0:field column="C_BPartner_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="M_PriceList_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="C_Currency_ID">
									<_0:val>304</_0:val>
								</_0:field>
								<_0:field column="IsSOTrx">
									<_0:val>N</_0:val>
								</_0:field>
								<_0:field column="Description">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="User1_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="User2_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="DateOrdered2">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="DateOrdered3">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="POReference">
									<_0:val>%s</_0:val>
								</_0:field>
							</_0:DataRow>
						</_0:ModelCRUD>
					</_0:operation>"""  % ( self.ad_org_id.ad_org_id ,C_DocTypeTarget_ID, C_DocType_ID, daymonth, daymonth, partner, 
						M_PriceList_ID,crm_description2, self.user1_id.c_elementvalue_id, self.user2_id.c_elementvalue_id, dateordered2, 
						dateordered3,daynow)


			for line_rec in vals:
				if partner == line_rec[0]:
					C_Charge_ID = line_rec[2]
					PriceList = line_rec[1]
					filter_id = line_rec[3]
					# crm_description = line_rec[4]

					line_body += """
					<_0:operation preCommit="false" postCommit="false">
						<_0:TargetPort>createData</_0:TargetPort>
						<_0:ModelCRUD>
							<_0:serviceType>ExpenseInvLines</_0:serviceType>
							<_0:TableName>C_InvoiceLine</_0:TableName>
							<RecordID>0</RecordID>
							<Action>createData</Action>
							<_0:DataRow>
								<!--Zero or more repetitions:-->
								<_0:field column="AD_Org_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="C_Tax_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="PriceList">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="PriceActual">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="PriceEntered">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="C_Charge_ID">
									<_0:val>%s</_0:val>
								</_0:field>
								<_0:field column="QtyEntered">
									<_0:val>1.0000</_0:val>
								</_0:field>
								<_0:field column="C_Invoice_ID">
									<_0:val>@C_Invoice.C_Invoice_ID</_0:val>
								</_0:field>
							</_0:DataRow>
						</_0:ModelCRUD>
					</_0:operation>"""  % ( self.ad_org_id.ad_org_id, C_Tax_ID,PriceList,PriceList,PriceList, C_Charge_ID)

			if commit_bool == True:
				lower_body = """
								<_0:operation preCommit="true" postCommit="true">
									<_0:TargetPort>setDocAction</_0:TargetPort>
									<_0:ModelSetDocAction>
										<_0:serviceType>CompleteExpenseInvoice</_0:serviceType>
										<_0:tableName>C_Invoice</_0:tableName>
										<_0:recordID>0</_0:recordID>
										<!--Optional:-->
										<_0:recordIDVariable>@C_Invoice.C_Invoice_ID</_0:recordIDVariable>
										<_0:docAction>CO</_0:docAction>
									</_0:ModelSetDocAction>
									<!--Optional:-->
								</_0:operation>
							</_0:operations>
						</_0:CompositeRequest>
					</_0:compositeOperation>
				</soapenv:Body>
			</soapenv:Envelope>"""

			else:
				print "#################### Generate Withdrawn Found ##### partner "
				lower_body = """
								</_0:operations>
							</_0:CompositeRequest>
						</_0:compositeOperation>
					</soapenv:Body>
				</soapenv:Envelope>"""


			body = upper_body + payment_body + line_body + lower_body
			print "ffffffffffffffffffffffffffffffffffffffffff" , body

			# if self.new_year_bool:
			# 	idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
			# else:
			# 	idempiere_url="http://35.200.227.4/ADInterface/services/compositeInterface"

			# idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
			idempiere_url="https://erpnew.wmvd.live/ADInterface/services/compositeInterface?wsdl"

			response = requests.post(idempiere_url,data=body,headers=headers)
			print response.content
			
			log = str(response.content)
			if log.find('DocumentNo') is not -1:
				# self.state = 'erp_posted'
				print "ssssssssssssssssssssssssssssssccccccccccc" , log
				documentno_log = log.split('column="DocumentNo" value="')[1].split('"></outputField>')[0]
				print "ssssssssssssssssssssssssss" , documentno_log , self.state
				self.state = 'posted'
				write_data = self.expense_automation_line_one2many.search([('id', '=', filter_id)]).sudo().write(
										{'log': documentno_log})


			if log.find('UNMARSHAL_ERROR') is not -1:
				write_data = self.expense_automation_line_one2many.search([('id', '=', filter_id)]).sudo().write(
										{'log': 'Manual Entry'})
				

			if log.find('IsRolledBack') is not -1:
				raise ValidationError("Error Occured  %s" % (log))


			if log.find('Invalid') is not -1:
				raise ValidationError("Error Occured %s" % (log))


		for line_rec in expense_invoice_filter:
			if line_rec.expense_automation_id.state == 'posted':
				line_rec.expense_name.sudo().action_sheet_move_create()
				line_rec.state = line_rec.expense_name.state


		
class expense_automation_line(models.Model):
	_name = 'expense.automation.line'
	_description = "Expense Automation Line"

	selection = fields.Boolean(string = "", nolabel="1")
	employee_id  = fields.Many2one('hr.employee', string='Employee')
	date  = fields.Date(string="Expense Date")
	expense_name  = fields.Many2one('hr.expense.sheet', string='Expense')
	meeting_date  = fields.Date(string="Meeting Date")
	expense_meeting_id  = fields.Many2one('calendar.event', string='Meeting')
	grade_amount = fields.Float('Allocated') 
	total_amount = fields.Float('Claimed') 
	manager_id = fields.Char('Manager', size=50) 
	grade_id = fields.Char('Grade', size=50) 
	state = fields.Char('State', size=50) 
	approval_status = fields.Char('Approval Status', size=50)
	documentno = fields.Char('Document No', size=50)
	name = fields.Char(string = "Expense No.")
	expense_automation_id  = fields.Many2one('expense.automation')
	approved_bool = fields.Boolean("Approved", store=True)
	meeting_address = fields.Char(string = "Meeting Address")
	log = fields.Text("Log")


	@api.multi
	def approve_expense(self):
		if self.expense_automation_id.state != 'posted':
			if self.state == 'submit':
				print "11111111111111111111111111111111 approve_expense 11111111111111111111111111111111"
				self.expense_name.approve_expense_sheets()
				self.state = self.expense_name.state
				self.approved_bool = True
				self.selection = False

		else:
			raise ValidationError(_("Expense cannot be approved in 'Post' State"))
