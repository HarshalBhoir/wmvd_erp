#!/usr/bin/env bash
from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT

from odoo.tools.translate import _
from odoo import tools, api
from odoo import api, fields, models, _ , registry, SUPERUSER_ID
from odoo.osv import    osv
# import erppeek
import logging
import xmlrpclib
import sys
from odoo.exceptions import UserError, Warning, ValidationError
import dateutil.parser

_logger = logging.getLogger(__name__)

import shutil
import os
import time
import psycopg2
import urllib
import tarfile
import csv
from cStringIO import StringIO
import xlwt
import re
import base64
import pytz
from odoo.addons.web.controllers.main import ExcelExport
from subprocess import Popen
import getpass
from odoo import http
from werkzeug import url_encode
from collections import Counter

import requests

# from io import StringIO
from time import gmtime, strftime
import calendar


# idempiere_url="http://35.200.227.4/ADInterface/services/compositeInterface"
headers = {'content-type': 'text/xml'}
datetimeFormat = '%Y-%m-%d %H:%M:%S'
# google_key = 'AIzaSyCt4jsSrJ9C9tIhlAg0hMerzY3lOE1yoq8'
google_key = 'AIzaSyAueXqmASv23IO3NSdPnVA_TNJOWADjEh8'


AVAILABLE_PRIORITIES = [
    ('0', 'Poor'),
    ('1', 'Very Low'),
    ('2', 'Low'),
    ('3', 'Normal'),
    ('4', 'High'),
    ('5', 'Very High')]


class sample_requisition(models.Model):
    _name = 'sample.requisition'
    _description = "Sample Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    # @api.multi
    @api.depends('quantity','excess_quantity')
    def _compute_total_quantity(self):
        for res in self:
            if res.quantity:
                print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , res.quantity
                res.total_quantity = res.quantity + (res.excess_quantity if res.excess_quantity else 0.0)

                print " --------------------- _compute_total_quantity -------------------------"


    # @api.depends('quantity','excess_quantity')
    # def _compute_total_quantity(self):
    #     for res in self:
    #         if res.quantity:
    #             print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , res.quantity
    #             res.total_quantity = res.quantity + (res.excess_quantity if res.excess_quantity else 0.0)

    #             print " --------------------- _compute_total_quantity -------------------------"


    @api.depends('product_id')
    def _compute_product_quantity_distributer(self):
        for res in self:

            if res.product_id and res.partner_id:
                product_sum = sum([x.quantity for x in self.env['sample.product.line'].sudo().search([('partner_id', '=', self.partner_id.id),
                                                                                                      ('product_id', '=', self.product_id.id)])])

                if product_sum <= 0:
                    res.zero_qty = True
                    raise UserError("No Quantity is left with the Distributer. Kindly contact Sales Support Team.")

                res.distributer_product_quantity = product_sum

                print "kkkkkkkkkkkccccccccccccccccccccccccccccccccc"

   
    name = fields.Char(string = "Sample No.")
    partner_id = fields.Many2one('res.partner',string="Distributor / Retailer" )
    date_sample = fields.Date(string="Sample Date" , default=lambda self: fields.datetime.now(), track_visibility='always')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid, track_visibility='always')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Generated'),
        ('refused', 'Refused'),
        ('approved', 'Approved'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sample.requisition'))
    
    
    ischeck = fields.Selection([('lead', 'Lead'), ('customer', 'Customer')], string='Is Lead/Customer')
    lead_id = fields.Many2one('crm.lead', string='Lead', track_visibility='onchange', domain="[('type', '=', 'lead')]")
    project_partner_id = fields.Many2one('res.partner',string="Customer" )
    product_id = fields.Many2one('product.product', string='Product', 
         domain=[('sale_ok', '=', True)])
    uom_id = fields.Many2one('product.uom', string='UOM', related='product_id.uom_id')

    quantity = fields.Float(string='Qty(Kg)',  store=True)
    excess_taken = fields.Boolean("Excess Qty Taken", default=False)
    excess_quantity = fields.Float(string='Excess Qty(Kg)',  store=True)
    total_quantity = fields.Float(string='Total Qty(Kg)', compute=_compute_total_quantity, store=True)
    # state = fields.Selection([('draft', 'Draft'),('done', 'Done'),], string='Status', default='draft')
    contact_person = fields.Char(string = "Contact Person")
    contact_no = fields.Char(string = "Contact No", size = 10)
    applicator =  fields.Char(string = "Applicator")
    applicator_no =  fields.Char(string = "Applicator No", size = 10)
    applicator_cost =  fields.Float(string = "Applicator Cost")
    city = fields.Char(string = "City")
    project_size = fields.Char(string = "Project Size")
    set_priority=fields.Selection(AVAILABLE_PRIORITIES , string='Rating')
    customer_feedback = fields.Text(string = "Cust Feedback")
    order_quantity = fields.Float(string='Order Qty',  store=True)
    order_amt = fields.Float(string='Order Amt',  store=True)
    followup_date = fields.Date(string="Follow Up Date" )
    sample_attachments = fields.Many2many('ir.attachment', 'sample_attachments_rel' , copy=False, attachment=True)
    checkin_lattitude = fields.Float('Checkin Latitude' , digits=(16, 5) , store=True, track_visibility='onchange') 
    checkin_longitude = fields.Float('Checkin Longitude', digits=(16, 5), store=True, track_visibility='onchange') 
    reverse_location = fields.Char('Current Location', track_visibility='onchange')
    latlong_bool = fields.Boolean("Latlong Bool" )
    distributer_product_quantity = fields.Float(string='Quantity Present(Qty)', compute=_compute_product_quantity_distributer, store=True)
    zero_qty =  fields.Boolean("Zero Qty" )
    

    @api.model
    @api.multi
    def process_update_address_scheduler_queue(self):
        today = datetime.now() - timedelta(days=1)
        daymonth = today.strftime( "%Y-%m-%d") 
        count = 0

        for rec in self.sudo().search([('status', '=','done'),('reverse_location', '=',False)]) : 
            if rec.checkin_lattitude and rec.checkin_longitude :
                  
                latitude = rec.checkin_lattitude
                longitude = rec.checkin_longitude

                f = urllib.urlopen("https://maps.googleapis.com/maps/api/geocode/json?latlng=%s,%s&key=%s" %(latitude , longitude, google_key))
                values = json.load(f)

                address = (values["results"][1]['formatted_address']).encode('utf8')
                count +=1
                print "Count *************************************" , count , address
                rec.write({'reverse_location': address})

                f.close()

        print "Update Address Schedular - Successfull"

    @api.multi
    def refresh_form(self):
        return True

    # @api.multi
    # def update_address(self):
    #     print "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv" , self.checkin_lattitude
    #     # return True




    @api.multi
    def update_data(self):

        if not (self.checkin_lattitude or self.checkin_longitude):
            raise UserError("Edit the Form and Click on 'Update Address' Button, then click on 'Submit' Button")

        issuance = self.env['sample.issuance'].sudo().search([('partner_id', '=', self.partner_id.id)], limit=1)

        if issuance:
                        
            head_line_data1 = {
                'documentno': self.name,
                'dateordered': self.date_sample,
                'deliveryadd': self.contact_person + self.city ,
                'product_id': self.product_id.id,
                'partner_id': self.partner_id.id,
                'quantity': self.total_quantity*(-1),
                'grandtotal': self.applicator_cost,
                'partner_id': self.partner_id.id,
                'sample_requisition_id': self.id,
                'sample_issuance_id': issuance.id,
                'user_id' : self.user_id.id,
            }
            line_create = self.env['sample.product.line'].create(head_line_data1)

            self.state = 'done'

        else:
            raise UserError("No Sampling issued for this Distributor / Retailer. Kindly contact Sales Support Team or Select other partner.")


    @api.model
    def create(self, vals):
        result = super(sample_requisition, self).create(vals)

        result.name = self.env['ir.sequence'].sudo().next_by_code('sample.requisition') or '/' 

        if result.partner_id:
            product_id = self.env['sample.product.line'].sudo().search([('partner_id', '=', result.partner_id.id)])
            if not product_id:
                raise UserError("No Sampling issued for this Distributor / Retailer. Kindly contact Sales Support Team or Select other partner.")

        if result.quantity == 0:
            raise UserError("Quantity cannot be 0 KG. Enter proper quantity in KG")

        if result.applicator_cost == 0:
            raise UserError("Applicator Cost cannot be 0 KG. Enter proper Cost")
        
        return result



    @api.onchange('partner_id')
    def _onchange_distributor(self):
        for res in self:
            if res.partner_id:
                product_id = self.env['sample.product.line'].sudo().search([('partner_id', '=', res.partner_id.id)])
                if product_id:
                    return {'domain': {'product_id': [('id', 'in', [i.product_id.id for i in product_id]),('sale_ok', '=', True)]}}
                else:
                    raise UserError("No Sampling issued for this Distributor / Retailer. Kindly contact Sales Support Team.")

    

class sample_issuance(models.Model):
    _name = 'sample.issuance'
    _description = "Sample Issuance"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    
    name = fields.Char(string = "Sample No.")
    partner_id = fields.Many2one('res.partner',string="Distributer / Retailer" )
    product_id = fields.Many2one('product.product', string='Product', 
         domain=[('sale_ok', '=', True)])
    quantity = fields.Float(string='Quantity(Kg)',  store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sample.issuance'))
    date_sample = fields.Date(string="Sample Date" , track_visibility='always')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid, track_visibility='always')
    sample_issuance_line_one2many = fields.One2many('sample.product.line','sample_issuance_id' , ondelete='cascade')

    @api.model
    def create(self, vals):
        result = super(sample_issuance, self).create(vals)

        if result.partner_id:
            partner_id = self.env['sample.issuance'].search([('partner_id','=',result.partner_id.id)])
            if len(partner_id) > 1 :
                raise UserError(result.partner_id.name + " is already present in Sample Issuance. ")

        result.name = self.env['ir.sequence'].sudo().next_by_code('sample.issuance') or '/' 
        
        return result



    @api.multi
    def update_quantity(self):
        return True

        



class sample_product_line(models.Model):
    _name = 'sample.product.line'
    _description = "Sample Product Line"
    # _order    = 'id desc'

    name = fields.Char(string = "Product No.")
    product_id = fields.Many2one('product.product', string='Product', 
         domain=[('sale_ok', '=', True)])
    uom_id = fields.Many2one('product.uom', string='UOM', related='product_id.uom_id')
    quantity = fields.Float(string='Quantity(Kg)',  store=True)
    partner_id = fields.Many2one('res.partner',string="Distributer / Retailer" )
    sample_issuance_id  = fields.Many2one('sample.issuance', ondelete='cascade')


    documentno = fields.Char(string = "Documentno")
    c_order_id = fields.Char(string = "C_Order_Id")
    dateordered = fields.Date(string = "Dateordered")
    business_partner = fields.Char(string = "Business Partner")
    invoice_partner = fields.Char(string = "Invoice Partner")
    partner_code = fields.Char(string = "Partner Code")
    bill_bpartner_id = fields.Char(string = "Bill Bpartner Id")
    deliveryadd = fields.Char(string = "Deliveryadd")
    grandtotal = fields.Float(string = "Grandtotal")
    m_product_id = fields.Char(string = "M_Product_Id")
    product = fields.Char(string = "Product")
    product_code = fields.Char(string = "Product Code")
    qtyentered = fields.Float(string = "Qtyentered")
    qtyordered = fields.Float(string = "Qtyordered")
    pricelist = fields.Float(string = "Pricelist")
    date_sample = fields.Date(string="Sample Date" , track_visibility='always')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid, track_visibility='always')
    sample_requisition_id  = fields.Many2one('sample.requisition', string='Requisition' , ondelete='cascade')



class sample_erp_update(models.TransientModel):
    _name = 'sample.erp.update'
    _description = "Sample ERP Update"


    name = fields.Char(string = "Sale Order No")
    product_id = fields.Many2one('product.product', string='Product', 
    domain=[('sale_ok', '=', True)])
    quantity = fields.Float(string='Quantity(Kg)',  store=True)
    partner_id = fields.Many2one('res.partner',string="Distributer / Retailer" )
    # sample_issuance_id  = fields.Many2one('sample.issuance')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sample.erp.update'))

# SO/VPF1920/00835
    @api.multi
    def update_quantity(self):

        conn_pg = None
        partner_name = ''

        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)

        if len(config_id) < 1:
            raise UserError(" DB Connection not set / Disconnected " )

        else:

            ad_client_id=self.company_id.ad_client_id

            print "#-------------Select --TRY----------------------#"
            try:

                if config_id:

                    print "#-------------Select --TRY----------------------#"
                    conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, password=config_id.password,
                     host= config_id.ip_address,port= config_id.port)
                    pg_cursor = conn_pg.cursor()

                    print "tttttttttttttttttttttttttttttttttttttttttttt" , pg_cursor


                    pg_cursor.execute("""select \
                                o.documentno,o.C_Order_ID,o.DateOrdered, \
                                (select Name from adempiere.c_bpartner where c_bpartner_id = o.c_bpartner_id) as "Business Partner" , \
                                (select Name from adempiere.c_bpartner where c_bpartner_id = o.Bill_BPartner_ID) as "Invoice Partner", \
                                (select Value from adempiere.c_bpartner where c_bpartner_id = o.Bill_BPartner_ID) as  "Partner Code", \
                                o.Bill_BPartner_ID,  o.DeliveryAdd, o.grandtotal, ol.M_Product_ID, \
                                (select Name from adempiere.m_product where M_Product_ID = ol.M_Product_ID) as "Product", \
                                (select Value from adempiere.m_product where M_Product_ID = ol.M_Product_ID) as  "Product Code", \
                                ol.QtyEntered,  ol.QtyOrdered, ol.PriceList, \
                                (select X12DE355 from adempiere.C_UOM where C_UOM_ID = ol.C_UOM_ID) as  "Product UOM" \
                                from adempiere.C_Order o \
                                JOIN adempiere.C_Orderline ol ON ol.C_Order_ID= o.C_Order_ID \
                                where o.documentno = %s and o.ad_client_id = %s \
                                and COALESCE(ol.M_Product_ID::text, '') <> '' """ ,(self.name,ad_client_id))

                     # o.C_BPartner_ID=1002708 and 


                    # pg_cursor.execute('select documentno from adempiere.C_Order where documentno = %s and ad_client_id = %s ' ,(self.name,ad_client_id))
                    # pg_cursor.execute("select * from adempiere.daily_schedular_query()")

 
                    entry_id = pg_cursor.fetchall()

                    print "jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj" , entry_id , self.name,ad_client_id

                    if entry_id == []:
                        raise UserError(" No Records Found " )

                    count = 0
                    print "kkkkkkkkkkddddddddddddddddddddddd" , entry_id



                    for record in entry_id:
                        count+= 1


                        Bill_BPartner_ID = (str(record[6]).split('.'))[0]
                        M_Product_ID = (str(record[9]).split('.'))[0]
                        partner = self.env['res.partner'].sudo().search([('c_bpartner_id', '=', Bill_BPartner_ID)], limit=1)
                        issuance = self.env['sample.issuance'].sudo().search([('partner_id', '=', partner.id)], limit=1)
                        product_id = self.env['product.product'].sudo().search([('m_product_id', '=', M_Product_ID)])

                        sample_product_line = self.env['sample.product.line'].sudo().search([('documentno', '=', record[0]),('product_id', '=', product_id.id)])

                        print "lllllllllllllllllllldddddddddddddddddddddddddddd" , sample_product_line , count

                        if sample_product_line:
                            raise UserError(record[0] + " is already present in the system")


                        if not partner:
                            raise UserError(record[5] + ' - ' + record[4] + " is not present in the system. Please add the Partner in the system from Customer Update Menu")

                        if not product_id:
                            raise UserError(record[11] + ' - ' + record[10] + " is not present in the system. Please add the product in the system from Product Update Menu ")

                        if issuance:
                            qty = record[15]
                            if qty.isdigit():
                                qty1 = float(qty)
                            else:
                                qty1 = 1
                            quantity = float(record[12]) * float(qty1)                        
                            head_line_data1 = {
                                'documentno': record[0],
                                'c_order_id': (str(record[1]).split('.'))[0],
                                'dateordered': record[2],
                                'deliveryadd': record[7],
                                'grandtotal': record[8],
                                'product_id': product_id.id,
                                'partner_id': partner.id,
                                'quantity': quantity,
                                'pricelist': record[14],
                                'sample_issuance_id': issuance.id,
                                'user_id':self.env.uid,
                            }
                            line_create = self.env['sample.product.line'].create(head_line_data1)
                            
                        else:
                            head_data = {
                                    'partner_id': partner.id,
                                    'user_id':self.env.uid,
                                    'company_id': 3 ,
                                }


                            issuance_id2 = self.env['sample.issuance'].create(head_data)

                            qty = record[15]
                            if qty.isdigit():
                                qty1 = float(qty)
                            else:
                                qty1 = 1
                            quantity = float(record[12]) * float(qty1)

                            # quantity = float(record[12]) * float(record[15])


                            head_line_data = {
                                    'documentno': record[0],
                                    'c_order_id': (str(record[1]).split('.'))[0],
                                    'dateordered': record[2],
                                    'deliveryadd': record[7],
                                    'grandtotal': record[8],
                                    'product_id': product_id.id,
                                    'partner_id': partner.id,
                                    'quantity': quantity,
                                    'pricelist': record[14],
                                    'sample_issuance_id': issuance_id2.id,
                                    'user_id' : self.env.uid,
                                }

                            issuance_line_id = self.env['sample.product.line'].create(head_line_data)


                   
            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    conn_pg.rollback()
         
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#" , conn_pg
                    conn_pg.close()



class sample_automation(models.Model):
    _name = 'sample.automation'
    _description = "Sample Automation"
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


    # @api.multi
    # def _compute_can_edit_name(self):
        
    #     self.can_edit_name = self.env.user.sudo().has_group('sales_meet.group_sample_manager_user')
    #     print "1111111111111111111111111111111111111111 _compute_can_edit_name"

    
    name = fields.Char(string = "sample")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sample.automation'))

    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    # display_address = fields.Char(string="Name", compute="_name_get" , store=True)

    sample_automation_line_one2many = fields.One2many('sample.automation.line','sample_automation_id')
    start_date = fields.Date(string='Start Date', required=True, default=datetime.today().replace(day=1))
    end_date = fields.Date(string="End Date", required=True, default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))


    sample_state = fields.Selection([
                    ('draft', 'Draft'),
                    ('done', 'Generated'),
                    ('refused', 'Refused'),
                    ('approved', 'Approved'),
                    ], string='Status', index=True)


    user_id = fields.Many2one('res.users', string='User') #, default=lambda self: self._uid, track_visibility='always'
    hr_sample_data = fields.Char('Name', size=256)
    file_name = fields.Binary('Sample Report', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('refused', 'Refused'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')

    ad_org_id = fields.Many2one('org.master', string='Organisation',  domain="[('company_id','=',company_id),('default','=',True)]" )
    filter_rep_bool = fields.Boolean('Filter Rep Generated' , default=False)
    new_year_bool = fields.Boolean('New Server' , default=False)
    dateacct = fields.Date(string='Accounting Date', required=True,default=datetime.today())

    # c_period_id = fields.Many2one('wp.c.period', string='CN To')
    c_elementvalue_id = fields.Many2one('wp.c.elementvalue', string='Cost Center')

    cnfromperiod = fields.Many2one('wp.c.period', string='CN From' ,  domain="[('company_id','=',company_id)]")
    cntoperiod = fields.Many2one('wp.c.period', string='CN To' ,  domain="[('company_id','=',company_id)]")
    user1_id = fields.Many2one('wp.c.elementvalue', string='Business Division' ,  domain="[('company_id','=',company_id),('c_element_id','=','1000005')]")
    user2_id = fields.Many2one('wp.c.elementvalue', string='Functions' ,  domain="[('company_id','=',company_id),('c_element_id','=','1000013')]")

    dateordered2 = fields.Date(string='Exp Period From', required=True, default=datetime.today().replace(day=1))
    dateordered3 = fields.Date(string='Exp Period To', required=True, default=datetime.today().replace(day=1))

    config_id = fields.Many2one('external.db.configuration', string='Database', default=_get_config )


    # can_edit_name = fields.Boolean(compute='_compute_can_edit_name')


    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]


    @api.multi
    def select_all(self):
        for record in self.sample_automation_line_one2many:
            if record.selection == True:
                record.selection = False

            elif record.selection == False:
                record.selection = True


    @api.multi
    def approve_all(self):
        for res in self.sample_automation_line_one2many:
            if res.selection:
                res.approved_bool = True
                res.selection = False
                print "88888888888888888888888888888888888888 approve_all 88888888888888888888888888888888888888"



    @api.multi
    def action_sample_report(self):
        self.sample_automation_line_one2many.unlink()
        result = []
        sale_name = invoice_number = dc_no = location = ''
        # file = StringIO()
        if self.user_id:

            hr_sample = self.env['sample.requisition'].sudo().search([
                                ('date_sample', '>=', self.start_date),
                                ('date_sample', '<=', self.end_date), 
                                ('state', '=', self.sample_state),
                                ('create_uid', '=', self.user_id.id)],order="create_uid, create_date asc")
        


        rep_name = ''
        start_date = datetime.strptime(self.start_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
        end_date = datetime.strptime(self.end_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
        if self.start_date == self.end_date:
            rep_name = "Sample Details Report(%s)" % (start_date)
        else:
            rep_name = "Sample Details Report(%s-%s)"  % (start_date, end_date)
        self.name = rep_name


        if (not hr_sample):
            raise Warning(_('Record Not Found'))

        if hr_sample:

            count = 0
            for hr_sample_id in hr_sample:
                if hr_sample_id and len(hr_sample_id) > 0:

                    vals = {

                            'name':hr_sample_id.id ,
                            'partner_id': hr_sample_id.partner_id.id ,
                            'date_sample':hr_sample_id.date_sample ,
                            'user_id':hr_sample_id.user_id.id ,
                            'state':hr_sample_id.state ,
                            'company_id':hr_sample_id.company_id.id ,
                            'ischeck':hr_sample_id.ischeck ,
                            'lead_id':hr_sample_id.lead_id.id ,
                            'sampling_partner': hr_sample_id.lead_id.name or hr_sample_id.project_partner_id.name,
                            'product_id':hr_sample_id.product_id.id ,
                            'uom_id':hr_sample_id.uom_id.id ,
                            'quantity':hr_sample_id.quantity ,
                            'excess_taken':hr_sample_id.excess_taken ,
                            'excess_quantity':hr_sample_id.excess_quantity ,
                            'total_quantity':hr_sample_id.total_quantity ,
                            'state':hr_sample_id.state ,
                            'contact_person':hr_sample_id.contact_person ,
                            'applicator':hr_sample_id.applicator ,
                            'applicator_cost':hr_sample_id.applicator_cost ,
                            'applicator_no':hr_sample_id.applicator_no ,
                            'project_size':hr_sample_id.project_size ,
                            'contact_no':hr_sample_id.contact_no ,
                            'set_priority':hr_sample_id.set_priority ,
                            
                        }

                    result.append(vals)
            self.state = 'done'
            self.sample_automation_line_one2many = result



    @api.multi
    def sample_automation_webservice(self):
        filtered_list = []
        filter_dict = {}
        
        vals = []
        documentno = ''
        C_Tax_ID = ''
        crm_description = ''
        crm_description2 = ''
        documentno_log =''
        commit_bool = False
        grandtotal = 0.0

        for res in self.sample_automation_line_one2many:
            if res.approved_bool:
                grandtotal += res.applicator_cost

            else:
                raise ValidationError(_('No Records Selected or No approved sample detected'))


        employee_ids = self.env['hr.employee'].sudo().search([
                                ('user_id','=',self.user_id.id),
                                '|',('active','=',False),('active','=',True)], limit=1)

        if employee_ids and employee_ids.c_bpartner_id:
            c_bpartner_id = employee_ids.c_bpartner_id #(str(record.employee_id.c_bpartner_id).split('.'))[0]
        else:
            raise ValidationError(_("Employee ID not found. Kindly Contact IT Helpdesk"))


        user_ids = self.env['wp.erp.credentials'].sudo().search([("wp_user_id","=",self.env.uid),("company_id","=",self.company_id.id)])

        if len(user_ids) < 1:
            raise ValidationError(_("User's ERP Credentials not found. Kindly Contact IT Helpdesk"))



        line_body = """ """
        body = """ """
        upper_body  = """ """
        payment_body = """ """
        lower_body = """ """

        commit_bool = False

        print "#-------------Select --TRY----------------------#"
        conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
            password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
        pg_cursor = conn_pg.cursor()
        

        query = "select LCO_TaxPayerType_ID from adempiere.C_BPartner where  C_BPartner_ID = %s and ad_client_id= %s  " % (c_bpartner_id,self.company_id.ad_client_id)

        pg_cursor.execute(query)
        record_query = pg_cursor.fetchall()

        if record_query[0][0] == None:
            print "------------------------------ commit_bool ----------------------" , record_query
            commit_bool = True

        # daymonth = datetime.today().strftime( "%Y-%m-%d 00:00:00")
        daymonth = self.dateacct + ' 00:00:00'
        dateordered2 = self.dateordered2 + ' 00:00:00'
        dateordered3 = self.dateordered3 + ' 00:00:00'
        # daynow = datetime.now()
        daynow  = datetime.now().strftime( "%y%m%d%H%M%S")

        crm_description2  = "Remi Exp from %s to %s " % (self.dateordered2, self.dateordered3)

        if self.company_id.ad_client_id == '1000000':
            C_DocType_ID = C_DocTypeTarget_ID = 1000235
            C_Tax_ID = 1000193
            M_PriceList_ID = 1000014
    
        elif self.company_id.ad_client_id == '1000001':
            C_DocType_ID = 1000056
        elif self.company_id.ad_client_id == '1000002':
            C_DocType_ID = 1000103
        elif self.company_id.ad_client_id == '1000003':
            C_DocType_ID = 1000150
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
                </_0:operation>"""  % ( self.ad_org_id.ad_org_id ,C_DocTypeTarget_ID, C_DocType_ID, daymonth, daymonth, c_bpartner_id, 
                    M_PriceList_ID,crm_description2, self.user1_id.c_elementvalue_id, self.user2_id.c_elementvalue_id, dateordered2, 
                    dateordered3,daynow)



        C_Charge_ID=1000232
        PriceList = grandtotal
        filter_id = self.id


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

        idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"

        response = requests.post(idempiere_url,data=body,headers=headers)
        print response.content
        
        log = str(response.content)
        if log.find('DocumentNo') is not -1:
            # self.state = 'erp_posted'
            documentno_log = log.split('column="DocumentNo" value="')[1].split('"></outputField>')[0]
            print "ssssssssssssssssssssssssss" , documentno_log , self.state
            self.state = 'posted'
            write_data = self.sample_automation_line_one2many.search([('sample_automation_id', '=', filter_id)]).sudo().write({'log': documentno_log})


        if log.find('UNMARSHAL_ERROR') is not -1:
            write_data = self.sample_automation_line_one2many.search([('sample_automation_id', '=', filter_id)]).sudo().write({'log': 'Manual Entry'})
            

        if log.find('IsRolledBack') is not -1:
            # documentno_log = log.split('<Error>')[1].split('</Error>')[0]
            raise ValidationError("Error Occured  %s" % (log))


        if log.find('Invalid') is not -1:
            # documentno_log = log.split('<faultstring>')[1].split('</faultstring>')[0]
            raise ValidationError("Error Occured %s" % (log))


        for line_rec in self.sample_automation_line_one2many:
            if line_rec.approved_bool:
                line_rec.name.state = 'approved'
                line_rec.state = 'approved'




    @api.multi
    def send_approval(self):
        amnt = total_samplecost = 0.0
        body = """ """
        subject = ""
        main_id = self.id

        todaydate = "{:%d-%b-%y}".format(datetime.now())

        line_html = ""

        sample_automation_line = self.sample_automation_line_one2many.search([('sample_automation_id', '=', self.id),('selection', '=', True)])

        if  len(sample_automation_line) < 1:
            raise ValidationError(_('No Records Selected'))

            
        for l in sample_automation_line:

            if l.selection:
                start_date = datetime.strptime(str(((l.date_sample).split())[0]), tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

                line_html += """
                <tr>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px; text-align: center;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                </tr>
                """ % (start_date, l.sampling_partner, l.applicator, l.product_id.name, l.total_quantity, l.applicator_cost)

                total_samplecost += l.applicator_cost

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <h3>Following are the details as Below Listed. </h3>

            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            Date
                        </th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            Sampling Partner
                        </th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            Applicator
                        </th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            Product
                        </th>             
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            KG
                        </th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            Total Fare
                        </th>
                    </tr>
                    %s
                </tbody>
            </table>
            <br/>

            <h2>Total Sampling Cost : %s </h2>


            <br/>

        """ % (line_html, total_samplecost)

        subject = "Request for Sample Expense Approval - ( %s )"  % (todaydate)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        approver = self.env['sample.master.approver'].search([("id","!=",0)])

        if len(approver) < 1:
            raise ValidationError("Sampling Master Config doesnot have any Approver. Configure the Approvers and Users ")
      
        for rec in approver:

            approve_url = base_url + '/sampling?%s' % (url_encode({
                    'model': 'sample.automation',
                    'sampling_id': main_id,
                    'res_id': rec.id,
                    'action': 'approve_ticket_sampling_manager',
                }))
            reject_url = base_url + '/sampling?%s' % (url_encode({
                    'model': 'sample.automation',
                    'sampling_id': main_id,
                    'res_id': rec.id,
                    'action': 'refuse_ticket_sampling',
                }))

            report_check = base_url + '/web#%s' % (url_encode({
                'model': 'sample.automation',
                'view_type': 'form',
                'id': main_id,
            }))

            full_body = body + """<br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF;
                             border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                              vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; 
                              border: 1px solid #337ab7; margin-right: 10px;">Approve All</a>
                        </td>
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF;
                             border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                              vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                               margin-right: 10px;">Reject All</a>
                        </td>

                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
                            border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                             vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                              margin-right: 10px;">Selective Approve/Reject</a>
                        </td>

                    </tr>
                </tbody>
            </table>
            """ % (approve_url, reject_url, report_check)

            composed_mail = self.env['mail.mail'].sudo().create({
                    'model': self._name,
                    'res_id': main_id,
                    'email_to': rec.approver.email,
                    # 'email_cc' : 'varad.dalvi@walplast.com',
                    'subject': subject,
                    'body_html': full_body,
                    'auto_delete': False,
                    'priority_mail': True,
                })

            # self.state='approval_sent'
            composed_mail.sudo().send()


    @api.multi
    def approve_ticket_sampling_manager(self):
        self.sudo().send_user_mail()
        self.state = 'approved'
        self.sudo().approve_all()


    @api.multi
    def send_user_mail(self):
        main_body  = """ """
        subject = ""
        main_id = self.id

        # employee_ids = self.env['hr.employee'].sudo().search([
        #                     ('user_id','=',meeting_id.user_id.id),
        #                     '|',('active','=',False),('active','=',True)])

        # user_email = self.env['res.users'].sudo().search([('user_id','=',self.create_uid.id)]).login
        sample_users = self.env['sample.master.user'].search([("id","!=",0)])

        for rec in sample_users:




            email_to = user_email #'sales.associates@walplast.com'

            todaydate = "{:%d-%b-%y}".format(datetime.now())

            main_body = """
                <style type="text/css">
                * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
                </style>
                <p>Hi Team,</p>

                <br/>
                <br/>


                <h2>BULK Sampling is approved</h2>

            """

            report_check = base_url + '/web#%s' % (url_encode({
                'model': 'sample.automation',
                'view_type': 'form',
                'id': main_id,
            }))

            full_body = body + """<br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
                            border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                            vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                            margin-right: 10px;">Check Sampling</a>
                        </td>

                    </tr>
                </tbody>
            </table>
            """ % (report_check)

            subject = "[Approved] Bulk Sampling for %s "  % (self.user_id.name)
            full_body = main_body 

            composed_mail = self.env['mail.mail'].sudo().create({
                    'model': self._name,
                    'res_id': main_id,
                    # 'email_from': email_from,
                    'email_to': rec.user.email, #email_to,
                    'subject': subject,
                    'body_html': full_body,
                    'auto_delete': False,
                    'priority_mail': True,

                })

            composed_mail.send()

            print "llllllllllllllllllllllllllllllllll Mail Sent to %s" % (email_to)



    @api.multi
    def sample_automation_report(self):
        file = StringIO()
        today_date = str(date.today())

        self.ensure_one()
        status = ''

        order_list = []
        second_heading = approval_status = ''
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Sample Report')
        fp = StringIO()
        row_index = 0

        main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
        sp_style = xlwt.easyxf('font: bold on, height 350;')
        header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
        base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
        base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
        base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')

        worksheet.col(0).width = 2000
        worksheet.col(1).width = 4000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 12000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 12000
        worksheet.col(6).width = 6000
        worksheet.col(7).width = 16000
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
        worksheet.col(21).width = 6008



        # Headers
        header_fields = [
        'SrNo.',
        'Date',
        'Applicator',
        'Sales Person Code',
        'Sales Person',
        'Product',
        'Qty in Bag',
        'Project Name',
        'Status',
        'Contact No.',
        'Applicator No.',
        'Total Cost',
        'Sample No.',
        'Document No.',

        'Contact Person',
        'City',
        'Project Size',
        'Order Qty',
        'Order Amt',
        'Ratings',
        'Follow Up Date',
        'Cust Feedback',
                        ]
        # row_index += 1
     
        for index, value in enumerate(header_fields):
            worksheet.write(row_index, index, value, base_style_yellow)
        row_index += 1

        count = 1

        for res in self.sample_automation_line_one2many:

                employee_ids = self.env['hr.employee'].sudo().search([
                                ('user_id','=',res.user_id.id),'|',('active','=',False),('active','=',True)])

                worksheet.write(row_index, 0,count, base_style )
                worksheet.write(row_index, 1,res.date_sample, base_style )
                worksheet.write(row_index, 2,res.applicator, base_style )
                worksheet.write(row_index, 3,employee_ids.emp_id, base_style )
                worksheet.write(row_index, 4,res.user_id.name, base_style )
                worksheet.write(row_index, 5,res.product_id.name, base_style )
                worksheet.write(row_index, 6,res.total_quantity, base_style )
                worksheet.write(row_index, 7,res.lead_id.name or res.project_partner_id.name, base_style )
                worksheet.write(row_index, 8,res.state, base_style )
                worksheet.write(row_index, 9,res.contact_no, base_style )
                worksheet.write(row_index, 10,res.applicator_no, base_style )
                worksheet.write(row_index, 11,res.applicator_cost, base_style )
                worksheet.write(row_index, 12,res.name.name, base_style )
                worksheet.write(row_index, 13,res.log  or '', base_style )

                worksheet.write(row_index, 14,res.contact_person  or '', base_style )
                worksheet.write(row_index, 15,res.city  or '', base_style )
                worksheet.write(row_index, 16,res.project_size  or '', base_style )
                worksheet.write(row_index, 17,res.order_quantity  or '' , base_style )
                worksheet.write(row_index, 18,res.order_amt  or '' , base_style )
                worksheet.write(row_index, 19,res.set_priority  or '', base_style )
                worksheet.write(row_index, 20,res.followup_date  or '', base_style )
                worksheet.write(row_index, 21,res.customer_feedback or '', base_style )

            
                row_index += 1
                count += 1


        row_index +=1
        workbook.save(fp)


        out = base64.encodestring(fp.getvalue())

        self.sudo().write({'file_name': out,'hr_sample_data':self.name+'.xls'})



    @api.multi
    def refuse_ticket_sampling(self):
        
        subject = "[Refused] Bulk Sample Expense"
        for sheet in self:
            body = (_("Bulk Sample Expense %s has been refused.<br/><ul class=o_timeline_tracking_value_list></ul>") % (sheet.name))
            sheet.sudo().message_post(body=body)

            cn_user = self.env['res.users'].search([("id","=",self.create_uid.id)])

            if len(cn_user) < 1:
                raise ValidationError("Sample Master Config doesnot have any User. Configure the Approvers and Users ")

            for rec in cn_user:
                full_body = body

                composed_mail = self.env['mail.mail'].sudo().create({
                        'model': self._name,
                        'res_id': self.id,
                        'email_to': rec.login,
                        'subject': subject,
                        'body_html': full_body,
                        'auto_delete': False,
                        # 'priority_mail': True,
                    })

                self.state = 'refused'
                composed_mail.send()



class sample_automation_line(models.Model):
    _name = 'sample.automation.line'
    _description = "Sample Automation Line"


    selection = fields.Boolean(string = "", nolabel="1")
    manager_id = fields.Char('Manager', size=50) 
    grade_id = fields.Char('Grade', size=50) 
    approval_status = fields.Char('Approval Status', size=50)
    sample_automation_id  = fields.Many2one('sample.automation')
    approved_bool = fields.Boolean("Approved", store=True)
    # employee_code = fields.Char(string = "sample Code")
    log = fields.Text("Log")


    name = fields.Many2one('sample.requisition',string="Sample No." )
    partner_id = fields.Many2one('res.partner',string="Distributor / Retailer" )
    date_sample = fields.Date(string="Sample Date" , default=lambda self: fields.datetime.now(), track_visibility='always')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid, track_visibility='always')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Generated'),
        ('refused', 'Refused'),
        ('approved', 'Approved'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sample.requisition'))
    
    
    ischeck = fields.Selection([('lead', 'Lead'), ('customer', 'Customer')], string='Is Lead/Customer')
    lead_id = fields.Many2one('crm.lead', string='Lead', track_visibility='onchange', domain="[('type', '=', 'lead')]")
    project_partner_id = fields.Many2one('res.partner',string="Customer" )
    sampling_partner = fields.Char('Sampling Partner')
    product_id = fields.Many2one('product.product', string='Product', 
         domain=[('sale_ok', '=', True)])
    uom_id = fields.Many2one('product.uom', string='UOM', related='product_id.uom_id')

    quantity = fields.Float(string='Qty(Kg)',  store=True)
    excess_taken = fields.Boolean("Excess Qty Taken", default=False)
    excess_quantity = fields.Float(string='Excess Qty(Kg)',  store=True)
    total_quantity = fields.Float(string='Total Qty(Kg)')
    # state = fields.Selection([('draft', 'Draft'),('done', 'Done'),], string='Status', default='draft')
    contact_person = fields.Char(string = "Contact Person")
    contact_no = fields.Char(string = "Contact No", size = 10)
    applicator =  fields.Char(string = "Applicator")
    applicator_no =  fields.Char(string = "Applicator No", size = 10)
    applicator_cost =  fields.Float(string = "Applicator Cost")
    city = fields.Char(string = "City")
    project_size = fields.Char(string = "Project Size")
    set_priority=fields.Selection(AVAILABLE_PRIORITIES , string='Rating')
    customer_feedback = fields.Text(string = "Cust Feedback")
    order_quantity = fields.Float(string='Order Qty',  store=True)
    order_amt = fields.Float(string='Order Amt',  store=True)
    followup_date = fields.Date(string="Follow Up Date" )



    @api.multi
    def approve_sample(self):
        if self.sample_automation_id.state != 'posted':
            if self.state == 'approved':
                self.approved_bool = False
                self.selection = False
                self.state =  'done'

            else:
                self.approved_bool = True
                self.state =  'approved'

        else:
            raise ValidationError(_("sample cannot be approved in 'Post' or 'Draft' State"))




class sample_masterConfig(models.Model):
    _name = "sample.master.config"

    @api.model
    def create(self, vals):
        result = super(sample_masterConfig, self).create(vals)

        a = self.search([("id","!=",0)])
        if len(a) >1:
            raise UserError(_('You can only create 1 Config Record'))

        return result

    @api.multi
    def _get_name(self):
        return "Sampling Config"

    name = fields.Char(string = "Config No.", default=_get_name)
    sample_approver_one2many = fields.One2many('sample.master.approver','config_id',string="Sample Master Approver")
    sample_user_one2many = fields.One2many('sample.master.user','config_user_id',string="Sample Master User")

class sample_masterApprover(models.Model):
    _name = "sample.master.approver"
    _order= "sequence"

    config_id = fields.Many2one('sample.master.config', string='Config', ondelete='cascade')
    approver = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Approver sequence')


class sample_masterUser(models.Model):
    _name = "sample.master.user"

    config_user_id = fields.Many2one('sample.master.config', string='Config', ondelete='cascade')
    user = fields.Many2one('res.users', string='User', required=True)
    sequence = fields.Integer(string='User sequence')