# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare

class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_default_branch(self):
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id
        return branch_id

    branch_id=fields.Many2one('res.branch', 'Branch', required=True , default=_get_default_branch)

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        if self.branch_id:
            wh = self.env['stock.warehouse'].search([('branch_id', '=',self.branch_id.id)])
            if wh:
                self.warehouse_id = wh[0]
            else:
                self.warehouse_id = False

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        res = super(sale_order, self)._prepare_invoice()
        res.update({'branch_id':self.branch_id.id})
        return res

class stock_picking(models.Model):
    _inherit='stock.picking'

    branch_id = fields.Many2one('res.branch','Branch')

class stock_move(models.Model):
    _inherit = 'stock.move'

    branch_id = fields.Many2one('res.branch','Branch')

    def _get_new_picking_values(self):
        res = super(stock_move, self)._get_new_picking_values()
        res.update({'branch_id':self.branch_id.id})
        return res
class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        result = super(ProcurementRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
        result.update({
                'branch_id':values.get('branch_id')
            })
        return result
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _action_launch_procurement_rule(self):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_move', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        errors = []
        for line in self:
            if line.state != 'sale' or not line.product_id.type in ('consu','product'):
                continue
            qty = 0.0
            for move in line.move_ids.filtered(lambda r: r.state != 'cancel'):
                qty += move.product_qty
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            if not line.order_id.procurement_group_id:
                line.order_id.procurement_group_id = self.env['procurement.group'].create({
                    'name': line.order_id.name, 'move_type': line.order_id.picking_policy,
                    'sale_id': line.order_id.id,
                    'partner_id': line.order_id.partner_shipping_id.id,
                })
            values = line._prepare_procurement_values(group_id=line.order_id.procurement_group_id)
            values.update({'branch_id':line.order_id.branch_id.id})
            product_qty = line.product_uom_qty - qty
            try:
                self.env['procurement.group'].run(line.product_id, product_qty, line.product_uom, line.order_id.partner_shipping_id.property_stock_customer, line.name, line.order_id.name, values)
            except UserError as error:
                errors.append(error.name)
        if errors:
            raise UserError('\n'.join(errors))
        return True



