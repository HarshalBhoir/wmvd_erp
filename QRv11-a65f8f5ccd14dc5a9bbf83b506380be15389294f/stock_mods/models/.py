# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import api, exceptions, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_image = fields.Binary("Is Image")
