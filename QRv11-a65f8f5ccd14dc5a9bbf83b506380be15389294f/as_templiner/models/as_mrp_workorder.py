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
    _inherit = 'mrp.workorder'

    def open_tablet_all_view(self):
        qty_production = self.qty_production
        qty_produced = self.qty_produced
        # if not self.production_id.product_id.sequence_id:
        #     raise UserError(_('El producto no posee secuencia serie a %s.')%self.production_id.product_id.name)
        vals = {}
        for qty in range(int(qty_produced+1),int(qty_production+1)):
            correlativo = self.production_id.product_id.as_cont + 1 
            self.production_id.product_id.as_cont = correlativo
            barcode = self.production_id.product_id.as_sku
            self.final_lot_id = self.env['stock.production.lot'].create({
                'name': str(barcode)+str(correlativo),
                'product_id': self.production_id.product_id.id,
                'ref': correlativo,
                'product_qty': qty,
                'origin': self.production_id.name,
            })
            vals[qty]= self.final_lot_id.id
            self.record_production()
            if qty_produced == qty_production:
                self.do_finish()
        workorder = self.env['mrp.workorder'].search([('production_id', '=', self.production_id.id),('state', '!=', 'done')])
        if workorder:
            for work in workorder:
                for qty in range(int(qty_produced+1),int(qty_production+1)):
                    work.final_lot_id = vals[qty]
                    work.record_production()
                    if qty_produced == qty_production:
                        work.do_finish()


       