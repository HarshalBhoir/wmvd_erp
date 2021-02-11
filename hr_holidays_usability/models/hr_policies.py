# -*- coding: utf-8 -*-
# ©  2015 2011,2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import date
from openerp import fields, models, api, _
from openerp.exceptions import Warning as UserError


class hr_policies(models.Model):
    _name = 'hr.policies'
    _description = 'Policies'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char('Name')
    policy = fields.Text('Policy')

