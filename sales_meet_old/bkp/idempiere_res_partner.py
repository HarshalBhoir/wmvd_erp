
from odoo import api, fields, models, _
from odoo.tools.translate import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.osv import  osv
from odoo import SUPERUSER_ID

class res_partner_extension(models.Model):
	_inherit = "res.partner"


	# c_bpartner_id=fields.Integer(string="c_bpartner_id" )
	ad_client_id=fields.Integer(string="ad_client_id" ) # company
	ad_org_id=fields.Integer(string="ad_org_id" )
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
	issmssubscription=fields.Char(string="issmssubscription" )
	c_salesregion_id =fields.Integer(string="C_SalesRegion_ID" )
	contact_person=fields.Char(string="Contact Person" )
	c_region_id=fields.Integer(string="c_region_id" )
	c_country_id=fields.Integer(string="c_country_id" )

	


