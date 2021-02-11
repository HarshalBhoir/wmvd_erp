#!/usr/bin/env bash

from odoo.tools.translate import _
from odoo import api, fields, models, _ , registry, SUPERUSER_ID, tools
import logging
from odoo.exceptions import UserError, Warning, ValidationError
import dateutil.parser

import re
from odoo import http
from werkzeug import url_encode
import time
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from time import gmtime, strftime
import calendar

_logger = logging.getLogger(__name__)

ZONES = [('north', 'North'),
        ('east', 'East'),
        ('central', 'Central'),
        ('Gujarat', 'Gujarat'),
        ('west', 'West'),
        ('south', 'South'),
        ('export', 'Export')]

todaydate_str = "{:%d-%b-%y}".format(datetime.now())

class cir_extension(models.Model):
    _name = 'cir.extension'
    _description = "CIR Extension"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    @api.multi
    def _compute_can_tse_edit(self):
        self.can_tse_edit = self.env.user.has_group('sales_meet.group_cir_module_tse')
        print "11111111111111111111111111111 _compute_can_tse_edit", self.can_tse_edit

    @api.multi
    def _compute_can_lab_edit(self):
        self.can_lab_edit = self.env.user.has_group('sales_meet.group_cir_module_lab')
        print "22222222222222222222222222222 _compute_can_lab_edit", self.can_lab_edit

    @api.multi
    def _compute_can_zsm_edit(self):
        self.can_zsm_edit = self.env.user.has_group('sales_meet.group_cir_module_zsm')
        print "33333333333333333333333333333 _compute_can_zsm_edit", self.can_zsm_edit

    @api.multi
    def _compute_can_ho_edit(self):
        self.can_ho_edit = self.env.user.has_group('sales_meet.group_sales_support_user')
        print "4444444444444444444444444444444444 _compute_can_ho_edit", self.can_ho_edit

    @api.multi
    def _compute_can_product_head_edit(self):
        self.can_product_head_edit = self.env.user.has_group('sales_meet.group_cir_module_product_head')
        print "55555555555555555555555555555 _compute_can_product_head_edit", self.can_product_head_edit

   
    name = fields.Char(string = "Complaint No.", copy=False)
    company_id = fields.Many2one('res.company', 'Company', 
                    default=lambda self: self.env['res.company']._company_default_get('cir.extension'))
    product_id = fields.Many2many('product.product', string='Product', domain=[('sale_ok', '=', True)])
    uom_id = fields.Many2one('product.uom', string='UOM')
    batch_no = fields.Char(string = "Batch No.")
    complaint_extent = fields.Char(string = "Extent of Complaint (Quantity)")

    partner_id = fields.Many2one('res.partner',string="Customer" )
    partner_address = fields.Char(string = "Address")
    state_id = fields.Many2one('res.country.state', string='State')
    partner_group_id = fields.Many2one("res.partner.group", string="Customer Group")
    complaint_id = fields.Many2one('cir.complaint.master',string="Complaint" )
    lead_id = fields.Many2one("crm.lead", string="Retailer/ Project / Site")
    distributer_complaint = fields.Boolean(string = "Distributer Complaint Bool", copy=False)
    salesuser_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self._uid, track_visibility='always')
    complaint_received_date = fields.Date(string="Complaint Received Date", copy=False )
    salesperson_remark = fields.Char(string = "Sales Remark", copy=False)
    salesuser_cir_attachments = fields.Many2many('ir.attachment', 'salesuser_cir_attachments_rel' , copy=False, 
        attachment=True , string='User Attachments')
    salesperson_bool = fields.Boolean(string = "Salesperson Bool", copy=False)

    investigator_id = fields.Many2one('res.users', string='Investigator')
    investigation_date = fields.Date(string="TSE Date", store=True , copy=False)
    tse_remark = fields.Char(string = "TSE Remark", copy=False)
    tse_cir_attachments = fields.Many2many('ir.attachment', 'tse_cir_attachments_rel', copy=False, attachment=True,
        string='TSE Attachments')
    tse_bool = fields.Boolean(string = "TSE Bool", copy=False)

    lab_remark = fields.Char(string = "LAB Remark", copy=False)
    lab_date = fields.Date(string="LAB Date", copy=False )
    cir_attachments = fields.Many2many('ir.attachment', 'cir_attachments_rel', copy=False, attachment=True , string='LAB Attachments')
    lab_bool = fields.Boolean(string = "LAB Bool", copy=False)

    manager_id = fields.Many2one('res.users', string='Manager')

    zsm_id = fields.Many2one('res.users', string='ZSM')
    zsm_remark = fields.Char(string = "ZSM Remark", copy=False)
    zsm_date = fields.Date(string="ZSM Date", copy=False )
    zsm_bool = fields.Boolean(string = "ZSM Bool", copy=False)
    
    product_head_id = fields.Many2one('res.users', string='Product Head')
    product_head_remark = fields.Char(string = "Product Head Remark", copy=False)
    product_head_date = fields.Date(string="Product Head Date" , copy=False)
    product_head_bool = fields.Boolean(string = "Product Head Bool", copy=False)

    applicator =  fields.Char(string = "Applicator")
    applicator_date = fields.Date(string = "Date of Applicator")

    ho_remark = fields.Char(string = "HO Remark", copy=False)
    ho_date = fields.Date(string="HO Date" , copy=False)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Submitted'),
        ('tse_approved', 'TSE Approved'),
        ('lab_approved', 'LAB Approved'),
        ('zsm_approved', 'ZSM Approved'),
        ('product_head_approved', 'Product Head Approved'),
        ('closed', 'Closed'),
        ], string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')

    zone = fields.Selection(ZONES, string='Zone', copy=False, index=True, store=True)

    conclusion = fields.Selection([
        ('Credit Note', 'Credit Note'),
        ('Replacement of Bags', 'Replacement of Bags'),
        ('Others', 'Others'),
        ], string='Conclusion', copy=False, index=True, store=True)

    credit_note_amount = fields.Float(string = "Credit Note Amount", copy=False)
    other_conclusion = fields.Char(string = "Other Conclusion", copy=False)
    replacement_bags = fields.Integer(string = "Bags No.", copy=False)
    source_id = fields.Many2one('org.master',string="Source of Supply", 
        domain="[('company_id','=',company_id),('cir_bool','=',True)]")
    invoice_no = fields.Char(string = "Invoice No")
    invoice_value = fields.Float(string = "Invoice Value")
    quantity_supplied = fields.Float(string = "Quantity Supplied")
    invoice_date = fields.Date(string = "Invoice Date")
    material_status = fields.Selection([('YES', 'YES'), ('NO', 'NO')], string = "Status of Material", index=True, store=True)
    courier_details = fields.Char(string = "Courier Service", copy=False)
    pod_details = fields.Char(string = "POD Details", copy=False)    

    can_tse_edit = fields.Boolean(compute='_compute_can_tse_edit')
    can_lab_edit = fields.Boolean(compute='_compute_can_lab_edit')
    can_zsm_edit = fields.Boolean(compute='_compute_can_zsm_edit')
    can_ho_edit = fields.Boolean(compute='_compute_can_ho_edit')
    can_product_head_edit = fields.Boolean(compute='_compute_can_product_head_edit')


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.state_id = self.partner_id.state_id.id
            self.partner_group_id = self.partner_id.partner_group_id.id
            self.partner_address = ((self.partner_id.street + ', ') if self.partner_id.street else ' ' )  \
                                    + ((self.partner_id.street2+ ', ') if self.partner_id.street2 else ' ' )  \
                                    + ((self.partner_id.city + ', ') if self.partner_id.city else ' ' )

            escalation = self.env['cir.escalation.line'].search([('company_id','=',self.company_id.id),
                ('state_id','=',self.partner_id.state_id.id)])
            if escalation:
                for esc in escalation:
                    if esc.state_id.id ==  self.partner_id.state_id.id:
                        self.zsm_id = esc.zsm_user_id.id
                        self.product_head_id = esc.report_user_id.id
                        self.investigator_id = esc.tse_user_id.id
                        self.manager_id = esc.manager_id.id
                        self.zone = esc.zone


    @api.onchange('state_id')
    def onchange_state_id(self):
        if self.state_id:
            escalation = self.env['cir.escalation.line'].search([('company_id','=',self.company_id.id),
                ('state_id','=',self.state_id.id)])
            if escalation:
                for esc in escalation:
                    self.zsm_id = esc.zsm_user_id.id
                    self.product_head_id = esc.report_user_id.id
                    self.investigator_id = esc.tse_user_id.id
                    self.manager_id = esc.manager_id.id
                    self.zone = esc.zone


    @api.onchange('zone')
    def onchange_zone(self):
        if self.zone:
            escalation = self.env['cir.escalation.line'].search([('company_id','=',self.company_id.id),
                ('state_id','=',self.state_id.id),('zone','=',self.zone)])
            if escalation:
                for esc in escalation:
                    self.zsm_id = esc.zsm_user_id.id
                    self.product_head_id = esc.report_user_id.id
                    self.investigator_id = esc.tse_user_id.id
                    self.manager_id = esc.manager_id.id


    @api.onchange('complaint_id')
    def onchange_complaint_id(self):
        if self.complaint_id :
            if self.complaint_id.distributer_complaint:
                self.distributer_complaint = True

            if not self.complaint_id.opt_out:
                self.material_status = 'YES'
            else:
                self.material_status = 'NO'



    @api.multi
    def close_cir(self):
        self.state = 'closed'

    @api.multi
    def update_data(self):
        if not self.name:
            self.name = self.env['ir.sequence'].next_by_code('cir.extension')
        self.send_generic_mail()

    def report_check(self,main_id):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_check = base_url + '/web#%s' % (url_encode({
                'model': self._name,
                'view_type': 'form',
                'id': main_id,
            }))
        rep_check = """
            <br/>
            <td>
                <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                    font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                    text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                    text-align: center; vertical-align: middle; cursor: pointer; 
                    white-space: nowrap; background-image: none; background-color: #337ab7; 
                    border: 1px solid #337ab7; margin-right: 10px;">Check Complaint</a>
            </td> 
            """  % ( report_check)
        return rep_check


    @api.multi
    def send_generic_mail(self):
        email_from = ''
        email_cc = []
        email_to = []
        todaydate = datetime.now().strftime( "%Y-%m-%d")

        matrix= self.env['cir.escalation.matrix'].sudo().search([('company_id','=',self.company_id.id)])
        lab_mail = (matrix.lab_mail).encode('ascii', 'ignore')
        complaints_mail = (matrix.complaint_mail_id).encode('ascii', 'ignore')
        salesuser_mail = (self.salesuser_id.email).encode('ascii', 'ignore')
        investigator_mail = (self.investigator_id.email).encode('ascii', 'ignore')
        zsm_mail = (self.zsm_id.email).encode('ascii', 'ignore')
        product_head_mail = (self.product_head_id.email).encode('ascii', 'ignore')
        manager_mail = (self.manager_id.email).encode('ascii', 'ignore')


        if self.env.user.has_group('sales_meet.group_cir_module_user') or self.state == 'draft':
            if self.salesperson_bool== False:
                print "1111111111111111111111111111111111111"
                
                if self.complaint_id.opt_out:
                    email_subcc = [complaints_mail, investigator_mail ]
                else:
                    email_subcc = [complaints_mail, investigator_mail , lab_mail]
                
                email_to = ",".join(email_subcc)
                email_from = salesuser_mail
                email_mgr = [zsm_mail, product_head_mail, manager_mail]
                email_cc = ",".join(email_mgr)

                self.state = 'done'
                self.salesperson_bool = True

            else:
                raise UserError(_('You (USER)have already Submitted the Form'))


        elif self.env.user.has_group('sales_meet.group_cir_module_tse') :
            if self.tse_bool== False:
                print "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                email_from = investigator_mail
                email_subcc = [complaints_mail, product_head_mail]
                email_to = ",".join(email_subcc)

                if self.complaint_id.opt_out:
                    email_mgr = [zsm_mail, manager_mail]
                else:
                    email_mgr = [zsm_mail, lab_mail , manager_mail]
                    
                email_cc = ",".join(email_mgr)
                self.state = 'tse_approved'
                self.tse_bool = True
                self.investigation_date = todaydate
                # self.sudo().write({'investigation_date':todaydate,'state': 'tse_approved','tse_bool':True,})

                print "ssssss" , self.investigation_date , todaydate , type(todaydate) , type(self.applicator_date)

                if not self.tse_remark :
                    raise ValidationError(" TSE Remark is not filled. Kindly Fill the field and submit the record" )

            else:
                raise UserError(_('You (TSE) have already Submitted the Form'))


        elif self.env.user.has_group('sales_meet.group_cir_module_lab'):
            if self.lab_bool== False:
                print "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb group_cir_module_lab"
                email_from = lab_mail
                email_subcc = [complaints_mail, product_head_mail]
                email_to = ",".join(email_subcc)

                email_mgr = [zsm_mail, manager_mail, investigator_mail, salesuser_mail]
                email_cc = ",".join(email_mgr)

                self.state = 'lab_approved'
                self.lab_bool = True
                self.lab_date = todaydate

                if not self.lab_remark :
                    raise ValidationError(" LAB Remark is not filled. Kindly Fill the field and submit the record" )

            else:
                raise UserError(_('You (LAB) have already Submitted the Form'))


        elif self.env.user.has_group('sales_meet.group_cir_module_zsm'):
            if self.zsm_bool== False:
                print "ccccccccccccccccccccccccccccccccccccccccc"
                email_from = zsm_mail
                email_subcc = [complaints_mail, salesuser_mail]
                email_to = ",".join(email_subcc)

                if self.complaint_id.opt_out:
                    email_mgr = [product_head_mail , manager_mail, investigator_mail]
                else:
                    email_mgr = [product_head_mail, manager_mail, investigator_mail, lab_mail]

                email_cc = ",".join(email_mgr)
                self.state = 'zsm_approved'
                self.zsm_bool = True
                self.zsm_date = todaydate

                if not self.zsm_remark :
                    raise ValidationError(" ZSM Remark is not filled. Kindly Fill the field and submit the record" )

            else:
                raise UserError(_('You (ZSM) have already Submitted the Form'))


        elif self.env.user.has_group('sales_meet.group_cir_module_product_head'):
            if self.product_head_bool== False:
                print "ddddddddddddddddddddddddddddddddddddddddd"
                email_from = product_head_mail

                email_subcc = [complaints_mail, salesuser_mail]
                email_to = ",".join(email_subcc)

                if self.complaint_id.opt_out:
                    email_mgr = [zsm_mail, manager_mail, investigator_mail]
                else:
                    email_mgr = [zsm_mail, manager_mail, investigator_mail, lab_mail]

                email_cc = ",".join(email_mgr)
                self.state = 'product_head_approved'
                self.product_head_bool = True
                self.product_head_date = todaydate

                if not self.product_head_remark :
                    raise ValidationError(" Product Head Remark is not filled. Kindly Fill the field and submit the record" )

                if not self.conclusion :
                    raise ValidationError(" Kindly Provide Conclusion for this request and submit the record" )

                self.close_cir()

            else:
                raise UserError(_('You (Product Head) have already Submitted the Form'))

        self.sudo().send_user_mail(email_from,email_to,email_cc)


    @api.multi
    def send_user_mail(self,email_from=False,email_to=False,email_cc=False):
        main_id = self.id
        if self.state == 'closed':
            subject = "[Closed] Complaint of %s by %s - ( %s ) " % (self.complaint_id.name ,self.partner_id.name, todaydate_str)
            if self.conclusion == "Credit Note":
                conclusion_option = 'Rs. ' + str(self.credit_note_amount)
            elif self.conclusion == "Replacement of Bags":
                conclusion_option = str(self.replacement_bags) + ' Bags'
            elif self.conclusion == "Others":
                conclusion_option = self.other_conclusion
            greeting_msg = """ <h3>Dear Team,</h3><br/>
            <h3>The Complaint of %s by %s is Closed.</h3>
            <h3>Conclusion : \n 
            %s - %s </h3><br/>""" % (self.complaint_id.name ,self.partner_id.name, self.conclusion, conclusion_option )

        else:
            subject = "Action required for pending complaint - ( %s )"  % (todaydate_str)
            greeting_msg = """ <h3>Dear Team,</h3><br/>
            <h3>A gentle reminder, please look into the below mention complaint and take necessary action to close at the earliest. 
                Details of complaint is as below.</h3><br/>"""
       
        start_date = datetime.strptime(str(((self.complaint_received_date).split())[0]), 
            tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

        body = """
            <table>
                <tr>  <th style=" text-align: left;padding: 8px;">Complaint Received Date</th>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Complaint No</th>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Customer Name</th>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Nature of Complaint</th>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Complaint Status</th>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">SalesPerson Remark</th>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">TSE Remark</th>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">LAB Remark</th>  <td> : %s</td></tr>
                <tr>  <th style=" text-align: left;padding: 8px;">Product Head Remark</th>  <td> : %s</td></tr>
            </table>
            <br/>
            <br/>

        """ % (start_date, self.name,self.partner_id.name, self.complaint_id.name, self.state,
               self.salesperson_remark or '', self.tse_remark or '', self.lab_remark or '', self.product_head_remark or ''   )

        full_body = greeting_msg + body + self.report_check(main_id)
        self.send_composed_mail(subject, full_body, email_from, email_to, email_cc, main_id)


    @api.model
    @api.multi
    def send_cir_schedular_mail(self):
        email_from = ''
        email_cc = []
        email_to = []

        matrix= self.env['cir.escalation.matrix'].sudo().search([('company_id','=',self.env.user.company_id.id)])
        lab_mail = (matrix.lab_mail).encode('ascii', 'ignore')
        complaints_mail = (matrix.complaint_mail_id).encode('ascii', 'ignore')

        for res in self.search([('state','not in',('draft','closed'))]):
            salesuser_mail = (res.salesuser_id.email).encode('ascii', 'ignore')
            investigator_mail = (res.investigator_id.email).encode('ascii', 'ignore')
            zsm_mail = (res.zsm_id.email).encode('ascii', 'ignore')
            product_head_mail = (res.product_head_id.email).encode('ascii', 'ignore')
            manager_mail = (res.manager_id.email).encode('ascii', 'ignore')

            email_from = salesuser_mail
            email_subcc = [complaints_mail, investigator_mail]
            email_to = ",".join(email_subcc)

            if res.complaint_id.opt_out:
                email_mgr = [zsm_mail, product_head_mail, manager_mail]
            else:
                email_mgr = [zsm_mail, product_head_mail, manager_mail, lab_mail] 
            
            email_cc = ",".join(email_mgr)

            main_id = res.id
            subject = "[Reminder] Action required for pending complaint - ( %s )"  % (todaydate_str)
            start_date = datetime.strptime(str(((res.complaint_received_date).split())[0]), 
                tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%y')

            body = """
                <h3>Dear Team,</h3>
                <br/>

                <h3>A gentle reminder, please look into the below mention complaint and take necessary action to close at the earliest. 
                    Details of complaint is as below.</h3>

                <br/>
                <table>
                    <tr>  <th style=" text-align: left;padding: 8px;">Complaint Received Date</th>  <td> : %s</td></tr>
                    <tr>  <th style=" text-align: left;padding: 8px;">Complaint No</th>  <td> : %s</td></tr>
                    <tr>  <th style=" text-align: left;padding: 8px;">Customer Name</th>  <td> : %s</td></tr>
                    <tr>  <th style=" text-align: left;padding: 8px;">Nature of Complaint</th>  <td> : %s</td></tr>
                    <tr>  <th style=" text-align: left;padding: 8px;">Complaint Status</th>  <td> : %s</td></tr>
                    <tr>  <th style=" text-align: left;padding: 8px;">SalesPerson Remark</th>  <td> : %s</td></tr>
                    <tr>  <th style=" text-align: left;padding: 8px;">TSE Remark</th>  <td> : %s</td></tr>
                    <tr>  <th style=" text-align: left;padding: 8px;">LAB Remark</th>  <td> : %s</td></tr>
                    <tr>  <th style=" text-align: left;padding: 8px;">Product Head Remark</th>  <td> : %s</td></tr>
                </table>
            <br/><br/>

        """ % (start_date, res.name,res.partner_id.name, res.complaint_id.name, res.state,
               res.salesperson_remark or '', res.tse_remark or '', res.lab_remark or '', res.product_head_remark or ''   )

            full_body = body + self.report_check(main_id)
            res.send_composed_mail(subject, full_body, email_from, email_to, email_cc, main_id)


    @api.multi
    def send_composed_mail(self,subject=False, full_body=False, email_from=False, email_to=False, email_cc=False, main_id=False):
        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': main_id,
                'email_from': email_from,
                'email_to': email_to,
                'email_cc' : email_cc,
                'subject': subject,
                'body_html': full_body,
            })

        composed_mail.send()
        print "--------------- email_to" , email_to, "---email_from ",email_from, "---email_cc " , email_cc ,"---main_id " , main_id



class cir_complaint_master(models.Model):
    _name = "cir.complaint.master"
    _description = 'Complaint Master'

    name = fields.Char(string = "Complaint")
    opt_out = fields.Boolean(string = "Mail Opt Out")
    distributer_complaint = fields.Boolean(string = "Distributer Complaint")


class cir_escalation_matrix(models.Model):
    _name = "cir.escalation.matrix"
    _description = 'Escalation Matrix'

    @api.model
    def create(self, vals):
        result = super(cir_escalation_matrix, self).create(vals)

        a = self.search([('company_id','=',result['company_id'].id)]) #("id","!=",0)
        if len(a) >1:
            raise UserError(_('You can only create 1 Config Record for the Company'))

        return result

    name = fields.Char(string = "Config No.", default="Escalation Config")
    lab_mail = fields.Char(string = "Lab Mail", required=True)
    complaint_mail_id = fields.Char(string = "Complaint Mail", required=True)
    salesupport_mail_id = fields.Char(string = "Support Mail", required=True)
    toll_free_user = fields.Char(string = "Toll Free")
    confirmation_mail = fields.Char(string = "Confirmation Mail")
    it_helpdesk_mail = fields.Char(string = "IT Helpdesk")
    erp_mail = fields.Char(string = "ERP Helpdesk")
    support_user_ids = fields.Many2many('res.users', string='Sales Support')
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('cir.escalation.matrix'))
    sample_approver_one2many = fields.One2many('cir.escalation.line','config_id',string="Escalation Line")

class cir_escalation_line(models.Model):
    _name = "cir.escalation.line"
    _description = 'Escalation Matrix Line'
    _order= "sequence"

    config_id = fields.Many2one('cir.escalation.matrix', string='Config', ondelete='cascade')
    tse_user_id = fields.Many2one('res.users', string='TSE', required=True)
    manager_id = fields.Many2one('res.users', string='Manager', required=True)
    report_user_id = fields.Many2one('res.users', string='Report', required=True)
    zsm_user_id = fields.Many2one('res.users', string='ZSM', required=True)
    support_user_ids = fields.Many2many('res.users', string='Sales Support')
    state_id = fields.Many2one('res.country.state', string='State', required=True)
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('cir.escalation.line'))
    sequence = fields.Integer(string='Approver sequence')
    zone = fields.Selection(ZONES, string='Zone', copy=False, index=True, store=True)