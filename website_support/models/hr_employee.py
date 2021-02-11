# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime


class hr_employee(models.Model):
    _inherit = 'hr.employee'

    kra_id = fields.Many2one('kr.kra', string="KRA")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
