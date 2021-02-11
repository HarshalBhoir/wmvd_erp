#!/usr/bin/env bash

from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from time import gmtime, strftime
import calendar
from odoo.tools.translate import _
from odoo import api, tools, fields, models, _ , registry, SUPERUSER_ID
from odoo.exceptions import UserError, Warning, ValidationError
import dateutil.parser
import time
import psycopg2
import urllib
from cStringIO import StringIO
import xlwt
import re
import base64
from odoo import http
from werkzeug import url_encode
import requests
import json
import logging
_logger = logging.getLogger(__name__)

# idempiere_url="http://35.200.227.4/ADInterface/services/compositeInterface"
idempiere_url="https://erpnew.wmvd.live/ADInterface/services/compositeInterface?wsdl"
headers = {'content-type': 'text/xml'}
datetimeFormat = '%Y-%m-%d %H:%M:%S'
google_key = 'AIzaSyAueXqmASv23IO3NSdPnVA_TNJOWADjEh8'

todaydate = "{:%d-%b-%y}".format(datetime.now())

AVAILABLE_PRIORITIES = [
    ('0', 'Poor'),
    ('1', 'Very Low'),
    ('2', 'Low'),
    ('3', 'Normal'),
    ('4', 'High'),
    ('5', 'Very High')]

ZONE = [
    ('north', 'North'),
    ('east', 'East'),
    ('central', 'Central'),
    ('Gujarat', 'Gujarat'),
    ('west', 'West'),
    ('south', 'South'),
    ('export', 'Export')]

STATE=[
    ('draft', 'Draft'),
    ('done', 'Generated'),
    ('refused', 'Refused'),
    ('approved', 'Approved'),
    ('posted', 'Posted'),
    ('Closed', 'Closed')]

class sample_requisition(models.Model):
    _name = 'sample.requisition'
    _description = "Sample Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    # @api.multi
    @api.depends('quantity','excess_quantity')
    def _compute_total_quantity(self):
        for res in self:
            if res.quantity or res.excess_quantity:
                print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , res.quantity
                res.total_quantity = (res.quantity if res.quantity else 0.0) + \
                (res.excess_quantity if res.excess_quantity else 0.0)

                print " --------------------- _compute_total_quantity -------------------------"


    @api.depends('product_id')
    def _compute_product_quantity_distributer(self):
        for res in self:
            if res.product_id and res.partner_id:
                product_lines = self.env['sample.product.line'].sudo().search([('partner_id', '=', self.partner_id.id),
                                                                ('product_id', '=', self.product_id.id)])
                product_sum = sum([x.quantity for x in product_lines])

                if product_sum <= 0:
                    res.zero_qty = True
                    res.excess_taken = True
                else:
                    res.zero_qty = False
                    res.excess_taken = False

                res.distributer_product_quantity = product_sum

   
    name = fields.Char(string = "Sample No.")
    partner_id = fields.Many2one('res.partner',string="Distributor / Retailer" )
    date_sample = fields.Date(string="Sample Date" , 
        default=lambda self: fields.datetime.now(), track_visibility='always')
    user_id = fields.Many2one('res.users', string='User', 
        default=lambda self: self._uid, track_visibility='always')
    state = fields.Selection(STATE, string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('sample.requisition'))
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
    contact_person = fields.Char(string = "Contact Person")
    contact_no = fields.Char(string = "Contact No", size = 10)
    applicator =  fields.Char(string = "Applicator")
    applicator_no =  fields.Char(string = "Applicator No", size = 10)
    applicator_cost =  fields.Float(string = "Applicator Cost")
    city = fields.Char(string = "City")
    project_size = fields.Char(string = "Project Size(Sq.Ft)")
    set_priority=fields.Selection(AVAILABLE_PRIORITIES , string='Rating')
    customer_feedback = fields.Text(string = "Cust Feedback")
    order_quantity = fields.Float(string='Order Qty(Kg)',  store=True)
    order_amt = fields.Float(string='Order Amt',  store=True)
    followup_date = fields.Date(string="Follow Up Date" )
    sample_attachments = fields.Many2many('ir.attachment', 'sample_attachments_rel' , copy=False, attachment=True)
    checkin_lattitude = fields.Float('Checkin Latitude' , digits=(16, 5) , store=True, track_visibility='onchange') 
    checkin_longitude = fields.Float('Checkin Longitude', digits=(16, 5), store=True, track_visibility='onchange') 
    reverse_location = fields.Char('Current Location', track_visibility='onchange')
    latlong_bool = fields.Boolean("Latlong Bool" )
    distributer_product_quantity = fields.Float(string='Quantity Present(Qty)', 
        compute=_compute_product_quantity_distributer, store=True)
    zero_qty =  fields.Boolean("Zero Qty" )
    bags = fields.Integer(string="Bags")
    partner_bool =  fields.Boolean("Partner Bool", default=False )
    state_id = fields.Many2one('res.country.state', string='State')
    order_status = fields.Selection([
        ('Order Received', 'Order Received'),
        ('Follow up', 'Follow up'),
        ('Order Dropped/Loose', 'Order Dropped/Loose'),
        ], string='Order Status', copy=False, index=True)
    zone = fields.Selection(ZONE, string='Zone', copy=False, index=True)
    manager_id = fields.Many2one('res.users', string='Manager')
    zsm_id = fields.Many2one('res.users', string='ZSM')
    applicator_type = fields.Selection([
        ('Internal', 'Internal'),
        ('External', 'External')], string='Applicator Type', copy=False, index=True)

    @api.onchange('state_id')
    def onchange_state_id(self):
        if self.state_id:
            escalation = self.env['cir.escalation.line'].search([('company_id','=',self.company_id.id),
                ('state_id','=',self.state_id.id)])
            if escalation:
                for esc in escalation:
                    self.zsm_id = esc.zsm_user_id.id
                    self.manager_id = esc.manager_id.id
                    self.zone = esc.zone
        else:
            self.zsm_id = False
            self.manager_id = False
            self.zone = False


    @api.onchange('zone')
    def onchange_zone(self):
        if self.zone:
            escalation = self.env['cir.escalation.line'].search([('company_id','=',self.company_id.id),
                ('state_id','=',self.state_id.id),('zone','=',self.zone)])
            if escalation:
                for esc in escalation:
                    self.zsm_id = esc.zsm_user_id.id
                    self.manager_id = esc.manager_id.id
        else:
            self.zsm_id = False
            self.manager_id = False
    

    @api.model
    @api.multi
    def process_update_address_scheduler_queue(self):
        count = 0
        for rec in self.sudo().search([('state', '=','done'),('reverse_location', '=',False)]) : 
            if rec.checkin_lattitude and rec.checkin_longitude :
                f = urllib.urlopen("https://maps.googleapis.com/maps/api/geocode/json?latlng=%s,%s&key=%s" %(rec.checkin_lattitude, 
                    rec.checkin_longitude, google_key))
                values = json.load(f)
                address = (values["results"][1]['formatted_address']).encode('utf8')
                rec.write({'reverse_location': address})
                f.close()
                count +=1
                print "Count *************************************" , count , address

        print "Update Address Schedular - Successfull"

    @api.multi
    def refresh_form(self):
        return True

    @api.multi
    def post_data(self):
        self.sudo().write({'state': 'posted'})

    @api.multi
    def set_to_draft(self):
        self.sudo().write({'state': 'draft'})

    @api.multi
    def set_to_close(self):
        self.sudo().write({'state': 'Closed'})

    @api.multi
    def update_data(self):

        if not (self.checkin_lattitude or self.checkin_longitude):
            raise UserError("Edit the Form and Click on 'Update Address' Button, then click on 'Submit' Button")
       
        if self.applicator_type == 'External':
            self.request_approval()

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
            raise UserError("No Sampling issued for this Distributor / Retailer. \n \
                Kindly contact Sales Support Team or Select other partner.")

    @api.multi
    def update_data_to_issuance(self):

        issuance = self.env['sample.issuance'].sudo().search([('partner_id', '=', self.partner_id.id)], limit=1)

        if issuance:
            if self.state == 'refused':
                delete_line_data = {'sample_requisition_id': self.id, 'sample_issuance_id': issuance.id }
                self.env['sample.product.line'].sudo().search([('sample_requisition_id', '=', self.id),
                    ('sample_issuance_id', '=', issuance.id)]).unlink()
        else:
            raise UserError("No Sampling issued for this Distributor / Retailer. \n \
                Kindly contact Sales Support Team or Select other partner.")


    @api.model
    def create(self, vals):
        result = super(sample_requisition, self).create(vals)

        result.name = self.env['ir.sequence'].sudo().next_by_code('sample.requisition') or '/' 

        if result.partner_id:
            product_id = self.env['sample.product.line'].sudo().search([('partner_id', '=', result.partner_id.id)])
            if not product_id:
                raise UserError("No Sampling issued for this Distributor / Retailer. \n \
                 Kindly contact Sales Support Team or Select other partner.")

        if result.quantity == 0 and result.zero_qty == False:
            raise UserError("Quantity cannot be 0 KG. Enter proper quantity in KG")

        if result.applicator_type == 'External'  and result.applicator_cost == 0:
            raise UserError("Applicator Cost cannot be 0 KG. Enter proper Cost")
        
        return result

    @api.multi
    def write(self, vals):
        result = super(sample_requisition, self).write(vals)

        if self.applicator_type == 'External'  and self.applicator_cost == 0:
            raise UserError("Applicator Cost cannot be 0 KG. Enter proper Cost")

        return result



    @api.onchange('partner_id')
    def _onchange_distributor(self):
        for res in self:
            if res.partner_id:
                product_id = self.env['sample.product.line'].sudo().search([('partner_id', '=', res.partner_id.id)])
                if product_id:
                    res.partner_bool = True
                    return {'domain': {'product_id': [('id', 'in', [i.product_id.id for i in product_id]),('sale_ok', '=', True)]}}
                else:
                    raise UserError("No Sampling issued for this Distributor / Retailer. Kindly contact Sales Support Team.")

            else:
                res.partner_bool = False
                res.product_id = False
                res.distributer_product_quantity = False

    @api.multi
    def approve_data(self):
        self.sudo().write({'state': 'approved'})
        if self.applicator_type == 'External':
            self.send_mail_to_user()
        
        # self.update_data_to_issuance()

    @api.multi
    def refuse_data(self):
        self.sudo().write({'state': 'refused'})
        if self.applicator_type == 'External':
            self.send_mail_to_user()
            self.update_data_to_issuance()

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
    def request_approval(self):
        main_body  = """ """
        subject = ""
        main_id = self.id
        totalamount = 0.0
        email_from = self.user_id.email
        matrix= self.env['cir.escalation.matrix'].search([('company_id','=',self.company_id.id)], limit=1)
        support_mail_ids = [(user.email).encode('ascii', 'ignore') for user in matrix.support_user_ids]
        escalation = self.env['cir.escalation.line'].search([
                                ('company_id','=',self.company_id.id),
                                ('state_id','=',self.state_id.id),
                                ('zone','=',self.zone)], limit=1)
        supportuser_mail_ids = [(user.email).encode('ascii', 'ignore') for user in escalation.support_user_ids]
        support_mail_ids.extend(supportuser_mail_ids)
        support_mail_ids.append(self.zsm_id.email)

        email_cc = ",".join(support_mail_ids)

        print "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaddddddddddddddd", support_mail_ids, email_cc

        email_to =  self.manager_id.email

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_check = base_url + '/web#%s' % (url_encode({
                'model': self._name,
                'view_type': 'form',
                'id': main_id,
            }))

        approve_url = base_url + '/meeting?%s' % (url_encode({
                'model': self._name,
                'meeting_id': main_id,
                'res_id': self.id,
                'action': 'approve_meeting',
            }))

        reject_url = base_url + '/meeting?%s' % (url_encode({
                'model': self._name,
                'meeting_id': main_id,
                'res_id': self.id,
                'action': 'refuse_meeting',
            }))

        main_body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>

            <p>Hi Team,</p>
            <h3>The following sampling request is created on %s by %s and is requesting an approval from your end.</h3>

            <table>
                    <tr>    <td style=" text-align: left;padding: 8px;">Meeting Date</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Distributor</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Counter/Retailer</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Product</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Total Quantity</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Total Cost</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">City</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">State</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Zone</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Manager</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">ZSM</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Contact Person</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Applicator</td>    <td> : %s</td></tr>
                    <tr>    <td style=" text-align: left;padding: 8px;">Order Status</td>    <td> : %s</td></tr>
                    
            </table>
            <br/>

            <h3>Kindly take necessary action by clicking the buttons below:</h3>

            <td>
                <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; 
                line-height: 18px; color: #FFFFFF; border-color:#337ab7; text-decoration: none; display: inline-block;
                margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; cursor: pointer; 
                white-space: nowrap; background-image: none; background-color: #337ab7; 
                  border: 1px solid #337ab7; margin-right: 10px;">Approve</a>
            </td>
            <td>
                <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; 
                line-height: 18px; color: #FFFFFF; border-color:#337ab7; text-decoration: none; display: inline-block;
                margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; cursor: pointer; 
                white-space: nowrap; background-image: none; background-color: #337ab7; 
                  border: 1px solid #337ab7; margin-right: 10px;">Reject</a>
            </td>

            <td>
                <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; 
                line-height: 18px; color: #FFFFFF; border-color:#337ab7; text-decoration: none; display: inline-block;
                margin-bottom: 0px; font-weight: 400; text-align: center; vertical-align: middle; cursor: pointer; 
                white-space: nowrap; background-image: none; background-color: #337ab7; 
                  border: 1px solid #337ab7; margin-right: 10px;">Check Request</a>
            </td>

        """ % (self.date_sample, self.user_id.name , self.date_sample, 
            self.partner_id.name, self.lead_id.name or self.project_partner_id.name or '', 
            self.product_id.name, self.total_quantity, 
            self.applicator_cost, self.city, self.state_id.name,
            self.zone, self.manager_id.name, self.zsm_id.name, self.contact_person, self.applicator,
            self.order_status or '', approve_url, reject_url, report_check)


        subject = "[Request] Approval for sampling requisition ( %s )- ( %s )" \
         % (self.partner_id.name, self.date_sample)
        full_body = main_body

        self.send_generic_mail(subject, full_body, email_from, email_to, email_cc)


    @api.multi
    def send_mail_to_user(self):
        main_body  = """ """
        subject = status = ""
        main_id = self.id
        totalamount = 0.0
        email_from = self.manager_id.email
        email_to = self.user_id.email

        matrix= self.env['cir.escalation.matrix'].search([('company_id','=',self.company_id.id)], limit=1)
        support_mail_ids = [(user.email).encode('ascii', 'ignore') for user in matrix.support_user_ids]
        escalation = self.env['cir.escalation.line'].search([('company_id','=',self.company_id.id),
                                ('state_id','=',self.state_id.id), ('zone','=',self.zone)], limit=1)
        supportuser_mail_ids = [(user.email).encode('ascii', 'ignore') for user in escalation.support_user_ids]
        support_mail_ids.extend(supportuser_mail_ids)
        support_mail_ids.append(self.zsm_id.email)
        email_cc = ",".join(support_mail_ids)

        if self.state == 'approved':
            status = 'approved'
            subject = "[Approved] Sampling Requisition to %s - ( %s )"  % (self.lead_id.name or self.project_partner_id.name, self.date_sample)

        else:
            status = 'refused'
            subject = "[Refused] Sampling Requisition to %s - ( %s )"  % (self.lead_id.name or self.project_partner_id.name, self.date_sample)

        main_body = """ <p>Hi %s,</p> <br/>
            <p>The request for sampling requistion for <b>%s</b> is %s. </p>
        """ % ( self.user_id.name , self.lead_id.name or self.project_partner_id.name,  status)
  
        full_body = main_body + self.report_check()

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
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('sample.issuance'))
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
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('sample.erp.update'))

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
            try:

                if config_id:

                    print "#-------------Select --TRY----------------------#"
                    conn_pg = psycopg2.connect(dbname= config_id.database_name, user=config_id.username, password=config_id.password,
                     host= config_id.ip_address,port= config_id.port)
                    pg_cursor = conn_pg.cursor()

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

                    # pg_cursor.execute('select documentno from adempiere.C_Order where \
                    # documentno = %s and ad_client_id = %s ' ,(self.name,ad_client_id))
                    # pg_cursor.execute("select * from adempiere.daily_schedular_query()")

 
                    entry_id = pg_cursor.fetchall()
                    print "jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj" , entry_id , self.name,ad_client_id

                    if entry_id == []:
                        raise UserError(" No Records Found " )

                    count = 0
                    for record in entry_id:
                        count+= 1

                        Bill_BPartner_ID = (str(record[6]).split('.'))[0]
                        M_Product_ID = (str(record[9]).split('.'))[0]
                        partner = self.env['res.partner'].sudo().search([('c_bpartner_id', '=', Bill_BPartner_ID)], limit=1)
                        issuance = self.env['sample.issuance'].sudo().search([('partner_id', '=', partner.id)], limit=1)
                        product_id = self.env['product.product'].sudo().search([('m_product_id', '=', M_Product_ID)])
                        sample_product_line = self.env['sample.product.line'].sudo().search([('documentno', '=', record[0]),
                                                                                            ('product_id', '=', product_id.id)])

                        print "lllllllllllllllllllldddddddddddddddddddddddddddd" , sample_product_line , count

                        if sample_product_line:
                            raise UserError(record[0] + " is already present in the system")


                        if not partner:
                            raise UserError(record[5] + ' - ' + record[4] + \
                                " is not present in the system. Please add the Partner in the system from Customer Update Menu")

                        if not product_id:
                            raise UserError(record[11] + ' - ' + record[10] + \
                                " is not present in the system. Please add the product in the system from Product Update Menu ")

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
                                    'company_id': self.company_id.id ,
                                }

                            issuance_id2 = self.env['sample.issuance'].create(head_data)

                            qty = record[15]
                            if qty.isdigit():
                                qty1 = float(qty)
                            else:
                                qty1 = 1
                            quantity = float(record[12]) * float(qty1)

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

    name = fields.Char(string = "sample")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('sample.automation'))
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    sample_automation_line_one2many = fields.One2many('sample.automation.line','sample_automation_id')
    start_date = fields.Date(string='Start Date', required=True, default=datetime.today().replace(day=1))
    end_date = fields.Date(string="End Date", required=True, 
        default=datetime.now().replace(day = calendar.monthrange(datetime.now().year, datetime.now().month)[1]))
    sample_state = fields.Selection(STATE, string='Status', index=True, default='approved')
    user_id = fields.Many2one('res.users', string='User')
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
    ad_org_id = fields.Many2one('org.master', string='Organisation',  
        domain="[('company_id','=',company_id),('default','=',True)]" )
    filter_rep_bool = fields.Boolean('Filter Rep Generated' , default=False)
    new_year_bool = fields.Boolean('New Server' , default=False)
    dateacct = fields.Date(string='Accounting Date', required=True,default=datetime.today())
    c_elementvalue_id = fields.Many2one('wp.c.elementvalue', string='Cost Center')
    cnfromperiod = fields.Many2one('wp.c.period', string='CN From' ,  domain="[('company_id','=',company_id)]")
    cntoperiod = fields.Many2one('wp.c.period', string='CN To' ,  domain="[('company_id','=',company_id)]")
    user1_id = fields.Many2one('wp.c.elementvalue', string='Business Division' ,  
        domain="[('company_id','=',company_id),('c_element_id','in',('1000005','1000008'))]" )
    user2_id = fields.Many2one('wp.c.elementvalue', string='Functions' ,  
        domain="[('company_id','=',company_id),('c_element_id','in',('1000013','1000017'))]")
    dateordered2 = fields.Date(string='Exp Period From', required=True, default=datetime.today().replace(day=1))
    dateordered3 = fields.Date(string='Exp Period To', required=True, default=datetime.today().replace(day=1))
    config_id = fields.Many2one('external.db.configuration', string='Database', default=_get_config )
    approval_sent = fields.Boolean("Approval Sent" , default=False )

    _sql_constraints = [
            ('check','CHECK((start_date <= end_date))',"End date must be greater then start date")  
    ]

    @api.onchange('sample_state')
    def onchange_sample_state(self):
        if self.sample_state == 'approved' :
            self.approval_sent = True
        else:
            self.approval_sent = False


    @api.multi
    def select_all(self):
        for record in self.sample_automation_line_one2many:
            if record.selection == True:
                record.selection = False
            elif record.selection == False:
                record.selection = True

    @api.multi
    def approve_ticket_sampling_manager(self):
        self.sudo().send_user_mail()
        self.sudo().approve_all()


    @api.multi
    def approve_all(self):
        self.state = 'approved'
        self.approval_sent = True
        for res in self.sample_automation_line_one2many:
            if res.selection and res.name.state == 'done':
                res.approved_bool = True
                res.selection = False
                res.name.state = 'approved'
                res.state = 'approved'
                print "88888888888888888888888888888888888888 approve_all 88888888888888888888888888888888888888"


    @api.multi
    def action_sample_report(self):
        self.sample_automation_line_one2many.unlink()
        order_lines = []
        rep_name = ''
        hr_sample = self.env['sample.requisition'].sudo().search([
                            ('date_sample', '>=', self.start_date),
                            ('date_sample', '<=', self.end_date), 
                            ('state', '=', self.sample_state),
                            ('applicator_cost', '>', 0),
                            ('create_uid', '=', self.user_id.id)],order="create_uid, create_date asc")
       
       
        start_date = datetime.strptime(self.start_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
        end_date = datetime.strptime(self.end_date, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
        if self.start_date == self.end_date:
            rep_name = "Sample Details Report(%s)" % (start_date)
        else:
            rep_name = "Sample Details Report(%s-%s)"  % (start_date, end_date)
        self.name = rep_name

        if (not hr_sample):
            raise Warning(_('Record Not Found'))

        for hr_sample_id in hr_sample:
            order_lines.append((0, 0,  {
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
                }))

         
        self.sample_automation_line_one2many = order_lines
        self.state = 'done'


    @api.multi
    def sample_automation_webservice(self):
        conn_pg = None
        documentno = C_Tax_ID = documentno_log = crm_description = crm_description2 = ''
        line_body = body = payment_body = upper_body = lower_body = """ """
        commit_bool = False
        grandtotal = 0.0
        filter_id = self.id

        if not self.user1_id:
            raise ValidationError(_('No Business Division Selected '))

        if not self.user2_id:
            raise ValidationError(_('No Functions Selected '))


        for res in self.sample_automation_line_one2many:

            if self.sample_state == 'approved':
                if res.selection:
                    grandtotal += res.applicator_cost
                else:
                    raise ValidationError(_('No Records Selected or Some Records are not selected. \n \
                        Kindly delete the line entries from below which are not selected \
                        and then Click on "Push To ERP" Button'))

            elif self.sample_state == 'done':
                if res.approved_bool:
                    grandtotal += res.applicator_cost
                else:
                    raise ValidationError(_('No Records Selected or No approved sample detected'))

            else:
                raise ValidationError(_('Sample state Not in Generated or Approved'))


        employee_ids = self.env['hr.employee'].sudo().search([('user_id','=',self.user_id.id),
                                         '|',('active','=',False),('active','=',True)], limit=1)

        if employee_ids:
            if employee_ids.c_bpartner_id:
                c_bpartner_id = employee_ids.c_bpartner_id
            else:
                raise ValidationError(_("Employee ID not found. Kindly Contact IT Helpdesk"))


        user_ids = self.env['wp.erp.credentials'].sudo().search([("wp_user_id","=",self.env.uid),
            ("company_id","=",self.company_id.id)])

        if len(user_ids) < 1:
            raise ValidationError(_("User's ERP Credentials not found. Kindly Contact IT Helpdesk"))


        try:
            print "#-------------Select --TRY----------------------#"
            conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, 
                password=self.config_id.password, host= self.config_id.ip_address,port=self.config_id.port)
            pg_cursor = conn_pg.cursor()
            

            query = "select LCO_TaxPayerType_ID from adempiere.C_BPartner where  C_BPartner_ID = %s and \
            ad_client_id= %s  " % (c_bpartner_id,self.company_id.ad_client_id)

            pg_cursor.execute(query)
            record_query = pg_cursor.fetchall()

            if record_query and record_query[0][0] == None:
                print "------------------------------ commit_bool ----------------------" , record_query
                commit_bool = True
            else:
                raise ValidationError(_("Employee ID cannot be found for the current company. Kindly Contact IT Helpdesk"))

            # daymonth = datetime.today().strftime( "%Y-%m-%d 00:00:00")
            daymonth = self.dateacct + ' 00:00:00'
            dateordered2 = self.dateordered2 + ' 00:00:00'
            dateordered3 = self.dateordered3 + ' 00:00:00'
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

            C_Charge_ID=1000232
            PriceList = grandtotal

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
                    </_0:operation>"""  % ( self.ad_org_id.ad_org_id ,C_DocTypeTarget_ID, C_DocType_ID, 
                        daymonth, daymonth, c_bpartner_id, 
                        M_PriceList_ID,crm_description2, self.user1_id.c_elementvalue_id, 
                        self.user2_id.c_elementvalue_id, dateordered2, 
                        dateordered3,daynow)

            
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

            # idempiere_url="http://35.200.135.16/ADInterface/services/compositeInterface"
            idempiere_url="https://erpnew.wmvd.live/ADInterface/services/compositeInterface?wsdl"

            response = requests.post(idempiere_url,data=body,headers=headers)
            print response.content

            line_ids = self.sample_automation_line_one2many.sudo().search([('sample_automation_id','=', filter_id)])
            
            log = str(response.content)
            if log.find('DocumentNo') is not -1:
                documentno_log = log.split('column="DocumentNo" value="')[1].split('"></outputField>')[0]
                print "ssssssssssssssssssssssssss" , documentno_log , self.state
                self.state = 'posted'
                write_data = line_ids.sudo().write({'log': documentno_log})

            if log.find('IsRolledBack') is not -1:
            	# documentno_log = log.split('<Error>')[1].split('</Error>')[0]
            	raise ValidationError("Error Occured  %s" % (log))

            if log.find('UNMARSHAL_ERROR') is not -1:
                write_data = line_ids.sudo().write({'log': 'Manual Entry'})

            if log.find('IsRolledBack') is not -1:
                raise ValidationError("Error Occured  %s" % (log))

            if log.find('Invalid') is not -1:
                raise ValidationError("Error Occured %s" % (log))

            for line_rec in line_ids:
                line_rec.name.state = 'posted'
                line_rec.state = 'posted'

        except psycopg2.DatabaseError, e:
            if conn_pg:
                print '#-------------------Except----------------------#Error %s' % e
                conn_pg.rollback()

        finally:
            if conn_pg:
                conn_pg.close()
                print "#--------------Select --44444444--Finally----------------------#" , pg_cursor


    @api.multi
    def send_approval(self):
        amnt = total_samplecost = 0.0
        body = """ """
        subject = line_html = ""
        main_id = self.id

        sample_automation_line = self.sample_automation_line_one2many.search([('sample_automation_id', '=', self.id),
                                                                                ('selection', '=', True)])

        if  len(sample_automation_line) < 1:
            raise ValidationError(_('No Records Selected'))
            
        for l in sample_automation_line:
            if l.selection:
                start_date = datetime.strptime(str(((l.date_sample).split())[0]), 
                    tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

                line_html += """
                <tr>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                    <td style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">%s</td>
                </tr>
                """ % (start_date, l.sampling_partner, l.applicator, l.product_id.name, l.total_quantity, l.applicator_cost)

                total_samplecost += l.applicator_cost

        body = """
            <h3>Hi Sir,</h3> <br/>
            <h3>Following are the details as Below Listed. </h3>

            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Date</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Sampling Partner</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Applicator</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Product</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">KG</th>
                        <th style="border: 1px solid black; padding-left: 5px; padding-right: 5px;">Total Fare</th>
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
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Approve All</a>
                        </td>
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Selective Approve/Reject</a>
                        </td>

                    </tr>
                </tbody>
            </table>
            """ % (approve_url, report_check)

            composed_mail = self.env['mail.mail'].sudo().create({
                    'model': self._name,
                    'res_id': main_id,
                    'email_to': rec.approver.email,
                    'subject': subject,
                    'body_html': full_body,
                    'auto_delete': False,
                })

            composed_mail.sudo().send()


    @api.multi
    def send_user_mail(self):
        main_id = self.id
        subject = "[Approved] Bulk Sampling for %s "  % (self.user_id.name)
        email_from = self.env.user.email
        sample_users = self.env['sample.master.user'].search([("id","!=",0)])
        if len(sample_users) < 1:
            raise ValidationError("Sampling Approval Config doesnot have any User. Configure the Approvers and Users ")

        support_email = [x.user.email for x in sample_users]
        email_to = ",".join(support_email)
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_check = base_url + '/web#%s' % (url_encode({
                'model': self._name,
                'view_type': 'form',
                'id': self.id,
            }))
        full_body = """ <p>Hi Team,</p> <br/><br/> 
        <h2>BULK Sampling is approved</h2> 

        <br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Check Sampling</a>
                        </td>
                    </tr>
                </tbody>
            </table>""" % (report_check)

        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': self.id,
                'email_from': email_from,
                'email_to': email_to,
                'subject': subject,
                'body_html': full_body,
                'auto_delete': False,
                'priority_mail': True,
            })

        composed_mail.send()
        print "-------------------------- Mail Sent to %s" % (email_to)



    @api.multi
    def sample_automation_report(self):
        file = StringIO()
        self.ensure_one()
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Sample Report')
        fp = StringIO()
        row_index = 0

        main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; \
            borders: bottom thick, top thick, left thick, right thick')
        sp_style = xlwt.easyxf('font: bold on, height 350;')
        header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; \
            borders: bottom thin, top thin, left thin, right thin; \
            pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
        base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
        base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
            pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
        base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
            pattern: pattern fine_dots, fore_color white, back_color yellow;')

        worksheet.col(0).width = 2000
        worksheet.col(1).width = 4000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 12000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 12000
        worksheet.col(6).width = 6000
        worksheet.col(7).width = 16000
        for tt in range(8,22):
            worksheet.col(tt).width  = 6000

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
            'Cust Feedback',]
     
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


class sample_automation_line(models.Model):
    _name = 'sample.automation.line'
    _description = "Sample Automation Line"

    selection = fields.Boolean(string = "", nolabel="1")
    manager_id = fields.Char('Manager', size=50) 
    grade_id = fields.Char('Grade', size=50) 
    approval_status = fields.Char('Approval Status', size=50)
    sample_automation_id  = fields.Many2one('sample.automation')
    approved_bool = fields.Boolean("Approved", store=True)
    log = fields.Text("Log")
    name = fields.Many2one('sample.requisition',string="Sample No." )
    partner_id = fields.Many2one('res.partner',string="Distributor / Retailer" )
    date_sample = fields.Date(string="Sample Date" , 
        default=lambda self: fields.datetime.now(), track_visibility='always')
    user_id = fields.Many2one('res.users', string='User', 
        default=lambda self: self._uid, track_visibility='always')
    state = fields.Selection(STATE, string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')
    company_id = fields.Many2one('res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('sample.requisition.line'))
    ischeck = fields.Selection([('lead', 'Lead'), ('customer', 'Customer')], string='Is Lead/Customer')
    lead_id = fields.Many2one('crm.lead', string='Lead', track_visibility='onchange',
        domain="[('type', '=', 'lead')]")
    project_partner_id = fields.Many2one('res.partner',string="Customer" )
    sampling_partner = fields.Char('Sampling Partner')
    product_id = fields.Many2one('product.product', string='Product', 
        domain=[('sale_ok', '=', True)])
    uom_id = fields.Many2one('product.uom', string='UOM', related='product_id.uom_id')
    quantity = fields.Float(string='Qty(Kg)',  store=True)
    excess_taken = fields.Boolean("Excess Qty Taken", default=False)
    excess_quantity = fields.Float(string='Excess Qty(Kg)',  store=True)
    total_quantity = fields.Float(string='Total Qty(Kg)')
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
            if self.sample_automation_id.sample_state == 'approved':
                if self.selection==True:
                    self.selection = False
                else:
                    self.selection = True

            #     if self.state == 'approved':
            #         self.approved_bool = False
            #         self.selection = False
            #         self.state =  'done'
            #     else:
            #         self.approved_bool = True
            #         self.state =  'approved'
            # else:
            #     self.selection = True
        else:
            raise ValidationError(_("sample cannot be approved in 'Post' or 'Draft' State"))


class sample_masterConfig(models.Model):
    _name = "sample.master.config"
    _description= "Sample Master Config"


    @api.model
    def create(self, vals):
        result = super(sample_masterConfig, self).create(vals)
        a = self.search([("id","!=",0)])
        if len(a) >1:
            raise UserError(_('You can only create 1 Config Record'))
        return result

    name = fields.Char(string = "Config No.", default="Sampling Config")
    sample_approver_one2many = fields.One2many('sample.master.approver','config_id',string="Sample Master Approver")
    sample_user_one2many = fields.One2many('sample.master.user','config_user_id',string="Sample Master User")
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('sample.master.config'))


class sample_masterApprover(models.Model):
    _name = "sample.master.approver"
    _order= "sequence"
    _description= "Sample Master Approver"

    config_id = fields.Many2one('sample.master.config', string='Config', ondelete='cascade')
    approver = fields.Many2one('res.users', string='Approver', required=True)
    sequence = fields.Integer(string='Approver sequence')


class sample_masterUser(models.Model):
    _name = "sample.master.user"
    _description= "Sample Master User"

    config_user_id = fields.Many2one('sample.master.config', string='Config', ondelete='cascade')
    user = fields.Many2one('res.users', string='User', required=True)
    sequence = fields.Integer(string='User sequence')