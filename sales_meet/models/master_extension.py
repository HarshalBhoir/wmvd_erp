# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from datetime import datetime, timedelta, date , time
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, tools, _
from time import gmtime, strftime
from odoo.exceptions import UserError , ValidationError
import time
import psycopg2
import string


class res_company_extension(models.Model):
	_inherit = 'res.company'
	
	ad_client_id = fields.Char(string="Client ID")
	attendance_maximum_hours_per_day = fields.Float(
		string='Attendance Maximum Hours Per Day', digits=(2, 2), default=11.0)


class res_country_extension(models.Model):
	_inherit = 'res.country'
	
	active = fields.Boolean(string="Active", default=True)
	c_country_id = fields.Char(string='Country ID' )


class res_country_state_extension(models.Model):
	_inherit = 'res.country.state'
	
	active = fields.Boolean(string="Active", default=True)
	district_ids = fields.One2many('res.state.district', 'state_id', string='Districts')
	c_region_id = fields.Char(string='State ID' )


class StateDistrict(models.Model):
	_description = "State District"
	_name = 'res.state.district'
	_order = 'code'

	state_id = fields.Many2one('res.country.state', string='State', required=True)
	active = fields.Boolean(string="Active", default=True)
	name = fields.Char(string='District Name', required=True )
	code = fields.Char(string='District Code', help='The district code.')
	c_city_id = fields.Char(string='City ID' )



class MDMConfig(models.Model):
	_name = "mdm.config"
	_description = "Mdm Config"

	@api.model
	def create(self, vals):
		result = super(MDMConfig, self).create(vals)

		a = self.search([("company_id","=",result.company_id.id)])
		if len(a) >1:
			raise UserError(_('You can only create 1 Config Record for company'))

		result.name = "MDM Config - " + result.company_id.name

		return result


	name = fields.Char(string = "Name")
	company_id = fields.Many2one('res.company', 'Company')
	mdm_approver_one2many = fields.One2many('mdm.approver','config_id',string="MDM Approver")
	org_id = fields.Many2one('org.master', string='Organisation')
	active = fields.Boolean('Active', default=True)

class MdmApprover(models.Model):
	_name = "mdm.approver"
	_order= "sequence"
	_description = "Mdm Approver"

	config_id = fields.Many2one('mdm.config', string='Config', ondelete='cascade')
	approver = fields.Many2one('res.users', string='Approver', required=True)
	sequence = fields.Integer(string='Approver sequence')
	company_id = fields.Many2one('res.company', 'Company')
	mdm_type =fields.Selection([('Customer', 'Customer'),
							   ('Vendor', 'Vendor'),
							   ('Product', 'Product')], 'Type')


class grade_master(models.Model):
	_name = "grade.master"
	_description = "Grade Master"

	name = fields.Char('Grade')
	isactive = fields.Boolean("Active", default=True)
	grade_line_ids = fields.One2many('grade.master.line', 'grade_line_id', 'Claim Lines', copy=True)
	designation = fields.Char("Designation")
	notice_during_probation = fields.Integer("During Probation Period (Days)")
	notice_after_confirmation = fields.Integer("After Confirmation (Days)")
	
	
class grade_master_line(models.Model):
	_name = "grade.master.line"
	_description = "Grade Master Lines"

	name = fields.Many2one('product.product', 'Claim Type', ondelete='cascade',  domain=[('can_be_expensed', '=', True)])
	value = fields.Char('Value')
	isactive = fields.Boolean("Active" , default=True)
	place = fields.Boolean("All Places")
	fixed_asset = fields.Boolean("Fixed")
	once_only = fields.Boolean("Only Once")
	grade_line_id = fields.Many2one('grade.master', 'Grade', ondelete='cascade')



class org_master(models.Model):
	_name = "org.master"
	_description = "Org Master"

	name = fields.Char('Organisation')
	isactive = fields.Boolean("Active", default=True)
	ad_org_id = fields.Char('Org ID')
	value = fields.Char('Value')
	prefix = fields.Char('Prefix')
	warehouse_master_ids = fields.One2many('warehouse.master', 'org_master_id', 'Pricelist Items')
	company_id = fields.Many2one('res.company', string='Company', index=True )
	default = fields.Boolean("Default", default=False)
	cir_bool = fields.Boolean("Visible in CIR", default=False)


class warehouse_master(models.Model):
	_name = "warehouse.master"
	_description = "Warehouse Master"

	name = fields.Char('Warehouse')
	isactive = fields.Boolean("Active", default=True)
	m_warehouse_id = fields.Char('Warehouse ID')
	value = fields.Char('Value')
	org_master_id = fields.Many2one('org.master', 'Other Pricelist')


class res_partner_group(models.Model):
	_name = "res.partner.group"

	name = fields.Char('Partner Group', required=False)
	value = fields.Char('Value')
	isactive = fields.Boolean("Active")
	c_bp_group_id = fields.Char('Business Partner Group')
	company_id = fields.Many2one('res.company', 'Company', 
		default=lambda self: self.env['res.company']._company_default_get('res.partner.group'))

	@api.model
	@api.multi
	def process_update_erp_c_bp_group_queue(self):
		conn_pg = None
		config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
		if config_id:

			try:
				print "#-------------Select --TRY----------------------#"
				conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
				 password=config_id.password, host= config_id.ip_address,port=config_id.port)
				pg_cursor = conn_pg.cursor()

				query = "select name , value, c_bp_group_id , ad_client_id from  adempiere.C_BP_Group where isactive = 'Y' " 

				pg_cursor.execute(query)
				records = pg_cursor.fetchall()

				if len(records) > 0:
					portal_c_bp_group_id = [ x.c_bp_group_id for x in self.env['res.partner.group'].search([('isactive','!=',False)])]

					for record in records:
						c_bp_group_id = (str(record[2]).split('.'))[0]
						ad_client_id = (str(record[3]).split('.'))[0]
						company_id = self.env['res.company'].search([('ad_client_id','=',ad_client_id)], limit=1)

						vals_line = {
							'c_bp_group_id': c_bp_group_id,
							'ad_client_id': ad_client_id,
							'isactive': True,
							'value':(str(record[1]).split('.'))[0],
							'name':record[0],
							'company_id': company_id.id,
						}

						if c_bp_group_id not in portal_c_bp_group_id:
							self.env['res.partner.group'].create(vals_line)
							print "00000000000000000 Group Created in CRM  000000000000000000000000000000000000000000000"


			except psycopg2.DatabaseError, e:
				if conn_pg:
					conn_pg.rollback()
				print '#----------Error %s' % e		

			finally:
				if conn_pg:
					conn_pg.close()
					print "#--------------Select --44444444--Finally----------------------#" , pg_cursor


class customer_erp_update(models.TransientModel):
	_name = 'customer.erp.update'
	_description = "Customer ERP Update"


	name = fields.Char(string = "Customer Code")
	company_id = fields.Many2one('res.company', 'Company', 
		default=lambda self: self.env['res.company']._company_default_get('customer.erp.update'))


	@api.multi
	def update_customer(self):
		conn_pg = None
		state_id = 596
		config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
		if config_id:

			try:
				print "#-------------Select --TRY----------------------#"
				conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
				 password=config_id.password, host= config_id.ip_address,port=config_id.port)
				pg_cursor = conn_pg.cursor()

				today = datetime.today()
				# daymonth = today.strftime( "%Y-%m-%d 00:00:00")

				records2 = self.env['res.partner'].sudo().search([('bp_code','=',self.name),'|',('company_id','=',self.company_id.id),
					('company_id','=',False)])

				if len(records2) > 0:
					raise UserError("Already present")

				query = " select \
					cb.c_bpartner_id,cb.name,cb.name2,cb.value,cb.c_bp_group_id,cb.socreditstatus, \
					cb.so_creditlimit,cb.taxid,cb.Cst_Tax_No,cb.TinNo,cb.GST_Tax,cb.Pan_No,cb.SalesRep_ID,cb.C_PaymentTerm_ID, \
					cbl.c_bpartner_location_id,cbl.c_location_id,cbl.phone,cbl.phone2,cbl.email, \
					cl.address1,cl.address2,cl.address3,cl.postal,cl.c_country_id,cl.c_region_id,cl.city \
					from adempiere.c_bpartner cb  \
					JOIN adempiere.c_bpartner_location cbl ON cbl.c_bpartner_id = cb.c_bpartner_id \
					JOIN adempiere.c_location cl ON cl.c_location_id = cbl.c_location_id \
					where cb.value = '%s' and cb.ad_client_id = %s \
					and cb.iscustomer = 'Y' and cb.isactive = 'Y' " %(self.name,self.company_id.ad_client_id)


				pg_cursor.execute(query)
				records = pg_cursor.fetchall()
			  
				if len(records) == 0:
					raise UserError("No records Found")

				for record in records:
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

					street2 = (str(record[20].encode('utf8') )  ) if record[20] else ''  + \
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

					portal_bp_code = [ x.bp_code for x in self.env['res.partner'].search([('bp_code','!=',False),('active','!=',False)])]
					portal_c_bpartner_id = [ x.c_bpartner_id for x in self.env['res.partner'].search([('bp_code','!=',False),
						('c_bpartner_id','=',False),
						('active','!=',False)])]

					print  "KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK" , record[3] 
					if record[3]:
						self.env['res.partner'].create(vals_line)
						print "000000000000000 Partner Created in CRM  000000000000000000000000000000000000000000000"


			except psycopg2.DatabaseError, e:
				if conn_pg:
					conn_pg.rollback()
				 
				print '#-------------------Except %s' % e		

			finally:
				if conn_pg:
					conn_pg.close()
					print "#--------------Select --44444444--Finally----------------------#" , pg_cursor




class Wp_C_Period(models.Model):
	_name = "wp.c.period"
	_description = "Period ERP"
	_order	= 'c_period_id desc'

	c_period_id = fields.Char('Period Id')
	ad_client_id= fields.Char('Client Id')
	active = fields.Boolean('Active')
	name = fields.Char('Name')
	periodno = fields.Char('Period No')
	c_year_id = fields.Char('Year ID')
	company_id = fields.Many2one('res.company', 'Company')

	@api.model
	@api.multi
	def process_update_erp_c_period_queue(self):

		conn_pg = None
		config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
		if config_id:

			try:
				print "#-------------Select --TRY----------------------#"
				conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, 
					password=config_id.password, host= config_id.ip_address,port=config_id.port)
				pg_cursor = conn_pg.cursor()

				query = " select c_period_id,ad_client_id,isactive,name,periodno,c_year_id \
				from adempiere.c_period where created::date > '2017-04-01' and isactive = 'Y' " 

				pg_cursor.execute(query)
				records = pg_cursor.fetchall()

				if len(records) > 0:
					portal_c_period_id = [ x.c_period_id for x in self.env['wp.c.period'].search([('active','!=',False)])]

					for record in records:
						c_period_id = (str(record[0]).split('.'))[0]
						
						if c_period_id not in portal_c_period_id:
							ad_client_id = (str(record[1]).split('.'))[0]
							company_id = self.env['res.company'].search([('ad_client_id','=',ad_client_id)], limit=1)

							vals_line = {
								'c_period_id': c_period_id,
								'ad_client_id': ad_client_id,
								'active':True,
								'name':record[3],
								'periodno':(str(record[4]).split('.'))[0],
								'c_year_id':(str(record[5]).split('.'))[0],
								'company_id': company_id.id,
							}

							self.env['wp.c.period'].create(vals_line)
							print "0000000000000 Period Created in CRM  0000000000000000"


			except psycopg2.DatabaseError, e:
				if conn_pg:
					conn_pg.rollback()
				print '#--------------Error %s' % e		

			finally:
				if conn_pg:
					conn_pg.close()
					print "#--------------Select --44444444--Finally----------------------#" , pg_cursor


class Wp_C_ElementValue(models.Model):
	_name = "wp.c.elementvalue"
	_description = "Element Value (ERP Account)"
	_rec_name = 'display_name'

	c_elementvalue_id = fields.Char('C_Elementvalue_Id')
	ad_client_id = fields.Char('Ad_Client_Id')
	active = fields.Boolean('Isactive')
	value = fields.Char('Value')
	name = fields.Char('Name')
	description = fields.Char('Description')
	accounttype = fields.Char('Accounttype')
	accountsign = fields.Char('Accountsign')
	isdoccontrolled = fields.Char('Isdoccontrolled')
	c_element_id = fields.Char('C_Element_Id')
	issummary = fields.Char('Issummary')
	postactual = fields.Char('Postactual')
	postbudget = fields.Char('Postbudget')
	postencumbrance = fields.Char('Postencumbrance')
	poststatistical = fields.Char('Poststatistical')
	isbankaccount = fields.Char('Isbankaccount')
	c_bankaccount_id = fields.Char('C_Bankaccount_Id')
	isforeigncurrency = fields.Char('Isforeigncurrency')
	c_currency_id = fields.Char('C_Currency_Id')
	account_id = fields.Char('Account_Id')
	isdetailbpartner = fields.Char('Isdetailbpartner')
	isdetailproduct = fields.Char('Isdetailproduct')
	bpartnertype = fields.Char('Bpartnertype')
	display_name = fields.Char(string="Name", compute="_name_get" , store=True)
	company_id = fields.Many2one('res.company', 'Company')
	customer_function_default = fields.Boolean()
	customer_business_division_default = fields.Boolean()
	bd_default = fields.Boolean()
	function_default = fields.Boolean()


	@api.multi
	@api.depends('name','value')
	def _name_get(self):
		for ai in self:
			if not (ai.display_name and ai.name):
				name = str(ai.value)  + ' - ' + str(ai.name)
				ai.display_name = name
			if not ai.display_name and ai.name:
				name = str(ai.name)
				ai.display_name = name


	@api.model
	@api.multi
	def process_update_erp_c_elementvalue_queue(self):

		conn_pg = None
		config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
		if config_id:

			print "#-------------Select --TRY----------------------#"
			try:
				conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
				 password=config_id.password, host= config_id.ip_address,port=config_id.port)
				pg_cursor = conn_pg.cursor()

				query = "select c_elementvalue_id,ad_client_id,isactive,value,name,description,accounttype, \
				accountsign,isdoccontrolled, c_element_id,issummary,postactual,postbudget,postencumbrance, \
				poststatistical,isbankaccount,c_bankaccount_id, isforeigncurrency,c_currency_id,account_id, \
				isdetailbpartner,isdetailproduct,bpartnertype from adempiere.C_ElementValue where isactive = 'Y' \
				and IsSummary = 'N' and c_element_id in ('1000005','1000008','1000013','1000017') " 

				pg_cursor.execute(query)
				records = pg_cursor.fetchall()
			   
				if len(records) > 0:
					portal_c_elementvalue_id = [ x.c_elementvalue_id for x in self.env['wp.c.elementvalue'].search([
							('active','!=',False)])]

					for record in records:
						c_elementvalue_id = (str(record[0]).split('.'))[0]

						if c_elementvalue_id not in portal_c_elementvalue_id:
							ad_client_id = (str(record[1]).split('.'))[0]
							company_id = self.env['res.company'].search([('ad_client_id','=',ad_client_id)], limit=1)

							vals_line = {
								'c_elementvalue_id': c_elementvalue_id,
								'ad_client_id': ad_client_id,
								'active': True,
								'value':(str(record[3]).split('.'))[0],
								'name':record[4],
								'description':record[5],
								'accounttype':record[6],
								'accountsign':record[7],
								'isdoccontrolled':record[8],
								'c_element_id':(str(record[9]).split('.'))[0],
								'issummary':record[10],
								'postactual':record[11],
								'postbudget':record[12],
								'postencumbrance':record[13],
								'poststatistical':record[14],
								'isbankaccount':record[15],
								'c_bankaccount_id':record[16],
								'isforeigncurrency':record[17],
								'c_currency_id':(str(record[18]).split('.'))[0],
								'account_id':record[19],
								'isdetailbpartner':record[20],
								'isdetailproduct':record[21],
								'bpartnertype':record[22],
								'company_id': company_id.id,
							}
					   
							self.env['wp.c.elementvalue'].create(vals_line)
							print "00000000000 elementvalue Created in CRM  0000000000000000000"


			except psycopg2.DatabaseError, e:
				if conn_pg:
					conn_pg.rollback()
				print '#----------Error %s' % e		

			finally:
				if conn_pg:
					conn_pg.close()
					print "#--------------Select --44444444--Finally----------------------#" , pg_cursor
