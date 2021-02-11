# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Maintainer: Cybrosys Technologies (<https://www.cybrosys.com>)
##############################################################################


from odoo import models, fields, api,_
from odoo.exceptions import UserError


class VisitDetails(models.Model):
    _name = 'fo.property.counter'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _rec_name = 'employee'
    _description = 'Property Details'

    employee = fields.Many2one('hr.employee',  string="Employee", required=True)
    date = fields.Date(string="Date", required=True)
    visitor_belongings = fields.One2many('fo.belongings', 'belongings_id_fov_employee', string="Personal Belongings",
                                         copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('prop_in', 'Taken In'),
        ('prop_out', 'Taken out'),
        ('cancel', 'Cancelled'),
    ], track_visibility='onchange', default='draft',
        help='If the employee taken the belongings to the company change state to ""Taken In""'
             'when he/she leave office change the state to ""Taken out""')

    @api.one
    def action_cancel(self):
        self.state = "cancel"

    @api.one
    def action_prop_in(self):
        count = 0
        number = 0
        for data in self.visitor_belongings:
            if not data.property_count:
                raise UserError(_('Please Add the Count.'))
            if data.permission == '1':
                count += 1
            number = data.number
        if number == count:
            raise UserError(_('No property can be taken in.'))
        else:
            self.state = 'prop_in'

    @api.multi
    def action_prop_out(self):
        self.state = "prop_out"



class VisitDetails(models.Model):
    _name = 'fo.visit'
    _inherit = ['mail.thread']
    _description = 'Visit'

    name = fields.Char(string="sequence", default=lambda self: _('New'))
    visitor = fields.Many2one("fo.visitor", string='Visitor')
    phone = fields.Char(string="Phone", required=True)
    email = fields.Char(string="Email", required=True)
    reason = fields.Many2many('fo.purpose', string='Purpose Of Visit', required=True,
                              help='Enter the reason for visit')
    visitor_belongings = fields.One2many('fo.belongings', 'belongings_id_fov_visitor', string="Personal Belongings",
                                         help='Add the belongings details here.')
    check_in_date = fields.Datetime(string="Check In Time", help='Visitor check in time automatically'
                                                                 ' fills when he checked in to the office.')
    check_out_date = fields.Datetime(string="Check Out Time", help='Visitor check out time automatically '
                                                                   'fills when he checked out from the office.')
    visiting_person = fields.Many2one('hr.employee',  string="Meeting With")
    department = fields.Many2one('hr.department',  string="Department")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('check_in', 'Checked In'),
        ('check_out', 'Checked Out'),
        ('cancel', 'Cancelled'),
    ], track_visibility='onchange', default='draft')

    @api.model
    def create(self, vals):
        if vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('fo.visit') or _('New')
            result = super(VisitDetails, self).create(vals)
            return result

    @api.one
    def action_cancel(self):
        self.state = "cancel"

    @api.one
    def action_check_in(self):
        self.state = "check_in"
        self.check_in_date = datetime.datetime.now()

    @api.multi
    def action_check_out(self):
        self.state = "check_out"
        self.check_out_date = datetime.datetime.now()

    @api.onchange('visitor')
    def visitor_details(self):
        if self.visitor:
            if self.visitor.phone:
                self.phone = self.visitor.phone
            if self.visitor.email:
                self.email = self.visitor.email

    @api.onchange('visiting_person')
    def get_emplyee_dpt(self):
        if self.visiting_person:
            self.department = self.visiting_person.department_id


class PersonalBelongings(models.Model):
    _name = 'fo.belongings'

    property_name = fields.Char(string="Property", help='Employee belongings name')
    property_count = fields.Char(string="Count", help='Count of property')
    number = fields.Integer(compute='get_number', store=True, string="Sl")
    belongings_id_fov_visitor = fields.Many2one('fo.visit', string="Belongings")
    belongings_id_fov_employee = fields.Many2one('fo.property.counter', string="Belongings")
    permission = fields.Selection([
        ('0', 'Allowed'),
        ('1', 'Not Allowed'),
        ('2', 'Allowed With Permission'),
        ], 'Permission', required=True, index=True, default='0', track_visibility='onchange')

    @api.multi
    @api.depends('belongings_id_fov_visitor', 'belongings_id_fov_employee')
    def get_number(self):
        for visit in self.mapped('belongings_id_fov_visitor'):
            number = 1
            for line in visit.visitor_belongings:
                line.number = number
                number += 1
        for visit in self.mapped('belongings_id_fov_employee'):
            number = 1
            for line in visit.visitor_belongings:
                line.number = number
                number += 1


class VisitPurpose(models.Model):
    _name = 'fo.purpose'

    name = fields.Char(string='Purpose', required=True, help='Meeting purpose in short term.eg:Meeting.')
    description = fields.Text(string='Description Of Purpose', help='Description for the Purpose.')



class VisitorDetails(models.Model):
    _name = 'fo.visitor'

    name = fields.Char(string="Visitor", required=True)
    visitor_image = fields.Binary(string='Image', attachment=True)
    street = fields.Char(string="Street")
    street2 = fields.Char(string="Street2")
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    phone = fields.Char(string="Phone", required=True)
    email = fields.Char(string="Email", required=True)
    id_proof = fields.Many2one('id.proof', string="ID Proof")
    id_proof_no = fields.Char(string="ID Number", help='Id proof number')
    company_info = fields.Many2one('res.partner', string="Company", help='Visiting persons company details')
    visit_count = fields.Integer(compute='_no_visit_count', string='# Visits')

    _sql_constraints = [
        ('field_uniq_email_and_id_proof', 'unique (email,id_proof)', "Please give the correct data !"),
    ]

    @api.multi
    def _no_visit_count(self):
        data = self.env['fo.visit'].search([('visitor', '=', self.ids), ('state', '!=', 'cancel')]).ids
        self.visit_count = len(data)


class VisitorProof(models.Model):
    _name = 'id.proof'
    _rec_name = 'id_proof'

    id_proof = fields.Char(string="Name")
    code = fields.Char(string="Code")
