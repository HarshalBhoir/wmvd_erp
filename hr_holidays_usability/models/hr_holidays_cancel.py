# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Holidays(models.Model):

    _name = "hr.holidays.cancel"
    _description = "Leave Cancellation"
    # _order = "type desc, date_from desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char('Description')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate', 'Approved')
    ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help="The status is set to 'To Submit', when a holiday cancel request is created." +
             "\nThe status is 'To Approve', when holiday cancel request is confirmed by user." +
             "\nThe status is 'Refused', when holiday request cancel is refused by manager." +
             "\nThe status is 'Approved', when holiday request cancel is approved by manager.")
    report_note = fields.Text('HR Comments')
    holiday = fields.Many2one("hr.holidays", string="Leaves", required=True, domain="[('state', '=', 'validate'),('mass_leave', '=', False)]")
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True, readonly=True,
                                  states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
                                  default=_default_employee)

    vacation_date_from = fields.Date(string='First Day of Vacation', track_visibility='onchange',compute='_compute_leave_data',)
    vacation_date_to = fields.Date(string='Last Day of Vacation', track_visibility='onchange',compute='_compute_leave_data',)
    number_of_days_temp = fields.Float(string="Number of days" , compute='_compute_leave_data',)
    leave_name = fields.Char('Description', compute='_compute_leave_data',)
    leave_type = fields.Char('Leave Type', compute='_compute_leave_data',)


    @api.depends('holiday')
    def _compute_leave_data(self):
        for holi in self:
            holi.vacation_date_from = holi.holiday.vacation_date_from
            holi.vacation_date_to = holi.holiday.vacation_date_to
            holi.number_of_days_temp = holi.holiday.number_of_days_temp
            holi.leave_name = holi.holiday.name
            holi.leave_type = holi.holiday.holiday_status_id.name

    @api.multi
    def action_approve(self):
        for record in self:
            record.holiday.action_refuse()
            if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.work_email:
                vals = {
                        'email_from': record.employee_id.parent_id.work_email,
                        'email_to': record.employee_id.work_email,
                        'email_cc': 'manisha.misal@walplast.com',
                        'subject': 'Leave Cancel Approval: From {manager} , {description}'
                                    .format(manager=record.employee_id.parent_id.name, description=record.name),
                        'body_html': """
                                    <p>
                                        Hello Mr {employee},
                                    </p>
                                    <p>
                                        The following leave request has been approved today in iPortal by {manager} : {leave}
                                    </p>
                                    <ul>
                                    <li>Public title : {holiday_name}</li>
                                    <li>Employee : {employee}</li>
                                    <li>Employee's manager : {manager}</li>
                                    <li>Start date : {vacation_date_from},  {vacation_time_from}</li>
                                    <li>End date : {vacation_date_from}  {vacation_time_from}</li>
                                    <li>Number of days : {number_of_days}</li>
                                    </ul>

                                    <p></p>
                                    
                                    <p>
                                        <a href="http://192.168.1.145:3300/mail/view?model={model}&amp;res_id={id}"
                                                style="background-color: #9E588B; margin-top: 10px; padding: 10px; text-decoration: none; color: #fff; border-radius: 5px; font-size: 16px;">
                                            <u>View Leave</u> <t t-esc="object._description.lower()"/>
                                        </a>
                                    </p>
                                    <p></p>

                                    <p>
                                        Thank You.
                                    </p>
                                """.format(employee=record.employee_id.name, manager=record.employee_id.parent_id.name, leave=record.holiday.display_name, 
                                    model=record._name, id=record.id, type=record.holiday.type, vacation_date_from=record.holiday.vacation_date_from, 
                                    vacation_date_to=record.holiday.vacation_date_to, vacation_time_from=record.holiday.vacation_time_from, 
                                    vacation_time_to=record.holiday.vacation_time_to, number_of_days=abs(record.holiday.number_of_days), holiday_name=record.holiday.name)}
                mail = self.env['mail.mail'].sudo().create(vals)
                mail.send()
            record.write({'state': 'validate'})

    @api.multi
    def action_refuse(self):
        for record in self:
            if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.work_email:
                vals = {
                        'email_to': record.employee_id.work_email,
                        'email_cc': 'manisha.misal@walplast.com',
                        'subject': 'Leave Cancel Refusal: From {manager} , {description}'
                                    .format(manager=record.employee_id.parent_id.name, description=record.name),
                        'body_html': """
                                    <p>
                                        Hello Mr {employee},
                                    </p>
                                    <p>
                                        The following leave request has been refused today in iPortal by {manager} : {leave}
                                    </p>
                                    <ul>
                                    <li>Public title : {holiday_name}</li>
                                    <li>Employee : {employee}</li>
                                    <li>Employee's manager : {manager}</li>
                                    <li>Start date : {vacation_date_from},  {vacation_time_from}</li>
                                    <li>End date : {vacation_date_from}  {vacation_time_from}</li>
                                    <li>Number of days : {number_of_days}</li>
                                    </ul>

                                    <p></p>
                                    
                                    <p>
                                        <a href="http://192.168.1.145:3300/mail/view?model={model}&amp;res_id={id}"
                                                style="background-color: #9E588B; margin-top: 10px; padding: 10px; text-decoration: none; color: #fff; border-radius: 5px; font-size: 16px;">
                                            <u>View Leave</u> <t t-esc="object._description.lower()"/>
                                        </a>
                                    </p>
                                    <p></p>

                                    <p>
                                        Thank You.
                                    </p>
                                """.format(employee=record.employee_id.name, manager=record.employee_id.parent_id.name, leave=record.holiday.display_name, 
                                    model=record._name, id=record.id, type=record.holiday.type, vacation_date_from=record.holiday.vacation_date_from, 
                                    vacation_date_to=record.holiday.vacation_date_to, vacation_time_from=record.holiday.vacation_time_from, 
                                    vacation_time_to=record.holiday.vacation_time_to, number_of_days=abs(record.holiday.number_of_days), holiday_name=record.holiday.name)}
                mail = self.env['mail.mail'].sudo().create(vals)
                mail.send()
            record.write({'state': 'refuse'})

    @api.multi
    def action_confirm(self):
        for record in self:
            if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.work_email:
                vals = {
                        'email_from': record.employee_id.work_email,
                        'email_to': record.employee_id.parent_id.work_email,
                        'email_cc': 'manisha.misal@walplast.com',
                        'subject': 'Leave Cancel Request: From {employee} , {description}'
                                    .format(employee=record.employee_id.name, description=record.name),
                        'body_html': """
                                    <p>
                                        Hello Mr {manager},
                                    </p>
                                    <p>
                                        There is a leave cancellation request on an approved leave {leave}
                                    </p>

                                    <ul>
                                    <li>Public title : {holiday_name}</li>
                                    <li>Employee : {employee}</li>
                                    <li>Employee's manager : {manager}</li>
                                    <li>Start date : {vacation_date_from},  {vacation_time_from}</li>
                                    <li>End date : {vacation_date_from}  {vacation_time_from}</li>
                                    <li>Number of days : {number_of_days}</li>
                                    </ul>

                                    <p></p>
                                    
                                    <p>
                                        <a href="http://192.168.1.145:3300/mail/view?model={model}&amp;res_id={id}"
                                                style="background-color: #9E588B; margin-top: 10px; padding: 10px; text-decoration: none; color: #fff; border-radius: 5px; font-size: 16px;">
                                            <u>View Leave</u> <t t-esc="object._description.lower()"/>
                                        </a>
                                    </p>
                                    <p></p>
                                    <p></p>

                                    <p>
                                        Thank You.
                                    </p>

                                """.format(employee=record.employee_id.name, manager=record.employee_id.parent_id.name, leave=record.holiday.display_name, 
                                    model=record._name, id=record.id, type=record.holiday.type, vacation_date_from=record.holiday.vacation_date_from, 
                                    vacation_date_to=record.holiday.vacation_date_to, vacation_time_from=record.holiday.vacation_time_from, 
                                    vacation_time_to=record.holiday.vacation_time_to, number_of_days=abs(record.holiday.number_of_days), holiday_name=record.holiday.name)}
                mail = self.env['mail.mail'].sudo().create(vals)
                mail.send()
            record.write({'state': 'confirm'})
