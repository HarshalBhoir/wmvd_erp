# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from datetime import datetime, timedelta, date , time
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import logging
from odoo.osv import  osv
from odoo import SUPERUSER_ID
from time import gmtime, strftime
from openerp.exceptions import UserError , ValidationError
import requests
import urllib
import simplejson

import shutil
import os
import time
import psycopg2
import urllib
import tarfile
import string

from odoo.osv.expression import get_unaccent_wrapper
from odoo.addons.base.res import res_partner


class res_partner_group(models.Model):
    _name = "res.partner.group"

    name = fields.Char('Partner Group', required=False)
    value = fields.Char('Value')
    isactive = fields.Boolean("Active")
    c_bp_group_id = fields.Char('Business Partner Group')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('res.partner.group'))



class res_company_extension(models.Model):
    _inherit = 'res.company'
    
    ad_client_id = fields.Char(string="Client ID")
    
    resource_calendar_ids = fields.One2many(
        'resource.calendar', 'company_id', 'Working Hours')
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Default Working Hours', ondelete='restrict')

    @api.model
    def _init_data_resource_calendar(self):
        self.search([('resource_calendar_id', '=', False)])._create_resource_calendar()

    def _create_resource_calendar(self):
        for company in self:
            company.resource_calendar_id = self.env['resource.calendar'].create({
                'name': _('Standard 40 hours/week'),
                'company_id': company.id
            }).id

    @api.model
    def create(self, values):
        company = super(ResCompany, self).create(values)
        if not company.resource_calendar_id:
            company.sudo()._create_resource_calendar()
        # calendar created from form view: no company_id set because record was still not created
        if not company.resource_calendar_id.company_id:
            company.resource_calendar_id.company_id = company.id
        return company





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


class res_partner_extension(models.Model):
    _inherit = "res.partner"
    #_rec_name = 'display_name'

    @api.depends('is_company')
    def _compute_company_type(self):
        for partner in self:
            partner.company_type = 'company' if partner.is_company else 'person'

    bp_code = fields.Char('Partner Code')
    c_bpartner_id = fields.Char('Idempiere ID')
    c_location_id = fields.Char('Location ID')
    c_bpartner_location_id = fields.Char('Address ID')
    partner_group_id = fields.Many2one("res.partner.group", string="Partner Group")
    pan_no = fields.Char('Pan No')
    taxid = fields.Char('Tax ID')
    aadhar_no = fields.Char('Aadhar No')
    tin_no = fields.Char('Tin No')
    vat_no = fields.Char('Vat No')
    cst_no = fields.Char('Cst No')
    gst_no = fields.Char('Gst No')
    state =fields.Selection([('draft', 'Draft'),
                               ('created', 'Created'),
                               ('updated', 'Updated')],
                              'State', default='draft',
                              track_visibility='onchange')

    creditstatus=fields.Selection([
        ('H', 'Credit Hold'),
        ('O', 'Credit OK'),
        ('S', 'Credit Stop'),
        ('W', 'Credit Watch'),
        ('X', 'No Credit Check')],'Credit Status', track_visibility='onchange')
    so_creditlimit=fields.Float(string="Credit limit" )
    totalopenbalance=fields.Float(string="Open Balance" )
    contact_name = fields.Char('Contact Name')

    bank_name = fields.Char('Bank Name')
    account_no = fields.Char('Account No')
    ifsc_code = fields.Char('IFSC Code')
    branch_name = fields.Char('Branch Name')
    cheque_no = fields.Char('Blank Cheque No')
    contact_name = fields.Char('Contact Name')
    address = fields.Char('Bank Address')
    bank_country = fields.Many2one("res.country", string='Country')
    district_id = fields.Many2one("res.state.district", string='District')
    # display_name = fields.Char(string="Name", compute="_name_get" , store=True)


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
    bulk_payment_bool=fields.Boolean(string="Bulk Payment" )


    # @api.multi
    # @api.depends('name','bp_code')
    # def _name_get(self):
    #     for ai in self:
    #         print "1111111111111111111"
    #         # print error
    #         if not (ai.display_name and ai.name):
    #             print "22222222222222222222"
    #             name = str(ai.name) + (' - ' + str(ai.bp_code) )  if ai.bp_code else ''
    #             ai.display_name = name
    #         if not ai.display_name and ai.name:
    #             print "333333333333333333333"
    #             name = str(ai.name) + (' - ' + str(ai.bp_code) )  if ai.bp_code else ''
    #             ai.display_name = name


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
                name += ' | ' + partner.bp_code
            # if partner.mobile:
            #     name += ' | ' + partner.mobile
            # elif partner.phone:
            #     name += ' | ' + partner.phone
            
            # if partner.comment:
            #     name += ' | ' + partner.comment
            res.append((partner.id, name))
        return res


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


                # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , today , type(today), daymonth , type(daymonth)


                query = " select \
cb.c_bpartner_id,cb.name,cb.name2,cb.value,cb.c_bp_group_id,cb.socreditstatus, \
cb.so_creditlimit,cb.taxid,cb.Cst_Tax_No,cb.TinNo,cb.GST_Tax,cb.Pan_No,cb.SalesRep_ID,cb.C_PaymentTerm_ID, \
cbl.c_bpartner_location_id,cbl.c_location_id,cbl.phone,cbl.phone2,cbl.email, \
cl.address1,cl.address2,cl.address3,cl.postal,cl.c_country_id,cl.c_region_id,cl.city \
from adempiere.c_bpartner cb  \
JOIN adempiere.c_bpartner_location cbl ON cbl.c_bpartner_id = cb.c_bpartner_id \
JOIN adempiere.c_location cl ON cl.c_location_id = cbl.c_location_id \
where cb.created::date >= '%s' and cb.ad_client_id = 1000000 and cb.iscustomer = 'Y' and cb.isactive = 'Y' and cl.c_country_id = 208 " %(today)


                # query2 = "select * from c_bpartner cb  where cb.created >= '2018-10-10 00:00:00' and cb.ad_client_id = 1000000 and cb.iscustomer = 'Y' "

                pg_cursor.execute(query)

                records = pg_cursor.fetchall()

                # print "RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR" , records

                
                if len(records) == 0:
                    pass
                    # raise UserError("No records Found")

                for record in records:

                    print "jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj" , record[23] , record[24] , record[4]
                    state = 'created'

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

                    street2 = (str(record[20].encode('utf8') )  ) if record[20] else ''  +  (',' +  str(record[21].encode('utf8')) ) if record[20] else ''
                    

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
                        'company_id':3,

                    }

                    portal_bp_code = [ x.bp_code for x in self.env['res.partner'].search([('bp_code','!=',False),('active','!=',False)])]
                    portal_c_bpartner_id = [ x.c_bpartner_id for x in self.env['res.partner'].search([('bp_code','!=',False),
                        ('c_bpartner_id','=',False),
                        ('active','!=',False)])]

                    print  "KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK" , record[3] 
                    if record[3] not in portal_bp_code:
                        self.env['res.partner'].create(vals_line)
                        print "0000000000000000000000000000000000 Partner Created in CRM  000000000000000000000000000000000000000000000"


                    if record[0] in portal_c_bpartner_id:

                        self.env['res.partner'].search([('bp_code', '=', record[3])]).write(
                                                                    {'c_bpartner_id': c_bpartner_id})

                        print "77777777777777777777777777777777 c_bpartner_id Created in CRM  77777777777777777777777777777777"


            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    print 'Error %s' % e  
                    conn_pg.rollback()
                 
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#" , pg_cursor
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

                pg_cursor.execute("select value FROM adempiere.c_bpartner where value ilike '"+state_code+"%' order by value desc limit 1")
                bp_code_check2 = pg_cursor.fetchall()
                bp_code_check3 = str(bp_code_check2[0][0])
                self.bp_code = state_code + str(int(([x.strip() for x in bp_code_check3.split('.')][0]).strip(state_code)) + 1)


                print " --------------------------- Customer ----------------------------------------------"
                if self.bp_code:

                    pg_cursor.execute("select c_bpartner_id FROM adempiere.c_bpartner where value = '%s'" %(self.bp_code.encode("utf-8")))
                    bp_code_check = pg_cursor.fetchall()

                    if  len(bp_code_check) != 0:
                        raise UserError("Partner Code already exists. Kindly change the partner code and update")

                pg_cursor.execute("select MAX(c_bpartner_id)+1 FROM adempiere.c_bpartner ")
                c_bpartner_id2 = pg_cursor.fetchall()
                c_bpartner_id3 = str(c_bpartner_id2[0][0])
                c_bpartner_id = int([x.strip() for x in c_bpartner_id3.split('.')][0])

                pg_cursor.execute("Insert INTO adempiere.c_bpartner(c_bpartner_id,name,name2,ad_client_id,ad_org_id,value,c_bp_group_id,IsCustomer,socreditstatus,\
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

                pg_cursor.execute('Insert into adempiere.c_location(c_location_id,ad_client_id,ad_org_id,isactive,createdby,updatedby,address1,address2,address3,\
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
                #     pg_cursor.execute("Select MAX(C_BP_BankAccount_ID)+1 FROM C_BP_BankAccount")
                #     C_BP_BankAccount_ID2 = pg_cursor.fetchall()
                #     C_BP_BankAccount_ID3 = str(C_BP_BankAccount_ID2[0][0])
                #     c_bp_bankaccount_id = int([x.strip() for x in C_BP_BankAccount_ID3.split('.')][0])

                #     pg_cursor.execute('Insert into C_BPartner_Location(c_bp_bankaccount_id,ad_client_id,ad_org_id,isactive,createdby,updatedby,\
                #         c_bpartner_id,isach,bankaccounttype,a_name,a_street,a_city,a_state,a_ident_dl,a_ident_ssn,a_country,ad_user_id,bpbankacctuse,a_zip)\
                #          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',\
                #         (c_bp_bankaccount_id,int(self.company_id.ad_client_id),0,'Y',int(self.user_id.ad_user_id),int(self.user_id.ad_user_id),
                #             c_bpartner_id,'N','C',self.bank_name,self.address,self.account_no,self.ifsc_code,self.branch_name,self.aadhar_no,
                #             self.bank_country.name,int(self.user_id.ad_user_id),'B',self.cheque_no))

                #      # commit the changes to the database
                #     conn_pg.commit()


                self.state = 'created'
                
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
    
    # @api.multi
    # def update_idempiere_partner(self):
    #     print "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        
    #     conn_pg = None
    #     print "[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[["
    #     config_id = self.env['external.db.configuration'].sudo().search([('id','=',2)])
    #     if config_id:
    #         print "#-------------Select --TRY----------------------#"
    #         try:
    #             conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, password=config_id.password, host= config_id.ip_address)
    #             pg_cursor = conn_pg.cursor()

    #             if self.c_bpartner_id:

    #                 if self.c_bpartner_id or self.name,
    #                             self.name,int(self.company_id.ad_client_id),0,self.bp_code,
    #                             int(self.partner_group_id.c_bp_group_id),'Y',self.creditstatus,self.so_creditlimit,
    #                             self.taxid or '', self.cst_no or '',self.tin_no or '',
    #                             self.gst_no, self.pan_no,int(self.env.user.ad_user_id),int(self.env.user.ad_user_id),int(self.user_id.ad_user_id)
    #                             ,int(self.property_payment_term_id.c_paymentterm_id)





    #                 pg_cursor.execute("update vendors SET vendor_name = %s WHERE vendor_id = %s")
    #                 updated_rows = pg_cursor.rowcount
    #                 # Commit the changes to the database
    #                 conn_pg.commit()


                
                
                

    #             print "ooooooooooooooooooooooooooooooooooooooooooooooooooooooo" , records



    #             self.state = 'updated'
    #             self.c_bpartner_id = c_bpartner_id
    #             # close communication with the database
    #             pg_cursor.close()



    #         except psycopg2.DatabaseError, e:
    #             if conn_pg:
    #                 print "#-------------------Except----------------------#"
    #                 conn_pg.rollback()

    #             print 'Error %s' % e    

    #         finally:
    #             if conn_pg:
    #                 print "#--------------Select ----Finally----------------------#"
    #                 conn_pg.close()

    #     else:
    #         raise UserError("DB Configuration not found.")








class customer_erp_update(models.TransientModel):
    _name = 'customer.erp.update'
    _description = "Customer ERP Update"


    name = fields.Char(string = "Customer Code")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('customer.erp.update'))


    @api.multi
    def update_customer(self):

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

                records2 = self.env['res.partner'].sudo().search([('bp_code','=',self.name),('company_id','=',self.company_id.id)])

                print "ooooooooooooooooooooooooooooofffffffffffffffffffffffff" , records2 , len(records2)

                if len(records2) > 0:
                    raise UserError("Already present")


                # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , today , type(today), daymonth , type(daymonth)


                query = " select \
                    cb.c_bpartner_id,cb.name,cb.name2,cb.value,cb.c_bp_group_id,cb.socreditstatus, \
                    cb.so_creditlimit,cb.taxid,cb.Cst_Tax_No,cb.TinNo,cb.GST_Tax,cb.Pan_No,cb.SalesRep_ID,cb.C_PaymentTerm_ID, \
                    cbl.c_bpartner_location_id,cbl.c_location_id,cbl.phone,cbl.phone2,cbl.email, \
                    cl.address1,cl.address2,cl.address3,cl.postal,cl.c_country_id,cl.c_region_id,cl.city \
                    from adempiere.c_bpartner cb  \
                    JOIN adempiere.c_bpartner_location cbl ON cbl.c_bpartner_id = cb.c_bpartner_id \
                    JOIN adempiere.c_location cl ON cl.c_location_id = cbl.c_location_id \
                    where cb.value = '%s' and cb.ad_client_id = %s and cb.iscustomer = 'Y' and cb.isactive = 'Y' " %(self.name,self.company_id.ad_client_id)


                # cb.created::date >= '%s' 


                

                pg_cursor.execute(query)

                records = pg_cursor.fetchall()

                print "RRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR" , records

                
                if len(records) == 0:
                    # pass
                    raise UserError("No records Found")

                for record in records:

                    print "jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj" , record[23] , record[24] , record[4]
                    state = 'created'

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

                    street2 = (str(record[20].encode('utf8') )  ) if record[20] else ''  +  (',' +  str(record[21].encode('utf8')) ) if record[20] else ''
                    

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
                        print "0000000000000000000000000000000000 Partner Created in CRM  000000000000000000000000000000000000000000000"



            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    print 'Error %s' % e  
                    conn_pg.rollback()
                 
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#" , pg_cursor
                    conn_pg.close()
                    print "#--------------Select --44444444--Finally----------------------#" , pg_cursor