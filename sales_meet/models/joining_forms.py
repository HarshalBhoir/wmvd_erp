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
from odoo.exceptions import UserError , ValidationError
import requests
import urllib
import simplejson
import dateutil.parser
import calendar
from odoo.addons import decimal_precision as dp
from werkzeug import url_encode


emp_stages = [('Draft', 'Draft'),
              ('Submitted', 'Submitted'),
              ('Approved', 'Approved'),
              ('Cancelled', 'Cancelled')]

emp_domain = [('Plant', 'Plant'),
                ('HO', 'HO'),
                ('Sales', 'Sales')]

bool_select = [('Yes', 'Yes'), ('No', 'No')]

emp_gender = [('Male', 'Male'), ('Female', 'Female')]

class EmployeeJoiningDetails(models.Model):

    _name = "wp.employee.joining.details"
    _description = "Employee Joining Details"
    _rec_name = 'name_related'


    @api.model
    def default_get(self, fields_list):
        res = super(EmployeeJoiningDetails, self).default_get(fields_list)

        a = self.search([("employee_id","=", res['employee_id'] )])

        print "lllllllllllllllllll" , a.parent_id.id , a.job_id.id ,  a.department_id.id , a , self
        if len(a) > 0:
            raise UserError(_('You can only Edit the earlier Record. New Record cannot be created'))


        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

        print "kkkkkkkkkkkk" , employee.parent_id.id , employee.job_id.id ,  employee.department_id.id , employee
        res['parent_id'] =  employee.parent_id.id
        res['job_id'] =  employee.job_id.id
        res['department_id'] =  employee.department_id.id

        return res


    name_related = fields.Char('Name')
    father_name = fields.Char('Father Name')
    mother_name = fields.Char('Mother Name')
    current_address = fields.Char('Current Address')
    permanent_address = fields.Char('Permanent Address')
    bank_name = fields.Char('Bank Name')
    account_bank_id = fields.Char('Account Number')
    ifsc_code = fields.Char('IFSC Code')
    bank_address = fields.Char('Bank Address')
    pan_no = fields.Char('Pan Card Number')
    passport_id = fields.Char('Passport Number')
    aadhar_no = fields.Char('Aadhar Card No.')
    uan_no = fields.Char('Previous UAN No. (if applicable)')
    esic_no = fields.Char('Previous ESIC No. (if applicable)')
    date_of_joining = fields.Date('Date of Joining')
    department_id = fields.Many2one('hr.department', 'Department')
    job_id = fields.Many2one('hr.job', 'Designation')
    work_location = fields.Char('Location')
    parent_id = fields.Many2one('hr.employee', 'Reporting  Authority')
    date = fields.Date('Date')
    # employee_id = fields.Many2one('hr.employee', 'Employee Ref', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))


    state = fields.Selection(emp_stages, string='Status', default='Draft' )


    @api.multi
    def update_employee(self):
        print "ssssssssssssssssssssssssssssssss"
        employee_obj = self.env['hr.employee'].search([('id', '=',self.employee_id.id)])
        employee_obj.sudo().write({
                                    'name_related': self.name_related,
                                    'father_name': self.father_name,
                                    'mother_name': self.mother_name,
                                    'bank_name': self.bank_name,
                                    'account_bank_id': self.account_bank_id,
                                    'ifsc_code': self.ifsc_code,
                                    'pan_no': self.pan_no,
                                    'aadhar_no': self.aadhar_no,
                                    'passport_id': self.passport_id,
                                    'uan_no': self.uan_no,
                                    'esic_no': self.esic_no,
                                    })


class EmployeeIDCard(models.Model):

    _name = "wp.employee.id.card"
    _description = "Employee ID Card"


    @api.model
    def default_get(self, fields_list):
        res = super(EmployeeIDCard, self).default_get(fields_list)
        a = self.search([("employee_id","=", res['employee_id'] )])
        if len(a) > 0:
            raise UserError(_('You can only Edit the earlier Record. New Record cannot be created'))
        return res


    @api.multi
    def _compute_can_edit_name(self):
        print "1111111111111111111111111111111111111111 _compute_can_edit_name"
        self.can_edit_name = self.env.user.has_group('sales_meet.group_employee_manager')


    name = fields.Char('Name')
    department_id = fields.Many2one('hr.department', 'Department')
    job_id = fields.Many2one('hr.job', 'Designation')
    emergency_contact = fields.Char('Name of the Contact Person in case of Emergency/Casualty')
    emergency_number = fields.Char('Phone No. of Contact Person in case of Emergency/Casualty')
    emp_id = fields.Char('Employee Code No.')
    blood_group = fields.Char('Blood Group')
    birthday = fields.Date('Date of Birth')
    date_of_joining =  fields.Date('Date of Joining')

    # employee_id = fields.Many2one('hr.employee', 'Employee Ref', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))

    can_edit_name = fields.Boolean(compute='_compute_can_edit_name')
    state = fields.Selection(emp_stages, string='Status', default='Draft' )

    @api.multi
    def update_employee(self):
        print "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh"
        pass


class EmployeeMediclaimRevised(models.Model):

    _name = "wp.employee.mediclaim.revised"
    _description = "Employee Mediclaim Revised"

    @api.model
    def default_get(self, fields_list):
        res = super(EmployeeMediclaimRevised, self).default_get(fields_list)
        a = self.search([("employee_id","=", res['employee_id'] )])
        if len(a) > 0:
            raise UserError(_('You can only Edit the earlier Record. New Record cannot be created'))
        return res


    name = fields.Char('Name')
    self_name = fields.Char('self')
    self_gender = fields.Selection(emp_gender, 'Gender')
    self_birthday =  fields.Date('Date of Birth')
    self_age = fields.Char('Age', compute='_age_self', readonly=True)

    spouse_name = fields.Char('Spouse Name')
    spouse_gender = fields.Selection(emp_gender, 'Gender')
    spouse_birthday =  fields.Date('Date of Birth')
    spouse_age = fields.Char('Age', compute='_age_spouse', readonly=True)

    first_child = fields.Char('1st Child')
    first_gender = fields.Selection(emp_gender, 'Gender')
    first_birthday =  fields.Date('Date of Birth')
    first_age = fields.Char('Age', compute='_age_first', readonly=True)

    second_child = fields.Char('2nd Child')
    second_gender = fields.Selection(emp_gender, 'Gender')
    second_birthday =  fields.Date('Date of Birth')
    second_age = fields.Char('Age', compute='_age_second', readonly=True)

    date = fields.Date('Date')
    mobile = fields.Char('Mobile')


    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))


    state = fields.Selection(emp_stages, string='Status', default='Draft' )


    @api.multi
    @api.depends('self_birthday')
    def _age_self(self):
        self.self_age = self.birthday_function(fields.Date.from_string(self.self_birthday))

    @api.multi
    @api.depends('spouse_birthday')
    def _age_spouse(self):
        self.spouse_age = self.birthday_function(fields.Date.from_string(self.spouse_birthday))


    @api.multi
    @api.depends('first_birthday') 
    def _age_first(self):
        self.first_age = self.birthday_function(fields.Date.from_string(self.first_birthday))

    @api.multi
    @api.depends('second_birthday')
    def _age_second(self):
        self.second_age = self.birthday_function(fields.Date.from_string(self.second_birthday))

    @api.multi
    def birthday_function(self,dob):
        gap = relativedelta(date.today(), dob)
        if gap.years > 0 or gap.months > 0:
            age = str(gap.years) + ' Years ' + \
             ((str(gap.months) + ' Months ') if gap.months else '') + ((str(gap.days) + ' Days ') if gap.days else '')
            return age



class EmployeeMediclaimReimbursement(models.Model):

    _name = "wp.employee.mediclaim.reimbursement"
    _description = "Employee Mediclaim Reimbursement"

    @api.model
    def default_get(self, fields_list):
        res = super(EmployeeMediclaimReimbursement, self).default_get(fields_list)
        a = self.search([("employee_id","=", res['employee_id'] )])
        if len(a) > 0:
            raise UserError(_('You can only Edit the earlier Record. New Record cannot be created'))
        return res


    name = fields.Char('Name')
    self_name = fields.Char('self')
    self_gender = fields.Selection(emp_gender, 'Gender')
    self_nominee =  fields.Boolean('Medical Reimbursement Nominee')
    self_lta_nominee =  fields.Boolean('LTA Nominee')

    spouse_name = fields.Char('Spouse Name')
    spouse_gender = fields.Selection(emp_gender, 'Gender')
    spouse_nominee =  fields.Boolean('Medical Reimbursement Nominee')
    spouse_lta_nominee =  fields.Boolean('LTA Nominee')

    first_child = fields.Char('1st Child')
    first_gender = fields.Selection(emp_gender, 'Gender')
    first_nominee =  fields.Boolean('Date of Birth')
    first_lta_nominee = fields.Boolean('Age')

    father_name = fields.Char('Father’s Name')
    father_gender = fields.Selection(emp_gender, 'Gender')
    father_nominee =  fields.Boolean('Medical Reimbursement Nominee')
    father_lta_nominee =  fields.Boolean('LTA Nominee')

    mother_name = fields.Char('Mother’s Name')
    mother_gender = fields.Selection(emp_gender, 'Gender')
    mother_nominee =  fields.Boolean('Medical Reimbursement Nominee')
    mother_lta_nominee =  fields.Boolean('LTA Nominee')

    date = fields.Date('Date')
    mobile = fields.Char('Mobile')


    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade',
     default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1))


    state = fields.Selection(emp_stages, string='Status', default='Draft' )


class EmployeePreJoiningDetails(models.Model):

    _name = "wp.employee.prejoining.details"
    _description = "Employee Pre Joining Details"


    @api.model
    def create(self, vals):
        res = super(EmployeePreJoiningDetails, self).create(vals)
        a = self.search([("applicant_id","=", res.applicant_id.id )])
        if len(a) > 1:
            raise UserError(_(' New Record cannot be created for this Applicant. You can only Edit the earlier Record.'))
        return res


    name = fields.Char('Name')
    # employee_id = fields.Many2one('hr.employee', string='Employee')
    applicant_id = fields.Many2one('hr.applicant', string='Applicant')
    company_id = fields.Many2one('res.company', 'Company')
    date_of_joining = fields.Date('Date of Joining')
    parent_id = fields.Many2one('hr.employee', 'Reporting  Authority')
    coach_id = fields.Many2one('hr.employee', 'HOD/ZSM')
    department_id = fields.Many2one('hr.department', 'Department')
    job_id = fields.Many2one('hr.job', 'Designation')
    work_location = fields.Char('Location')
    work_email = fields.Char('Work Email')

    domain = fields.Selection(emp_domain, string='Domain', copy=False)
    buddy_id = fields.Many2one('hr.employee', string="Buddy")
    state = fields.Selection(emp_stages, string='Status', default='Draft' )
    employee_id = fields.Many2one('hr.employee', string='Employee')
    orientation_plan =  fields.Date('7 Day Orientation Plan Received on')
    reminder1 =  fields.Date('Reminder 1 Sent on')
    reminder2 =  fields.Date('Reminder 2 Sent on')
    reminder3 =  fields.Date('Reminder 3 Sent on')
    kra_received =  fields.Date('KRA Received')
    kra_intimation =  fields.Date('KRA follow up Intimation with BHR')
    reporting_manager_mail =  fields.Date('Mail to Reporting Manager on')
    manager_joinee_call =  fields.Date('Call by Reporting to joinee on')
    mail_call_candidate =  fields.Date('Mail & Call to Candidate on')
    mail_to_it =  fields.Date('Mail to IT on')
    mail_to_admin =  fields.Date('Mail to Admin on')
    sim_request =  fields.Date('SIM Card Request Sent On')

    el_member_id = fields.Many2one('hr.employee', string="EL Member")
    mail_to_el_member =  fields.Date('Mail to EL Member')
    el_member_joinee_call = fields.Selection(bool_select, string='Call by EL member to joinee', copy=False)

    reporting_manager_mail2 =  fields.Date('Mail to Reporting Manager-2')
    mail_call_candidate2 =  fields.Date('Mail to Candidate-2')
    mail_to_it2 =  fields.Date('Mail to IT-2')
    mail_to_admin2 =  fields.Date('Mail to Admin-2')
    sim_request2 =  fields.Date('SIM Card Request Sent-2')
    mail_to_el_member2 =  fields.Date('Mail to EL Member-2')

    gif_shared =  fields.Date('GIF Shared on')
    sms1 =  fields.Date('SMS 1')
    sms2 =  fields.Date('SMS 2')
    sms3 =  fields.Date('SMS 3')

    photo_received =  fields.Date('Photo received on')
    id_card_details =  fields.Date('ID Card Details received on')
    bank_details =  fields.Date('Bank Details received on')
    welcome_note =  fields.Date('Welcome Note')
    confirmation_mail_if_joinee_doesnot_join = fields.Date('Confirmation mail to Admin in cases Sales emplyoee does not join')
    lunch =  fields.Date('Lunch')
    comment =  fields.Text('Comment if any')


    @api.onchange('applicant_id')
    def onchange_applicant_id(self):
        if self.applicant_id:
            a = self.search([("applicant_id","=", self.applicant_id.id )])
            if len(a) > 0:
                raise UserError(_(' New Record cannot be created for this Applicant. You can only Edit the earlier Record.'))

            self.name =  self.applicant_id.name
            self.date_of_joining =  self.applicant_id.joining_date
            self.parent_id =  self.applicant_id.hiring_id.id
            self.company_id =  self.applicant_id.company_id.id
            self.department_id =  self.applicant_id.department_id.id
            self.job_id =  self.applicant_id.job_id.id
            self.work_location =  self.applicant_id.location
            self.domain =  self.applicant_id.domain
            self.buddy_id =  self.applicant_id.buddy_id.id
        else:
            self.name =  False
            self.date_of_joining =  False
            self.parent_id = False
            self.company_id = False
            self.department_id = False
            self.job_id = False
            self.work_location = False
            self.domain = False
            self.buddy_id = False


    @api.multi
    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        # print eerrror
        employee = False
        if self.work_email:
            for applicant in self:
                address_id = contact_name = False
                if applicant.applicant_id.partner_id:
                    address_id = applicant.applicant_id.partner_id.address_get(['contact'])['contact']
                    contact_name = applicant.applicant_id.partner_id.name_get()[0][1]

                print "s cccccccccccccccccc dddddddd" , applicant.job_id , applicant.applicant_id.partner_name , contact_name
                if applicant.job_id and (applicant.applicant_id.partner_name or contact_name):
                    applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                    employee = self.env['hr.employee'].create({'name': applicant.applicant_id.partner_name or contact_name,
                                               'job_id': applicant.job_id.id,
                                               'address_home_id': address_id,
                                               'department_id': applicant.department_id.id or False,
                                               'address_id': applicant.company_id and applicant.company_id.partner_id and 
                                                             applicant.company_id.partner_id.id or False,
                                               'work_email': applicant.work_email or False,
                                               'work_phone': applicant.applicant_id.partner_phone or False,
                                               'parent_id': applicant.applicant_id.hiring_id.id,
                                               'personal_email': applicant.applicant_id.email_from or False,
                                               'work_location': applicant.applicant_id.location or False,
                                               'date_of_joining': applicant.applicant_id.joining_date or False,
                                               'buddy_id': applicant.buddy_id.id or False,
                                               'mobile_phone': applicant.applicant_id.partner_mobile or False,
                                               'company_id': applicant.company_id.id or False,



                                                   })
                    applicant.applicant_id.write({'emp_id': employee.id})
                    applicant.write({'employee_id': employee.id,'state': 'Approved'})

                    applicant.applicant_id.job_id.message_post(
                        body=_('New Employee %s Hired') % applicant.applicant_id.partner_name if applicant.applicant_id.partner_name else applicant.applicant_id.name,
                        subtype="hr_recruitment.mt_job_applicant_hired")
                    # employee._broadcast_welcome()
                    if employee.work_email:
                        employee.create_user()
                

                else:
                    raise UserError(_('You must define an Applied Job and a Contact Name for this applicant.'))

            employee_action = self.env.ref('hr.open_view_employee_list')
            dict_act_window = employee_action.read([])[0]
            if employee:
                dict_act_window['res_id'] = employee.id
            dict_act_window['view_mode'] = 'form,tree'
            return dict_act_window

        else:
            raise UserError(_('Kindly fill the Work Email and then click on "Create Employee" Button'))


    @api.multi
    def update_employee(self):
        print "ssssssssssssssssssssssssssssssss"
        employee_obj = self.env['hr.employee'].search([('id', '=',self.employee_id.id)])
        employee_obj.sudo().write({
                                    'name_related': self.name_related,
                                    'father_name': self.father_name,
                                    'mother_name': self.mother_name,
                                    'bank_name': self.bank_name,
                                    'account_bank_id': self.account_bank_id,
                                    'ifsc_code': self.ifsc_code,
                                    'pan_no': self.pan_no,
                                    'aadhar_no': self.aadhar_no,
                                    'passport_id': self.passport_id,
                                    'uan_no': self.uan_no,
                                    'esic_no': self.esic_no,
                                    })

    # @api.multi
    # def write(self, vals):
    #     result = super(EmployeePreJoiningDetails, self).write(vals)
    #     print "ssssssssssssssssssssssssssssssss", vals
    #     employee_obj = self.env['hr.employee'].search([('id', '=',self.employee_id.id)])
    #     if employee_obj:
    #         employee_obj.sudo().write(vals)
    #     print eroor

    #     return result



class EmployeeOnboardingDetails(models.Model):

    _name = "wp.employee.onboarding.details"
    _description = "Employee Onboarding Details"

    @api.model
    def create(self, vals):
        res = super(EmployeeOnboardingDetails, self).create(vals)
        a = self.search([("employee_id","=", res.employee_id.id )])
        print "fffffffffffffff", len(a)
        if len(a) > 1:
            raise UserError(_(' New Record cannot be created for this Employee. You can only Edit the earlier Record.'))
        return res


    name = fields.Char('Name')
    emp_id =  fields.Char('Emp No.')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    date_of_joining = fields.Date('Date of Joining')
    parent_id = fields.Many2one('hr.employee', 'Reporting  Authority')
    coach_id = fields.Many2one('hr.employee', 'HOD/ZSM')
    department_id = fields.Many2one('hr.department', 'Department')
    job_id = fields.Many2one('hr.job', 'Designation')
    work_location = fields.Char('Location')
    domain = fields.Selection(emp_domain, string='Domain', copy=False)
    grade_id = fields.Many2one("grade.master", string="Grade")
    buddy_id = fields.Many2one('hr.employee', string="Buddy")
    company_id = fields.Many2one('res.company', 'Company')
    offer_issued_tat1_date = fields.Date('Offer Letter Issued On (TAT 1 days)')
    acceptance_documented = fields.Date('Acceptance Documented')
    appointment_letter_issued_tat1_date = fields.Date('Appointment Letter Issued On (TAT 1 days)')
    al_acceptance_documented = fields.Date('AL Acceptance Documented')
    delayed_reason = fields.Char('Reason if release delayed')

    id_card_request = fields.Date('ID CARD Request Sent to Admin (TAT 1 day)')
    id_card_issued = fields.Date('ID Card Issued on (TAT 5 days) (Weekly MIS sent by admin to HR)')
    visiting_card_request = fields.Date('Visiting Card Request Sent to Admin (TAT  0 day)')
    visiting_card_issued = fields.Date('Visiting Card Issued on (TAT 5 days) (Weekly MIS sent by admin to HR)')
    joining_kit_issued = fields.Date('Joining KIT issued on (TAT 0 day) (Weekly MIS sent by Admin to HR)')
    joining_booklet_issued = fields.Date('Joining Booklet issued on (TAT 0 day) (Weekly MIS sent by Admin to HR)')
    joining_booklet_received = fields.Date('Joining Booklet Received on')
    sim_card_issued = fields.Date('Sim Card Issued on (TAT 0 day) (Weekly MIS sent by admin to HR)')
    bank_letter_request_payroll = fields.Date('Bank Letter Request to payroll sent on (TAT 1 days)')
    bank_letter_issued = fields.Date('Bank Letter Issued On (TAT 1 days) (Weekly MIS sent by payroll to HR)')
    reason_if_no = fields.Char('Reason if NO')
    file_issued_to_payroll = fields.Date('File Issued to payroll on (TAT 1-9 days)')
    saral_entry = fields.Date('Saral entry done on (TAT 2-10 days) (Weekly MIS sent by payroll to HR)')
    portal_link_sent = fields.Date('Portal link sent on (6-13days) (Weekly MIS sent to HR)')
    portal_induction = fields.Date('Portal Induction (Weekly MIS sent to HR)')


    hr_tele_induction = fields.Date('HR Tele - INDUCTION')
    hr_f2f_joining_induction = fields.Date('HR F2F joining Induction (Weekly MIS sent to HR)')
    mediclaim_induction = fields.Date('Mediclaim Induction (TAT 0) (Weekly MIS sent to HR)')
    travel_policy_induction = fields.Date('Travel Policy induction (mail sent on)')
    orientation_booklet_issued = fields.Date('7Day Orientation Booklet Issued on')
    orientation_booklet_received = fields.Date('7Day Orientation Booklet Received on')
    relieving_experience_letter_received = fields.Date('Relieving & Experience Letter Received on')
    re_reminder1 = fields.Date('R&E Reminder 1 (30days from DOJ)')
    re_reminder2 = fields.Date('R&E Reminder 2 (45 days from DOJ)')
    emp_declaration_letter = fields.Selection(bool_select, string='Emp Declaration Letter', copy=False)
    salary_on_hold = fields.Float('Salary on Hold ')

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:

            a = self.search([("employee_id","=", self.employee_id.id )])
            if len(a) > 0:
                raise UserError(_(' New Record cannot be created for this Employee. You can only Edit the earlier Record.'))

            self.name =  self.employee_id.name
            self.date_of_joining =  self.employee_id.date_of_joining
            self.parent_id =  self.employee_id.parent_id.id
            self.coach_id =  self.employee_id.coach_id.id
            self.department_id =  self.employee_id.department_id.id
            self.job_id =  self.employee_id.job_id.id
            self.work_location =  self.employee_id.work_location
            # self.domain =  self.employee_id.domain
            # self.buddy_id =  self.employee_id.buddy_id.id
        else:
            self.name =  False
            self.date_of_joining = False
            self.parent_id = False
            self.coach_id = False
            self.department_id = False
            self.job_id = False
            self.work_location = False
            # self.domain = False
            # self.buddy_id = False