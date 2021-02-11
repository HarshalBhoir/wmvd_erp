# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import math

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare

class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _inherit = 'mrp.production'

    final_product_lot = fields.Many2one('stock.production.lot', string='Serie',readonly=True,store=True)

    # @api.multi
    # def open_produce_product(self):
    #     self.ensure_one()
    #     barcode= self.product_id.as_sku
    #     action = self.env.ref('mrp.act_mrp_product_produce').read()[0]
    #     if not self.final_product_lot:
    #         correlativo= self.env['ir.sequence'].next_by_code('mrp.series')
    #         self.final_product_lot = self.env['stock.production.lot'].create({
    #             'name': str(barcode)+str(correlativo),
    #             'product_id': self.product_id.id,
    #             'product_qty': self.product_qty,
    #             'ref': correlativo,
    #             'origin': 'open_produce_product error',
    #         })
    #         action.update({
    #             'context': {
    #                 'default_final_product_lot': self.final_product_lot.id,
                
    #             },
    #         })
    #     return action

    # @api.model
    # def create(self, vals):
    #     mrp = super(MrpProduction, self).create(vals)
    #     barcode= mrp.product_id.as_sku
    #     if not mrp.final_product_lot:
    #         correlativo= self.env['ir.sequence'].next_by_code('mrp.series')
    #         mrp.final_product_lot = self.env['stock.production.lot'].create({
    #             'name': str(barcode)+str(correlativo),
    #             'product_id': mrp.product_id.id,
    #             'product_qty': mrp.product_qty,
    #             'ref': correlativo,
    #             'origin': mrp.name,
    #         })
    #     return mrp

    # @api.multi
    # def write(self, vals):
    #     result = super(MrpProduction, self).write(vals)
    #     barcode= self.product_id.as_sku
    #     if not self.final_product_lot:
    #         correlativo= self.env['ir.sequence'].next_by_code('mrp.series')
    #         self.final_product_lot = self.env['stock.production.lot'].create({
    #             'name': str(barcode)+str(correlativo),
    #             'product_id': self.product_id.id,
    #             'ref': correlativo,
    #             'origin': 'Write error',
    #         })
    #     return result