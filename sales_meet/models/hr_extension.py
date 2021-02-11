# -*- coding: utf-8 -*-

from odoo.tools.translate import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _ , tools, SUPERUSER_ID
from time import gmtime, strftime
from odoo.exceptions import UserError , ValidationError
import calendar
from werkzeug import url_encode

emp_stages = [('joined', 'Probation'),
              ('grounding', 'Grounding'),
              ('offrole', 'OffRole'),
              ('test_period', 'Test Period'),
              ('employment', 'Employment'),
              ('notice_period', 'Notice Period'),
              ('relieved', 'Resigned'),
              ('terminate', 'Terminated')]


class hr_insurance_policy(models.Model):
    _name = "hr.insurance.policy"
    _description = "Insurance Policy"

    name  = fields.Char('Insurance')


class hr_videocon_policy(models.Model):
    _name = "hr.videocon.policy"
    _description = "videocon Policy"

    name  = fields.Char('VIDEOCON LIBERTY POLICY No.')


class hr_employee_category(models.Model):
    _inherit = "hr.employee.category"

    category_id  = fields.Char('Category ID')



class hr_extension(models.Model):
    _inherit = "hr.employee"

    @api.depends('idcard_ids')
    def _compute_no_of_idcard(self):
        for rec in self:
            rec.no_of_idcard = len(rec.idcard_ids.ids)


    @api.depends('joining_ids')
    def _compute_no_of_joining(self):
        for rec in self:
            rec.no_of_joining = len(rec.joining_ids.ids)

    @api.depends('medrev_ids')
    def _compute_no_of_medrev(self):
        for rec in self:
            rec.no_of_medrev = len(rec.medrev_ids.ids)


    @api.depends('reimb_ids')
    def _compute_no_of_reimb(self):
        for rec in self:
            rec.no_of_reimb = len(rec.reimb_ids.ids)


    @api.model
    def create(self, vals):
        result = super(hr_extension, self).create(vals)
        result.stages_history.sudo().create({'start_date': date.today(),
                                             'employee_id': result.id,
                                             'state': 'joined'})
        return result

    @api.multi
    def start_grounding(self):
        self.state = 'grounding'
        self.stages_history.sudo().create({'start_date': date.today(),
                                           'employee_id': self.id,
                                           'state': 'grounding'})

    @api.multi
    def set_as_employee(self):
        self.state = 'employment'
        stage_obj = self.stages_history.search([('employee_id', '=', self.id),
                                                ('state', '=', 'test_period')])
        if stage_obj:
            stage_obj.sudo().write({'end_date': date.today()})
        self.status = 'present'
        self.stages_history.sudo().create({'start_date': date.today(),
                                           'employee_id': self.id,
                                           'state': 'employment'})


    @api.multi
    def start_notice_period(self):
        self.state = 'notice_period'
        stage_obj = self.stages_history.search([('employee_id', '=', self.id),
                                                ('state', '=', 'employment')])
        if stage_obj:
            stage_obj.sudo().write({'end_date': date.today()})
        self.stages_history.sudo().create({'start_date': date.today(),
                                           'employee_id': self.id,
                                           'state': 'notice_period'})

    @api.multi
    def relived(self):
        self.state = 'relieved'
        self.active = False
        stage_obj = self.stages_history.search([('employee_id', '=', self.id),
                                                ('state', '=', 'notice_period')])
        if stage_obj:
            stage_obj.sudo().write({'end_date': date.today()})
        self.stages_history.sudo().create({'end_date': date.today(),
                                           'employee_id': self.id,
                                           'state': 'relieved'})

    @api.multi
    def start_test_period(self):
        self.state = 'test_period'
        self.stages_history.search([('employee_id', '=', self.id),
                                    ('state', '=', 'grounding')]).sudo().write({'end_date': date.today()})
        self.stages_history.sudo().create({'start_date': date.today(),
                                           'employee_id': self.id,
                                           'state': 'test_period'})

    @api.multi
    def terminate(self):
        self.state = 'terminate'
        self.active = False
        stage_obj = self.stages_history.search([('employee_id', '=', self.id),
                                                ('state', '=', 'employment')])

        if stage_obj:
            stage_obj.sudo().write({'end_date': date.today()})
        else:
            self.stages_history.search([('employee_id', '=', self.id),
                                        ('state', '=', 'grounding')]).sudo().write({'end_date': date.today()})
        self.stages_history.sudo().create({'end_date': date.today(),
                                           'employee_id': self.id,
                                           'state': 'terminate'})

    # bp_code = fields.Char('Partner Code')
    grade_id = fields.Many2one("grade.master", string="Grade")
    c_bpartner_id = fields.Char('Idempiere ID')
    emp_id = fields.Char('Employee ID')
    date_of_joining = fields.Date("Date of Joining")
    date_of_resignation = fields.Date("Date of Resignation")
    last_date = fields.Date("Last Date Working")
    status = fields.Selection([
        ('present', 'Present'),
        ('transfer', 'Transfer'),
        ('left', 'Left')
        ], string='Status', copy=False, index=True, store=True)
    zone = fields.Selection([
        ('north', 'North'),
        ('east', 'East'),
        ('central', 'Central'),
        ('west', 'West'),
        ('south', 'South')
        ], string='Zone', copy=False, index=True, store=True)
    roll = fields.Selection([
        ('onroll', 'Onroll'),
        ('offroll', 'Offroll'),
        ('contract', 'Contract'),
        ('GQT', 'GQT'),
        ('Trainee', 'Trainee'),
        ('consultant', 'Consultant')
        ], string='Roll', copy=False, index=True, store=True)
    fnf = fields.Selection([
        ('na', 'NA'),
        ('pending', 'Pending'),
        ('processed', 'Processed')
        ], string='F & F', copy=False, index=True, store=True)
    category_ids_many2one = fields.Many2one("hr.employee.category", string="Category")
    category_id = fields.Char(string="Category ID" , related='category_ids_many2one.category_id')
    age = fields.Char('Age', compute='_age_employee')

    state = fields.Selection(emp_stages, string='Status', default='joined', track_visibility='always', copy=False)
    stages_history = fields.One2many('hr.employee.status.history', 'employee_id', string='Stage History')
    work_state = fields.Char(string="Work State" )
    blood_group = fields.Char(string="Blood Group" )
    pan_no = fields.Char('Pan No')
    aadhar_no = fields.Char('Aadhar No')
    personal_email = fields.Char('Personal Email')
    qualification = fields.Char('Qualification')
    further_addition = fields.Text('Further Addition')
    experience = fields.Char('Experience', compute='_date_of_joining')
    other_experience = fields.Char('Other Experience')
    father_name = fields.Char('Father/Husband Name')
    mother_name = fields.Char('Mother Name')

    pf_no_with_company = fields.Char('PF NO with Company')
    pf_no = fields.Char('Only PF No.')
    pf_ceiling = fields.Selection([
        ('na', 'NA'),
        ('applicable', 'APPLICABLE'),
        ('not_applicable', 'NOT APPLICABLE')
        ], string='PF Ceiling', copy=False, index=True, store=True)
    uan_no = fields.Char('UAN No')
    company_esic_no = fields.Char('Company ESIC No.')
    esic_no = fields.Char('ESIC No.')
    insurance_id = fields.Many2one("hr.insurance.policy", string="CUVLA Policy No.")
    uvl_no = fields.Char('Member No. UVL')
    cuvlap = fields.Selection([
        ('na', 'NA'),
        ('active', 'ACTIVE'),
        ('addition_pending', 'ADDITION PENDING')
        ], string='CUVLAP', copy=False, index=True, store=True)    
    videocon_insurance_id = fields.Many2one("hr.videocon.policy", string="VIDEOCON LIBERTY POLICY No.")
    vlc_no = fields.Char('VIDEOCON LIBERTY CARD NO')
    card_status = fields.Selection([
        ('na', 'NA'),
        ('active', 'ACTIVE'),
        ('addition_pending', 'ADDITION PENDING'),
        ('not_applicable', 'NOT APPLICABLE')
        ], string='Card Status', copy=False, index=True, store=True)

    bank_name = fields.Char('Bank Name')
    account_bank_id = fields.Char('Bank Account ID')
    ifsc_code = fields.Char('IFSC Code')

    state_id = fields.Many2one("res.country.state", string="State")
    district_many2many = fields.Many2many('res.state.district', string='Districts' ,  domain="[('active','=',True)]")

    joining_ids = fields.One2many('wp.employee.joining.details', 'employee_id', 'Joining Ref.')
    no_of_joining = fields.Integer('No of Joining Details',
                                   compute='_compute_no_of_joining',
                                   readonly=True)

    idcard_ids = fields.One2many('wp.employee.id.card', 'employee_id', 'ID card Ref.')
    no_of_idcard = fields.Integer('No of ID card Details',
                                   compute='_compute_no_of_idcard',
                                   readonly=True)


    medrev_ids = fields.One2many('wp.employee.mediclaim.revised', 'employee_id', 'Mediclaim Ref.')
    no_of_medrev = fields.Integer('No of Mediclaim Details',
                                   compute='_compute_no_of_medrev',
                                   readonly=True)


    reimb_ids = fields.One2many('wp.employee.mediclaim.reimbursement', 'employee_id', 'ID card Ref.')
    no_of_reimb = fields.Integer('No of Reimbursement Details',
                                   compute='_compute_no_of_reimb',
                                   readonly=True)


    user_check_tick = fields.Boolean(default=False)
    kra_id = fields.Many2one('kr.kra', string="KRA")
    buddy_id = fields.Many2one('hr.employee', string="Buddy")
    domain = fields.Selection([
                ('Plant', 'Plant'),
                ('HO', 'HO'),
                ('Sales', 'Sales')], string='Domain', copy=False)

    no_autoclose = fields.Boolean(string='Don\'t Autoclose Attendances')
    

    @api.multi
    def create_user(self):
        executive_group = self.env.ref('sales_meet.group_sales_meet_executive')
        salesman_group = self.env.ref('sales_team.group_sale_salesman_all_leads')
        retailer_group = self.env.ref('sales_meet.group_retailer_module_user')
        sampling_group = self.env.ref('sales_meet.group_sampling_module_user')
        cir_group = self.env.ref('sales_meet.group_cir_module_user')

        user_id = self.env['res.users'].sudo().create({
            'name': self.name,
            'login': self.work_email,
            'email': self.work_email,
            'company_id': self.company_id.id,
            'employee_id': self.id,
            'company_ids': [(6, 0, [self.company_id.id])],
            'groups_id': [(6, 0, [executive_group.id, 
                salesman_group.id, retailer_group.id, 
                sampling_group.id, cir_group.id, 
                self.env.ref('base.group_user').id])]

        })
        user_id.employee_id.user_id = user_id.id
        self.address_home_id = user_id.partner_id.id
        self.user_check_tick = True

    @api.onchange('address_home_id')
    def user_checking(self):
        if self.address_home_id:
            self.user_check_tick = True
        else:
            self.user_check_tick = False

    @api.onchange('state_id')
    def onchange_state_id(self):
        if self.state_id:
            self.work_state = self.state_id.name
        else:
            self.work_state = ''


    @api.multi
    @api.depends('birthday')
    def _age_employee(self):
        today = date.today()
        for record in self:
            age = []
            dob = fields.Date.from_string(record.birthday)
            gap = relativedelta(today, dob)
            if gap.years > 0 or gap.months > 0:
                record.age = str(gap.years) + ' Years ' +\
                 ((str(gap.months) + ' Months ') if gap.months else '') + ((str(gap.days) + ' Days ') if gap.days else '')


    @api.multi
    @api.depends('date_of_joining')
    def _date_of_joining(self):
        today = date.today()
        for record in self:
            age = []
            doj = fields.Date.from_string(record.date_of_joining)
            gap = relativedelta(today, doj)
            if gap.years > 0:
                record.experience = str(gap.years) + ' Years ' +\
                 ((str(gap.months) + ' Months ') if gap.months else '') + ((str(gap.days) + ' Days ') if gap.days else '')

    @api.model
    def get_ul(self, empl_id, date_from, date_to):
        # if date_to is None:
        #     date_to = datetime.now().strftime('%Y-%m-%d')
        unpaid = self.env['hr.holidays.status'].search([('name','=','Unpaid')])
        # print "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        self._cr.execute("select sum(o.number_of_days) from hr_holidays as o where \
                             o.employee_id=%s \
                             AND to_char(o.date_from, 'YYYY-MM-DD') >= %s AND to_char(o.date_to, 'YYYY-MM-DD') <= %s ",
                            (empl_id, date_from, date_to))
        res = self._cr.fetchall()

        # print "JJJJJJJJJJJJJJJJJJJJJJJJJJ" , res
        return res and res[0] or 0.0


    @api.model
    def get_leaves(self, empl_id, date_from, date_to, unpaid):
        self._cr.execute("select sum(o.number_of_days) from hr_holidays as o where \
                             o.employee_id=%s \
                             AND to_char(o.date_from, 'YYYY-MM-DD') >= %s AND to_char(o.date_to, 'YYYY-MM-DD') <= %s AND o.holiday_status_id = %s",
                            (empl_id, date_from, date_to, unpaid))
        res = self._cr.fetchone()

        return res and res[0] or 0.0




    @api.multi
    def send_joining_details(self):
        tkt_type_val = 'Joining Details'
        lines = ''
        amnt = 0.0
        body = """ """
        subject = ""
        recepients = []

        recepients.append(self.work_email)

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <h3>Hello Candidate,</h3>
            <h4>Kindly Click on respective buttons for Submitting Information. </h4>

            <br/>

        """ 

        subject = "Joining Detail Forms"
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        joining_action = self.env['ir.actions.act_window'].sudo().search([('view_type', '=', 'form'),
            ('res_model', '=', 'wp.employee.joining.details')], limit=1).id

        idcard_action = self.env['ir.actions.act_window'].sudo().search([('view_type', '=', 'form'),
            ('res_model', '=', 'wp.employee.id.card')], limit=1).id

        medrev_action = self.env['ir.actions.act_window'].sudo().search([('view_type', '=', 'form'),
            ('res_model', '=', 'wp.employee.mediclaim.revised')], limit=1).id

        reimb_action = self.env['ir.actions.act_window'].sudo().search([('view_type', '=', 'form'),
            ('res_model', '=', 'wp.employee.mediclaim.reimbursement')], limit=1).id
        
        for rec in recepients:

            joining_form = base_url + '/web#%s' % (url_encode({
                'model': 'wp.employee.joining.details',
                'view_type': 'tree',
                # 'id': main_id,
                'action': joining_action,
            }))

            idcard_form = base_url + '/web#%s' % (url_encode({
                'model': 'wp.employee.id.card',
                'view_type': 'tree',
                # 'id': main_id,
                'action': idcard_action,
            }))

            medrev_form = base_url + '/web#%s' % (url_encode({
                'model': 'wp.employee.mediclaim.revised',
                'view_type': 'tree',
                # 'id': main_id,
                'action': medrev_action,
            }))

            reimb_form = base_url + '/web#%s' % (url_encode({
                'model': 'wp.employee.mediclaim.reimbursement',
                'view_type': 'tree',
                # 'id': main_id,
                'action': reimb_action,
            }))

            full_body = body + """<br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
                            border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                             vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                              margin-right: 10px;">Joining Form</a>
                        </td>

                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
                            border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                             vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                              margin-right: 10px;">ID Card Form</a>
                        </td>

                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
                            border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                             vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                              margin-right: 10px;">Mediclaim Revised Form</a>
                        </td>

                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
                            border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                             vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                              margin-right: 10px;">Medicla Reimbursment & LTA Form</a>
                        </td>

                    </tr>
                </tbody>
            </table>
            """ % (joining_form, idcard_form, medrev_form ,reimb_form )

            
            composed_mail = self.env['mail.mail'].sudo().create({
                    'model': self._name,
                    'res_id': self.id,
                    'email_to': rec,
                    'subject': subject,
                    'body_html': full_body,
                })
            composed_mail.sudo().send()



class hr_payslip(models.Model):
    _inherit = "hr.payslip"

    unpaid_id = fields.Many2one('hr.holidays.status', string="Status",
      default=lambda self: self.env['hr.holidays.status'].search([('name', '=', 'Unpaid')], limit=1))
    month_days = fields.Integer(string="Days" , store=True, track_visibility='always')

    @api.onchange('date_from','date_to')
    def _default_days(self):
        if self.date_from and self.date_to:
            date_from = self.date_from
            date_to = self.date_to
            today = datetime.now()
            daymonthfrom = datetime.strptime(date_from, "%Y-%m-%d")
            daymonthto = datetime.strptime(date_to, "%Y-%m-%d")
            monthfrom = daymonthfrom.strftime("%m")
            monthto = daymonthto.strftime("%m")
            yearfrom = int(daymonthfrom.strftime("%Y"))
            yearto = daymonthto.strftime("%Y")

            monthfrom2 =  int(monthfrom[1:] if monthfrom.startswith('0') else monthfrom)
            monthto2 =  int(monthto[1:] if monthto.startswith('0') else monthto)

            if monthfrom2 == monthto2:
                self.month_days =  calendar.monthrange(yearfrom,monthfrom2)[1]



class EmployeeStageHistory(models.Model):
    _name = 'hr.employee.status.history'
    _description = 'Status History'

    @api.depends('end_date')
    def get_duration(self):
        for each in self:
            if each.end_date and each.start_date:
                duration = fields.Date.from_string(each.end_date) - fields.Date.from_string(each.start_date)
                each.duration = duration.days

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    duration = fields.Integer(compute=get_duration, string='Duration(days)')
    state = fields.Selection(emp_stages, string='Stage')
    employee_id = fields.Many2one('hr.employee', invisible=1)


class WizardEmployee(models.TransientModel):
    _name = 'wizard.employee.stage'

    @api.multi
    def set_as_employee(self):
        context = self._context
        employee_obj = self.env['hr.employee'].search([('id', '=', context.get('employee_id'))])
        if self.related_user:
            employee_obj.user_id = self.related_user
        employee_obj.set_as_employee()

    related_user = fields.Many2one('res.users', string="Related User")
