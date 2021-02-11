# -*- coding: utf-8 -*-

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
from odoo.exceptions import UserError, Warning, ValidationError
from werkzeug import url_encode

AVAILABLE_ZONE=[('North', 'North'),
                ('East', 'East'),
                ('Central', 'Central'),
                ('West', 'West'),
                ('South', 'South'),
                ('Export', 'Export')]

AVAILABLE_STATES=[('Draft', 'Draft'),
                ('Done', 'Generated'),
                ('Refused', 'Refused'),
                ('Approved', 'Approved'),
                ('Posted', 'Posted'),
                ('Reimbursement Approved', 'Reimbursement Approved')]

class marketing_master(models.Model):
    _name = "marketing.master"
    _description = "Marketing Master"

    name = fields.Char('Name',default="Guidelines Config")
    active = fields.Boolean("Active", default=True)
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('marketing.master'))
    marketing_line_ids = fields.One2many('marketing.master.line', 'marketing_line_id', 'Claim Lines', copy=True)
    owner_id = fields.Many2one('res.users', string='Owner')
    handled_by_id = fields.Many2one('res.users', string='Handled By')


    @api.model
    def create(self, vals):
        result = super(marketing_master, self).create(vals)
        a = self.search([("company_id","=",result.company_id.id)])
        if len(a) >1:
            raise UserError(_('You can only create 1 Config Record per company'))
        else:
            result.name = result.company_id.short_name + "- Guidelines Config"
        return result
    

class marketing_master_line(models.Model):
    _name = "marketing.master.line"
    _description = "Marketing Master Line"

    name = fields.Char('Marketing Master Line')
    active = fields.Boolean("Active" , default=True)
    marketing_line_id = fields.Many2one('marketing.master', 'Marketing Master', ondelete='cascade')
    meeting_type = fields.Many2one('calendar.event.type', 'Meeting', domain=[('marketing_bool','=',True)])
    meeting_abbrv = fields.Char('Abbreviation', related='meeting_type.short_name')
    attendees_no = fields.Integer('No. of Attendees')
    categ_ids = fields.Many2many('product.category', string='Focus Material')
    audience_id = fields.Many2many('marketing.audience', string='Audience Type')
    snacks_dinner = fields.Char('Snacks/Dinner')
    snacks_dinner_budget = fields.Float('Snacks/Dinner Budget (Rs.)')
    gift_budget = fields.Float('Gift Budget (Rs.)')
    total_pp = fields.Float('Total PP (Rs.)')
    grand_amount = fields.Float('Grand Amount (Rs.)')


class CalendarEventType(models.Model):
    _inherit = 'calendar.event.type'

    marketing_bool = fields.Boolean("Marketing Bool")
    short_name = fields.Char('Abbrevation')

class marketing_audience(models.Model):
    _name = "marketing.audience"
    _description = "Marketing Audience"

    name = fields.Char('Audience')
    active = fields.Boolean("Active" , default=True)


class meeting_attendance(models.Model):
    _name = "meeting.attendance"
    _description = "Meeting Attendance"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

    name = fields.Char('Attendance')
    meeting_attendance_line_ids = fields.One2many('meeting.attendance.line', 'attendance_id', 
        'Attendance Lines', copy=True)
    # meeting_id = fields.Many2one("calendar.event", string="Meeting" )
    meet_requisition_id = fields.Many2one("meet.requisition", string="Meeting", 
        domain=[('state','=','approved')])
    meeting_date = fields.Date('Meeting Date')
    partner_id = fields.Many2one('res.partner', string='Distributor', track_visibility='onchange',
        domain="[('customer', '=', True)]")
    lead_id = fields.Many2one('crm.lead', string='Lead', track_visibility='onchange', 
        domain="[('type', '=', 'lead')]")
    meeting_type = fields.Many2one('calendar.event.type', 'Meeting Type', domain=[('marketing_bool', '=', True)])
    location = fields.Char('Location' )
    city = fields.Char('City')
    state_id = fields.Many2one('res.country.state', string='State')
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self._uid, 
        track_visibility='always')
    manager_id = fields.Many2one('res.users', string='Manager')
    zsm_id = fields.Many2one('res.users', string='ZSM')
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('meeting.attendance'))
    food_cost =  fields.Float(string = "Food Cost - Per Person")
    food_attachments = fields.Many2many('ir.attachment', copy=False, attachment=True)

    gift_cost =  fields.Float(string = "Gift Cost - Per Person")
    gift_attachments = fields.Many2many('ir.attachment', copy=False, attachment=True)
    meeting_photos_attachments = fields.Many2many('ir.attachment', copy=False, attachment=True)
    painter_count =  fields.Integer(string = "No.- Painter/Contractor")
    total_cost =  fields.Float(compute='_compute_total_cost', string = "Total Cost", store=True)
    total_advance_cost =  fields.Float(compute='_compute_total_advance_cost', 
        string = "Total Advance Amount Req.", store=True)
    zone = fields.Selection(AVAILABLE_ZONE, string='Zone', copy=False, index=True, store=True)
    state = fields.Selection(AVAILABLE_STATES, string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='Draft')

    @api.model
    def create(self, vals):
        line_config = self.env['marketing.master.line'].sudo().search([('meeting_type','=',vals['meeting_type'])])
        food_bool = painter_bool = gift_bool = ''
        print "1111111111111111111111111111111111" , vals
        if line_config:

            if vals['food_cost'] and line_config.snacks_dinner_budget < vals['food_cost']:
                food_bool = ("Food Cost Per Person cannot be more than %s for %s" \
                    % (line_config.snacks_dinner_budget, line_config.meeting_type.name))

            if vals['painter_count'] and line_config.attendees_no < vals['painter_count']:
                painter_bool = ("Number of attendees cannot be more than %s for %s" \
                    % (line_config.attendees_no, line_config.meeting_type.name))

            if vals['gift_cost'] and line_config.gift_budget < vals['gift_cost']:
                gift_bool = ("Gift Cost Per Person cannot be more than %s for %s" \
                    % (line_config.gift_budget, line_config.meeting_type.name))

            if food_bool or painter_bool or gift_bool:
                warning_bool = food_bool + '\n' + painter_bool + '\n' + gift_bool
                raise Warning(warning_bool)


        result = super(meeting_attendance, self).create(vals)
        result.name = "MA/" + str(result.company_id.short_name)  +"/"  + str(result.id).zfill(5)
        return result

    @api.multi
    def update_data(self):
        self.state = 'done'
        self.send_mail_to_marketing()

    @api.multi
    def approve_data(self):
        self.sudo().write({'state': 'approved'})
        self.send_mail_to_marketing_handled_by()

    @api.multi
    def refuse_data(self):
        self.sudo().write({'state': 'refused'})
        self.send_mail_to_marketing_handled_by()

    # @api.multi
    # def reimbursement_approve_data(self):
    #     self.sudo().write({'state': 'Reimbursement Approved'})
    #     self.send_mail_to_marketing_handled_by()
    #     self.meet_requisition_id.state = 'Reimbursement Approved'
    #     # self.sudo().write({'state': 'Reimbursement Approved'})





    @api.onchange('meet_requisition_id')
    def onchange_meet_requisition_id(self):
        if self.meet_requisition_id:
            self.meeting_date =  self.meet_requisition_id.meeting_date
            self.partner_id =  self.meet_requisition_id.partner_id.id
            self.lead_id =  self.meet_requisition_id.lead_id.id
            self.meeting_type =  self.meet_requisition_id.meeting_type.id
            self.location =  self.meet_requisition_id.location
            self.city =  self.meet_requisition_id.city
            self.state_id =  self.meet_requisition_id.state_id.id
            self.zone =  self.meet_requisition_id.zone
            self.manager_id =  self.meet_requisition_id.manager_id.id
            self.zsm_id =  self.meet_requisition_id.zsm_id.id
        else:
            self.meeting_date =  False
            self.partner_id =  False
            self.lead_id =  False
            self.meeting_type =  False
            self.location =  ''
            self.city =  ''
            self.state_id =  False
            self.zone =  False
            self.manager_id =  False
            self.zsm_id =  False



    @api.onchange('painter_count')
    def onchange_painter_count(self):
        if self.painter_count:
            line_config = self.env['marketing.master.line'].sudo().search([('meeting_type','=',self.meeting_type.id)])
            if line_config:
                if line_config.attendees_no < self.painter_count:
                    raise Warning(_("Number of attendees cannot be more than %s for %s" \
                        % (line_config.attendees_no, self.meeting_type.name)))

    @api.onchange('food_cost')
    def onchange_food_cost(self):
        if self.food_cost:
            line_config = self.env['marketing.master.line'].sudo().search([('meeting_type','=',self.meeting_type.id)])
            if line_config:
                if line_config.snacks_dinner_budget < self.food_cost:
                    raise Warning(_("Food Cost Per Person cannot be more than %s for %s" \
                        % (line_config.snacks_dinner_budget, self.meeting_type.name)))

    @api.onchange('gift_cost')
    def onchange_gift_cost(self):
        if self.gift_cost:
            line_config = self.env['marketing.master.line'].sudo().search([('meeting_type','=',self.meeting_type.id)])
            if line_config:
                if line_config.gift_budget < self.gift_cost:
                    raise Warning(_("Gift Cost Per Person cannot be more than %s for %s" \
                        % (line_config.gift_budget, self.meeting_type.name)))


    @api.multi
    @api.depends('food_cost', 'gift_cost')
    def _compute_total_cost(self):
        self.total_cost = (self.food_cost if self.food_cost else 0.0) + \
                            (self.gift_cost if self.gift_cost else 0.0 )

    @api.multi
    @api.depends('painter_count', 'total_cost')
    def _compute_total_advance_cost(self):
        self.total_advance_cost = self.painter_count * self.total_cost



    @api.multi
    def send_mail_to_marketing(self):
        main_body  = """ """
        subject = ""
        main_id = self.id
        totalamount = 0.0
        email_from = self.user_id.email
        config_mail = self.env['marketing.master'].search([("active","=",True)])
        email_to = config_mail.owner_id.email 
        email_cc1 =  self.zsm_id.email
        email_cc2 =  config_mail.handled_by_id.email
        email_cc3 =  self.manager_id.email
        email_cc_list = [email_cc1, email_cc2, email_cc3]
        email_cc =  ",".join(email_cc_list)

        todaydate = "{:%d-%b-%y}".format(datetime.now())
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
            <h3>The following meeting is scheduled on %s by %s and is requesting an approval from your end.</h3>

            <table>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Meeting Type</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Meeting Date</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Distributor</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Counter/Retailer</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Location</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">City</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">State</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Zone</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Manager</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">ZSM</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">No. Expected - Painter/Contractor</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Food Cost - Per Person</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Gift Cost - Per Person</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Total Cost - Per Person</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Total Budget</td>
                        <td> : %s</td>
                    </tr>
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

        """ % (self.meeting_date, self.user_id.name , self.meeting_type.name, self.meeting_date, 
            self.partner_id.name, self.lead_id.name, self.location, self.city, self.state_id.name,
            self.zone, self.manager_id.name, self.zsm_id.name, self.painter_count, self.food_cost,
            self.gift_cost, self.total_cost, self.total_advance_cost,
            approve_url, reject_url, report_check)


        subject = "[Request]] Reimbursement Approval for Retailer/Painter Meeting ( %s )- ( %s )" \
         % (self.partner_id.name, self.meeting_date)
        full_body = main_body

        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': main_id,
                'email_from': email_from,
                'email_to': email_to,
                'email_cc': email_cc,
                'subject': subject,
                'body_html': full_body,

            })

        composed_mail.send()


    @api.multi
    def send_mail_to_marketing_handled_by(self):
        main_body  = """ """
        check_request = """ """
        subject = ""
        status = ""
        main_id = self.id
        totalamount = 0.0
        
        config_mail = self.env['marketing.master'].search([("active","=",True)])
        email_from = config_mail.owner_id.email 
        todaydate = "{:%d-%b-%y}".format(datetime.now())
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_check = base_url + '/web#%s' % (url_encode({
                'model': self._name,
                'view_type': 'form',
                'id': main_id,
            }))

        if self.state == 'approved':
            email_to = config_mail.handled_by_id.email 
            status = 'approved'
            subject = "[Approved] Reimbursement for Meeting to %s - ( %s )"  % (self.meeting_type.name, self.meeting_date)

            check_request = """ 
                <td>
                    <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px;
                        font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                        text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                        text-align: center; vertical-align: middle; cursor: pointer; white-space: nowrap;
                        background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                        margin-right: 10px;">Check Request</a>
                </td>
            """ % (report_check)

        else:
            email_to = self.user_id.email
            status = 'refused'
            subject = "[Refused] Reimbursement for Meeting to %s - ( %s )"  % (self.meeting_type.name, self.meeting_date)

        main_body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <p>Hi %s,</p>

            <br/>
            <p>The Reimbursement for <b>%s</b> is %s. </p>

            <br/>

        """ % ( self.user_id.name , self.meeting_type.name,status)

        

        # You can Fill up the Meeting Attendance from the Meeting form itself 
        #     by clicking on the "Attendances" button.
        
        full_body = main_body + check_request
        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': main_id,
                'email_from': email_from,
                'email_to': email_to,
                'subject': subject,
                'body_html': full_body,

            })

        composed_mail.send()

   
class meeting_attendance_line(models.Model):
    _name = "meeting.attendance.line"
    _description = "Meeting Attendance Line"

    name = fields.Char('Name')
    active = fields.Boolean("Active" , default=True)
    attendance_id = fields.Many2one('meeting.attendance', 'Attendance Master', ondelete='cascade')
    mobile = fields.Char('Mobile No.')


class meet_requisition(models.Model):
    _name = 'meet.requisition'
    _description = "Meet Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order    = 'id desc'

       
    name = fields.Char(string = "Meet No.")
    meeting_type = fields.Many2one('calendar.event.type', 'Meeting Type', domain=[('marketing_bool', '=', True)])
    advanced_date = fields.Date(string="Advanced Date")
    meeting_date = fields.Date(string="Meeting Date" , default=lambda self: fields.datetime.now())
    partner_id = fields.Many2one('res.partner',string="Distributor" )
    lead_id = fields.Many2one('crm.lead', string='Counter/Retailer', domain="[('type', '=', 'lead')]")
    location = fields.Char(string = "Location")
    city = fields.Char(string = "City")
    state_id = fields.Many2one('res.country.state', string='State')
    user_id = fields.Many2one('res.users', string='User', 
        default=lambda self: self._uid, track_visibility='always', copy=False)
    manager_id = fields.Many2one('res.users', string='Manager')
    zsm_id = fields.Many2one('res.users', string='ZSM')
    company_id = fields.Many2one('res.company', 'Company', 
        default=lambda self: self.env['res.company']._company_default_get('meet.requisition'))
    expected_painter =  fields.Integer(string = "No. Expected - Painter/Contractor")
    expected_food_cost =  fields.Float(string = "Expected Food Cost - Per Person")
    expected_gift_cost =  fields.Float(string = "Expected Gift Cost - Per Person")
    total_cost =  fields.Float(compute='_compute_total_cost', string = "Total Cost - Per Person", store=True)
    total_advance_cost =  fields.Float(compute='_compute_total_advance_cost', 
        string = "Total Advance Amount Req.", store=True)
    attendance_id = fields.Many2one('meeting.attendance', string="Attendance")
    attendance_count = fields.Integer(compute='_compute_attendance_count', string='Attendances')
    zone = fields.Selection(AVAILABLE_ZONE, string='Zone', copy=False, index=True)
    gift_by = fields.Selection([('Self','Self'),('Company','Company')], string='Gift By', copy=False, index=True)
    
    state = fields.Selection(AVAILABLE_STATES, string='Status', readonly=True,
        copy=False, index=True, track_visibility='always', default='draft')


    @api.model
    def create(self, vals):
        line_config = self.env['marketing.master.line'].sudo().search([('meeting_type', '=', vals['meeting_type'])])
        food_bool = ''
        painter_bool = ''
        gift_bool = ''
        print "aaaaaaaaaaaaaaaaaaaaaaaaaaa" , vals
        if line_config:
            if vals['expected_food_cost'] and line_config.snacks_dinner_budget < vals['expected_food_cost']:
                food_bool = ("Food Cost Per Person cannot be more than %s for %s" \
                    % (line_config.snacks_dinner_budget, line_config.meeting_type.name))

            if vals['expected_painter'] and line_config.attendees_no < vals['expected_painter']:
                painter_bool = ("Number of attendees cannot be more than %s for %s" \
                    % (line_config.attendees_no, line_config.meeting_type.name))

            if vals['expected_gift_cost'] and line_config.gift_budget < vals['expected_gift_cost']:
                gift_bool = ("Gift Cost Per Person cannot be more than %s for %s" \
                    % (line_config.gift_budget, line_config.meeting_type.name))

            if food_bool or painter_bool or gift_bool:
                warning_bool = food_bool + '\n' + painter_bool + '\n' + gift_bool
                raise Warning(warning_bool)

        result = super(meet_requisition, self).create(vals)
        result.name = "MR/" + str(result.company_id.short_name)  + "/"  + str(result.id).zfill(5)
        return result
    
    @api.multi
    def update_data(self):
        self.send_mail_to_approver()
        self.state = 'done'

    @api.multi
    @api.depends('expected_food_cost', 'expected_gift_cost')
    def _compute_total_cost(self):
        self.total_cost = (self.expected_food_cost if self.expected_food_cost else 0.0) + \
                            (self.expected_gift_cost if self.expected_gift_cost else 0.0 )

    @api.multi
    @api.depends('expected_painter', 'total_cost')
    def _compute_total_advance_cost(self):
        self.total_advance_cost = self.expected_painter * self.total_cost

    @api.multi
    def approve_data(self):
        self.sudo().write({'state': 'approved'})
        self.send_mail_to_salesperson()

    @api.multi
    def refuse_data(self):
        self.sudo().write({'state': 'refused'})
        self.send_mail_to_salesperson()


    @api.multi
    def _compute_attendance_count(self):
        data = self.env['meeting.attendance'].search([('meet_requisition_id', 'in', self.ids)]).ids
        self.attendance_count = len(data)

    @api.onchange('expected_painter')
    def onchange_expected_painter(self):
        if self.expected_painter:
            line_config = self.env['marketing.master.line'].sudo().search([('meeting_type','=',self.meeting_type.id)])
            if line_config:
                if line_config.attendees_no < self.expected_painter:
                    raise Warning(_("Number of attendees cannot be more than %s for %s" \
                        % (line_config.attendees_no, self.meeting_type.name)))

    @api.onchange('expected_food_cost')
    def onchange_expected_food_cost(self):
        if self.expected_food_cost:
            line_config = self.env['marketing.master.line'].sudo().search([('meeting_type','=',self.meeting_type.id)])
            if line_config:
                if line_config.snacks_dinner_budget < self.expected_food_cost:
                    raise Warning(_("Food Cost Per Person cannot be more than %s for %s" \
                        % (line_config.snacks_dinner_budget, self.meeting_type.name)))

    @api.onchange('expected_gift_cost')
    def onchange_expected_gift_cost(self):
        if self.expected_gift_cost:
            line_config = self.env['marketing.master.line'].sudo().search([('meeting_type','=',self.meeting_type.id)])
            if line_config:
                if line_config.gift_budget < self.expected_gift_cost:
                    raise Warning(_("Gift Cost Per Person cannot be more than %s for %s" \
                        % (line_config.gift_budget, self.meeting_type.name)))


    @api.multi
    def get_attached_docs(self):
        attendance_ids = self.env['meeting.attendance'].search([("meet_requisition_id","=",self.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('sales_meet.action_meeting_attendance')
        list_view_id = imd.xmlid_to_res_id('sales_meet.view_meeting_attendance_tree')
        form_view_id = imd.xmlid_to_res_id('sales_meet.view_meeting_attendance_form')
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
        if len(attendance_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % attendance_ids.ids
        elif len(attendance_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = attendance_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


    @api.multi
    def create_meet_attendance(self):

        # employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)]).id
        self.ensure_one()
        
        ctx = self._context.copy()
        attendance_ids = self.env['meeting.attendance'].search([('meet_requisition_id', '=', self.id)])
        if attendance_ids:
            result = self.get_attached_docs()
        if not attendance_ids:
            ctx.update({
                'search_default_meet_requisition_id': self.id,
                'default_meet_requisition_id': self.id,
                'default_meeting_date': self.meeting_date,
                'default_partner_id': self.partner_id.id,
                'default_lead_id': self.lead_id.id,
                'default_meeting_type': self.meeting_type.id,
                'default_location': self.location,
                'default_city': self.city,
                'default_state_id': self.state_id.id,
                'default_zone': self.zone,
                'default_manager_id': self.manager_id.id,
                'default_zsm_id': self.zsm_id.id,
                
            })
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('sales_meet.action_meeting_attendance')
            form_view_id = imd.xmlid_to_res_id('sales_meet.view_meeting_attendance_form')
            
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'target': 'current',
                
                'context': ctx,
                'res_model': action.res_model,
            }
        return result
    


    @api.multi
    def send_mail_to_approver(self):
        main_body  = """ """
        subject = ""
        main_id = self.id
        totalamount = 0.0
        email_from = self.user_id.email
        email_to = self.zsm_id.email

        config_mail = self.env['marketing.master'].search([("active","=",True)])
        email_cc1 =  config_mail.owner_id.email
        email_cc2 =  config_mail.handled_by_id.email
        email_cc3 =  self.manager_id.email
        email_cc_list = [email_cc1, email_cc2, email_cc3]
        email_cc =  ",".join(email_cc_list)

        todaydate = "{:%d-%b-%y}".format(datetime.now())
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
            <h3>The following meeting is scheduled on %s by %s and is requesting an approval from your end.</h3>

            <table>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Meeting Type</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Meeting Date</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Distributor</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Counter/Retailer</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Location</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">City</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">State</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Zone</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Manager</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">ZSM</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">No. Expected - Painter/Contractor</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Expected Food Cost - Per Person</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Expected Gift Cost - Per Person</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Total Cost - Per Person</td>
                        <td> : %s</td>
                    </tr>
                    <tr>
                        <th style=" text-align: left;padding: 8px;">Total Budget Required</td>
                        <td> : %s</td>
                    </tr>
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

        """ % (self.meeting_date, self.user_id.name , self.meeting_type.name, self.meeting_date, 
            self.partner_id.name, self.lead_id.name, self.location, self.city, self.state_id.name,
            self.zone, self.manager_id.name, self.zsm_id.name, self.expected_painter, self.expected_food_cost,
            self.expected_gift_cost, self.total_cost, self.total_advance_cost,
            approve_url, reject_url, report_check)


        subject = "Request for Retailer/Painter Meeting Approval ( %s )- ( %s )"  % (self.partner_id.name, todaydate)
        full_body = main_body

        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': main_id,
                'email_from': email_from,
                'email_to': email_to,
                'email_cc': email_cc,
                'subject': subject,
                'body_html': full_body,

            })

        composed_mail.send()


    @api.multi
    def send_mail_to_salesperson(self):
        main_body  = """ """
        check_request = """ """
        subject = ""
        status = ""
        main_id = self.id
        totalamount = 0.0
        email_to = self.user_id.email
        # config_mail = self.env['credit.note.config'].search([("id","!=",0)])
        # email_from =  config_mail.confirmation_mail
        email_from =  self.zsm_id.email
        todaydate = "{:%d-%b-%y}".format(datetime.now())
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_check = base_url + '/web#%s' % (url_encode({
                'model': self._name,
                'view_type': 'form',
                'id': main_id,
            }))

        if self.state == 'approved':
            status = 'approved'
            subject = "[Approved] Meeting to %s - ( %s )"  % (self.meeting_type.name, self.meeting_date)

            check_request = """ 
                <td>
                    <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px;
                        font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                        text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                        text-align: center; vertical-align: middle; cursor: pointer; white-space: nowrap;
                        background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                        margin-right: 10px;">Check Request</a>
                </td>
            """ % (report_check)

        else:
            status = 'refused'
            subject = "[Refused] Meeting to %s - ( %s )"  % (self.meeting_type.name, self.meeting_date)

        main_body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <p>Hi %s,</p>

            <br/>
            <p>The <b>%s</b> is %s. </p>

            <br/>

        """ % ( self.user_id.name , self.meeting_type.name,status)

        

        # You can Fill up the Meeting Attendance from the Meeting form itself 
        #     by clicking on the "Attendances" button.
        
        full_body = main_body + check_request
        composed_mail = self.env['mail.mail'].sudo().create({
                'model': self._name,
                'res_id': main_id,
                'email_from': email_from,
                'email_to': email_to,
                'subject': subject,
                'body_html': full_body,

            })

        composed_mail.send()