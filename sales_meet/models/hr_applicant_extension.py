# -*- coding: utf-8 -*-
# Author: Denis Leemann
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, tools, _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import SUPERUSER_ID
from time import gmtime, strftime
from odoo.exceptions import UserError , ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT

class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    same_candidate_application_ids = fields.Many2many(
        'hr.applicant',
        string='Same candidates',
        compute='_compute_same_candidate_application_count',
        readonly=True,
    )
    same_candidate_application_count = fields.Integer(
        'Number of similar candidates',
        compute='_compute_same_candidate_application_count',
        readonly=True,
    )

    location = fields.Char(string='Location')
    requisition_date = fields.Date('Requisition Date')
    allocation_date = fields.Date('Allocation Date')
    requisition_aeging = fields.Char(string='Requisition Aeging to till date', compute='_requisition_aeging', readonly=True)
    allocation_aeging = fields.Char(string='Allocation Aeging to till date', compute='_allocation_aeging', readonly=True)
    domain = fields.Selection([
        ('Plant', 'Plant'),
        ('HO', 'HO'),
        ('Sales', 'Sales')
        ], string='Domain', copy=False)
    requisition_code = fields.Char(string='Requisition Code')
    hiring_id = fields.Many2one('hr.employee', string="Hiring Manager")
    requisition_type = fields.Selection([
        ('NEW', 'NEW'),
        ('Replacement', 'Replacement'),
        ], string='Requisition Type', copy=False)
    replacement_id = fields.Many2one('hr.employee', string="Replacement")
    replacement_job_id = fields.Many2one('hr.job', "Ex Employee Designation")
    ex_emp_ctc = fields.Char(string='Ex Employee CTC')
    cv_shared_date = fields.Date('CV Shared Date')
    mention_cancel = fields.Selection([
        ('Cancelled', 'Cancelled'),
        ('Transferred', 'Transferred'),
        ], string='Mention name if cancelled/transferred', copy=False)


    selection_date = fields.Date('Selection Date')
    offer_date = fields.Date('Offer Date')
    offer_released_id = fields.Many2one('hr.employee', string="Offer Released By")
    joining_date = fields.Date('Joining Date')
    ref_check1_date = fields.Date('Ref Check 1(Date)')
    ref_check2_date = fields.Date('Ref Check 2(Date)')
    ref_check_hr_date = fields.Date('Ref Check Sent to HR')
    hr_ref_received_date = fields.Date('HR Ref Received(Date)')
    hr_ref_sent_repmanager_date = fields.Date('HR Ref Check Sent- Reporting Manager(Date)')
    hr_ref_received_repmanager_date = fields.Date('HR Ref Check Received- Reporting Manager(Date)')

    aptitude_test = fields.Selection([
        ('Yes', 'Yes'),
        ('No', 'No'),
        ], string='Aptitude Test Conducted?', copy=False)
    aptitude_test_scores = fields.Float('Aptitude Test Scores')
    technical_test = fields.Selection([
        ('Yes', 'Yes'),
        ('No', 'No'),
        ], string='Technical Test Conducted?', copy=False)
    technical_test_scores = fields.Float('Technical Test Scores')
    test_result = fields.Char(string='Test Result')

    buddy_id = fields.Many2one('hr.employee', string="Buddy")

    total_cv_sent = fields.Integer(string='Total CVs sent to hiring manager')
    cv_shared_today = fields.Integer(string="CV's Shared today")
    total_candidate_lined = fields.Integer(string='Total Candidate Lined Up For Interview ')
    total_interview_with_hiring_manager = fields.Integer(string='Total interviews with Hiring Manager')
    time_taken_close_position = fields.Integer(string='Time taken to close position')
    current_status = fields.Selection([
        ('Position Closed', 'Position Closed'),
        ('Candidate about to join', 'Candidate about to join'),
        ], strng='Current Status', copy=False)
    hrs24_48_cv = fields.Integer(string='24/48 HRS CV')
    backup_cv = fields.Integer(string='Backup CVs')

    offer_accepted_tat1_date = fields.Date('Offer accepted On(TAT 1 day)')
    resignation_received_date = fields.Date('Resignation received on')
    resignation_acceptance_date = fields.Date('Resignation Acceptance received on ')
    reminder_1tat2_date = fields.Date('Reminder 1(TAT 2 days after offer release)')
    reminder_2tat4_date = fields.Date('Reminder 2(TAT 4 days after offer release)')
    reminder_3tat7_date = fields.Date('Reminder 3 (TAT 7 days after offer release)')
    final_reminder_tat10_date = fields.Date('Final reminder (TAT 10 days after offer release)')
    offer_withdrawal_intimation_date = fields.Date('Offer withdrawal Intimation (TAT 12days after offer release)')

    new_employee_bool = fields.Selection([
        ('New Employee', 'New Employee'),
        ('Existing Employee', 'Existing Employee'),
        ], strng='New Employee ?', default="New Employee", copy=False)
    employees_id = fields.Many2one('hr.employee', string="Existing Employee")

    prejoining_ids = fields.One2many('wp.employee.prejoining.details', 'applicant_id', 'PreJoining')
    no_of_prejoining = fields.Integer('No of Joining Details',
                                   compute='_compute_no_of_prejoining',
                                   readonly=True)


    @api.depends('prejoining_ids')
    def _compute_no_of_prejoining(self):
        for rec in self:
            rec.no_of_prejoining = len(rec.prejoining_ids.ids)


    @api.multi
    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        # print eerrror
        employee = False
        for applicant in self:
            address_id = contact_name = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
                contact_name = applicant.partner_id.name_get()[0][1]
            if applicant.job_id and (applicant.partner_name or contact_name):
                applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                employee = self.env['hr.employee'].create({'name': applicant.partner_name or contact_name,
                                               'job_id': applicant.job_id.id,
                                               'address_home_id': address_id,
                                               'department_id': applicant.department_id.id or False,
                                               'address_id': applicant.company_id and applicant.company_id.partner_id and applicant.company_id.partner_id.id or False,
                                               'work_email': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.email or False,
                                               'work_phone': applicant.partner_mobile or False,
                                               'parent_id': applicant.hiring_id.id,
                                               'personal_email': applicant.email_from or False,
                                               'work_location': applicant.location or False,
                                               'date_of_joining': applicant.joining_date or False,
                                               'buddy_id': applicant.buddy_id.id or False,
                                               'mobile_phone': applicant.partner_mobile or False,



                                               })
                applicant.write({'emp_id': employee.id})
                applicant.job_id.message_post(
                    body=_('New Employee %s Hired') % applicant.partner_name if applicant.partner_name else applicant.name,
                    subtype="hr_recruitment.mt_job_applicant_hired")
                employee._broadcast_welcome()
                # employee.create_user()
            else:
                raise UserError(_('You must define an Applied Job and a Contact Name for this applicant.'))

        employee_action = self.env.ref('hr.open_view_employee_list')
        dict_act_window = employee_action.read([])[0]
        if employee:
            dict_act_window['res_id'] = employee.id
        dict_act_window['view_mode'] = 'form,tree'
        return dict_act_window

        

    @api.depends('email_from', 'partner_phone')
    def _compute_same_candidate_application_count(self):
        for applicant in self:
            domain = ['|', '&', ('email_from', '=', applicant.email_from),
                      ('email_from', '!=', False), '&',
                      ('partner_phone', '=', applicant.partner_phone),
                      ('partner_phone', '!=', False)]
            if not isinstance(applicant.id, models.NewId):
                domain = [('id', '!=', applicant.id)] + domain
            same_apps = self.with_context(active_test=False).search(domain)
            applicant.same_candidate_application_ids = same_apps
            applicant.same_candidate_application_count = len(same_apps)

    def action_view_applicants(self):
        action = self.env.ref('hr_recruitment.crm_case_categ0_act_job')
        result = action.read()[0]
        result['domain'] = [('id', 'in',
                            self.same_candidate_application_ids.ids)]
        result['context'] = {'active_test': False, }
        return result

    @api.model
    def create(self, vals):

        vals['requisition_code'] = self.env['ir.sequence'].next_by_code('hr.applicant')
        result = super(HrApplicant, self).create(vals)

        return result

    @api.multi
    @api.depends('requisition_date')
    def _requisition_aeging(self):
        for res in self:
            if res.requisition_date:
                res.requisition_aeging = res.ageing_function(fields.Date.from_string(res.requisition_date))

    @api.multi
    @api.depends('allocation_date')
    def _allocation_aeging(self):
        for res in self:
            if res.allocation_date:
                res.allocation_aeging = res.ageing_function(fields.Date.from_string(res.allocation_date))
  

    @api.multi
    def ageing_function(self,dob):
        gap = relativedelta(date.today(), dob)
        # if gap.years > 0 or gap.months > 0:
        age = ((str(gap.years) + ' Years ')  if gap.years > 0 else '') + \
         ((str(gap.months) + ' Months ') if gap.months else '') + ((str(gap.days) + ' Days ') if gap.days else '')
        return age

    @api.onchange('allocation_date','offer_accepted_tat1_date')
    def onchange_offer_accepted_tat1_date(self):
        if self.offer_accepted_tat1_date and self.allocation_date:
            offer_accepted_tat1_date = datetime.strptime(self.offer_accepted_tat1_date, "%Y-%m-%d")
            allocation_date = datetime.strptime(self.allocation_date, "%Y-%m-%d")
            delta= offer_accepted_tat1_date.date() -  allocation_date.date()
            self.time_taken_close_position = delta.days


    @api.onchange('name')
    def onchange_name_partner(self):
        if self.name:
            self.partner_name = self.name

    @api.onchange('employees_id')
    def onchange_name(self):
        if self.employees_id and self.new_employee_bool== 'Existing Employee':
            self.name = self.employees_id.name
            self.partner_name = self.employees_id.name