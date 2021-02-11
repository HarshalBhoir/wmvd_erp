# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    as_sku = fields.Char(string='SKU')
    as_cont = fields.Integer(string='Numero de Series',store=True, readonly=True)

    @api.model
    def create(self, vals):
        product = super(ProductTemplate, self).create(vals)
        if product.as_sku:
            product_sku = self.env['product.template'].search([('as_sku', '=', product.as_sku)])
            if len(product_sku)>1:
                raise UserError(_('Su codigo SKU ya ha sido asignado a %s.')%product_sku[0].name)
        return product

    @api.multi
    def write(self, vals):
        result = super(ProductTemplate, self).write(vals)
        if self.as_sku:
            product_sku = self.env['product.template'].search([('as_sku', '=', self.as_sku)])
            if len(product_sku)>1:
                raise UserError(_('Su codigo SKU ya ha sido asignado a %s.')%product_sku[0].name)
        return result