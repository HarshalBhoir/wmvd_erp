# -*- coding: utf-8 -*-
# © 2015-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
import logging
from openerp.tools import float_compare

from datetime import date

logger = logging.getLogger(__name__)


class HrHolidaysStatus(models.Model):
    _inherit = 'hr.holidays.status'

    vacation_compute_method = fields.Selection([
        ('worked', u'Open days'),
        ('business', u'Working days'),
        ], string='Vacation Compute Method', required=True,
        default='worked')
    add_validation_manager = fields.Boolean(
        string='Allocation validated by HR Manager',
        help="If enabled, allocation requests for this leave type "
        "can be validated only by an HR Manager "
        "(not possible by an HR Officer).")
    compensatory_days = fields.Boolean('CompOff')
    restrict_probation = fields.Boolean('Restrict for Probationary Employees', store=True, track_visibility='onchange')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    holiday_exclude_mass_allocation = fields.Boolean(
        string='Exclude from Mass Holiday Allocation')


class HrHolidays(models.Model):
    _inherit = 'hr.holidays'

    @api.multi
    def unlink(self):
        for leave in self:
            if leave.state in ['refuse','validate1','validate1']:
                raise UserError(_('You cannot delete a Confirmed/Refused Leave.'))
        super(HrHolidays, self).unlink()


    @api.onchange('employee_id')
    def _is_manager(self):

        for res in self:
            if res.type == 'add':
                if self.user_has_groups('hr_holidays.group_hr_holidays_manager'):
                    res.is_manager = True
                else:
                    holiday_type_ids = self.env['hr.holidays.status'].search([("name","=",'Compensatory Days')])
                    if holiday_type_ids:
                        res.holiday_status_id = holiday_type_ids.id

                    return {'domain': {
                    'holiday_status_id': [('compensatory_days', '=',True)], }}

            else:
                if res.employee_id.state == 'joined':
                    return {'domain': {
                        'holiday_status_id': [('restrict_probation', '=',False)], }}



    @api.model
    def _usability_compute_number_of_days(self):
        # depend on the holiday_status_id
        hhpo = self.env['hr.holidays.public']
        days = 0.0
        if (
                self.type == 'remove' and
                self.holiday_type == 'employee' and
                self.vacation_date_from and
                self.vacation_time_from and
                self.vacation_date_to and
                self.vacation_time_to and
                self.vacation_date_from <= self.vacation_date_to):
            if self.holiday_status_id.vacation_compute_method == 'business':
                business = True
            else:
                business = False
            date_dt = start_date_dt = fields.Date.from_string(
                self.vacation_date_from)
            end_date_dt = fields.Date.from_string(
                self.vacation_date_to)

            while True:
                # REGULAR COMPUTATION
                # if it's a bank holidays, don't count
                if hhpo.is_public_holiday(date_dt, self.employee_id.id):
                    logger.info(
                        "%s is a bank holiday, don't count", date_dt)
                # it it's a saturday/sunday
                elif date_dt.weekday() in (6,7):
                    logger.info(
                        "%s is a sunday, don't count", date_dt)
                else:
                    days += 1.0
                # special case for friday when compute_method = business
                if (
                        business and
                        date_dt.weekday() == 6 and
                        not hhpo.is_public_holiday(
                        date_dt + relativedelta(days=1),
                        self.employee_id.id)):
                    days += 1.0
                # PARTICULAR CASE OF THE FIRST DAY
                if date_dt == start_date_dt:
                    if self.vacation_time_from == 'noon':
                        if (
                                business and
                                date_dt.weekday() == 6 and
                                not hhpo.is_public_holiday(
                                date_dt + relativedelta(days=1),
                                self.employee_id.id)):
                            days -= 1.0  # result = 2 - 1 = 1
                        else:
                            days -= 0.5
                # PARTICULAR CASE OF THE LAST DAY
                if date_dt == end_date_dt:
                    if self.vacation_time_to == 'noon':
                        if (
                                business and
                                date_dt.weekday() == 6 and
                                not hhpo.is_public_holiday(
                                date_dt + relativedelta(days=1),
                                self.employee_id.id)):
                            days -= 1.5  # 2 - 1.5 = 0.5
                        else:
                            days -= 0.5
                    break
                date_dt += relativedelta(days=1)
        return days

    @api.depends('holiday_type', 'employee_id', 'holiday_status_id')
    def _compute_current_leaves(self):
        for holi in self:
            total_allocated_leaves = 0
            current_leaves_taken = 0
            current_remaining_leaves = 0
            if (
                    holi.holiday_type == 'employee' and
                    holi.employee_id and
                    holi.holiday_status_id):
                days = holi.holiday_status_id.get_days(holi.employee_id.id)
                total_allocated_leaves =\
                    days[holi.holiday_status_id.id]['max_leaves']
                current_leaves_taken =\
                    days[holi.holiday_status_id.id]['leaves_taken']
                current_remaining_leaves =\
                    days[holi.holiday_status_id.id]['remaining_leaves']
            holi.total_allocated_leaves = total_allocated_leaves
            holi.current_leaves_taken = current_leaves_taken
            holi.current_remaining_leaves = current_remaining_leaves

    @api.depends('payslip_date')
    def _compute_payslip_status(self):
        for holi in self:
            if holi.payslip_date:
                holi.payslip_status = True
            else:
                holi.payslip_status = False

    def _set_payslip_status(self):
        for holi in self:
            if holi.payslip_status:
                holi.payslip_date = fields.Date.context_today(self)
            else:
                holi.payslip_date = False

    vacation_date_from = fields.Date(
        string='First Day of Vacation', track_visibility='onchange',
        readonly=True, states={
            'draft': [('readonly', False)],
            'confirm': [('readonly', False)]},
        help="Enter the first day of vacation. For example, if "
        "you leave one full calendar week, the first day of vacation "
        "is Monday morning (and not Friday of the week before)")
    vacation_time_from = fields.Selection([
        ('morning', 'Morning'),
        ('noon', 'Noon'),
        ], string="Start of Vacation", track_visibility='onchange',
        default='morning', readonly=True, states={
            'draft': [('readonly', False)],
            'confirm': [('readonly', False)]},
        help="For example, if you leave one full calendar week, "
        "the first day of vacation is Monday Morning")
    vacation_date_to = fields.Date(
        string='Last Day of Vacation', track_visibility='onchange',
        readonly=True, states={
            'draft': [('readonly', False)],
            'confirm': [('readonly', False)]},
        help="Enter the last day of vacation. For example, if you "
        "leave one full calendar week, the last day of vacation is "
        "Friday evening (and not Monday of the week after)")
    vacation_time_to = fields.Selection([
        ('noon', 'Noon'),
        ('evening', 'Evening'),
        ], string="End of Vacation", track_visibility='onchange',
        default='evening', readonly=True, states={
            'draft': [('readonly', False)],
            'confirm': [('readonly', False)]},
        help="For example, if you leave one full calendar week, "
        "the end of vacation is Friday Evening")
    current_leaves_taken = fields.Float(
        compute='_compute_current_leaves', string='Current Leaves Taken',
        readonly=True)
    current_remaining_leaves = fields.Float(
        compute='_compute_current_leaves', string='Current Remaining Leaves',
        readonly=True)
    total_allocated_leaves = fields.Float(
        compute='_compute_current_leaves', string='Total Allocated Leaves',
        readonly=True)
    limit = fields.Boolean(  # pose des pbs de droits
        related='holiday_status_id.limit', string='Allow to Override Limit',
        readonly=True)
    payslip_date = fields.Date(
        string='Transfer to Payslip Date', track_visibility='onchange',
        readonly=True)
    # even with the new boolean field "payslip_status", I want to keep
    # the "posted_date" (renamed payslip_date) field, because I want structured
    # info. The main argument is that, if I don't write down the info at the end
    # of the wizard "Post Leave Requests", I want to easily
    # re-display the info
    payslip_status = fields.Boolean(
        readonly=True, compute='_compute_payslip_status',
        inverse='_set_payslip_status', store=True, track_visibility='onchange')
    number_of_days_temp = fields.Float(string="Number of days")
    # The 'name' field is displayed publicly in the calendar
    # So the label should not be 'Description' but 'Public Title'
    name = fields.Char(
        string='Public Title',
        help="Warning: this title is shown publicly in the "
        "calendar. Don't write private/personnal information in this field.")
    # by default, there is no company_id field on hr.holidays !
    company_id = fields.Many2one(
        related='employee_id.resource_id.company_id', store=True,
        readonly=True)
    state = fields.Selection(default='draft')  # hr_holidays, default='confirm'
    is_manager = fields.Boolean('Is Manager', store=True, track_visibility='onchange')
    mass_leave = fields.Boolean('Mass Leave', store=True, track_visibility='onchange')


    @api.constrains(
        'vacation_date_from', 'vacation_date_to', 'holiday_type', 'type')
    def _check_vacation_dates(self):
        hhpo = self.env['hr.holidays.public']
        for holi in self:
            if holi.type == 'remove':
                if holi.vacation_date_from > holi.vacation_date_to:
                    raise ValidationError(_(
                        'The first day cannot be after the last day !'))
                elif (
                        holi.vacation_date_from == holi.vacation_date_to and
                        holi.vacation_time_from == holi.vacation_time_to):
                    raise ValidationError(_(
                        "The start of vacation is exactly the "
                        "same as the end !"))
                date_from_dt = fields.Date.from_string(
                    holi.vacation_date_from)
                if date_from_dt.weekday() in (6,7):
                    raise ValidationError(_(
                        "The first day of vacation cannot be a "
                        "sunday !"))
                date_to_dt = fields.Date.from_string(
                    holi.vacation_date_to)
                if date_to_dt.weekday() in (6,7):
                    raise ValidationError(_(
                        "The last day of Vacation cannot be a "
                        "saturday or sunday !"))
                if hhpo.is_public_holiday(date_from_dt, holi.employee_id.id):
                    raise ValidationError(_(
                        "The first day of vacation cannot be a "
                        "bank holiday !"))
                if hhpo.is_public_holiday(date_to_dt, holi.employee_id.id):
                    raise ValidationError(_(
                        "The last day of vacation cannot be a "
                        "bank holiday !"))

    @api.onchange('vacation_date_from', 'vacation_time_from')
    def vacation_from(self):
        hour = 5  # = morning
        if self.vacation_time_from and self.vacation_time_from == 'noon':
            hour = 13  # noon, LOCAL TIME
            # Warning : when the vacation STARTs at Noon, it starts at 1 p.m.
            # to avoid an overlap (which would be blocked by a constraint of
            # hr_holidays) if a user requests 2 half-days with different
            # holiday types on the same day
        datetime_str = False
        if self.vacation_date_from:
            date_dt = fields.Date.from_string(self.vacation_date_from)
            if self._context.get('tz'):
                localtz = pytz.timezone(self._context['tz'])
            else:
                localtz = pytz.utc
            datetime_dt = localtz.localize(datetime(
                date_dt.year, date_dt.month, date_dt.day, hour, 0, 0))
            # we give to odoo a datetime in UTC
            datetime_str = fields.Datetime.to_string(
                datetime_dt.astimezone(pytz.utc))
        self.date_from = datetime_str

    @api.onchange('vacation_date_to', 'vacation_time_to')
    def vacation_to(self):
        hour = 22  # = evening
        if self.vacation_time_to and self.vacation_time_to == 'noon':
            hour = 12  # Noon, LOCAL TIME
            # Warning : when vacation STOPs at Noon, it stops at 12 a.m.
            # to avoid an overlap (which would be blocked by a constraint of
            # hr_holidays) if a user requests 2 half-days with different
            # holiday types on the same day
        datetime_str = False
        if self.vacation_date_to:
            date_dt = fields.Date.from_string(self.vacation_date_to)
            if self._context.get('tz'):
                localtz = pytz.timezone(self._context['tz'])
            else:
                localtz = pytz.utc
            datetime_dt = localtz.localize(datetime(
                date_dt.year, date_dt.month, date_dt.day, hour, 0, 0))
            # we give to odoo a datetime in UTC
            datetime_str = fields.Datetime.to_string(
                datetime_dt.astimezone(pytz.utc))
        self.date_to = datetime_str

    @api.onchange(
        'vacation_date_from', 'vacation_time_from', 'vacation_date_to',
        'vacation_time_to', 'number_of_days_temp', 'type', 'holiday_type',
        'holiday_status_id')
    def leave_number_of_days_change(self):
        if self.type == 'remove':
            days = self._usability_compute_number_of_days()
            self.number_of_days_temp = days

    # Neutralize the native on_change on dates
    def _onchange_date_from(self):
        return {}

    def _onchange_date_to(self):
        return {}

    # I want to set number_of_days_temp as readonly in the view of leaves
    # and, even in v8, we can't write on a readonly field
    # So I inherit write and create
    @api.model
    def create(self, vals):
        obj = super(HrHolidays, self).create(vals)
        if obj.type == 'remove':
            days = obj._usability_compute_number_of_days()
            obj.number_of_days_temp = days
        return obj

    @api.multi
    def write(self, vals):
        res = super(HrHolidays, self).write(vals)
        for obj in self:
            if obj.type == 'remove':
                days = obj._usability_compute_number_of_days()
                if days != obj.number_of_days_temp:
                    obj.number_of_days_temp = days
        return res

    @api.multi
    def action_confirm(self):
        for record in self:
            if not self._context.get('no_email_notification'):
                # template = self.env.ref(
                #     'hr_holidays_usability.email_template_hr_holidays')
                # template.with_context(
                #     dbname=self._cr.dbname,
                #     new_holiday_state='submitted').send_mail(holi.id)

                if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.work_email and record.type=='remove':
                    vals = {
                            'email_from': record.employee_id.work_email,
                            'email_to': record.employee_id.parent_id.work_email,
                            'email_cc': 'manisha.misal@walplast.com',
                            'subject': 'Leave Submitted: From {employee} , {description}'
                                        .format(employee=record.employee_id.name, description=record.name),
                            'body_html': """
                                        <p>
                                            Hello Mr {manager},
                                        </p>
                                        <p>
                                            The following leave request has been submitted today in iPortal by {employee}
                                        </p>


                                        <ul>
                                        <li>Public title : {holiday_name}</li>
                                        <li>Employee : {employee}</li>
                                        <li>Employee's manager : {manager}</li>
                                        <li>Leave type : {leave_type}</li>
                                        <li>Start date : {vacation_date_from},  {vacation_time_from}</li>
                                        <li>End date : {vacation_date_from}  {vacation_time_from}</li>
                                        <li>Number of days : {number_of_days}</li>
                                        <li>Notes for the manager : {notes}</li>
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

                                    """.format(employee=record.employee_id.name, manager=record.employee_id.parent_id.name, leave=record.display_name, 
                                        model=record._name, id=record.id, type=record.type, vacation_date_from=record.vacation_date_from, 
                                        vacation_date_to=record.vacation_date_to, vacation_time_from=record.vacation_time_from, 
                                        vacation_time_to=record.vacation_time_to, number_of_days=abs(record.number_of_days), holiday_name=record.name, 
                                        notes=record.notes, leave_type=record.holiday_status_id.name)}

                if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.work_email and record.type=='add':
                    vals = {
                            'email_from': record.employee_id.work_email,
                            'email_to': record.employee_id.parent_id.work_email,
                            'email_cc': 'manisha.misal@walplast.com',
                            'subject': 'Leave Allocation Submitted: From {employee} , {description}'
                                        .format(employee=record.employee_id.name, description=record.name),
                            'body_html': """
                                        <p>
                                            Hello Mr {manager},
                                        </p>
                                        <p>
                                            The following leave allocation request has been submitted today in iPortal by {employee}
                                        </p>


                                        <ul>
                                        <li>Public title : {holiday_name}</li>
                                        <li>Employee : {employee}</li>
                                        <li>Employee's manager : {manager}</li>
                                        <li>Leave type : <b>{leave_type}  </b></li>
                                        <li>Start date : {vacation_date_from},  {vacation_time_from}</li>
                                        <li>End date : {vacation_date_from}  {vacation_time_from}</li>
                                        <li>Number of days : {number_of_days}</li>
                                        <li>Notes for the manager : {notes}</li>
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

                                    """.format(employee=record.employee_id.name, manager=record.employee_id.parent_id.name, leave=record.display_name, 
                                        model=record._name, id=record.id, type=record.type, vacation_date_from=record.vacation_date_from, 
                                        vacation_date_to=record.vacation_date_to, vacation_time_from=record.vacation_time_from, 
                                        vacation_time_to=record.vacation_time_to, number_of_days=abs(record.number_of_days), holiday_name=record.name, 
                                        notes=record.notes, leave_type=record.holiday_status_id.name)}
                mail = self.env['mail.mail'].sudo().create(vals)
                mail.send()
        return super(HrHolidays, self).action_confirm()

    @api.multi
    def action_validate(self):
        for holi in self:
            if holi.user_id == self.env.user:
                if holi.type == 'remove':
                    raise UserError(_(
                        "You cannot validate your own Leave request '%s'.")
                        % holi.name)
                elif (
                        holi.type == 'add' and
                        not self.env.user.has_group(
                            'hr_holidays.group_hr_holidays_manager')):
                    raise UserError(_(
                        "You cannot validate your own Allocation "
                        "request '%s'.") % holi.name)
            if (
                    holi.type == 'add' and
                    holi.holiday_status_id.add_validation_manager and
                    not self.env.user.has_group(
                        'hr_holidays.group_hr_holidays_manager')):
                raise UserError(_(
                    "Allocation request '%s' has a leave type '%s' that "
                    "can be approved only by an HR Manager.")
                    % (holi.name, holi.holiday_status_id.name))
            # if not self._context.get('no_email_notification'):
            #     if holi.employee_id and holi.employee_id.parent_id and holi.employee_id.parent_id.work_email:
            #         vals = {
            #                 'email_from': holi.employee_id.parent_id.work_email,
            #                 'email_to': holi.employee_id.work_email,
            #                 'email_cc': 'manisha.misal@walplast.com',
            #                 'subject': 'Leave Approval: From {manager} , {description}'
            #                             .format(manager=holi.employee_id.parent_id.name, description=holi.name),
            #                 'body_html': """
            #                             <p>
            #                                 Hello Mr {employee},
            #                             </p>
            #                             <p>
            #                                 The following leave request has been approved today in iPortal by {manager}
            #                             </p>


            #                             <ul>
            #                             <li>Public title : {holiday_name}</li>
            #                             <li>Employee : {employee}</li>
            #                             <li>Employee's manager : {manager}</li>
            #                             <li>Leave type : {leave_type}</li>
            #                             <li>Start date : {vacation_date_from},  {vacation_time_from}</li>
            #                             <li>End date : {vacation_date_from}  {vacation_time_from}</li>
            #                             <li>Number of days : {number_of_days}</li>
            #                             <li>Notes for the manager : {notes}</li>
            #                             </ul>

            #                             <p></p>
                                        
            #                             <p>
            #                                 <a href="http://192.168.1.145:3300/mail/view?model={model}&amp;res_id={id}"
            #                                         style="background-color: #9E588B; margin-top: 10px; padding: 10px; text-decoration: none; color: #fff; border-radius: 5px; font-size: 16px;">
            #                                     <u>View Leave</u> <t t-esc="object._description.lower()"/>
            #                                 </a>
            #                             </p>
            #                             <p></p>
            #                             <p></p>

            #                             <p>
            #                                 Thank You.
            #                             </p>

            #                         """.format(employee=holi.employee_id.name, manager=holi.employee_id.parent_id.name, leave=holi.display_name, 
            #                             model=holi._name, id=holi.id, type=holi.type, vacation_date_from=holi.vacation_date_from, 
            #                             vacation_date_to=holi.vacation_date_to, vacation_time_from=holi.vacation_time_from, 
            #                             vacation_time_to=holi.vacation_time_to, number_of_days=abs(holi.number_of_days), holiday_name=holi.name, 
            #                             notes=holi.notes, leave_type=holi.holiday_status_id.name)}
            #     mail = self.env['mail.mail'].sudo().create(vals)
            #     mail.send()
                # template = self.env.ref(
                #     'hr_holidays_usability.email_template_hr_holidays')
                # template.with_context(
                #     dbname=self._cr.dbname,
                #     new_holiday_state='validated').send_mail(holi.id)
        return super(HrHolidays, self).action_validate()

    @api.multi
    def action_refuse(self):
        for holi in self:
            if (
                    holi.user_id == self.env.user and
                    not self.env.user.has_group(
                        'hr_holidays.group_hr_holidays_manager')):
                raise UserError(_(
                    "You cannot refuse your own Leave or Allocation "
                    "holiday request '%s'.")
                    % holi.name)
            if not self._context.get('no_email_notification') and holi.state=='confirm':
            #     template = self.env.ref(
            #         'hr_holidays_usability.email_template_hr_holidays')
            #     template.with_context(
            #         dbname=self._cr.dbname,
            #         new_holiday_state='refused').send_mail(holi.id)

                if holi.employee_id and holi.employee_id.parent_id and holi.employee_id.parent_id.work_email:
                    vals = {
                            'email_from': holi.employee_id.parent_id.work_email,
                            'email_to': holi.employee_id.work_email,
                            'email_cc': 'manisha.misal@walplast.com',
                            'subject': 'Leave Refusal: From {manager} , {description}'
                                        .format(manager=holi.employee_id.parent_id.name, description=holi.name),
                            'body_html': """
                                        <p>
                                            Hello Mr {employee},
                                        </p>
                                        <p>
                                            The following leave request has been Refused today in iPortal by {manager}
                                        </p>


                                        <ul>
                                        <li>Public title : {holiday_name}</li>
                                        <li>Employee : {employee}</li>
                                        <li>Employee's manager : {manager}</li>
                                        <li>Leave type : {leave_type}</li>
                                        <li>Start date : {vacation_date_from},  {vacation_time_from}</li>
                                        <li>End date : {vacation_date_from}  {vacation_time_from}</li>
                                        <li>Number of days : {number_of_days}</li>
                                        <li>Notes for the manager : {notes}</li>
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

                                    """.format(employee=holi.employee_id.name, manager=holi.employee_id.parent_id.name, leave=holi.display_name, 
                                        model=holi._name, id=holi.id, type=holi.type, vacation_date_from=holi.vacation_date_from, 
                                        vacation_date_to=holi.vacation_date_to, vacation_time_from=holi.vacation_time_from, 
                                        vacation_time_to=holi.vacation_time_to, number_of_days=abs(holi.number_of_days), holiday_name=holi.name, 
                                        notes=holi.notes, leave_type=holi.holiday_status_id.name)}
                mail = self.env['mail.mail'].sudo().create(vals)
                mail.send()
        return super(HrHolidays, self).action_refuse()


class ResCompany(models.Model):
    _inherit = 'res.company'

    mass_allocation_default_holiday_status_id = fields.Many2one(
        'hr.holidays.status', string='Default Leave Type for Mass Allocation')


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    mass_allocation_default_holiday_status_id = fields.Many2one(
        related='company_id.mass_allocation_default_holiday_status_id')


class HrPublicHolidays(models.Model):
    _name = 'hr.holidays.public'
    _description = 'Public Holidays'
    _rec_name = 'year'
    _order = "year"

    display_name = fields.Char(
        "Name",
        compute="_compute_display_name",
        readonly=True,
        store=True
    )
    year = fields.Integer(
        "Calendar Year",
        required=True,
        default=date.today().year
    )
    line_ids = fields.One2many(
        'hr.holidays.public.line',
        'year_id',
        'Holiday Dates'
    )
    country_id = fields.Many2one(
        'res.country',
        'Country'
    )

    @api.multi
    @api.constrains('year', 'country_id')
    def _check_year(self):
        for r in self:
            r._check_year_one()

    def _check_year_one(self):
        if self.country_id:
            domain = [('year', '=', self.year),
                      ('country_id', '=', self.country_id.id),
                      ('id', '!=', self.id)]
        else:
            domain = [('year', '=', self.year),
                      ('country_id', '=', False),
                      ('id', '!=', self.id)]
        if self.search_count(domain):
            raise UserError(_('You can\'t create duplicate public holiday '
                              'per year and/or country'))
        return True

    @api.multi
    @api.depends('year', 'country_id')
    def _compute_display_name(self):
        for r in self:
            if r.country_id:
                r.display_name = '%s (%s)' % (r.year, r.country_id.name)
            else:
                r.display_name = r.year

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, rec.display_name))
        return result

    @api.model
    @api.returns('hr.holidays.public.line')
    def get_holidays_list(self, year, employee_id=None):
        """
        Returns recordset of hr.holidays.public.line
        for the specified year and employee
        :param year: year as string
        :param employee_id: ID of the employee
        :return: recordset of hr.holidays.public.line
        """
        holidays_filter = [('year', '=', year)]
        employee = False
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            if employee.address_id and employee.address_id.country_id:
                holidays_filter.append((
                    'country_id',
                    'in',
                    [False, employee.address_id.country_id.id]))

        pholidays = self.search(holidays_filter)
        if not pholidays:
            return list()

        states_filter = [('year_id', 'in', pholidays.ids)]
        if employee and employee.address_id and employee.address_id.state_id:
            states_filter += ['|',
                              ('state_ids', '=', False),
                              ('state_ids', '=',
                               employee.address_id.state_id.id)]
        else:
            states_filter.append(('state_ids', '=', False))

        hhplo = self.env['hr.holidays.public.line']
        holidays_lines = hhplo.search(states_filter)
        return holidays_lines

    @api.model
    def is_public_holiday(self, selected_date, employee_id=None):
        """
        Returns True if selected_date is a public holiday for the employee
        :param selected_date: datetime object or string
        :param employee_id: ID of the employee
        :return: bool
        """
        if isinstance(selected_date, basestring):
            selected_date = fields.Date.from_string(selected_date)
        holidays_lines = self.get_holidays_list(
            selected_date.year, employee_id=employee_id)
        if holidays_lines and len(holidays_lines.filtered(
                lambda r: r.date == fields.Date.to_string(selected_date))):
            return True
        return False
