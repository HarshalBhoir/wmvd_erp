# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo import tools
from HTMLParser import HTMLParser
from random import randint
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta, date , time
import logging
from dateutil import relativedelta
from odoo.exceptions import UserError, Warning, ValidationError
from werkzeug import url_encode


_logger = logging.getLogger(__name__)

todaydate = "{:%d-%b-%y}".format(datetime.now())

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
        
class WebsiteSupportTicket(models.Model):

    _name = "website.support.ticket"
    _description = "Website Support Ticket"
    _rec_name = "subject"
    _inherit = ['mail.thread','ir.needaction_mixin']
    _order = 'computed_priority desc, write_date, id'


    def _default_state(self):
        return self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_open')

    def _default_priority_id(self):
        default_priority = self.env['website.support.ticket.priority'].sudo().search([('sequence','=','1')])
        return default_priority[0]

    def _default_company_id(self):
        company = self.env['res.users'].sudo().search([('id', '=', self.env.uid)],limit=1).company_id.id
        return company


    create_user_id = fields.Many2one('res.users', "Created By")
    priority_id = fields.Many2one('website.support.ticket.priority', default=_default_priority_id, string="Priority")
    partner_id = fields.Many2one('res.partner', string="Partner")
    user_id = fields.Many2one('res.users', string="Assigned User")
    person_name = fields.Char(string='Person Name')
    email = fields.Char(string="Email")
    support_email = fields.Char(string="Support Email")
    category = fields.Many2one('website.support.ticket.categories', string="Category", track_visibility='onchange')
    sub_category_id = fields.Many2one('website.support.ticket.subcategory', string="Sub Category")
    subject = fields.Char(string="Subject")
    description = fields.Text(string="Description")
    state = fields.Many2one('website.support.ticket.states', readonly=True, default=_default_state, string="State")
    conversation_history = fields.One2many('website.support.ticket.message', 'ticket_id', string="Conversation History")
    attachment = fields.Binary(string="Attachments")
    attachment_filename = fields.Char(string="Attachment Filename")
    attachment_ids = fields.One2many('ir.attachment', 'res_id', 
        domain=[('res_model', '=', 'website.support.ticket')], string="Media Attachments")
    unattended = fields.Boolean(string="Unattended", compute="_compute_unattend", store="True", 
        help="In 'Open' state or 'Customer Replied' state taken into consideration name changes")
    portal_access_key = fields.Char(string="Portal Access Key")
    ticket_number = fields.Integer(string="Ticket Number")
    ticket_number_display = fields.Char(string="Ticket Number Display", compute="_compute_ticket_number_display")
    ticket_color = fields.Char(related="priority_id.color", string="Ticket Color")
    company_id = fields.Many2one('res.company', string="Company", default=_default_company_id)
    support_rating = fields.Integer(string="Support Rating")
    support_comment = fields.Text(string="Support Comment")
    close_comment = fields.Text(string="Close Comment")
    close_time = fields.Datetime(string="Close Time")
    close_date = fields.Date(string="Close Date")
    closed_by_id = fields.Many2one('res.users', string="Delegated To /Closed By")
    time_to_close = fields.Integer(string="Time to close (seconds)")
    extra_field_ids = fields.One2many('website.support.ticket.field', 'wst_id', string="Extra Details")
    status = fields.Selection([('draft', 'Draft'),
                        ('submitted', 'Submitted'),
                        ('inprogress', 'InProgress'),
                        ('10%', '10 %'),
                        ('30%', '30 %'),
                        ('50%', '50 %'),
                        ('80%', '80 %'),
                       ('completed', 'Completed')], default="draft" , string='Status', track_visibility='onchange')
    start_time = fields.Datetime(string="Start Time")
    estimated_hours = fields.Char(string="Estimated Hours")
    actual_hours = fields.Char(string="Actual Hours")
    project_id = fields.Many2one('project.project', 'Project', domain=[('allow_timesheets', '=', True)])
    activity_log_one2many = fields.One2many('ticket.activity.log', 'ticket_id', string='Activity Logs')
    activity_log_list_one2many = fields.One2many('ticket.activity.log.list', 'list_ticket_id', string='Activity Logs')

    analytic_timesheet_ids = fields.One2many('account.analytic.line', 'support_ticket_id', string="Timesheet")
    timesheet_project_id = fields.Many2one('project.project', string="Timesheet Project", compute="_compute_timesheet_project_id")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", compute="_compute_analytic_account_id")
    asset_id = fields.Many2one('bt.asset', string="Asset")
    approx_cost = fields.Float(string="Approx Cost")
    target_closure_date = fields.Datetime(string="Target Closure Date")
    initiated_date = fields.Datetime(string="Initiated Date")

    source = fields.Selection([('inhouse', 'In-house'), ('outsourced', 'Outsourced')], string='Source', default='inhouse')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    requisition_id = fields.Many2one('res.users', string="Requisition By")
    computed_priority = fields.Float(string="Computed Priority", compute="_get_priority", store=True)
    mobile = fields.Char(string="Mobile No", size=10)


    @api.depends('priority_id')
    def _get_priority(self):
        for rec in self:
            rec.computed_priority = int(rec.priority_id.sequence)
    
    @api.multi
    def open_close_ticket_wizard(self):
        timesheet_count = len(self.analytic_timesheet_ids)
        if timesheet_count == 0:
            raise UserError("Timesheets must be filled in before the ticket can be closed")

        return {
            'name': "Close Support Ticket",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'website.support.ticket.close',
            'context': {'default_ticket_id': self.id},
            'target': 'new'
        }

    @api.multi
    def _compute_analytic_account_id(self):
        default_analytic_account = self.env['ir.model.data'].get_object('website_support', 'customer_support_account')

        for record in self:
            record.analytic_account_id = default_analytic_account.id

    @api.multi
    def _compute_timesheet_project_id(self):
        setting_timesheet_default_project_id = self.env['ir.values'].get_default('website.support.settings', 'timesheet_default_project_id')
        
        for record in self:
            if setting_timesheet_default_project_id:
                record.timesheet_project_id = setting_timesheet_default_project_id


    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        if self.asset_id and self.asset_id.service_asset==True:
            self.approx_cost = self.asset_id.purchase_value

    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.person_name = self.partner_id.name
            self.email = self.partner_id.email
            requisition = self.env['res.users'].sudo().search([('partner_id','=', self.partner_id.id)]).id
            if requisition:
                self.requisition_id = requisition

    
    def message_new(self, msg, custom_values=None):
        """ Create new support ticket upon receiving new email"""

        defaults = {'support_email': msg.get('to'), 'subject': msg.get('subject')}

        #Extract the name from the from email if you can        
        if "<" in msg.get('from') and ">" in msg.get('from'):
            start = msg.get('from').rindex( "<" ) + 1
            end = msg.get('from').rindex( ">", start )
            from_email = msg.get('from')[start:end]
            from_name = msg.get('from').split("<")[0].strip()
            defaults['person_name'] = from_name
        else:
            from_email = msg.get('from')

        defaults['email'] = from_email
        
        #Try to find the partner using the from email
        search_partner = self.env['res.partner'].sudo().search([('email','=', from_email)])
        if len(search_partner) > 0:
            defaults['partner_id'] = search_partner[0].id
            defaults['person_name'] = search_partner[0].name

        defaults['description'] = tools.html_sanitize(msg.get('body'))
        
        portal_access_key = randint(1000000000,2000000000)
        defaults['portal_access_key'] = portal_access_key

        #Assign to default category
        setting_email_default_category_id = self.env['ir.values'].get_default('website.support.settings', 'email_default_category_id')
        
        if setting_email_default_category_id:
            defaults['category'] = setting_email_default_category_id
        
        return super(WebsiteSupportTicket, self).message_new(msg, custom_values=defaults)

    def message_update(self, msg_dict, update_vals=None):
        """ Override to update the support ticket according to the email. """

        body_short = tools.html_sanitize(msg_dict['body'])
        #body_short = tools.html_email_clean(msg_dict['body'], shorten=True, remove=True)
                
        #s = MLStripper()
        #s.feed(body_short)
        #body_short = s.get_data()
                
        #Add to message history field for back compatablity
        self.conversation_history.create({'ticket_id': self.id, 'by': 'customer', 'content': body_short })

        #If the to email address is to the customer then it must be a staff member...
        if msg_dict.get('to') == self.email:
            change_state = self.env['ir.model.data'].get_object('website_support','website_ticket_state_staff_replied')        
        else:
            change_state = self.env['ir.model.data'].get_object('website_support','website_ticket_state_customer_replied')
        
        self.state = change_state.id

        return super(WebsiteSupportTicket, self).message_update(msg_dict, update_vals=update_vals)

    @api.one
    @api.depends('ticket_number')
    def _compute_ticket_number_display(self):
        if self.ticket_number:
            self.ticket_number_display = str(self.id) + " / " + "{:,}".format( self.ticket_number )
        else:
            self.ticket_number_display = self.id
            
    @api.depends('state')
    def _compute_unattend(self):
        opened_state = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_open')
        customer_replied_state = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_customer_replied')

        if self.state == opened_state or self.state == customer_replied_state:
            self.unattended = True

    @api.multi
    def open_close_ticket_wizard(self):

        return {
            'name': "Close Support Ticket",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'website.support.ticket.close',
            'context': {'default_ticket_id': self.id},
            'target': 'new'
        }


    def report_check(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_check = base_url + '/web#%s' % (url_encode({
                'model': self._name,
                'view_type': 'form',
                'id': self.id,
            }))
        rep_check = """
            <td>
                <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                    font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                    text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                    text-align: center; vertical-align: middle; cursor: pointer; 
                    white-space: nowrap; background-image: none; background-color: #337ab7; 
                    border: 1px solid #337ab7; margin-right: 10px;">Check Ticket</a>
            </td> 
            """  % ( report_check)
        return rep_check

    @api.multi
    def action_submitted(self):
        self.send_mail_to_category_users()
        self.status = 'submitted'
        self.state = self.env['website.support.ticket.states'].search([("sequence","=",2)])


    @api.multi
    def send_mail_to_category_users(self):
        full_body  = """ """
        subject = ""
        email_from = self.create_user_id.email
        email_to_many = [x.email for x in self.env['website.support.ticket.categories'].sudo().search([("id","=",self.category.id)]).cat_user_ids]
        if not email_to_many:
            raise UserError(_('Team is missing in this category. Contact IT for Updation'))
        email_to = ",".join(email_to_many)

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <p>Hi Team,</p>
            <br/>

            <p>You have been assigned with a Ticket - %s </p>
            <br/>

            <h3>Kindly take necessary action by clicking the buttons below:</h3>


            <table>
              
              <tr><th style=" text-align: left;padding: 8px;">Subject No</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Description</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">User</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Priority</td><td> : %s</td></tr>

            </table>
            <br/>
            
        """ % ( self.ticket_number or '', self.subject or '', self.description or '', self.create_user_id.name,
         self.priority_id.name)

        full_body = body + self.report_check()
  
        subject = "Ticket Raised against %s by ( %s )- ( %s )"  % (self.category.name, self.create_user_id.name, todaydate)

        self.send_generic_mail(subject, full_body, email_from, email_to)


    @api.multi
    def send_mail_to_ticket_creator(self):
        full_body  = """ """
        subject = ""
        email_from = self.closed_by_id.email
        if self.create_user_id.id == self.requisition_id.id:
            email_to = self.create_user_id.email
        else:
            email_to = self.create_user_id.email + "," + self.requisition_id.email
      
        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <p>Hi %s,</p>
            <br/>

            <p> We have closed the ticket - %s at %s </p>
            <br/>

            <h3>Kindly take necessary action by clicking the buttons below:</h3>

            <table>
              
              <tr><th style=" text-align: left;padding: 8px;">Subject No</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Description</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Priority</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Closed By</td><td> : %s</td></tr>
              <tr><th style=" text-align: left;padding: 8px;">Remark</td><td> : %s</td></tr>

            </table>
            <br/>


        """ % ( self.create_user_id.name, self.ticket_number or '', self.close_time or '',
         self.subject or '', self.description or '', self.priority_id.name, self.closed_by_id.name, 
         self.close_comment)

        full_body = body + self.report_check()
  
        subject = "[Closed] Ticket against %s by ( %s )- ( %s )"  % (self.category.name, self.create_user_id.name, todaydate)

        self.send_generic_mail(subject, full_body, email_from, email_to)


    @api.multi
    def send_delegate_mail(self):
        full_body  = """ """
        subject = ""
        email_from = self.user_id.email
        email_to = self.closed_by_id.email

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <p>Hi %s,</p>
            <br/>

            <p><b>%s</b> has delegated a ticket -   <b>%s</b> dated <b>%s</b>  to you.</p>
            <p>The ticket is raised by %s and is regarding %s. Click on the button below.</p>
            <p> Kindly resolve the issue as per the given TAT</p>
            <br/>


        """ % ( self.closed_by_id.name , self.user_id.name , self.ticket_number , self.create_date, self.create_user_id.name, 
            self.subject )

        full_body = body + self.report_check()

        subject = "[Delegated] Ticket against %s by ( %s )- ( %s )"  % (self.category.name, self.create_user_id.name, todaydate)

        self.send_generic_mail(subject, full_body, email_from, email_to)



    @api.multi
    def send_generic_mail(self,subject=False, full_body=False, email_from=False, email_to=False):
        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': self.id,
                'email_from': email_from,
                'email_to': email_to,
                'subject': subject,
                'body_html': full_body,
            })

        composed_mail.send()

    @api.multi
    def start_ticket(self):

        self.status = 'inprogress'
        self.state = self.env['website.support.ticket.states'].search([("sequence","=",3)])

        self.start_time= self.initiated_date = datetime.now()
        self.user_id = self.env.user.id

        if self.target_closure_date and not self.estimated_hours:
            date_format = "%Y-%m-%d %H:%M:%S"
            date_1 = datetime.strptime(self.initiated_date, date_format)
            date_2 = datetime.strptime(self.target_closure_date, date_format)

            difference = relativedelta.relativedelta(date_2, date_1)

            years = difference.years
            months = difference.months
            days = difference.days
            hours = difference.hours
            minutes = difference.minutes

            # print "Difference is %s year, %s months, %s days, %s hours, %s minutes " %(years, months, days, hours, minutes)
            self.estimated_hours = ((str(years) + ' year,') if years !=0 else '') + ' ' + (str(months) + ' months,' if months !=0  else '' ) + ' ' +\
             (str(days) + ' days,' if days !=0  else '') + ' ' + (str(hours) + ' hours,' if hours !=0  else '') + ' ' + (str(minutes) + ' minutes' if minutes !=0 else '' )



    @api.model
    def _needaction_domain_get(self):
        open_state = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_open')
        custom_replied_state = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_customer_replied')
        return ['|',('state', '=', open_state.id ), ('state', '=', custom_replied_state.id)]


    def send_survey(self):
        notification_template = self.env['ir.model.data'].sudo().get_object('website_support', 'support_ticket_survey')
        values = notification_template.generate_email(self.id)
        surevey_url = "support/survey/" + str(self.portal_access_key)
        values['body_html'] = values['body_html'].replace("_survey_url_",surevey_url)
        send_mail = self.env['mail.mail'].create(values)
        send_mail.send(True)

    @api.model
    def create(self, vals):
        new_id = super(WebsiteSupportTicket, self).create(vals)

        new_id.ticket_number = new_id.company_id.next_support_ticket_number

        #Add one to the next ticket number
        write_data = self.env['res.company'].search([('id', '=', new_id.company_id.id)]).sudo().write({
                                                        'next_support_ticket_number': new_id.company_id.next_support_ticket_number+1,
                                                        })
        # new_id.company_id.next_support_ticket_number += 1



        # #Auto create contact if one with that email does not exist
        # setting_auto_create_contact = self.env['ir.values'].get_default('website.support.settings', 'auto_create_contact')
        
        # if setting_auto_create_contact and 'email' in vals:
        #     if self.env['res.partner'].search_count([('email','=',vals['email'])]) == 0:
        #         if 'person_name' in vals:
        #             new_contact = self.env['res.partner'].create({'name':vals['person_name'], 'email': vals['email'], 'company_type': 'person'})
        #         else:
        #             new_contact = self.env['res.partner'].create({'name':vals['email'], 'email': vals['email'], 'company_type': 'person'})
                    
        #         new_id.partner_id = new_contact.id
                    
        # #(BACK COMPATABILITY) Fail safe if no template is selected, future versions will allow disabling email by removing template
        # ticket_open_email_template = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_open').mail_template_id
        # if ticket_open_email_template == False:
        #     ticket_open_email_template = self.env['ir.model.data'].sudo().get_object('website_support', 'support_ticket_new')
        #     ticket_open_email_template.send_mail(new_id.id, True)
        # else:
        #     ticket_open_email_template.send_mail(new_id.id, True)

        # #Send an email out to everyone in the category
        # notification_template = self.env['ir.model.data'].sudo().get_object('website_support', 'new_support_ticket_category')
        # support_ticket_menu = self.env['ir.model.data'].sudo().get_object('website_support', 'website_support_ticket_menu')
        # support_ticket_action = self.env['ir.model.data'].sudo().get_object('website_support', 'website_support_ticket_action')
        
        # for my_user in new_id.category.cat_user_ids:
        #     values = notification_template.generate_email(new_id.id)
        #     values['body_html'] = values['body_html'].replace("_ticket_url_", "web#id=" + str(new_id.id) + "&view_type=form&model=website.support.ticket&menu_id=" + str(support_ticket_menu.id) + "&action=" + str(support_ticket_action.id) ).replace("_user_name_",  my_user.partner_id.name)
        #     #values['body'] = values['body_html']
        #     values['email_to'] = my_user.partner_id.email
                        
        #     send_mail = self.env['mail.mail'].create(values)
        #     send_mail.send()
            
        #     #Remove the message from the chatter since this would bloat the communication history by a lot
        #     send_mail.mail_message_id.res_id = 0
            
        return new_id
        
    # @api.multi
    # def write(self, values, context=None):

    #     update_rec = super(WebsiteSupportTicket, self).write(values)

    #     if 'state' in values:
    #         if self.state.mail_template_id:
    #             self.state.mail_template_id.send_mail(self.id, True)
                
    #     #Email user if category has changed
    #     if 'category' in values:
    #         change_category_email = self.env['ir.model.data'].sudo().get_object('website_support', 'new_support_ticket_category_change')
    #         change_category_email.send_mail(self.id, True)

    #     if 'user_id' in values:
    #         setting_change_user_email_template_id = self.env['ir.values'].get_default('website.support.settings', 'change_user_email_template_id')
        
    #         if setting_change_user_email_template_id:
    #             email_template = self.env['mail.template'].browse(setting_change_user_email_template_id)
    #         else:
    #             #Default email template
    #             email_template = self.env['ir.model.data'].get_object('website_support','support_ticket_user_change')

    #         email_values = email_template.generate_email([self.id])[self.id]
    #         email_values['model'] = "website.support.ticket"
    #         email_values['res_id'] = self.id
    #         assigned_user = self.env['res.users'].browse( int(values['user_id']) )
    #         email_values['email_to'] = assigned_user.partner_id.email
    #         email_values['body_html'] = email_values['body_html'].replace("_user_name_", assigned_user.name)
    #         email_values['body'] = email_values['body'].replace("_user_name_", assigned_user.name)
    #         send_mail = self.env['mail.mail'].create(email_values)
    #         send_mail.send()

        
    #     return update_rec


class WebsiteSupportTicketField(models.Model):
    _name = "website.support.ticket.field"

    wst_id = fields.Many2one('website.support.ticket', string="Support Ticket")
    name = fields.Char(string="Label")
    value = fields.Char(string="Value")
    
class WebsiteSupportTicketMessage(models.Model):
    _name = "website.support.ticket.message"
    
    ticket_id = fields.Many2one('website.support.ticket', string='Ticket ID')
    by = fields.Selection([('staff','Staff'), ('customer','Customer')], string="By")
    content = fields.Html(string="Content")
   
class WebsiteSupportTicketCategories(models.Model):

    _name = "website.support.ticket.categories"
    _order = "sequence asc"
    
    sequence = fields.Integer(string="Sequence")
    name = fields.Char(required=True, translate=True, string='Category Name')
    cat_user_ids = fields.Many2many('res.users', string="Category Users")

    @api.model
    def create(self, values):
        sequence=self.env['ir.sequence'].next_by_code('website.support.ticket.categories')
        values['sequence']=sequence
        return super(WebsiteSupportTicketCategories, self).create(values)
        
class WebsiteSupportTicketSubCategories(models.Model):

    _name = "website.support.ticket.subcategory"
    _order = "sequence asc"

    sequence = fields.Integer(string="Sequence")
    name = fields.Char(required=True, translate=True, string='Sub Category Name')   
    parent_category_id = fields.Many2one('website.support.ticket.categories', required=True, string="Parent Category")
    additional_field_ids = fields.One2many('website.support.ticket.subcategory.field', 'wsts_id', string="Additional Fields")
 
    @api.model
    def create(self, values):
        sequence=self.env['ir.sequence'].next_by_code('website.support.ticket.subcategory')
        values['sequence']=sequence
        return super(WebsiteSupportTicketSubCategories, self).create(values)

class WebsiteSupportTicketSubCategoryField(models.Model):

    _name = "website.support.ticket.subcategory.field"
        
    wsts_id = fields.Many2one('website.support.ticket.subcategory', string="Sub Category")
    name = fields.Char(string="Label")
    type = fields.Selection([('textbox','Textbox')], default="textbox", string="Type")
    
class WebsiteSupportTicketStates(models.Model):

    _name = "website.support.ticket.states"
    _order = 'sequence'
    
    name = fields.Char(required=True, translate=True, string='State Name')
    sequence = fields.Integer(
        "Sequence", default=10,
        help="Gives the sequence order when displaying a list of stages.")
    mail_template_id = fields.Many2one('mail.template', domain="[('model_id','=','website.support.ticket')]", string="Mail Template")

    @api.multi
    def unlink(self):
        for order in self:
            if order.env.uid != 1 or not order.user_has_groups('website_support.group_website_support_manager'):
                raise UserError(_('You cannot delete States'))
        return super(WebsiteSupportTicketStates, self).unlink()

class WebsiteSupportTicketPriority(models.Model):

    _name = "website.support.ticket.priority"
    _order = "sequence asc"

    sequence = fields.Integer(string="Sequence")
    name = fields.Char(required=True, translate=True, string="Priority Name")
    color = fields.Char(string="Color")
    
    @api.model
    def create(self, values):
        sequence=self.env['ir.sequence'].next_by_code('website.support.ticket.priority')
        values['sequence']=sequence
        return super(WebsiteSupportTicketPriority, self).create(values)
        
class WebsiteSupportTicketUsers(models.Model):
    _inherit = "res.users"
    
    cat_user_ids = fields.Many2many('website.support.ticket.categories', string="Category Users")

class WebsiteSupportTicketCompose(models.Model):

    _name = "website.support.ticket.close"

    ticket_id = fields.Many2one('website.support.ticket', string="Ticket ID")
    message = fields.Text(string="Close Message")

    def close_ticket(self):

        self.ticket_id.close_time = datetime.now()
        self.ticket_id.status = 'completed'
        
        #Also set the date for gamification
        self.ticket_id.close_date = date.today()
        
        diff_time = datetime.strptime(self.ticket_id.close_time, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(self.ticket_id.create_date, DEFAULT_SERVER_DATETIME_FORMAT)            
        self.ticket_id.time_to_close = (diff_time.seconds )/360

        if self.ticket_id.start_time:
            # diff_time2 = datetime.datetime.strptime(self.ticket_id.close_time, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.datetime.strptime(self.ticket_id.start_time, DEFAULT_SERVER_DATETIME_FORMAT)
            # self.ticket_id.actual_hours = (diff_time2.seconds)/360

            date_format = "%Y-%m-%d %H:%M:%S"

            date_1 = datetime.strptime(self.ticket_id.start_time, date_format)
            date_2 = datetime.strptime(self.ticket_id.close_time, date_format)


            #This will find the difference between the two dates
            difference = relativedelta.relativedelta(date_2, date_1)

            years = difference.years
            months = difference.months
            days = difference.days
            hours = difference.hours
            minutes = difference.minutes

            print "Difference is %s year, %s months, %s days, %s hours, %s minutes " %(years, months, days, hours, minutes)
            self.ticket_id.actual_hours = ((str(years) + ' year,') if years !=0 else '') + ' ' + (str(months) + ' months,' if months !=0  else '' ) + ' ' +\
             (str(days) + ' days,' if days !=0  else '') + ' ' + (str(hours) + ' hours,' if hours !=0  else '') + ' ' + (str(minutes) + ' minutes' if minutes !=0 else '' )

            # print "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" , self.ticket_id.actual_hours



        closed_state = self.env['ir.model.data'].sudo().get_object('website_support', 'website_ticket_state_staff_closed')
        
        #We record state change manually since it would spam the chatter if every 'Staff Replied' and 'Customer Replied' gets recorded
        message = "<ul class=\"o_mail_thread_message_tracking\">\n<li>State:<span> " + self.ticket_id.status + " </span><b>-></b> " + closed_state.name + " </span></li></ul>"
        self.ticket_id.message_post(body=message, subject="Ticket Closed by Staff")

        self.ticket_id.close_comment = self.message
        self.ticket_id.closed_by_id = self.env.user.id
        self.ticket_id.state = closed_state.id
        self.ticket_id.send_mail_to_ticket_creator()

        if self.ticket_id.asset_id.service_asset == True and self.ticket_id.approx_cost and self.ticket_id.asset_id.state == 'draft':
            print "gggggggggggggggggggggggggggggggggggggggggggggggggggggg" , self.ticket_id.asset_id.service_asset , self.ticket_id.approx_cost, self.ticket_id.asset_id.department_id.name, self.ticket_id.asset_id.company_id.name

            budget_id = self.env['bt.budget'].search([('department_id','=',self.ticket_id.asset_id.department_id.id),
                                                        ('state','=','approved'),
                                                        ('company_id','=',self.ticket_id.asset_id.company_id.id)])
            print "33333333333333333333333333333333333333333333333333333333" , budget_id
            if budget_id:
                print "ooooooooooooooooooooooooooooo" , budget_id
                # print error
                for budget in budget_id[0]:
                    budget_line_id = self.env['bt.budget.line'].search([('budget_id','=',budget.id),('category_id','=',self.ticket_id.asset_id.budget_category_id.id)])
                    if budget_line_id:
                        budget.amount_alloted += self.ticket_id.approx_cost
                        self.ticket_id.asset_id.state == 'active'
                        for line in budget_line_id:
                            line.claimed += self.ticket_id.approx_cost
            else:
                raise Warning(_(" Budget not found for below Department and Company")) 


        # #Auto send out survey
        # setting_auto_send_survey = self.env['ir.values'].get_default('website.support.settings', 'auto_send_survey')
        # if setting_auto_send_survey:
        #     self.ticket_id.send_survey()
        
        # #(BACK COMPATABILITY) Fail safe if no template is selected
        # closed_state_mail_template = self.env['ir.model.data'].get_object('website_support', 'website_ticket_state_staff_closed').mail_template_id

        # if closed_state_mail_template == False:
        #     closed_state_mail_template = self.env['ir.model.data'].sudo().get_object('website_support', 'support_ticket_closed')
        #     closed_state_mail_template.send_mail(self.ticket_id.id, True)
    
class WebsiteSupportTicketCompose(models.Model):

    _name = "website.support.ticket.compose"

    ticket_id = fields.Many2one('website.support.ticket', string='Ticket ID')
    partner_id = fields.Many2one('res.partner', string="Partner", readonly="True")
    email = fields.Char(string="Email", readonly="True")
    subject = fields.Char(string="Subject", readonly="True")
    body = fields.Text(string="Message Body")
    template_id = fields.Many2one('mail.template', string="Mail Template", domain="[('model_id','=','website.support.ticket'), ('built_in','=',False)]")
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            values = self.env['mail.compose.message'].generate_email_for_composer(self.template_id.id, [self.ticket_id.id])[self.ticket_id.id]                
            self.body = values['body']
            
    @api.one
    def send_reply(self):
        #Send email
        values = {}

        setting_staff_reply_email_template_id = self.env['ir.values'].get_default('website.support.settings', 'staff_reply_email_template_id')
        
        if setting_staff_reply_email_template_id:
            email_wrapper = self.env['mail.template'].browse(setting_staff_reply_email_template_id)
        else:
            #Defaults to staff reply template for back compatablity
            email_wrapper = self.env['ir.model.data'].get_object('website_support','support_ticket_reply_wrapper')

        values = email_wrapper.generate_email([self.id])[self.id]
        values['model'] = "website.support.ticket"
        values['res_id'] = self.ticket_id.id
        send_mail = self.env['mail.mail'].create(values)
        send_mail.send()
        
        #Add to message history field for back compatablity
        self.env['website.support.ticket.message'].create({'ticket_id': self.ticket_id.id, 'by': 'staff', 'content':self.body.replace("<p>","").replace("</p>","")})
        
        #Post in message history
        #self.ticket_id.message_post(body=self.body, subject=self.subject, message_type='comment', subtype='mt_comment')
	
	staff_replied = self.env['ir.model.data'].get_object('website_support','website_ticket_state_staff_replied')
	self.ticket_id.state = staff_replied.id


class TicketActivityLog(models.TransientModel):
    _name = "ticket.activity.log"
    _description = "Log an Activity"

    @api.model
    def _default_ticket_id(self):
        if 'default_ticket_id' in self._context:
            return self._context['default_ticket_id']
        if self._context.get('active_model') == 'website.support.ticket':
            return self._context.get('active_id')
        return False

    
    name = fields.Text('Description')
    ticket_id= fields.Many2one('website.support.ticket', 'Ticket', required=True, default=_default_ticket_id)
    followup_date = fields.Date('Next Follow-Up Date')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)


    @api.multi
    def action_log(self):
        # return self.env['ir.values'].sudo().set_default('ticket.activity.log', 'name', self.name)
        write_data = self.env['ticket.activity.log.list'].sudo().create({
                                                        'create_date': self.create_date,
                                                        'user_id': self.user_id.id,
                                                        'name': self.name,
                                                        'list_ticket_id': self.ticket_id.id,
                                                        })
        return True


class TicketActivityLoglist(models.Model):
    _name = "ticket.activity.log.list"
    _description = "Log an Activity"

    # @api.model
    # def _default_ticket_id(self):
    #     if 'default_ticket_id' in self._context:
    #         return self._context['default_ticket_id']
    #     if self._context.get('active_model') == 'website.support.ticket':
    #         return self._context.get('active_id')
    #     return False

    
    name = fields.Text('Description')
    ticket_id= fields.Many2one('website.support.ticket')
    followup_date = fields.Date('Next Follow-Up Date')
    user_id = fields.Many2one('res.users', string='User')
    list_ticket_id = fields.Many2one('website.support.ticket', 'Ticket')

