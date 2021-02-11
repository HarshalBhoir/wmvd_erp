# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2014-Today BrowseInfo (<http://www.browseinfo.in>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
from odoo.tools.translate import _
from datetime import datetime, timedelta, date
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
import odoo.addons.decimal_precision as dp



class crm_extension(models.Model):
    _inherit = "crm.lead"
    _rec_name = 'display_name'

    # bp_code = fields.Char('Partner Code')
    partner_group_id = fields.Many2one("res.partner.group", string="Group")
    pan_no = fields.Char('Pan No')
    tin_no = fields.Char('Tin No')
    vat_no = fields.Char('Vat No')
    cst_no = fields.Char('Cst No')
    gst_no = fields.Char('Gst No')
    credit_limit = fields.Float(string='Credit limit')
    mail_date = fields.Date('Mail Date')
    action_date = fields.Date('Action Date')
    response_time =fields.Char('Response Time')
    enquiry_type_id = fields.Many2one("enquiry.type", string="Enquiry Type")
    enquiry_date = fields.Date('Enquiry Date')
    enquiry_month = fields.Char('Enquiry Month' , store=True, track_visibility='onchange')
    zone = fields.Selection([
        ('north', 'North'),
        ('east', 'East'),
        ('central', 'Central'),
        ('west', 'West'),
        ('south', 'South'),
        ('export', 'Export')
        ], string='Zone', copy=False, index=True, store=True)

    product_id = fields.Many2many("product.product", string="Product Offered")
    categ_id = fields.Many2one('product.category', string='Product Category')
    escalated_ids = fields.Many2many('res.users', string='Escalated To')
    activity_log_one2many = fields.One2many('crm.activity.log', 'lead_id', string='Activity Logs')
    sales_user_id =  fields.Many2one("res.users", string="Forwarded To")
    closed_month =  fields.Char('Order/Closed Month' , store=True, track_visibility='onchange')
    status = fields.Selection([
            ('first_order','First-Order'),
            ('re_order','Re-Order'),
            ('incorrect','Incorrect'),
            ('lost','Lost'),
            ('open','Open'),
            ('regret','Regret'),
        ], string='Status', copy=False, index=True, store=True)
    attach_doc_count = fields.Integer(string="Number of documents attached", compute='count_docs')

    isproject = fields.Boolean('Project')
    rera_no = fields.Char('RERA')
    project_source = fields.Selection([
            ('ho','HO'),
            ('self_visit','Self-Visit'),
        ], string='Project Source', copy=False, index=True, store=True)


    site_details = fields.Text('Site Details')
    site_status = fields.Char('Site Status')
    ownership_type = fields.Selection([
            ('government','Government'),
            ('private','Private'),('charitable','Charitable'),
        ], string='Ownership Type', copy=False, index=True, store=True)

    project_type = fields.Selection([
            ('commercial','Commercial'),
            ('residential','Residential'),('industrial','Industrial'),('government','Government'),
        ], string='Project Type', copy=False, index=True, store=True)

    site_street = fields.Char('Street')
    site_street2 = fields.Char('Street2')
    site_zip = fields.Char('Zip', change_default=True)
    site_city = fields.Char('City')
    site_state_id = fields.Many2one("res.country.state", string='State')
    site_country_id = fields.Many2one('res.country', string='Country')

    handledby_ids = fields.Many2many('res.users','project2_lead_details_report_res_user_rel', string='Handled By')
    assistedby_ids = fields.Many2many('res.users','project_lead_details_report_res_user_rel', string='Assisted By')
    activity_log_list_one2many = fields.One2many('crm.lead.log.list', 'list_lead_id', string='Activity Logs')
    project_contact_one2many = fields.One2many('project.contacts', 'project_lead_id', string='Project Contacts')
    business_generated = fields.Float('Business Generated')
    display_name = fields.Char(string="Name", compute="_name_get" , store=True)

    # _sql_constraints = [
    #         ('mobile_uniq', 'unique(mobile)', 'Number already present in other lead'),
    #         ('phone_uniq', 'unique(phone)', 'Number already present in other lead'),
    #     ]


    

    @api.multi
    @api.depends('name','city')
    def _name_get(self):
        for ai in self:
            if not (ai.display_name and ai.name):
                name = str(ai.name) + ' - ' + str(ai.city)
                ai.display_name = name
            if not ai.display_name and ai.name:
                name = str(ai.name)
                ai.display_name = name


    @api.model
    def create(self, vals):
        result = super(crm_extension, self).create(vals)

        print "111111111111 Lead Create 1111111111111" , result.type
        if result.phone and result.type == 'lead':
            phone = self.env['crm.lead'].search(['|',('phone','=',result.phone),('mobile','=',result.phone)])
            if len(phone) > 1 :
                phname = phone[1].name 
                raise UserError("Phone Number already present in the lead ' " + phname + " '")

            if len(result.phone) != 10:
                raise UserError(" Kindly enter 10 digit phone number")

            lead_id = self.env['project.contacts'].search([('number','=',result.phone)])
            if len(lead_id) > 0 :
                name = lead_id[0].project_lead_id.name 
                raise UserError("Phone Number already present in the lead's contact list ' " + name + " '")

        if result.mobile  and result.type == 'lead' :

            mobile = self.env['crm.lead'].search(['|',('phone','=',result.mobile),('mobile','=',result.mobile)])
            if len(mobile) > 1 :
                mbname = mobile[1].name 
                raise UserError("Mobile Number already present in the lead ' " + mbname + " '. Kindly Use the Existing Lead")

            if len(result.mobile) != 10:
                raise UserError(" Kindly enter 10 digit phone number")

            molead_id = self.env['project.contacts'].search([('number','=',result.mobile)])
            if len(molead_id) > 1 :
                name = molead_id[1].project_lead_id.name 
                raise UserError("Mobile Number already present in the lead's contact list ' " + name + " '")


        return result
    
    @api.multi
    def write(self, vals):
        result = super(crm_extension, self).write(vals)


        print "111111111111 write 111111111111" , self.type

        if self.phone and self.type == 'lead':
            

            phone = self.env['crm.lead'].search(['|',('phone','=',self.phone),('mobile','=',self.phone)])
            if len(phone) > 1 :
                phname = phone[1].name 
                raise UserError("Phone Number already present in the lead ' " + phname + " '")

            if len(self.phone) != 10:
                raise UserError(" Kindly enter 10 digit phone number")

            lead_id = self.env['project.contacts'].search([('number','=',self.phone)])
            if len(lead_id) > 0 :
                name = lead_id[0].project_lead_id.name 
                raise UserError("Phone Number already present in the lead's contact list ' " + name + " '")

        if self.mobile  and self.type == 'lead':


            mobile = self.env['crm.lead'].search(['|',('phone','=',self.mobile),('mobile','=',self.mobile)])
            if len(mobile) > 1 :
                mbname = mobile[1].name 
                raise UserError("Mobile Number already present in the lead ' " + mbname + " '")

            if len(self.mobile) != 10:
                raise UserError(" Kindly enter 10 digit phone number")

            molead_id = self.env['project.contacts'].search([('number','=',self.mobile)])
            if len(molead_id) > 0 :
                name = molead_id[0].project_lead_id.name 
                raise UserError("Mobile Number already present in the lead's contact list ' " + name + " '")

        return result


    @api.onchange('name')
    def onchange_name(self):
        if self.name :
            self.partner_name = self.name


    @api.onchange('phone','mobile')
    def onchange_number(self):
        if self.phone :
            if len(self.phone)  != 10:
                raise UserError(" Kindly enter 10 digit contact number")
        if  self.mobile:
            if len(self.mobile) != 10:
                raise UserError(" Kindly enter 10 digit contact number")


    @api.multi
    @api.onchange('isproject')
    def onchange_isproject(self):
        if self.isproject :
            project = self.env['res.partner.group'].search([("name","ilike",'%project%')])
            if len(project) > 0:
                self.partner_group_id = project[0].id


    @api.onchange('partner_group_id')
    def onchange_partner_group_id(self):
        if self.partner_group_id :
            project = self.env['res.partner.group'].search([("name","ilike",'%project%')])
            
            if self.partner_group_id.id in [ x.id for x in project] :
                self.isproject = True
            else:
                self.isproject = False



    @api.multi
    @api.onchange('action_date')
    def count_days(self):
        if self.action_date and self.mail_date :
            start_date = datetime.strptime(self.mail_date, "%Y-%m-%d")
            end_date = datetime.strptime(self.action_date, "%Y-%m-%d")
            self.response_time = abs((end_date-start_date).days)


    @api.onchange('enquiry_date','closed_month')
    def onchange_month(self):
        if self.enquiry_date:
            enquiry_date = self.enquiry_date
            daymonthfrom = datetime.strptime(enquiry_date, "%Y-%m-%d")
            monthfrom = daymonthfrom.strftime("%b")
            yearfrom = int(daymonthfrom.strftime("%y"))
            self.enquiry_month =  monthfrom + '-' + str(yearfrom)
        if self.date_closed:
            date_closed = self.date_closed
            daymonthfrom2 = datetime.strptime(date_closed, "%Y-%m-%d")
            monthfrom2 = daymonthfrom2.strftime("%b")
            yearfrom2 = int(daymonthfrom2.strftime("%y"))
            self.closed_month =  monthfrom2 + '-' + str(yearfrom2)




    @api.multi
    def send_mail(self):
        user_id_emails = ''
        if self.sales_user_id:
            user_id = [user.login.encode("utf-8") for user in self.escalated_ids]            

            if self.user_id.login:
                user_id.append(str(self.user_id.login))

            user_id_emails = ",".join([str(x) for x in user_id])


            template_id = self.env['ir.model.data'].get_object_reference('sales_meet','lead_assign_action')[1]
            email_template_obj = self.env['mail.template'].browse(template_id)
            if template_id:
                values = email_template_obj.generate_email(self.id, fields=None)
                values['email_from'] = self.user_id.login
                values['email_to'] = self.sales_user_id.login
                values['email_cc'] = user_id_emails
                values['res_id'] = False
                mail_mail_obj = self.env['mail.mail']
                msg_id = mail_mail_obj.sudo().create(values)
                self.mail_date = datetime.now()
                if msg_id:
                    print "1111111111111111 send_mail 1111111111111111"
                    msg_id.sudo().send()

        else:
            raise UserError(" 'Forward To' field is blank. Kindly update")

        return True

    @api.multi
    def count_docs(self):
        meeting_ids = self.env['calendar.event'].search(['|',("lead_id","=",self.id),("opportunity_id","=",self.id)])
        if len(meeting_ids):
            self.attach_doc_count = len(meeting_ids) or 0


    @api.multi
    def get_attached_docs(self):
        meeting_ids = self.env['calendar.event'].search(['|',("lead_id","=",self.id),("opportunity_id","=",self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('sales_meet.action_calendar_event_crm')
        list_view_id = imd.xmlid_to_res_id('sales_meet.view_calendar_event_tree_extension')
        form_view_id = imd.xmlid_to_res_id('sales_meet.view_calendar_event_form_extension')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'],
                [False, 'graph'], [False, 'kanban'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(meeting_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % meeting_ids.ids
        elif len(meeting_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = meeting_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


    @api.multi
    def create_event(self):
        if self.sales_user_id or self.handledby_ids:
            new_stage = self.env['crm.stage'].search([('name', '=','New')])
            calendar_event_vals = {
                    'name': self.title_action,
                    'start_datetime': self.date_action,
                    'stop_datetime': self.date_action,
                    'start': self.date_action,
                    'stop': self.date_action,
                    'allday': False,
                    'show_as': 'busy',
                    'partner_ids': [(6, 0, [])] or '',
                    'partner_id': self.partner_id.id if self.partner_id  else '',
                    'stage_id': new_stage.id or '',
                    'categ_id': self.next_activity_id.id,
                    'user_id': self.sales_user_id.id if self.sales_user_id else [x[0].id for x in self.handledby_ids][0],
                    'ischeck': 'opportunity' if self.type == 'opportunity' else 'lead',
                    'lead_id': self.id if self.type == 'lead' else '',
                    'opportunity_id': self.id if self.type == 'opportunity' else '',
                    'next_flag':True,
                    'checkin_lattitude':0.0,
                    'checkin_longitude':0.0,
                    'ho_lead':True,
                }

            # # if self.name == self.search([('id','in',inv_res)])
            # prod_package = self.env['product.packaging'].search([('name','=',self.title_action)])

            self.env['calendar.event'].sudo().create(calendar_event_vals)

            self.next_activity_id = self.date_action = self.title_action = ''

        else:
            raise UserError(" 'Forward To' field is blank. Kindly update")


    @api.multi
    def create_meeting(self):

        # employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)]).id
        self.ensure_one()
        
        ctx = self._context.copy()
        meetings_ids = self.env['calendar.event'].search([('lead_id', '=', self.id)])
        if meetings_ids:
            result = self.get_attached_docs()
        if not meetings_ids:
            partner_ids = self.env.user.partner_id.ids
            if self.partner_id:
                partner_ids.append(self.partner_id.id)
            ctx.update({
                'search_default_lead_id': self.id if self.type == 'lead' else False, # 
                'default_ischeck': 'lead' ,#  
                'default_lead_id': self.id if self.type == 'lead' else False,#  
                'default_partner_id': self.partner_id.id,
                'default_partner_ids': partner_ids,
                'default_team_id': self.team_id.id,
                'default_name': "Meeting With " + self.name , #self.name, 
                
            })
            # self.state = 'done'
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('sales_meet.action_calendar_event_crm')
            form_view_id = imd.xmlid_to_res_id('sales_meet.view_calendar_event_form_extension')
            
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'target': 'current',
                
                'context': ctx,
                'res_model': action.res_model,
            }
            # 'target': action.target,
        return result


# ----------------------- for direct List view (Tree) -----------------------
    @api.multi
    def action_schedule_meeting_lead(self):
        self.ensure_one()
        action = self.env.ref('sales_meet.action_calendar_event_crm').read()[0]
        partner_ids = self.env.user.partner_id.ids
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        action['context'] = {
            'search_default_lead_id': self.id if self.type == 'lead' else False, # 
            'default_ischeck': 'lead' ,#  
            'default_lead_id': self.id if self.type == 'lead' else False,#  
            'default_partner_id': self.partner_id.id,
            'default_partner_ids': partner_ids,
            'default_team_id': self.team_id.id,
            'default_name': self.name,
        }

        return action
# ----------------------- for direct List view (Tree) -----------------------
    

# class res_partner_group(models.Model):
#     _name = "res.partner.group"

#     name = fields.Char('Partner Group', required=False)
#     value = fields.Char('Value')
#     isactive = fields.Boolean("Active")



class enquiry_type(models.Model):
    _name = "enquiry.type"
    _description="Enquiry Type"

    name = fields.Char('Enquiry', required=False)
    isactive = fields.Boolean("Active")


class ActivityLog(models.TransientModel):

    _inherit = "crm.activity.log"

    sale_description = fields.Text('Sales Description')
    ho_description = fields.Text('HO Description')
    followup_date = fields.Date('Next Follow-Up Date')
    delay_reason = fields.Char('Delay Reason')
    order_details  = fields.Text('Order Details')
    quantity = fields.Char('Quantity (Kg)')
    business_generated = fields.Char('Business Generated')
    status = fields.Selection([
            ('first_order','First-Order'),
            ('re_order','Re-Order'),
            ('incorrect','Incorrect'),
            ('lost','Lost '),
            ('open','Open'),
            ('regret','Regret'),
        ], string='Status', copy=False, index=True, store=True)
    closed_month =  fields.Char('Order/Closed Month' , store=True, track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)


    @api.onchange('date_deadline')
    def onchange_month(self):
        if self.date_deadline:
            date_closed = self.date_deadline
            daymonthfrom2 = datetime.strptime(date_closed, "%Y-%m-%d")
            monthfrom2 = daymonthfrom2.strftime("%b")
            yearfrom2 = int(daymonthfrom2.strftime("%y"))
            self.closed_month =  monthfrom2 + '-' + str(yearfrom2)


class Lead2OpportunityPartner_extension(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'
    
    name = fields.Selection([('convert', 'Convert to opportunity'),], 'Conversion Action', required=True)

    # name = fields.Selection([
    #     ('convert', 'Convert to opportunity'),
    #     ('merge', 'Merge with existing opportunities')
    # ], 'Conversion Action', required=True)


class PartnerBinding_extension(models.TransientModel):
    _inherit = 'crm.partner.binding'
    
    action = fields.Selection([
        ('exist', 'Link to an existing customer'),
        ('create', 'Create a new customer'),
    ], 'Related Customer', required=True)

    #     action = fields.Selection([
    #     ('exist', 'Link to an existing customer'),
    #     ('create', 'Create a new customer'),
    #     ('nothing', 'Do not link to a customer')
    # ], 'Related Customer', required=True)



class CrmLeadLoglist(models.Model):
    _name = "crm.lead.log.list"
    _description = "Log an Activity"

    @api.model
    def _default_lead_id(self):
        if 'default_lead_id' in self._context:
            return self._context['default_lead_id']
        if self._context.get('active_model') == 'crm.lead':
            return self._context.get('active_id')
        return False

    
    name = fields.Text('Description')
    lead_id= fields.Many2one('crm.lead', default=_default_lead_id)
    followup_date = fields.Date('Next Follow-Up Date')
    # user_id = fields.Many2one('res.users', string='Salesperson')
    list_lead_id = fields.Many2one('crm.lead', 'Ticket')

    sale_description = fields.Text('Sales Description')
    ho_description = fields.Text('HO Description')
    followup_date = fields.Date('Next Follow-Up Date')
    date_deadline = fields.Date('Close Date')
    delay_reason = fields.Char('Delay Reason')
    order_details  = fields.Text('Order Details')
    quantity = fields.Char('Quantity (Kg)')
    business_generated = fields.Float('Business Generated')
    status = fields.Selection([
            ('first_order','First-Order'),
            ('re_order','Re-Order'),
            ('incorrect','Incorrect'),
            ('lost','Lost'),
            ('open','Open'),
            ('regret','Regret'),
        ], string='Status', copy=False, index=True, store=True)
    closed_month =  fields.Char('Order/Closed Month' , store=True, track_visibility='onchange')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)

    next_activity_id = fields.Many2one('crm.activity', 'Activity')
    title_action = fields.Char('Summary')
    note = fields.Html('Note')
    date_action = fields.Date('Next Activity Date')
    team_id = fields.Many2one('crm.team', 'Sales Team')
    planned_revenue = fields.Float('Expected Revenue')


    @api.onchange('date_deadline')
    def onchange_month(self):
        if self.date_deadline:
            date_closed = self.date_deadline
            daymonthfrom2 = datetime.strptime(date_closed, "%Y-%m-%d")
            monthfrom2 = daymonthfrom2.strftime("%b")
            yearfrom2 = int(daymonthfrom2.strftime("%y"))
            self.closed_month =  monthfrom2 + '-' + str(yearfrom2)


    @api.multi
    def action_log(self):
        for log in self:
            log.write({
                'date_deadline': log.date_deadline if log.date_deadline else False,
                'title_action': log.title_action,
                'date_action': log.date_action,
                'next_activity_id': log.next_activity_id.id,
                'list_lead_id':log.lead_id.id,
                'sale_description':log.sale_description,
                'ho_description':log.ho_description,
                'status':log.status,
                'delay_reason':log.delay_reason,
                'user_id':log.user_id.id,
                'followup_date':log.followup_date,
                'closed_month':log.closed_month,
                'order_details':log.order_details,
                'quantity':log.quantity,
                'business_generated':log.business_generated,
            })

            log.list_lead_id.write({'status':log.status,
                'date_deadline':log.date_deadline})
            if log.business_generated:
                log.list_lead_id.business_generated += log.business_generated
                
        return True



class project_contacts(models.Model):
    _name = "project.contacts"
    _description = "Project Contacts"

    
    name = fields.Char('Contact Name')
    project_lead_id= fields.Many2one('crm.lead')
    number = fields.Char('Contact No', size=10)
    designation = fields.Char('Designation')

    _sql_constraints = [
            ('number_uniq', 'unique(number)', 'Number already present in the lead'),
        ]

    @api.onchange('number')
    def onchange_number(self):
        if self.number:
            if len(self.number) != 10:
                raise UserError(" Kindly enter 10 digit contact number")
            lead_id = self.env['project.contacts'].search([('number','=',self.number)])
            if lead_id :
                name = lead_id.project_lead_id.name 
                raise UserError(" Number already present in the lead ' " + name + " '")


    @api.model
    def create(self, vals):
        contact = self.env['project.contacts'].search([('number','=',self.number)])
        result = super(project_contacts, self).create(vals)
        
        if result.number :
            number = lead = ''

            mobile = self.env['crm.lead'].search(['|',('mobile','=',result.number),('phone','=',result.number),('type','=','lead')])
            
            if mobile  or contact:
                if mobile :
                    number = mobile.mobile or mobile.phone
                    lead = mobile.name
                if contact :
                    number = contact.number
                    lead = contact.project_lead_id.name
                raise UserError("Created Number ' " + number  + " ' already present in the lead's contact list ' " + lead + " '")


        return result
    
    @api.multi
    def write(self, vals):
        contact = self.env['project.contacts'].search([('number','=',self.number)])
        result = super(project_contacts, self).write(vals)

        if self.number :
            number = lead = ''
            mobile = self.env['crm.lead'].search(['|',('mobile','=',self.number),('phone','=',self.number),('type','=','lead')])
            
            if mobile or contact:
                if mobile :
                    number = mobile.mobile
                    lead = mobile.name

                if contact :
                    number = contact.number
                    lead = contact.project_lead_id.name
                raise UserError("Created Number ' " + number  + " ' already present in the lead's contact list ' " + lead + " '")

        return result