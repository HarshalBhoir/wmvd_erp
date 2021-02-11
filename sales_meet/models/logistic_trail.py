#!/usr/bin/env python
# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from odoo import api, fields, models, _ , registry, SUPERUSER_ID, tools
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import time
import dateutil.parser
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, Warning, ValidationError
import psycopg2
import urllib
import re
from odoo import http
from werkzeug import url_encode
import requests
from urllib2 import Request, urlopen
from urllib import urlencode
from .google_maps import GoogleMaps
from bs4 import BeautifulSoup
import logging

_logger = logging.getLogger(__name__)

class LogisticForecast(models.Model):
    _name = 'logistic.forecast'
    _description = "Logistic Forecast"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    name = fields.Char(string = "LT")
    date = fields.Date(string="Date" , default=lambda self: fields.datetime.now())
    origin = fields.Char(string = "Origin")
    destination = fields.Char(string = "Destination")
    distance = fields.Char(string = "Distance")
    actual_distance = fields.Float(string = "Actual Distance")
    duration = fields.Char(string = "Duration")
    state_id = fields.Many2one('res.country.state', string='State')
    diesel_price = fields.Float(string = "Diesel Price")
    actual_diesel_price = fields.Float(string = "Actual Diesel Price")
    vehicle_size = fields.Float(string = "Vehicle Size(Tons)")
    vehicle_avg = fields.Float(string = "Vehicle Avg (Diesel/Litre)")
    amount= fields.Float(string = "Total Amount")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('logistic.forecast'))
    day_to_reach = fields.Float(string = "Days to Reach")
    mileage = fields.Float(string = "Mileage", compute="calculate_mileage", store=True)
    total_diesel_cost = fields.Float(string = "Total Diesel Cost", compute="calculate_diesel_cost", store=True)
    driver_commission = fields.Float(string = "Driver Commission")
    owner_commission = fields.Float(string = "Owner Commission")
    brokerage_commission = fields.Float(string = "Brokerage Commission")
    labour_cost = fields.Float(string = "Labour Cost")
    extra_cost = fields.Float(string = "Extra Cost")
    toll = fields.Float(string = "Toll")
    additional_taxes = fields.Float(string = "Additional Taxes")
    cost_per_ton = fields.Float(string = "Cost Per Ton", compute="calculate_cost_per_ton", store=True)
    calculated_total_cost = fields.Float(string = "Calculated Total Cost", compute="total_calculation", store=True)
    final_total_cost = fields.Float(string = "Final Total Cost")
    vehicle_wheels = fields.Selection([
        ('6', '6'),
        ('10', '10'),
        ('12', '12'),
        ('14', '14'),
        ('18', '18'),], string='Wheels on Vehicle', copy=False, index=True)

    state = fields.Selection([
        ('Draft', 'Draft'),
        ('InProgress', 'InProgress'),
        ('Done', 'Done'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='Draft')

    @api.model
    def create(self, vals):
        result = super(LogisticForecast, self).create(vals)
        result.name = "LF/" + str(result.company_id.short_name)  +"/"  + str(result.id).zfill(5)
        return result

    @api.multi
    def get_duration(self, context=None):
        origin = self.origin
        destination= self.destination
        departure_time = context.get('departure_time')
        if not departure_time:
            n = datetime.now()
            departure_time = int(time.mktime(n.timetuple()))
        maps = GoogleMaps()
        distance_google = maps.distance(origin, destination, mode='transit', departure_time=departure_time)
        self.duration = maps.duration(origin, destination, mode='transit', departure_time=departure_time)
        self.distance = distance_google
        self.actual_distance = (distance_google).split()[0]

    @api.multi
    def get_fuelprice(self):
        if self.state_id and self.date:
            fuel_price_id = self.env['logistic.fuel.price'].sudo().search([('state_id', '=', self.state_id.id),
                ('date', '=', self.date)], limit=1)
            if fuel_price_id: self.diesel_price =  self.actual_diesel_price = fuel_price_id.price
        else:
            raise ValidationError(_('Kindly fill State / Date Field'))


    @api.multi
    @api.depends('actual_distance','vehicle_avg')
    def calculate_mileage(self):
        for res in self:
            if res.actual_distance and res.vehicle_avg:
                res.mileage = res.actual_distance / res.vehicle_avg

    @api.multi
    @api.depends('actual_distance','actual_diesel_price')
    def calculate_diesel_cost(self):
        for res in self:
            # if res.actual_distance and res.vehicle_avg and res.actual_diesel_price:
            #     res.total_diesel_cost = res.actual_diesel_price * res.mileage
            if res.actual_distance !=0 and res.actual_diesel_price !=0 :
                res.total_diesel_cost = res.actual_diesel_price * res.actual_distance


    @api.multi
    @api.depends('actual_distance','actual_diesel_price', 
        'driver_commission', 'owner_commission', 'brokerage_commission',
         'labour_cost', 'extra_cost', 'toll', 'additional_taxes')
    @api.onchange('actual_distance','actual_diesel_price', 
        'driver_commission', 'owner_commission', 'brokerage_commission', 
        'labour_cost', 'extra_cost', 'toll', 'additional_taxes')
    def total_calculation(self):
        for res in self:
            if res.total_diesel_cost !=0:
                res.final_total_cost = res.calculated_total_cost = res.total_diesel_cost + \
                                        (res.driver_commission if res.driver_commission else 0.0 ) + \
                                        (res.owner_commission if res.owner_commission else 0.0 ) + \
                                        (res.brokerage_commission if res.brokerage_commission else 0.0 ) + \
                                        (res.labour_cost if res.labour_cost else 0.0 ) + \
                                        (res.extra_cost if res.extra_cost else 0.0 ) + \
                                        (res.toll if res.toll else 0.0 ) + \
                                        (res.additional_taxes if res.additional_taxes else 0.0 )

    @api.multi
    @api.depends('calculated_total_cost','vehicle_size')
    def calculate_cost_per_ton(self):
        for res in self:
            if res.calculated_total_cost != 0  and res.vehicle_size != 0  :
                res.cost_per_ton = res.calculated_total_cost / res.vehicle_size


class LogisticFuelLog(models.Model):
    _name = "logistic.fuel.log"
    _description = "Logistic Fuel Log"
    _order    = 'id desc'

    name = fields.Char(string = "Fuel Log No.")
    date = fields.Date(string="Date" , default=lambda self: fields.datetime.now())
    fuel_price_one2many = fields.One2many('logistic.fuel.price','fuel_log_id',string="Fuel Price")
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('Done', 'Done'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='Draft')

    @api.model
    def create(self, vals):
        result = super(LogisticFuelLog, self).create(vals)
        result.name = "FL/"+ str(result.id).zfill(5)
        return result

    @api.model
    @api.multi
    def get_fuelprice_schedular(self):
        todaydate = "{:%Y-%m-%d}".format(datetime.now())
        vals_sch = {
                    'date': datetime.today(),
                    'name': 'Fuel Log (' + todaydate + ') ',
                    'state' : 'Done',
                    }
        fuel_log_id = self.env['logistic.fuel.log'].sudo().create(vals_sch)
        try:
            data=[]
            page = requests.get("https://economictimes.indiatimes.com/wealth/fuel-price/diesel")
            print("Diesel : Page Loaded successfully : " + str(page.status_code)+"\n")
            soup = BeautifulSoup(page.content, 'html.parser')
            tables=soup.find_all('table')
            for row in tables:
                for j in row.find_all('tr'):
                    datadict={}
                    datalist=j.find_all('td')
                    if(len(datalist)!=0):
                        datadict["State"]=datalist[0].text
                        datadict["Price"]=datalist[1].text
                        datadict["Change"]=datalist[2].text
                    data.append(datadict)

            if data:
                for drow in data:
                    
                    cityname=""
                    price=""
                    changes=""
                    for dkey,dval in drow.iteritems():
                        if(dkey=="State"):
                            cityname=dval;
                        if(dkey=="Price"):
                            price=dval;
                        if(dkey=="Change"):
                            changes=dval;
                        else:
                            pass

                        if cityname and price and changes:
                            state_name = (cityname).encode('ascii', 'ignore').decode('ascii')
                            price_name = (price).encode('ascii', 'ignore').decode('ascii')
                            state_id = self.env['res.country.state'].sudo().search([('name', '=', state_name)], limit=1)

                            if state_id:

                                vals_line = {
                                    'name': state_name,
                                    'fuel_log_id': fuel_log_id.id,
                                    'price_char': price_name,
                                    'change_price': (changes).encode('ascii', 'ignore').decode('ascii'),
                                    'state_id': state_id.id,
                                    'price': (price_name).split('/')[0]
                                }

                                self.env['logistic.fuel.price'].sudo().create(vals_line)
                    
                  

        except Exception as ex:
            raise ValidationError(_(ex))
            print(ex)


    @api.multi
    def get_fuelprice(self):
        try:
            data=[]
            page = requests.get("https://economictimes.indiatimes.com/wealth/fuel-price/diesel")
            print("Diesel : Page Loaded successfully : "+str(page.status_code)+"\n")
            soup = BeautifulSoup(page.content, 'html.parser')
            tables=soup.find_all('table')
            for row in tables:
                for j in row.find_all('tr'):
                    datadict={}
                    datalist=j.find_all('td')
                    if(len(datalist)!=0):
                        datadict["State"]=datalist[0].text
                        datadict["Price"]=datalist[1].text
                        datadict["Change"]=datalist[2].text
                    data.append(datadict)

            if data:
                for drow in data:
                    
                    cityname=""
                    price=""
                    changes=""
                    for dkey,dval in drow.iteritems():
                        if(dkey=="State"):
                            cityname=dval;
                        if(dkey=="Price"):
                            price=dval;
                        if(dkey=="Change"):
                            changes=dval;
                        else:
                            pass

                        if cityname and price and changes:
                            state_name = (cityname).encode('ascii', 'ignore').decode('ascii')
                            price_name = (price).encode('ascii', 'ignore').decode('ascii')
                            state_id = self.env['res.country.state'].sudo().search([('name', '=', state_name)], limit=1)

                            if state_id:

                                vals_line = {
                                    'name': state_name,
                                    'fuel_log_id': self.id,
                                    'price_char': price_name,
                                    'change_price': (changes).encode('ascii', 'ignore').decode('ascii'),
                                    'state_id': state_id.id,
                                    'price': (price_name).split('/')[0]
                                }

                                self.env['logistic.fuel.price'].sudo().create(vals_line)
                    
                  

            self.state == 'Done'
        except Exception as ex:
            raise ValidationError(_(ex))
            print(ex)
    

class LogisticFuelPrice(models.Model):
    _name = "logistic.fuel.price"
    _description = "Logistic Fuel Price"

    name = fields.Char(string = "State/City")
    date = fields.Date(string="Date" , default=lambda self: fields.datetime.now())
    fuel_log_id = fields.Many2one('logistic.fuel.log', string='Fuel Log', ondelete='cascade')
    price = fields.Float(string='Price')
    price_char = fields.Char(string='Price Char')
    change_price = fields.Char(string='Change')
    state_id = fields.Many2one('res.country.state', string='State')



class LogisticTrail(models.Model):
    _name = 'logistic.trail'
    _description = "Logistic Trail"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    name = fields.Char(string = "LT")
    partner_id = fields.Many2one('res.partner',string="Partner" )
    date_start = fields.Date(string="From Date" , default=lambda self: fields.datetime.now())
    date_end = fields.Date(string="To Date" , default=lambda self: fields.datetime.now())
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self._uid, track_visibility='always')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('inprogress', 'InProgress'),
        ('done', 'Message Sent'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('credit.note'))
    report_generated = fields.Boolean("Report", default=False)
    invoice_no = fields.Char(string = "Invoice No")
    value = fields.Char(string = "Code")
    c_bpartner_id = fields.Char(string = "Partner")
    dateacct = fields.Date(string="Invoiced Date")
    documentno = fields.Char(string = "Documentno")
    deliveryadd = fields.Text(string = "Delivery Addr")
    delivery_date = fields.Date(string="Delivery Date")
    mobile = fields.Char(string = "Mobile No")
    chln_no=fields.Char(string = "Chln no")
    chln_date=fields.Date(string = "Chln Date")
    vhcl_no=fields.Char(string = "Vhcl No")
    lr_no=fields.Char(string = "Lr No")
    lr_date=fields.Date(string = "Lr Date")
    trpt_name=fields.Char(string = "Trpt Name")
    podate=fields.Date(string = "Po Date")
    ponum=fields.Char(string = "Po No")
    driver_mob=fields.Char(string = "Driver Mob")
    time_rml=fields.Datetime(string = "Time RML")
    message_text = fields.Text(string = "Message")
    lt_line_one2many = fields.One2many('logistic.trail.line','lt_id',string="LT Line")
    partner_name = fields.Char(string = "Partner")
    condition = fields.Selection([
        ('logistic', 'Logistic'),
        ('schedular', 'Schedular')], string='Condition')
    date_schedular = fields.Date(string="Date")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id :
            if self.partner_id.bp_code:
                self.value = self.partner_id.bp_code
            else:
                raise ValidationError(_('Partner Code not found. Kindly enter '))

    
    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and self.env.uid != 1:
                raise UserError(_('You can only delete Draft Entries'))
        return super(LogisticTrail, self).unlink()


    @api.multi
    def db_configuration(self):
        conn_pg = None
        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)
        if config_id:

            print "#-------------Select --TRY----------------------#"
            conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, 
                password=config_id.password, host= config_id.ip_address, port= config_id.port)
            pg_cursor = conn_pg.cursor()

        return pg_cursor

    @api.multi
    def sendSMS(self,apikey, numbers, sender, message):
        data =  urlencode({'apikey': apikey, 'numbers': numbers,
            'message' : message, 'sender': sender})
        data = data.encode('utf-8')
        request = Request("https://api.textlocal.in/send/?")
        f = urlopen(request, data)
        fr = f.read()
        return(fr)
     
    @api.multi
    def send_message(self):
        message = ''

        lt_line = self.lt_line_one2many.search([('lt_id', '=', self.id),('state', '=', 'approved')])

        if  len(lt_line) < 1:
            raise ValidationError(_('No Records Selected'))


        for res in lt_line:

            if len(res.deliveryadd) > 99:
                raise ValidationError(_('Delivery Address is too long. Kindly trim down the Delivery Address'))

            message ='Walplast: Material Delivered at '+ res.deliveryadd + ', on Date ' \
            + res.delivery_date + ' delivered by ' + res.vhcl_no \
            + (', InvNo. '+ res.poreference if res.poreference else res.documentno)

            # if not res.mobile:
            #     raise ValidationError(_('Mobile Number Not Found'))

            if len(res.mobile) != 10:
                raise ValidationError(_('Mobile Number is wrong. Kindly enter 10 Mobile Number'))
            mobile = '91' + res.mobile
            self.state = 'done'

            # resp =  self.sendSMS('AqaOOPzhVKM-YIbUWiw1XeOqvGvhBbNrBjIJlIcVKr', '918446350886','WLPLST',
            # 'Dear Sir, Order 12345 is processed. Qty 20 Tons, Vehicle 12345 ,LR 321 ,Driver No. 8446350886 , Thank you.')
            resp =  self.sendSMS('AqaOOPzhVKM-YIbUWiw1XeOqvGvhBbNrBjIJlIcVKr', mobile,'WLPLST', message)
            print "-------------------------Response -------------------" , resp
            self.message_text = message

        
    @api.multi
    def search_invoices(self):
        conn_pg = None
        partner_name = ''

        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)

        if len(config_id) < 1:
            raise UserError(" DB Connection not set / Disconnected " )

        else:

            ad_client_id=self.company_id.ad_client_id
            value = self.value.upper()

            print "#-------------Select --TRY----------------------#" , value
            try:

                pg_cursor = self.db_configuration()

                if self.company_id:

                    pg_cursor.execute("select \
                     (select name from adempiere.c_bpartner where c_bpartner_id=invc.c_bpartner_id) as CustomerName, \
                     (select value from adempiere.c_bpartner where c_bpartner_id=invc.c_bpartner_id) as CustomerCode, \
                     (select DeliveryAdd from adempiere.c_order where c_order_id=invc.c_order_id) as DeliveryAdd, \
                     invc.dateacct::date, \
                     invc.chln_no, \
                     invc.chln_date::date, \
                     invc.vhcl_no, \
                     invc.lr_no, \
                     invc.lr_date::date, \
                     invc.trpt_name, \
                     invc.podate::date, \
                     invc.ponum, \
                     invc.driver_mob, \
                     invc.documentno, \
                     (select phone from adempiere.c_bpartner where c_bpartner_id=invc.c_bpartner_id) as CustomerCode, \
                      invc.time_rml, invc.poreference \
                        from adempiere.C_Invoice invc where invc.posted = 'Y' and \
                        invc.c_order_id is not null and invc.C_DocType_ID = 1000239 and \
                        invc.docstatus='CO' and invc.ad_client_id = %s and \
                        invc.dateacct::date between %s and %s and \
                    (select value from adempiere.c_bpartner \
                    where c_bpartner_id=invc.c_bpartner_id) = %s" ,(ad_client_id,self.date_start,self.date_end, value))

 
                entry_id = pg_cursor.fetchall()

                if entry_id == []:
                    raise UserError(" No Records Found " )


                print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , entry_id

                for record in entry_id:
                    vals_line = {
                        'lt_id' : self.id,
                        'c_bpartner_id': record[0],
                        'deliveryadd': record[2],
                        'dateacct': record[3],
                        'chln_no': record[4],
                        'chln_date': record[5],
                        'vhcl_no': record[6],
                        'lr_no': record[7],
                        'lr_date': record[8],
                        'trpt_name': record[9],
                        'podate': record[10],
                        'ponum': record[11],
                        'driver_mob': record[12],
                        'documentno': record[13],
                        'mobile':  record[14],
                        'time_rml': record[15],
                        'poreference': record[16],
                        'length_address': len(record[2]) if record[2] else '',
                    }
                    partner_name = record[0]
                    create_ids = self.env['logistic.trail.line'].create(vals_line)

                # create_ids = self.sudo().write(vals_line)
                self.partner_name = partner_name
                self.state='inprogress'

                todaydate = "{:%Y-%m-%d}".format(datetime.now())

                self.name = 'Logistic (' + todaydate + ') ' + self.partner_name
                   
            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    conn_pg.rollback()
         
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#"
                    conn_pg.close()



    @api.multi
    def search_daily_invoice_schedular(self):
        conn_pg = None
        partner_name = ''

        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)

        if len(config_id) < 1:
            raise UserError(" DB Connection not set / Disconnected " )

        else:

            ad_client_id=self.company_id.ad_client_id
            todaydate = self.date_schedular or    "{:%Y-%m-%d}".format(datetime.now())
            # value = self.value.upper()

            print "#-------------Select --TRY----------------------#" 
            try:

                pg_cursor = self.db_configuration()

                if self.company_id:

                    pg_cursor.execute("select \
                        partner.name as CustomerName, \
                        partner.value  as CustomerCode, \
                        (select DeliveryAdd from adempiere.c_order where c_order_id=invc.c_order_id) as DeliveryAdd, \
                        invc.dateacct::date, \
                        invc.chln_no, \
                        invc.chln_date::date, \
                        invc.vhcl_no, \
                        invc.lr_no, \
                        invc.lr_date::date, \
                        invc.trpt_name, \
                        invc.podate::date, \
                        invc.ponum, \
                        invc.driver_mob, \
                        invc.documentno, \
                        partner.phone  as CustomerCode, \
                        invc.time_rml, invc.poreference , \
                        (select name from adempiere.C_BP_Group where C_BP_Group_ID = partner.C_BP_Group_ID) as Group , \
                        (select EMail from adempiere.C_BPartner_Location where c_bpartner_id = partner.c_bpartner_id limit 1) as Email, \
                        invc.c_invoice_id  , \
                        (select email from adempiere.ad_user where AD_User_ID=partner.SalesRep_ID) as sale_email, \
                        (select name from adempiere.ad_user where AD_User_ID=partner.SalesRep_ID) as sale_exec, \
                        cl.c_region_id, \
                        (select name from adempiere.c_region where c_region_id=cl.c_region_id) as State, \
                        (select name from adempiere.c_elementvalue where c_elementvalue_id=invc.user1_id) as BusinessDivision \
                from adempiere.C_Invoice invc \
                    JOIN adempiere.c_bpartner partner ON partner.c_bpartner_id = invc.c_bpartner_id \
                    JOIN adempiere.c_bpartner_location cbl ON cbl.c_bpartner_id = partner.c_bpartner_id \
                    JOIN adempiere.c_location cl ON cl.c_location_id = cbl.c_location_id \
                where \
                    invc.docstatus='CO' and invc.ad_client_id = %s and invc.dateacct::date = %s \
                    and  invc.posted = 'Y' and invc.c_order_id is not null and invc.C_DocType_ID = 1000239 and \
                    (select C_BP_Group_ID from adempiere.C_BP_Group where C_BP_Group_ID = partner.C_BP_Group_ID) \
                    in (1000062 , 1000004 , 1000005 , 1000001 , 1000002)" ,(ad_client_id,todaydate))


                    # 1000062 , 1000004 , 1000005 , 1000001 , 1000002 and Time_Rml is not null


                entry_id = pg_cursor.fetchall()

                if entry_id == []:
                    raise UserError(" No Records Found " )


                # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , entry_id

                for record in entry_id:
                    print "lllllllllloooooooooooooooooooooooooooooooooooooooooooooo", record[8],

                    vals_line = {
                        'lt_id' : self.id,
                        'c_bpartner_id': record[0],
                        'deliveryadd': record[2],
                        'dateacct': record[3],
                        'chln_no': record[4],
                        'chln_date': record[5],
                        'vhcl_no': record[6],
                        'lr_no': record[7],
                        'lr_date': record[8],
                        'trpt_name': record[9],
                        'podate': record[10],
                        'ponum': record[11],
                        'driver_mob': record[12],
                        'documentno': record[13],
                        'mobile':  record[14],
                        'time_rml': record[15],
                        'poreference': record[16],
                        'length_address': len(record[2]) if record[2] else '',
                        'email' : record[18],
                        'c_invoice_id' : (str(record[19]).split('.'))[0] , # (str(line_rec.c_invoice_id).split('.'))[0]
                        'sales_email' : record[20],
                        'sales_exec' : record[21],
                        'state_region' : record[23],
                        'business_division' : record[24],
                    }
                    # partner_name = record[0]
                    create_ids = self.env['logistic.trail.line'].create(vals_line)

                # create_ids = self.sudo().write(vals_line)
                # self.partner_name = partner_name
                self.state='inprogress'
                self.name = 'Daily Schedular (' + todaydate + ') '
                   
            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    conn_pg.rollback()
         
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#"
                    conn_pg.close()




    @api.model
    @api.multi
    def process_daily_invoice_products_schedular_queue(self):
        print "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv process_daily_invoice_products_schedular_queue"
        # self.search_daily_invoice_schedular()

        conn_pg = None
        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)


        if len(config_id) < 1:
            raise UserError(" DB Connection not set / Disconnected " )

        else:

            company_id = self.env['res.company'].sudo().search([('id', '=', 3)], limit=1)

            ad_client_id = company_id.ad_client_id
            todaydate = self.date_schedular or    "{:%Y-%m-%d}".format(datetime.now())


            print "llllllllll ad_client_id    fffffffffffffff" , ad_client_id , self.env.user.company_id

            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, 
                    password=config_id.password, host= config_id.ip_address,port=config_id.port)
                pg_cursor = conn_pg.cursor()

                pg_cursor.execute("select \
                        partner.name as CustomerName, \
                        partner.value  as CustomerCode, \
                        (select DeliveryAdd from adempiere.c_order where c_order_id=invc.c_order_id) as DeliveryAdd, \
                        invc.dateacct::date, \
                        invc.chln_no, \
                        invc.chln_date::date, \
                        invc.vhcl_no, \
                        invc.lr_no, \
                        invc.lr_date::date, \
                        invc.trpt_name, \
                        invc.podate::date, \
                        invc.ponum, \
                        invc.driver_mob, \
                        invc.documentno, \
                        partner.phone  as CustomerCode, \
                        invc.time_rml, invc.poreference , \
                        (select name from adempiere.C_BP_Group where C_BP_Group_ID = partner.C_BP_Group_ID) as Group , \
                        (select EMail from adempiere.C_BPartner_Location where c_bpartner_id = partner.c_bpartner_id) as Email, \
                        invc.c_invoice_id , \
                        (select email from adempiere.ad_user where AD_User_ID=partner.SalesRep_ID) as sale_email, \
                        (select name from adempiere.ad_user where AD_User_ID=partner.SalesRep_ID) as sale_exec, \
                        cl.c_region_id, \
                        (select name from adempiere.c_region where c_region_id=cl.c_region_id) as State, \
                        (select name from adempiere.c_elementvalue where c_elementvalue_id=invc.user1_id) as BusinessDivision \
                from adempiere.C_Invoice invc \
                    JOIN adempiere.c_bpartner partner ON partner.c_bpartner_id = invc.c_bpartner_id \
                    JOIN adempiere.c_bpartner_location cbl ON cbl.c_bpartner_id = partner.c_bpartner_id \
                    JOIN adempiere.c_location cl ON cl.c_location_id = cbl.c_location_id \
                where \
                    invc.docstatus='CO' and invc.ad_client_id = %s and invc.dateacct::date = %s \
                    and  invc.posted = 'Y' and invc.c_order_id is not null and invc.C_DocType_ID = 1000239 and \
                    (select C_BP_Group_ID from adempiere.C_BP_Group where C_BP_Group_ID = partner.C_BP_Group_ID) \
                    in (1000062 , 1000004 , 1000005 , 1000001 , 1000002)" ,(ad_client_id,todaydate)) 

              
                entry_id = pg_cursor.fetchall()

                if entry_id != []:

                    # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , entry_id
                    vals_sch = {
                                'company_id': self.company_id.id,
                                'date_schedular': todaydate,
                                'name': 'Daily Schedular (' + todaydate + ') ',
                                'state' : 'inprogress',
                                'condition' : 'schedular',

                                }

                    invoice_schedular = self.env['logistic.trail'].create(vals_sch)

                    print "lllllllllllllllllllllllllllllllllbbbbbbbbbbbbbbbbbb" , invoice_schedular

                    for record in entry_id:
                        print "lllllllllloooooooooooooooooooooooooooooooooooooooooooooo", record[8],

                        vals_line = {
                            'lt_id' : invoice_schedular.id,
                            'c_bpartner_id': record[0],
                            'deliveryadd': record[2],
                            'dateacct': record[3],
                            'chln_no': record[4],
                            'chln_date': record[5],
                            'vhcl_no': record[6],
                            'lr_no': record[7],
                            'lr_date': record[8],
                            'trpt_name': record[9],
                            'podate': record[10],
                            'ponum': record[11],
                            'driver_mob': record[12],
                            'documentno': record[13],
                            'mobile':  record[14],
                            'time_rml': record[15],
                            'poreference': record[16],
                            'length_address': len(record[2]) if record[2] else '',
                            'email' : record[18],
                            'condition' : 'schedular',
                            'c_invoice_id' : (str(record[19]).split('.'))[0] , # (str(line_rec.c_invoice_id).split('.'))[0] 
                            'sales_email' : record[20],
                            'sales_exec' : record[21],
                            'state_region' : record[23],
                            'business_division' : record[24],
                        }
                        # partner_name = record[0]
                        create_ids = self.env['logistic.trail.line'].create(vals_line)

                    # create_ids = self.sudo().write(vals_line)
                   
            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    conn_pg.rollback()
         
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#"
                    conn_pg.close()

 


class LogisticTrailLine(models.Model):
    _name = 'logistic.trail.line'
    _description = "Logistic Trail Line"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    # @api.multi
    @api.depends('dateacct')
    def _compute_delayed_date(self):
        for res in self:
            if res.delivery_date:
                print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , res.delivery_date
                create_date = dateutil.parser.parse(res.dateacct).date()
                delay = res.delay
                res.delayed_date = create_date + timedelta(days=delay )

                print " --------------------- _compute_delayed_date -------------------------"
    

    # location = fields.Char(string = "Location")
    lt_id  = fields.Many2one('logistic.trail', ondelete='cascade')
    name = fields.Char(string = "LT Line")
    value = fields.Char(string = "Code")
    c_bpartner_id = fields.Char(string = "Partner")
    dateacct = fields.Date(string="Invoiced Date")
    documentno = fields.Char(string = "Documentno")
    deliveryadd = fields.Text(string = "Delivery Addr")
    mobile = fields.Char(string = "Mobile No")
    delivery_date = fields.Date(string="Delivery Date" , default=lambda self: fields.datetime.now())
    chln_no=fields.Char(string = "Chln no")
    chln_date=fields.Date(string = "Chln Date")
    vhcl_no=fields.Char(string = "Vhcl No")
    lr_no=fields.Char(string = "Lr No")
    lr_date=fields.Date(string = "Lr Date")
    trpt_name=fields.Char(string = "Trpt Name")
    podate=fields.Date(string = "Po Date")
    ponum=fields.Char(string = "Po No")
    driver_mob=fields.Char(string = "Driver Mob")
    time_rml=fields.Datetime(string = "Time RML")
    state = fields.Selection([
                            ('draft', 'Draft'),
                            ('approved', 'Approved'),
                            ('reverted', 'Reverted')], 
                            string='Status' , default='draft')

    poreference= fields.Char(string = "Invoice No")
    length_address = fields.Integer(string = "Len") #, compute='onchange_deliveryadd'
    email  = fields.Char(string = "Email")
    c_invoice_id = fields.Char(string = "C_Invoice_Id")
    delay = fields.Integer(string = "Delay",default=2)
    delayed_date = fields.Date(string="Delayed Date", compute=_compute_delayed_date, store=True)
    mail_boolean = fields.Boolean("Mailed", default=False)
    schedular_boolean = fields.Boolean("Schedular", default=False)
    condition = fields.Selection([
        ('logistic', 'Logistic'),
        ('schedular', 'Schedular')], string='Condition')

    lineproduct_one2many = fields.One2many('wp.invoice.line.products','lineproduct_id',string="Product Line")
    html_view = fields.Html("HTML View")
    sales_email = fields.Char(string = "Exec Email")
    sales_exec = fields.Char(string = "Sales Exec")
    date_reverted = fields.Date(string = "Revert Date")
    state_region = fields.Char(string = "State")
    business_division = fields.Char(string = "Business Division")


    @api.multi
    def approve_invoice(self):

        if self.condition == 'logistic':
            if self.lt_id.state !='done':
                if self.state == 'approved':
                    self.state = 'draft'
                else:
                    if not self.mobile:
                        raise UserError(" Enter Mobile No. " )
                    if not self.deliveryadd:
                        raise UserError(" Enter Delivery Addr " )
                    if not self.vhcl_no:
                        raise UserError(" Enter Vehicle No. " )
                    appr_line = {'state': 'draft'}

                    self.lt_id.lt_line_one2many.write(appr_line)
                    self.state = 'approved'

        else:
            print "99999999999999999999999 approve_invoice " , self.email , self.mail_boolean
            if (self.email or self.sales_email)  and  not self.mail_boolean :
                if not self.schedular_boolean:
                    self.mail_boolean = True
                    self.state = 'approved'


                print "--------------------- approve_invoice -------------------------------"
                self.search_daily_invoice_products_schedular()
                self.send_mail()


    @api.onchange('deliveryadd')
    def onchange_deliveryadd(self):
        for res in self:
            if res.deliveryadd :
                res.length_address = len(res.deliveryadd)

    
    @api.model
    @api.multi
    def process_mail_daily_invoice_products_schedular_queue(self):
        print " ------------------ process_mail_daily_invoice_products_schedular_queue ---------------------------"
        date_search = "{:%Y-%m-%d}".format(datetime.now())
        line_data = self.env['logistic.trail.line'].search([("state","=", 'draft'),("condition","=",'schedular')])
        for res in line_data:

            print "aaaaaaaaaaaaaaaaaaaa" , res.documentno , res.delayed_date
            if date_search == res.delayed_date:
                print "mail =-------Initial --====" , res.documentno  , res.mail_boolean , res.state , res.schedular_boolean

                res.schedular_boolean = True
                
                res.approve_invoice()
                # res.mail_boolean = True
                # res.state = 'approved'

                print "mail =--------Ending========" , res.documentno  , res.mail_boolean , res.state , res.schedular_boolean


    @api.multi
    def search_daily_invoice_products_schedular(self):

        print "------------------ search_daily_invoice_products_schedular ------------------------------ "

        conn_pg = None
        partner_name = ''

        config_id = self.env['external.db.configuration'].sudo().search([('state', '=', 'connected')], limit=1)

        if len(config_id) < 1:
            raise UserError(" DB Connection not set / Disconnected " )

        else:

            try:
                if config_id:

                    print "#-------------Select --TRY----------------------#" , self.c_invoice_id
                    conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username,
                     password=config_id.password,
                     host= config_id.ip_address,port= config_id.port)
                    pg_cursor = conn_pg.cursor()


                    pg_cursor.execute("select c_invoiceline_id , c_invoice_id, \
                        (select name from adempiere.m_product where m_product_id = cil.m_product_id ) as Product, \
                        QtyEntered, PriceList, TotalPriceList, \
                        (select name from adempiere.c_uom where c_uom_id = cil.c_uom_id ) as UOM \
                        from adempiere.c_invoiceline  cil \
                        where c_invoice_id = %s and m_product_id is not null " ,[self.c_invoice_id])


                    entry_id = pg_cursor.fetchall()

                    if entry_id == []:
                        raise UserError(" No Records Found " )


                    # print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , entry_id

                    for record in entry_id:
                        vals_line = {
                            'lineproduct_id' : self.id,
                            'c_invoiceline_id':record[0],
                            'c_invoice_id':record[1],
                            'product':record[2],
                            'qtyentered':record[3],
                            'pricelist':record[4],
                            'totalpricelist':record[5],
                            'uom':record[6],

                        }
                        create_ids = self.env['wp.invoice.line.products'].create(vals_line)

                   
            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    conn_pg.rollback()
         
                print 'Error %s' % e        

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#"
                    conn_pg.close()


    @api.multi
    def send_mail(self):
        amnt = totalcn = totalamount = 0.0
        body = """ """
        main_body  = """ """
        line_html = subject = ""
        main_id = self.id
        todaydate = "{:%d-%b-%y}".format(datetime.now())

        config_mail = self.env['cir.escalation.matrix'].search([("id","!=",0)])
        email_from =  config_mail.salesupport_mail_id

        toll_free_user = config_mail.toll_free_user
        if self.sales_email:
            email_cc = self.sales_email + ','  + toll_free_user
        else:
            email_cc = toll_free_user

        # email_to = 'harshal.bhoir@walplast.com'
        email_to = self.email
        
        main_body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>

            <table >
                <tbody>
                    <tr >
                        <td >
                            <img src="https://www.walplast.net/sales_meet/static/description/company_walplast.png"/>
                        </td>
                        
                    </tr>
                </tbody>
            </table>
            <br/>

            <table >
                <tbody>
                    <tr >
                        <td valign="top" style="padding-top:0; padding-right:18px; padding-bottom:9px; 
                                                padding-left:368px;font-size: large;">
                            <p>Shipping Confirmation Order # %s</p>
                        </td> 
                    </tr>

                    <tr >
                        <td valign="top" style="padding-top:0; padding-right:18px; 
                                                padding-bottom:9px; padding-left:18px;">
                            <p style="font-size: 16px; color: black;" >Hello %s,</p>
                            <p style="color: black;">We thought you'd like to know that we've dispatched your item(s). 
                            Your order is on the way.</p>
                        </td> 
                        
                    </tr>
                </tbody>
            </table>
            <br/>

        """ % (self.documentno, self.c_bpartner_id)

        for l in self.lineproduct_one2many:
            line_html += """
            <tr>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px; text-align: center;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
            </tr>
            """ % (l.product , l.qtyentered, l.uom)

            totalamount += l.pricelist

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>

            <h3 style="color: black;">Following are the details as Below Listed. </h3>
            <div class="table-responsive">   

            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            Product
                        </th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            QTY
                        </th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            UOM
                        </th>
                    </tr>
                    %s
                </tbody>
            </table>
            </div>
            <br/>


        """ % (line_html)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        approve_url = base_url + '/salesdelivery?%s' % (url_encode({
                    'model': 'logistic.trail.line',
                    'delivery_id': self.id,
                    'res_id': self.id,
                    'action': 'approve_delivery_sales_order',
                }))

        button_line = """<br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <td>
                        <p>Click Here: </p>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Material Delivered</a>
                        </td>
                    </tr>
                </tbody>
            </table>
            """ % (approve_url)


        footer_body = """ 

            <table align="left" border="0" cellpadding="0" cellspacing="0" style="max-width:100%; 
            min-width:100%;" width="100%" >
                <tbody>
                    <tr>
                    
                        <td valign="top" style="padding-top:0; padding-right:18px; padding-bottom:9px; padding-left:18px;">

                        <h3>Note : </h3>

                        <p>Request to kindly confirm the delivery at your site, within 7 working days.
                         If not it will be considered as delivered</p>
                        
                        

                        <p>In case of shortage/ damage material please click on below link : (Only for Sales Exec)</p>
                        <a href="https://cutt.ly/RyTHioU" target="_blank" style="-webkit-user-select: none; 
                        padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF;
                         border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; 
                         font-weight: 400; text-align: center;
                          vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; 
                          background-color: #337ab7; 
                          border: 1px solid #337ab7; margin-right: 10px;">CIR Link
                        </a>

                        <br/><br/>
                    
                        <h3>Terms &amp; Condition</h3>
                        <ol>
                            
                            <li><p>If you require any more information or have any questions about our site's disclaimer, 
                            please feel free to contact us by email at&nbsp;
                            <a href="mailto:sales.associates@walplast.com">sales.associates@walplast.com</a></p></li>

                            <li><p>Interest will be Charged @ 24 % p.a from the date of
                                invoice if not paid within 7 days from the date of good received. Goods once
                                sold cannot be returned and/or exchanged.</p></li>

                            <li><p> Payment are to be made by A/c Payee Cheques or by NEFT/RTGS to our Bank A/C</p></li>

                            <li><p> We hereby certify that my/our registeration certificate under the GST ACT2017 is in 
                            force on the date on which the sale of goods specified in this 
                            tax invoice is made by me/us.</p></li>

                        </ol>

                    </td>
                </tr>
                </tbody>
            </table>


        """


        subject = "Material Delivered by Walplast - ( %s )"  % (todaydate)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
      
        full_body = main_body  + body + button_line + footer_body
        self.html_view = full_body

        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': main_id,
                'email_from': email_from,
                'email_to': email_to,
                'email_cc': email_cc,
                'subject': subject,
                'body_html': full_body,
                'auto_delete': False,
            })

        composed_mail.send()
        self.state = 'approved'

        print "llllllllllllllllllllllllllllllllll Mail Sent to %s and %s" % (self.email, email_cc)

    @api.multi
    def approve_delivery_sales_order(self):
        self.sudo().send_user_mail()
        self.state = 'reverted'
        self.date_reverted = datetime.now()

    @api.multi
    def send_user_mail(self):
        main_body  = """ """
        subject = ""
        main_id = self.id
        totalamount = 0.0
        # config_mail = self.env['credit.note.config'].search([("id","!=",0)])
        # email_to =  config_mail.confirmation_mail

        config_mail = self.env['cir.escalation.matrix'].search([("id","!=",0)])
        email_to =  config_mail.confirmation_mail

        toll_free_user = config_mail.toll_free_user
        if self.sales_email:
            email_cc = self.sales_email + ','  + toll_free_user
        else:
            email_cc = toll_free_user

        # toll_free_user = 'mustafa.shaikh@walplast.com'
        # if self.sales_email:
        #     email_cc = self.sales_email + ','  + toll_free_user
        # else:
        #     email_cc = 'mustafa.shaikh@walplast.com'

        todaydate = "{:%d-%b-%y}".format(datetime.now())

        main_body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <p>Hi Team,</p>

            <br/>
            <br/>

            <p><b>%s</b> has confirmed that material of invoice 
            <b>%s</b> dated <b>%s</b> has been delivered to its given delivery address.</p>

        """ % ( self.c_bpartner_id , self.documentno , self.dateacct)

        line_html = ""

        for l in self.lineproduct_one2many:
            line_html += """
            <tr>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px; text-align: center;">%s</td>
                <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
            </tr>
            """ % (l.product , l.qtyentered, l.uom)

            totalamount += l.pricelist

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>

            <h3 style="color: black;">Following are the details as Below Listed. </h3>
            <div class="table-responsive">   

            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            Product
                        </th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            QTY
                        </th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">
                            UOM
                        </th>
                    </tr>
                    %s
                </tbody>
            </table>
            </div>
            <br/>


        """ % (line_html)

        subject = "[Confirmation] Material Delivered to %s - ( %s )"  % (self.c_bpartner_id, todaydate)
        full_body = main_body + body

        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': main_id,
                'email_from': self.email,
                'email_to': email_to,
                'email_cc': email_cc,
                'subject': subject,
                'body_html': full_body,
                'auto_delete': False,

            })

        composed_mail.send()
        self.state = 'reverted'

        print "llllllllllllllllllllllllllllllllll Mail Sent to %s and %s" % (email_to, email_cc)


class WpInvoiceLineProducts(models.Model):
    _name = 'wp.invoice.line.products'
    _description = "Invoice Line Products"
    
    lineproduct_id  = fields.Many2one('logistic.trail.line', ondelete='cascade')
    name = fields.Char(string = "Product Line")
    c_invoiceline_id = fields.Char(string = "C_Invoiceline_Id")
    c_invoice_id = fields.Char(string = "C_Invoice_Id")
    product = fields.Char(string = "Product")
    qtyentered = fields.Float(string = "Qty")
    pricelist = fields.Float(string = "Price")
    totalpricelist = fields.Float(string = "Total")
    uom = fields.Char(string = "UOM")
