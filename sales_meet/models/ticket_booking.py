# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError , ValidationError
from odoo.tools.translate import _
from datetime import datetime, timedelta, date
import dateutil.parser
from werkzeug import url_encode
import time


class ticket_booking(models.Model):
    """ Class to define various channels using which letters can be sent or
    received like : post, fax, email. """
    _name = 'ticket.booking'
    _description = "Ticket Booking"
    _order  = 'id desc'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.model
    def default_get(self, fields_list):
        res = super(ticket_booking, self).default_get(fields_list)

        if res['employee_id']:
            employee_id = self.env['hr.employee'].sudo().search([('id', '=', res['employee_id'])])
            res['manager_id'] = employee_id.parent_id.id or ''
            res['mobile'] = employee_id.mobile_phone if employee_id.mobile_phone else employee_id.work_phone or ''
            res['grade_id'] = employee_id.grade_id.id or ''
            res['age'] = employee_id.age or ''
            res['company_id'] = employee_id.company_id.id or ''
        return res


    @api.multi
    def _compute_can_edit_name(self):
        self.can_edit_name = self.env.user.has_group('sales_meet.group_lettermgmt_manager')
        print "1111111111111111111111111111111111111111 _compute_can_edit_name"


    name =  fields.Char('Number')
    booking_date =fields.Date('Booking Date')
    return_booking_date =fields.Date('Return Booking Date')
    from_date =fields.Datetime('From Date')
    return_date =fields.Datetime('Return Date', track_visibility='onchange')
    from_location =  fields.Char('From Location')
    to_location =  fields.Char('To Location')
    train_number =  fields.Char('Train/Bus/Flight No')
    seat_berth =  fields.Char('Seat/Berth')
    return_train_number =  fields.Char('Return Train/Bus/Flight No')
    return_seat_berth =  fields.Char('Return Seat/Berth')
    employee_id = fields.Many2one('hr.employee', string='Employee', 
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))
    age =  fields.Char('Age')
    grade_id = fields.Many2one("grade.master", 'Grade' , store=True, track_visibility='onchange' )
    amount =  fields.Float('Amount', track_visibility='onchange')
    return_amount =  fields.Float('Return Journey Amount', track_visibility='onchange')
    pnr_start =  fields.Char('PNR (Start)')
    pnr_return =  fields.Char('PNR (Return)')
    manager_id = fields.Many2one('hr.employee', string='Approval' ,  track_visibility='onchange')
    state = fields.Selection([('draft', 'Draft'),
        ('created', 'Submitted'), 
        ('approved', 'Approved'), 
        ('booked', 'Booked'), 
        ('cancel', 'Cancelled')], 'Status',default='draft')
    company_id = fields.Many2one('res.company', string='Company', store=True)
    description = fields.Text('Description', help="Description ........")
    transport_mode = fields.Selection([
        ('road', 'By Road') ,
        ('rail', 'By Railway'), 
        ('flight', 'By Flight')], 'Mode Of Transport')
    booking_type = fields.Selection([('travel', 'Travel') ,('hotel', 'Hotel')], 'Booking Type')

    product_id = fields.Many2one('product.product', string='Product', domain=[('can_be_expensed', '=', True)])
    today_date =fields.Date('Date')
    reason = fields.Text('Reject Reason' )
    mobile =  fields.Char('Mobile')

    hotel_name = fields.Char('Hotel')
    address = fields.Char('Hotel Address')
    hotel_contact_no = fields.Char('Hotel Contact No')
    checkin = fields.Datetime('Check IN')
    checkout = fields.Datetime('Check OUT')
    return_travel = fields.Boolean('Return Travel')
    booking_description = fields.Text('Booking Description')

    can_edit_name = fields.Boolean(compute='_compute_can_edit_name')

    booking_reason = fields.Selection([
                    ('clm', 'Client Meeting'),
                    ('pe', 'Plant Emergency'), 
                    ('cbs', 'Critical Business Support'), 
                    ('other', 'Any Other (need to be mentioned)')], 'Booking reason')


    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft' and self.env.uid != 1:
                raise UserError(_('You can only delete Draft Entries'))
        return super(ticket_booking, self).unlink()


    @api.multi
    def action_booking_reason(self):
        booking_reason = ''
        if self.booking_reason == 'clm':
            booking_reason = 'Client Meeting'
        elif self.booking_reason == 'pe':
            booking_reason = 'Plant Emergency'
        elif self.booking_reason == 'cbs':
            booking_reason = 'Critical Business Support'
        elif self.booking_reason == 'other':
            booking_reason = 'Any Other (need to be mentioned)'
        return booking_reason



    @api.multi
    def action_validate(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''

        if self.booking_date:
            self.state ='booked'
        
        else:
            raise ValidationError(_('Kindly Fill Booking Details First'))

        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('sales_meet', 'email_template_booking_user')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'ticket.booking',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "sales_meet.mail_template_data_notification_email_wp_ticket_booking"
        })
        
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


    @api.multi
    def refuse_ticket_booking(self,reason=False):

        print "ffffffffffffffffffffff" , reason , self.reason
        if reason and not self.reason and self.env.uid == 1:
            self.write({'state': 'cancel','reason': reason})
        elif not self.reason and self.env.uid != 1:
            raise ValidationError(_('Update the Rejection reason below'))
        else:
            self.write({'state': 'cancel','reason': self.reason})

        time.sleep(1)
            
        self.send_rejected_mail()

    @api.multi
    def approve_ticket_booking_manager(self):
        frontdesk_manager = self.env.user.has_group('sales_meet.group_lettermgmt_manager')
        if str(self.manager_id.work_email) == str(self.env.user.login) or frontdesk_manager or self.env.uid == 1:
            # self.sudo().write({'state': 'manager_approve', 'responsible_id': self.env.user.id, 'approve_date':date.today()})
            self.write({'state': 'approved'})
            self.send_approved_mail()
        else:
            raise UserError("Only %s 's manager (%s) or \
                Admin can approve his Request" %(self.employee_id.name,self.employee_id.parent_id.name))


    @api.multi
    def resubmit(self):
        self.write({'state': 'draft'})


    @api.onchange('transport_mode')
    def _onchange_transport_mode(self):
        if self.transport_mode:
            product_id = self.env['product.product'].search([('transport_mode', '=', self.transport_mode)])
            if product_id:
                self.product_id = product_id[0].id
            for line_ids in self.grade_id.grade_line_ids:
                for lines in line_ids:
                    if lines.name.id == self.product_id.id:
                        self.amount = lines.value


    @api.multi
    def action_dates(self):
        fromdate = todate = ''
        fromdate2 = (self.from_date.split(' '))[0]
        daymonth = datetime.strptime(fromdate2, "%Y-%m-%d")
        fromdate = "{:%d %b %y}".format(daymonth)

        if self.return_date:

            todate2 = (self.return_date.split(' '))[0]
            todaymonth2 = datetime.strptime(todate2, "%Y-%m-%d")
            todate = "{:%d %b %y}".format(todaymonth2)

        return fromdate , todate

    @api.multi
    def action_booking_type(self):
        booking_type = ''
        if self.booking_type == 'travel':
            booking_type = 'Travel'
        elif self.booking_type == 'hotel':
            booking_type = 'Hotel'
        return booking_type


    @api.multi
    def action_transport_mode(self):
        transport_mode = ''
        if self.transport_mode == 'road':
            transport_mode = 'By Road'
        elif self.transport_mode == 'rail':
            transport_mode = 'By Railway'
        elif self.transport_mode == 'flight':
            transport_mode = 'By Flight'
        return transport_mode


    @api.multi
    def action_submit(self):
        
        name = self.env['ir.sequence'].sudo().next_by_code('ticket.booking3') or '/'
        fromdate = self.action_dates()[0]
        transport_mode = self.action_transport_mode()

        self.name = ( 'Hotel Booking '  if self.booking_type == 'hotel' \
            else ('Travel ' + transport_mode ) ) + '(' + fromdate + ')' + name
        self.state = 'created'
        self.send_user_mail()


    @api.multi
    def send_user_mail(self):
        body = """ """
        subject = ""
        recepients=[]

        transport_mode = self.action_transport_mode()
        fromdate = self.action_dates()[0]
        todate = self.action_dates()[1]

        email_from = self.env.user.email
        recepients.append(self.manager_id)
        managers = list(set([x.work_email for x in recepients if x.work_email]))
        email_to = ",".join(managers)

        upper_body = """
                <style type="text/css">
                * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
                </style>

                <h3>Hello %s,</h3>
                <h4> I have raised my %s request in the portal, kindly have a look & approve. </h4>

            """ % (self.manager_id.name,self.action_booking_type())


        if self.booking_type == 'hotel':
            body = """
                <table>
                  <tr><th style=" text-align: left;padding: 8px;">Booking Reason</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">From Date</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">Return Date</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">To Location</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">Description</td><td> : %s</td></tr>
                </table>

        """ % (self.action_booking_reason(),fromdate, todate, self.to_location, self.description)


        if self.booking_type == 'travel':
            body = """
                <table>
                  <tr><th style=" text-align: left;padding: 8px;">Booking Reason</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">From Date</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">Return Date</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">From Location</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">To Location</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">Mode Of Transport</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">Description</td><td> : %s</td></tr>
                </table>

            """ % (self.action_booking_reason(),fromdate  or '', todate or '', self.from_location  or '', \
                self.to_location  or '', transport_mode  or '', self.description or '')

        subject = "Approval for %s booking of %s - ( %s )"  % (self.action_booking_type(),self.employee_id.name,fromdate)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
      
        approve_url = base_url + '/booking?%s' % (url_encode({
                'model': self._name,
                'booking_id': self.id,
                'res_id': self.id,
                'action': 'approve_ticket_booking_manager',
            }))
        reject_url = base_url + '/booking?%s' % (url_encode({
                'model': self._name,
                'booking_id': self.id,
                'res_id': self.id,
                'action': 'refuse_ticket_booking',
            }))

        report_check = base_url + '/web#%s' % (url_encode({
            'model': self._name,
            'view_type': 'form',
            'id': self.id,
        }))

        full_body = upper_body + body + """<br/>
        <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
            <tbody>
                <tr class="text-center">
                    <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Approve</a>
                        </td>
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Reject</a>
                        </td>

                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; 
                                font-size: 12px; line-height: 18px; color: #FFFFFF; border-color:#337ab7; 
                                text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400;
                                text-align: center; vertical-align: middle; cursor: pointer; 
                                white-space: nowrap; background-image: none; background-color: #337ab7; 
                                border: 1px solid #337ab7; margin-right: 10px;">Check Request</a>
                        </td>

                </tr>
            </tbody>
        </table>
        """ % (approve_url, reject_url, report_check)

        self.send_generic_mail(subject, full_body, email_from, email_to)


    @api.multi
    def send_approved_mail(self):
        tech_user = []
        fromdate, todate = self.from_date, self.return_date
        transport_mode = self.action_transport_mode()

        for user in self.env['res.users'].sudo().search([('active','=',True)]):
            if user.has_group('sales_meet.group_lettermgmt_manager') :
                tech_user.append(user)
        tech_partners = list(set([x.login for x in tech_user if x.login]))
        email_to = ",".join(tech_partners)
        email_from = self.env.user.email

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
      

        url_link = base_url + '/web#%s' % (url_encode({
            'model': 'ticket.booking',
            'view_type': 'form',
            'id': self.id,
        }))

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>

            <h3>Hello Team,</h3>
            <h4> This email is regarding Travel Booking by %s.
            I have approved the request in the portal, kindly proceed. </h4>

            <h3>Following are the details as below listed. </h3>

                <table>
                  <tr><th style=" text-align: left;padding: 8px;">From Date</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">Return Date</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">From Location</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">To Location</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">Mode Of Transport</td><td> : %s</td></tr>
                  <tr><th style=" text-align: left;padding: 8px;">Description</td><td> : %s</td></tr>
                </table>

                <br/><br/>

                <b>Click here  :</b> <a href="%s"
                style="background-color: #337ab7; margin-top: 10px; padding: 10px; text-decoration: none;
                 color: #fff; border-radius: 5px; font-size: 16px;">
                View Request<t t-esc="object._description.lower()"/>
                </a> 

                <br/><br/><br/><br/>

        """ % (self.employee_id.name, fromdate or '', todate or '', self.from_location or '',
         self.to_location or '', transport_mode or '', self.description or '',url_link)

        subject = "[Approved] %s booking of %s - ( %s )"  % (self.action_booking_type(),self.employee_id.name,fromdate)
        full_body = body

        self.send_generic_mail(subject, full_body, email_from, email_to)


    @api.multi
    def send_rejected_mail(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        url_link = base_url + '/web#%s' % (url_encode({
            'model': self._name,
            'view_type': 'form',
            'id': self.id,
        }))

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>

            <h3>Hello %s,</h3>
            <h4> Your Request for %s has been rejected. </h4>

            <h3>The reason is: </h3>
                <ul>
                    <li>Reason    &nbsp;&nbsp;  : <span>%s</span></li>
                </ul>
                <br/><br/>

                <b>Click here  :</b> <a href="%s"
                style="background-color: #337ab7; margin-top: 10px; padding: 10px; text-decoration: none; 
                color: #fff; border-radius: 5px; font-size: 16px;">
                View Request<t t-esc="object._description.lower()"/>
                </a> 

                <br/><br/><br/><br/>

        """ % (self.employee_id.name, self.name, self.reason or '' ,url_link)

        subject = "[Rejected] %s Booking of %s"  % (self.action_booking_type(),self.employee_id.name) 
        full_body = body
        email_from = 'admin@walplast.com'
        email_to = self.employee_id.work_email

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
