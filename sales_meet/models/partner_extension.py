# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date , time
from odoo import api, fields, models, tools, _
import logging
from odoo.osv import  osv
from time import gmtime, strftime
from odoo.exceptions import UserError , ValidationError
import time
import psycopg2
import string
import base64
from werkzeug import url_encode
from odoo.osv.expression import get_unaccent_wrapper

todaydate = "{:%d-%b-%y}".format(datetime.now())

headers2 = """SalesRep_ID,\
M_PriceList_ID[Name],\
IsDirect,\
IsTrueCustomer,\
IsCRM,\
User1_ID[Value],\
User2_ID[Value],\
IsSMSSubscription,\
Phone,\
AD_Org_ID[Name],\
IsCustomer,\
IsSalesRep,\
IsVendor,\
Value,\
IsEmployee,\
Name,\
Name2,\
Description,\
IsActive,\
IsSummary,\
SOCreditStatus,\
IsTaxExempt,\
IsPOTaxExempt,\
ReferenceNo,\
C_BP_Group_ID[Value],\
IsProspect,\
Cst_Tax_No,\
Pan_No,\
TinNo,\
GST_Tax,\
C_BPartner_Location>EMail,\
C_BPartner_Location>C_BPartner_ID[Value],\
C_BPartner_Location>Name,\
C_BPartner_Location>IsActive,\
C_BPartner_Location>Phone,\
C_BPartner_Location>Phone2,\
C_BPartner_Location>IsShipTo,\
C_BPartner_Location>IsBillTo,\
C_BPartner_Location>IsPayFrom,\
C_BPartner_Location>IsRemitTo,\
C_BPartner_Location>C_Location>Address1,\
C_BPartner_Location>C_Location>Address2,\
C_BPartner_Location>C_Location>Address3,\
C_BPartner_Location>C_Location>Address4,\
C_BPartner_Location>C_Location>City,\
C_BPartner_Location>C_Location>C_City_ID[Name],\
C_BPartner_Location>C_Location>Address5,\
C_BPartner_Location>C_Location>Postal,\
C_BPartner_Location>C_Location>C_Region_ID[Name],\
C_BPartner_Location>C_Location>RegionName,\
C_BPartner_Location>C_Location>C_Country_ID[Name],\
C_BPartner_Location>C_Location>IsValid,\
C_BP_BankAccount>C_BPartner_ID[Value],\
C_BP_BankAccount>IsActive,\
C_BP_BankAccount>IsACH,\
C_BP_BankAccount>BPBankAcctUse,\
C_BP_BankAccount>AccountNo,\
C_BP_BankAccount>X_Drawee_Location,\
C_BP_BankAccount>X_IFC_Code,\
C_BP_BankAccount>U_Deposit_Bank,\
C_BP_BankAccount>X_BeneBankBranchName,\
C_BP_BankAccount>U_Deposit_Chq\n"""


class res_partner_extension(models.Model):
	_inherit = "res.partner"

	@api.depends('is_company')
	def _compute_company_type(self):
		for partner in self:
			partner.company_type = 'company' if partner.is_company else 'person'

	def _default_function_id(self):
		elementvalue = self.env['wp.c.elementvalue'].sudo().search([('company_id','=',self.env.user.company_id.id),
			('function_default', '=',True)], limit=1)
		if not elementvalue:
			return False
		else:
			elementvalue_id = elementvalue.id
			return elementvalue_id

	def _default_bd_id(self):
		elementvalue = self.env['wp.c.elementvalue'].sudo().search([('company_id','=',self.env.user.company_id.id),
			('bd_default', '=',True)], limit=1)
		if not elementvalue:
			return False
		else:
			elementvalue_id = elementvalue.id
			return elementvalue_id


	@api.multi
	def _compute_can_edit_fields(self):
		self.can_edit_name = self.env.user.has_group('sales_meet.group_it_user')
		print "--- _compute_can_edit_fields res_partner_extension", self.can_edit_name

	bp_code = fields.Char('Partner Code')
	partner_group_id = fields.Many2one("res.partner.group", string="Partner Group")
	pan_no = fields.Char('Pan No')
	taxid = fields.Char('Tax ID')
	aadhar_no = fields.Char('Aadhar No')
	tin_no = fields.Char('TIN No')
	vat_no = fields.Char('VAT No')
	cst_no = fields.Char('CST No')
	gst_no = fields.Char('GST No')
	state =fields.Selection([('Draft', 'Draft'),
							('Submitted', 'Submitted'),
							('Approved', 'Approved'),
							('Created', 'Created'),
							('Updated', 'Updated')],
							'State', default='Draft',
							track_visibility='onchange')
	
	contact_name = fields.Char('Contact Name')
	bank_name = fields.Char('Bank Name')
	account_no = fields.Char('Account No')
	ifsc_code = fields.Char('IFSC Code')
	branch_name = fields.Char('Branch Name')
	cheque_no = fields.Char('Blank Cheque No')
	pricelist = fields.Char('Pricelist')
	street = fields.Char(size=59)
	street2 = fields.Char(size=59)
	contact_name = fields.Char('Contact Name')
	address = fields.Char('Bank Address')
	bank_country = fields.Many2one("res.country", string='Country')
	district_id = fields.Many2one("res.state.district", string='District')
	company_type = fields.Selection(string='Company Type',
		selection=[('person', 'Individual'), ('company', 'Company')], default='company')

	c_bpartner_id = fields.Char('Idempiere ID')
	c_location_id = fields.Char('Location ID')
	c_bpartner_location_id = fields.Char('Address ID')
	ad_client_id=fields.Integer(string="ad_client_id" )
	ad_org_id=fields.Integer(string="ad_org_id" )
	org_id = fields.Many2one('org.master', string='Org',  domain="[('company_id','=',company_id)]" )
	isactive=fields.Char(string="isactive" )
	isonetime=fields.Char(string="isonetime" )
	isprospect=fields.Char(string="isprospect" )
	isvendor=fields.Char(string="isvendor" )
	iscustomer=fields.Char(string="iscustomer" )
	isemployee=fields.Char(string="isemployee" )
	issalesrep=fields.Char(string="issalesrep" )
	c_bp_group_id=fields.Integer(string="c_bp_group_id" )
	value=fields.Char(string="Search Key" )
	salesrep_id=fields.Integer(string="salesrep_id" )

	taxid=fields.Char(string="taxid" )
	istaxexempt=fields.Char(string="istaxexempt" )
	firstsale=fields.Datetime(string="firstsale" )
	issmssubscription=fields.Boolean(string="issmssubscription" )
	c_salesregion_id =fields.Integer(string="C_SalesRegion_ID" )
	contact_person=fields.Char(string="Contact Person" )
	c_region_id=fields.Integer(string="c_region_id" )
	c_country_id=fields.Integer(string="c_country_id" )
	bulk_payment_bool=fields.Boolean(string="Bulk Payment" )

	user1_id = fields.Many2one('wp.c.elementvalue', string='Business Division' , 
		domain="[('company_id','=',company_id),('c_element_id','in',('1000005','1000008'))]", default=_default_bd_id)
	user2_id = fields.Many2one('wp.c.elementvalue', string='Functions', 
		domain="[('company_id','=',company_id),('c_element_id','in',('1000013','1000017'))]", default=_default_function_id)
	
	can_edit_fields = fields.Boolean(compute='_compute_can_edit_fields')

	cheque1 = fields.Char(string='Cheque 1')
	amount1 = fields.Float(string='Amount 1')
	cheque2 = fields.Char(string='Cheque 2')
	amount2 = fields.Float(string='Amount 2')
	cheque3 = fields.Char(string='Cheque 3')
	amount3 = fields.Float(string='Amount 3')
	security_deposit_amount = fields.Float(string='SD Amount')
	sd_cheque_no = fields.Char(string='SD Cheque No.')
	security_cheque_details = fields.Char(string='Security Cheque Details')
	security_deposit = fields.Char(string='Security Deposit')
	totalopenbalance=fields.Float(string="Open Balance" )
	credit_days = fields.Char(string='Credit Days')
	creditstatus=fields.Selection([
		('H', 'Credit Hold'),
		('O', 'Credit OK'),
		('S', 'Credit Stop'),
		('W', 'Credit Watch'),
		('X', 'No Credit Check')],'Credit Status', default='W' , track_visibility='onchange')
	so_creditlimit=fields.Float(string="Credit limit"  )

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

	crm_kyc_id = fields.Many2one("wp.res.partner", string='CRM KYC')

	@api.model
	def name_search(self, name, args=None, operator='ilike', limit=100):
		if args is None:
			args = []
		if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
			self.check_access_rights('read')
			where_query = self._where_calc(args)
			self._apply_ir_rules(where_query, 'read')
			from_clause, where_clause, where_clause_params = where_query.get_sql()
			where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

			# search on the name of the contacts and of its company
			search_name = name
			if operator in ('ilike', 'like'):
				search_name = '%%%s%%' % name
			if operator in ('=ilike', '=like'):
				operator = operator[1:]

			unaccent = get_unaccent_wrapper(self.env.cr)

			query = """SELECT id
						 FROM res_partner
					  {where} ({bp_code} {operator} {percent}
						   OR {display_name} {operator} {percent}
						   OR {reference} {operator} {percent}
						   OR {phone} {operator} {percent}
						   OR {mobile} {operator} {percent})
						   -- don't panic, trust postgres bitmap
					 ORDER BY {display_name} {operator} {percent} desc,
							  {display_name}
					""".format(where=where_str,
							   operator=operator,
							   bp_code=unaccent('bp_code'),
							   display_name=unaccent('display_name'),
							   reference=unaccent('ref'),
							   phone=unaccent('phone'),
							   mobile=unaccent('mobile'),
							   percent=unaccent('%s'))

			where_clause_params += [search_name]*6
			if limit:
				query += ' limit %s'
				where_clause_params.append(limit)
			self.env.cr.execute(query, where_clause_params)
			partner_ids = map(lambda x: x[0], self.env.cr.fetchall())

			if partner_ids:
				return self.browse(partner_ids).tgl_name_get()
			else:
				return []
		return self.search(args, limit=limit).tgl_name_get()

	@api.multi
	def tgl_name_get(self):
		res = []
		for partner in self:
			name = partner.name
			if partner.bp_code:
				name += " | " + partner.bp_code
			res.append((partner.id, name))
		return res

	@api.onchange('district_id')
	def onchange_district_id(self):
		if self.district_id :
			self.state_id = self.district_id.state_id.id
			self.country_id  = self.district_id.state_id.country_id.id

		else:
			self.state_id = False
			self.country_id  = False


	@api.multi
	def download_customer_data(self):
		# sql = """SELECT 
		#		  bp_code,
		#		  name,
		#		  mobile,
		#		  email
		#	  FROM
		#		  res_partner
		#	  WHERE id={}""".format(self.id)

		# print "11111111111111111" , sql
		# self.env.cr.execute(sql)
		# rows = self.env.cr.fetchall()
		# print "222222222222222222" , rows
		csv =  headers2 #"""'CODE', 'NAME', 'MOBILE', 'EMAIL'\n"""
		ext= ".csv"
		print "333333333333333333" , csv

		rows = [(1000000,
				self.pricelist or '',
				'N',
				'N',
				'N',
				self.user1_id.value or '',
				self.user2_id.value or '',
				'Y' if self.mobile else 'N',
				self.mobile or '',
				'*',
				'Y' ,
				'N',
				'N',
				self.bp_code or '',
				'N',
				self.name or '',
				self.name or '',
				self.comment or '',
				'Y',
				'N',
				self.creditstatus or '',
				'N',
				'N',
				self.user1_id.name or '',
				self.partner_group_id.value or '',
				'N',
				self.cst_no or '',
				self.pan_no or '',
				self.tin_no or '',
				self.gst_no or '',
				self.email or '',
				self.bp_code or '',
				self.district_id.name,
				'Y',
				self.mobile or '',
				self.phone or '',
				'Y',
				'Y',
				'Y',
				'Y',
				('"' +str(self.street) + '"' ) if self.street else '',
				('"' + self.street2  + '"' ) if self.street2 else '',
				'',
				('"' + self.city + '"' )  if self.city else '',
				self.district_id.name,
				'', #self.district_id.name,
				'',
				self.zip or '',
				self.state_id.name,
				self.state_id.name,
				self.country_id.name,
				'N',
				self.bp_code or '',
				'Y',
				'N',
				'B',
				self.account_no or '',
				('"' + self.address+ '"' )  if self.address else '',
				self.ifsc_code or '',
				('"' + self.bank_name + '"' ) if self.bank_name else '',
				('"' + self.branch_name + '"' ) if self.branch_name else '',
				('"' + self.cheque_no + '"' ) if self.branch_name else '',
				)]

		print("ddddddddddddddddddddddddddddddddddddddd", rows)

		if rows:
			for row in rows:
				csv_row = ""
				for item in row:
					csv_row+= "{},".format(item)
				csv+="{}\n".format(csv_row[:-1])

		filetxt="customer"+str("{:%d%m%y%h%m%s}".format(datetime.now()))+ ext

		document_vals = {'name': filetxt,			 
						 'datas': csv.encode('base64'),
						 'datas_fname': filetxt,  
						 'res_model': self._name,
						 'res_id': self.id,
						 'type': 'binary',
						 'extension': ext }

		ir_id = self.env['ir.attachment'].sudo().create(document_vals)
		attachment = self.env['ir.attachment'].search([('name', '=', filetxt)])

		return {
				'type': 'ir.actions.act_url',
				'url': '/web/content/%s?download=true' % (attachment.id),
				'target': 'new',
				'nodestroy': False,
			}


	# @api.multi
	# def action_manual_export_customer(self):

	#	 filetxt="customer"+str("{:%d%m%y%h%m%s}".format(datetime.now()))+".csv"
	#	 with open(filetxt, mode='wb') as file:

	#		 writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
	#		 # create a row contains heading of each column
	#		 writer.writerow(['CODE', 'NAME', 'MOBILE', 'EMAIL'])
	#		 # fetch products and write respective data.
	#		 for customer in self:
	#			 name = customer.name
	#			 code = customer.bp_code
	#			 mobile = customer.mobile
	#			 email = customer.email
	#			 writer.writerow([code, name, mobile, email])

	#		 filename = Path(filetxt)
	#		 webbrowser.open(filename.absolute().as_uri())

	
	@api.multi
	def approved_from_owner(self):
		self.state = 'Approved'

	@api.multi
	def confirm_customer(self):
		if self.state == 'Approved':
			self.state = 'Created'
			self.active = True

	@api.multi
	def update_customer_from_erp(self):

		if not self.c_bpartner_id:
			conn_pg = None
			config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
			if config_id:
				try:
					print "#-------------Select --TRY----------------------#"
					conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
					 password=config_id.password, host= config_id.ip_address,port=config_id.port)
					pg_cursor = conn_pg.cursor()

					query = " select \
		cb.c_bpartner_id, cbl.c_bpartner_location_id,cbl.c_location_id \
		from adempiere.c_bpartner cb  \
		JOIN adempiere.c_bpartner_location cbl ON cbl.c_bpartner_id = cb.c_bpartner_id \
		JOIN adempiere.c_location cl ON cl.c_location_id = cbl.c_location_id \
		where cb.value = '%s' and cb.ad_client_id = %s " %(self.bp_code,self.company_id.ad_client_id)

					pg_cursor.execute(query)
					records = pg_cursor.fetchall()
				   
					if len(records) == 0:
						raise UserError("Partner Doesnot exists in the given Company")

					for record in records:				   
						self.write({'c_bpartner_id': (str(record[0]).split('.'))[0],
									'c_bpartner_location_id': (str(record[1]).split('.'))[0],
									'c_location_id': (str(record[2]).split('.'))[0],
									'state' : 'Updated'})

						print "--------------- c_bpartner_id Update in CRM  -------------------"

					self.crm_kyc_id.send_created_mail()


				except psycopg2.DatabaseError, e:
					if conn_pg:
						conn_pg.rollback()
					print '#-------------------Except------------------ %s' % e		

				finally:
					if conn_pg:
						conn_pg.close()
						print "#--------------Select --44444444--Finally----------------------#" , pg_cursor


	@api.model
	@api.multi
	def process_update_customer_scheduler_queue(self):

		conn_pg = None
		state_id = 596
		config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
		if config_id:

			print "#-------------Select --TRY----------------------#"
			try:
				conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
				 password=config_id.password, host= config_id.ip_address,port=config_id.port)
				pg_cursor = conn_pg.cursor()

				print "lllllllllllllpg_cursor pg_cursorpg_cursorpg_cursorpg_cursorpg_cursor" , pg_cursor

				today = datetime.today()
				# daymonth = today.strftime( "%Y-%m-%d 00:00:00")

				query = " select \
cb.c_bpartner_id,cb.name,cb.name2,cb.value,cb.c_bp_group_id,cb.socreditstatus, \
cb.so_creditlimit,cb.taxid,cb.Cst_Tax_No,cb.TinNo,cb.GST_Tax,cb.Pan_No,cb.SalesRep_ID,cb.C_PaymentTerm_ID, \
cbl.c_bpartner_location_id,cbl.c_location_id,cbl.phone,cbl.phone2,cbl.email, \
cl.address1,cl.address2,cl.address3,cl.postal,cl.c_country_id,cl.c_region_id,cl.city \
from adempiere.c_bpartner cb  \
JOIN adempiere.c_bpartner_location cbl ON cbl.c_bpartner_id = cb.c_bpartner_id \
JOIN adempiere.c_location cl ON cl.c_location_id = cbl.c_location_id \
where cb.created::date >= '%s' and cb.iscustomer = 'Y' and cb.isactive = 'Y' and cl.c_country_id = 208 " %(today)

				pg_cursor.execute(query)
				records = pg_cursor.fetchall()

				if len(records) == 0:
					pass

				portal_bp_code = [ x.bp_code for x in self.env['res.partner'].search([('bp_code','!=',False),
						('active','!=',False)])]
				portal_c_bpartner_id = [ x.c_bpartner_id for x in self.env['res.partner'].search([('bp_code','!=',False),
					('c_bpartner_id','=',False),
					('active','!=',False)])]

				for record in records:

					print  "KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK" , record[3] 
					if record[3] not in portal_bp_code:

						print "jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj" , record[23] , record[24] , record[4]
						state = 'Created'

						c_bp_group_id = (str(record[4]).split('.'))[0]
						c_region_id = (str(record[24]).split('.'))[0]
						c_country_id = (str(record[23]).split('.'))[0]
						c_bpartner_id = (str(record[0]).split('.'))[0]
						c_bpartner_location_id = (str(record[14]).split('.'))[0]
						c_location_id = (str(record[15]).split('.'))[0]

						partner_group_id = self.env['res.partner.group'].sudo().search([('c_bp_group_id','=',c_bp_group_id)]).id
						user_id = 1
						
						property_payment_term_id = self.env['account.payment.term'].sudo().search([('c_paymentterm_id','=',record[13])]).id
						country_id = self.env['res.country'].sudo().search([('c_country_id','=',c_country_id)]).id
						if record[24]:
							state_id = self.env['res.country.state'].sudo().search([('c_region_id','=',c_region_id)]).id

						street2 = (str(record[20].encode('utf8') )  ) if record[20] else ''  +  \
						(',' +  str(record[21].encode('utf8')) ) if record[20] else ''
						
						vals_line = {
							
							'c_bpartner_id': c_bpartner_id,
							'name':record[1],
							'bp_code':record[3],
							'partner_group_id': partner_group_id,
							'creditstatus':record[5],
							'so_creditlimit':record[6],
							'taxid':record[7],
							'cst_no':record[8],
							'tin_no':record[9],
							'gst_no':record[10],
							'pan_no':record[11],
							'user_id':user_id,
							'property_payment_term_id':property_payment_term_id,
							'c_bpartner_location_id': c_bpartner_location_id,
							'c_location_id': c_location_id,
							'phone':record[16],
							'mobile':record[17],
							'email':record[18],
							'street':record[19],
							'street2': street2,
							'zip':record[22],
							'country_id':country_id,
							'state_id':state_id,
							'city':record[25],
							'state': state,
							'customer':True,
							'supplier':False,
							'company_id': self.company_id.id,
							'company_type': 'company',

						}
					
						self.env['res.partner'].create(vals_line)
						print "--------- Partner Created in CRM  ------"


					if record[0] in portal_c_bpartner_id:

						self.env['res.partner'].search([('bp_code', '=', record[3])]).write(
																	{'c_bpartner_id': c_bpartner_id})

						print "------------------- c_bpartner_id Updated in CRM  --------------"


			except psycopg2.DatabaseError, e:
				if conn_pg:
					conn_pg.rollback()
				print '#-------------------Except------------------ %s' % e		

			finally:
				if conn_pg:
					conn_pg.close()
					print "#--------------Select --44444444--Finally----------------------#" , pg_cursor




	@api.multi
	def create_idempiere_partner(self):
		conn_pg = None
		config_id = self.env['external.db.configuration'].sudo().search([('id','=',1)])
		if config_id:
			try:

				print "#-------------Select --TRY----------------------#"
				conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, 
					password=config_id.password, host= config_id.ip_address,port=config_id.port)
				pg_cursor = conn_pg.cursor()

				state_code = self.state_id.code

				pg_cursor.execute("select value FROM adempiere.c_bpartner where value ilike '" \
					+state_code+"%' order by value desc limit 1")
				bp_code_check2 = pg_cursor.fetchall()
				bp_code_check3 = str(bp_code_check2[0][0])
				self.bp_code = state_code + str(int(([x.strip() for x in bp_code_check3.split('.')][0]).strip(state_code)) + 1)


				print " --------------------------- Customer ----------------------------------------------"
				if self.bp_code:

					pg_cursor.execute("select c_bpartner_id FROM adempiere.c_bpartner \
						where value = '%s'" %(self.bp_code.encode("utf-8")))
					bp_code_check = pg_cursor.fetchall()

					if  len(bp_code_check) != 0:
						raise UserError("Partner Code already exists. Kindly change the partner code and update")

				pg_cursor.execute("select MAX(c_bpartner_id)+1 FROM adempiere.c_bpartner ")
				c_bpartner_id2 = pg_cursor.fetchall()
				c_bpartner_id3 = str(c_bpartner_id2[0][0])
				c_bpartner_id = int([x.strip() for x in c_bpartner_id3.split('.')][0])

				pg_cursor.execute("Insert INTO adempiere.c_bpartner(c_bpartner_id,name,name2,ad_client_id,ad_org_id,\
					value,c_bp_group_id,IsCustomer,socreditstatus,\
					so_creditlimit,taxid,Cst_Tax_No,TinNo,GST_Tax,Pan_No,createdby,updatedby,SalesRep_ID,C_PaymentTerm_ID)\
					 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",\
					(c_bpartner_id,self.name,
					self.name,int(self.company_id.ad_client_id),0,self.bp_code,
					int(self.partner_group_id.c_bp_group_id),'Y',self.creditstatus,self.so_creditlimit,
					self.taxid or '', self.cst_no or '',self.tin_no or '',
					self.gst_no, self.pan_no,int(self.env.user.ad_user_id),int(self.env.user.ad_user_id),int(self.user_id.ad_user_id)
					,int(self.property_payment_term_id.c_paymentterm_id)))
				 # commit the changes to the database
				conn_pg.commit()
				self.c_bpartner_id = c_bpartner_id


				print " --------------------------- Location ----------------------------------------------"

				pg_cursor.execute("Select MAX(c_location_id)+1 FROM adempiere.c_location")
				c_bpartneraddress_id2 = pg_cursor.fetchall()
				c_bpartneraddress_id3 = str(c_bpartneraddress_id2[0][0])
				c_bpartneraddress_id = int([x.strip() for x in c_bpartneraddress_id3.split('.')][0])

				pg_cursor.execute('Insert into adempiere.c_location(c_location_id,ad_client_id,ad_org_id,isactive, \
					createdby,updatedby,address1,address2,address3,\
				 postal,c_country_id,c_region_id,regionname,isvalid,c_city_id,city)  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
				 (c_bpartneraddress_id,int(self.company_id.ad_client_id),0,'Y',int(self.user_id.ad_user_id),int(self.user_id.ad_user_id), 
					self.street or '', self.street2 or '', self.city or '', self.zip or '',
					int(self.country_id.c_country_id),int(self.state_id.c_region_id), self.state_id.name,'N' ,int(self.district_id.c_city_id),self.district_id.name))
				 # commit the changes to the database
				conn_pg.commit()
				self.c_location_id = c_bpartneraddress_id

				print " --------------------------- Adresss ---------------------------------------------- "

				pg_cursor.execute("Select MAX(c_bpartner_location_id)+1 FROM adempiere.c_bpartner_location")
				c_bpartnerlocation_id2 = pg_cursor.fetchall()
				c_bpartnerlocation_id3 = str(c_bpartnerlocation_id2[0][0])
				c_bpartnerlocation_id = int([x.strip() for x in c_bpartnerlocation_id3.split('.')][0])

				pg_cursor.execute('Insert into adempiere.C_BPartner_Location(c_bpartner_location_id,c_location_id,c_bpartner_id,ad_client_id,ad_org_id,createdby,\
					updatedby,isbillto,isactive,isshipto,ispayfrom,isremitto,phone,phone2,email,name) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
					(c_bpartnerlocation_id,c_bpartneraddress_id,c_bpartner_id,int(self.company_id.ad_client_id),0,int(self.user_id.ad_user_id),
						int(self.user_id.ad_user_id),'Y','Y','Y','Y','Y',self.phone or '',self.mobile or '', self.email or '',
						 self.city or ''))
				 # commit the changes to the database
				conn_pg.commit()
				self.c_bpartner_location_id = c_bpartnerlocation_id

				print "ooooooooooooooooooooooooooooooooooooooooooooooooooooooo"

				if self.contact_name:
					pg_cursor.execute("Select MAX(AD_User_ID)+1 FROM adempiere.AD_User")
					AD_User_ID2 = pg_cursor.fetchall()
					AD_User_ID3 = str(AD_User_ID2[0][0])
					ad_user_id = int([x.strip() for x in AD_User_ID3.split('.')][0])

					contact_value = ((self.contact_name)[0] + self.contact_name.split(' ')[1]).lower()
					print "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" , contact_value

					pg_cursor.execute('Insert into adempiere.AD_User(ad_user_id,ad_client_id,ad_org_id,isactive,createdby,updatedby,name,c_bpartner_id,processing,\
						notificationtype,isfullbpaccess,isinpayroll,islocked,isnopasswordreset,isexpired,issaleslead,issmssubscription,iserpuser,iscrm,\
						isaddmailtextautomatically,salesrep_id,value) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
						(ad_user_id,int(self.company_id.ad_client_id),0,'Y',int(self.user_id.ad_user_id),int(self.user_id.ad_user_id),
							self.contact_name,c_bpartner_id,'N','E','Y','N','N','N','N','N','N','N','N','N',int(self.user_id.ad_user_id),contact_value))
					 # commit the changes to the database
					conn_pg.commit()
					# self.c_bpartner_location_id = c_bpartnerlocation_id

				# if self.account_no:
				#	 pg_cursor.execute("Select MAX(C_BP_BankAccount_ID)+1 FROM C_BP_BankAccount")
				#	 C_BP_BankAccount_ID2 = pg_cursor.fetchall()
				#	 C_BP_BankAccount_ID3 = str(C_BP_BankAccount_ID2[0][0])
				#	 c_bp_bankaccount_id = int([x.strip() for x in C_BP_BankAccount_ID3.split('.')][0])

				#	 pg_cursor.execute('Insert into C_BPartner_Location(c_bp_bankaccount_id,ad_client_id,ad_org_id,isactive,createdby,updatedby,\
				#		 c_bpartner_id,isach,bankaccounttype,a_name,a_street,a_city,a_state,a_ident_dl,a_ident_ssn,a_country,ad_user_id,bpbankacctuse,a_zip)\
				#		  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
				#		 (c_bp_bankaccount_id,int(self.company_id.ad_client_id),0,'Y',int(self.user_id.ad_user_id),int(self.user_id.ad_user_id),
				#			 c_bpartner_id,'N','C',self.bank_name,self.address,self.account_no,self.ifsc_code,self.branch_name,self.aadhar_no,
				#			 self.bank_country.name,int(self.user_id.ad_user_id),'B',self.cheque_no))

				#	  # commit the changes to the database
				#	 conn_pg.commit()


				self.state = 'Created'
				
				# close communication with the database
				pg_cursor.close()



			except psycopg2.DatabaseError, e:
				if conn_pg:
					print "#-------------------Except----------------------#"
					conn_pg.rollback()

				print 'Error %s' % e	

			finally:
				if conn_pg:
					print "#--------------Select ----Finally----------------------#"
					conn_pg.close()

		else:
			raise UserError("DB Configuration not found.")
	