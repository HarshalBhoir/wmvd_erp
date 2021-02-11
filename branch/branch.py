# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import pycompat
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError

class res_branch(models.Model):
    _name = 'res.branch'

    
    name = fields.Char('Name')
    address = fields.Text('Address', size=252)
    telephone_no = fields.Char("Telephone No")
    company_id =  fields.Many2one('res.company', 'Company', required=True)


class stock_warehouse(models.Model):
    _inherit = 'stock.warehouse'

    branch_id = fields.Many2one('res.branch', 'Branch')

class stock_location(models.Model):
    _inherit = 'stock.location'

    branch_id = fields.Many2one('res.branch', 'Branch')

    @api.multi
    @api.constrains('branch_id')
    def _check_branch(self):
        for location in self:
            warehouse_obj = self.env['stock.warehouse']
            warehouse_id = warehouse_obj.search(
                ['|', '|', ('wh_input_stock_loc_id', '=', location.id),
                 ('lot_stock_id', '=', location.id),
                 ('wh_output_stock_loc_id', '=', location.id)])
            for warehouse in warehouse_id:
                if location.branch_id != warehouse.branch_id:
                    raise UserError(_('Configuration error\nYou  must select same branch on a location as asssigned on a warehouse configuration.'))




class res_users(models.Model):
    _inherit = 'res.users'

    
    branch_id = fields.Many2one('res.branch', 'Branch', required=True)
    branch_ids = fields.Many2many('res.branch', id1='user_id', id2='branch_id',string='Branch')



class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'   
    @api.multi
    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res
        qty = 0.0
        price_unit = self._get_stock_move_price_unit()
        for move in self.move_ids.filtered(lambda x: x.state != 'cancel' and not x.location_dest_id.usage == "supplier"):
            qty += move.product_qty
        template = {
            'name': self.name or '',
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'date': self.order_id.date_order,
            'date_expected': self.date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': self.order_id._get_destination_location(),
            'picking_id': picking.id,
            'partner_id': self.order_id.dest_address_id.id,
            'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.order_id.picking_type_id.id,
            'group_id': self.order_id.group_id.id,
            'origin': self.order_id.name,
            'route_ids': self.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in self.order_id.picking_type_id.warehouse_id.route_ids])] or [],
            'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
            'branch_id':self.order_id.branch_id.id
        }
        diff_quantity = self.product_qty - qty
        if float_compare(diff_quantity, 0.0,  precision_rounding=self.product_uom.rounding) > 0:
            template['product_uom_qty'] = diff_quantity
            res.append(template)
        return res

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _get_purchase_default_branch(self):
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id
        return branch_id

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        type_obj = self.env['stock.picking.type']
        if self.branch_id:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'),
                                     ('warehouse_id.branch_id', '=',
                                      self.branch_id.id)])
            if picking_type:
                self.picking_type_id = picking_type[0]
            else:
                raise UserError(
                    _("No Warehouse has the branch same as the one selected "
                      "in the Purchase Order")
                )


    branch_id = fields.Many2one('res.branch', 'Branch', required=True, default = _get_purchase_default_branch)    

    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s") % self.partner_id.name)
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
            'branch_id':self.branch_id.id
        }




class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _get_invoice_default_branch(self):
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.user.id).branch_id.id or False
        return branch_id

    
    branch_id = fields.Many2one('res.branch', 'Branch', required=True, default = _get_invoice_default_branch)
    

   
    
#     def invoice_pay_customer(self, cr, uid, ids, context=None):
#         result = super(account_invoice, self).invoice_pay_customer(cr, uid, ids, context=context)
#         inv = self.pool.get('account.invoice').browse(cr, uid, ids[0], context=context)
#         sale_order_id = inv.sale_order_id and inv.sale_order_id.id or False
#         if sale_order_id:
#             result.get('context').update({'default_branch_id': inv.branch_id.id, 'default_sale_order_id':sale_order_id})
#         else:
#             result.get('context').update({'default_branch_id': inv.branch_id.id})
#         return result



class account_voucher(models.Model):

    _inherit = 'account.voucher'

    @api.model
    def _get_voucher_default_branch(self):
        user_obj = self.env['res.users']
        branch_id = user_obj.browse(self.env.uid).branch_id.id  or False
        return branch_id

    branch_id = fields.Many2one('res.branch', 'Branch', required=True, default = _get_voucher_default_branch)







   

    



class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def default_get(self, fields):
        items = []
        rec = super(AccountPayment, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        if active_model or active_ids:
            invoices = self.env[active_model].browse(active_ids)
            rec['branch_id'] = invoices[0].branch_id.id
        return rec

    branch_id = fields.Many2one('res.branch', string='Branch', )

    def _get_counterpart_move_line_vals(self, invoice=False):
        
        res = super(AccountPayment, self)._get_counterpart_move_line_vals(invoice=invoice)
        res.update({
            'branch_id' : self.branch_id.id,
            })
        return res
    
    def _get_liquidity_move_line_vals(self, amount):
        user_pool =  self.env['res.users']
        res = super(AccountPayment, self)._get_liquidity_move_line_vals(amount)
        res.update({'branch_id':self.branch_id.id })
        return res



# class account_invoice_refund(models.TransientModel):
#    
#     _inherit = 'account.invoice.refund'
# 
#     @api.model
#     def _get_invoice_refund_default_branch(self):
#         if self._context.get('active_id'):
#             ids = self._context.get('active_id')
#             user_pool = self.env['account.invoice']
#             branch_id = user_pool.browse(self.env.uid).branch_id and user_pool.browse(ids).branch_id.id or False
#             return branch_id
# 
# 
#     branch_id = fields.Many2one('res.branch', 'Branch', default = _get_invoice_refund_default_branch , required=True)






class account_invoice_line(models.Model):

    _inherit = 'account.invoice.line'

    branch_id  = fields.Many2one('res.branch', 'Branch')



class account_bank_statement(models.Model):

    _inherit = 'account.bank.statement'

    @api.model
    def _get_bank_statement_default_branch(self):
        user_pool = self.env['res.users']
        branch_id = user_pool.browse(self.env.uid).branch_id.id  or False
        return branch_id

    branch_id = fields.Many2one('res.branch', 'Branch', default=_get_bank_statement_default_branch ,required=True)



class account_bank_statement_line(models.Model):


    _inherit = 'account.bank.statement.line'

    @api.model
    def _get_bank_statement_default_branch(self):
        user_pool = self.env['res.users']
        branch_id = user_pool.browse(self.env.uid).branch_id.id  or False
        return branch_id



    branch_id = fields.Many2one('res.branch', 'Branch', related='statement_id.branch_id', default=_get_bank_statement_default_branch ,required=True)



    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        """ Match statement lines with existing payments (eg. checks) and/or payables/receivables (eg. invoices and credit notes) and/or new move lines (eg. write-offs).
            If any new journal item needs to be created (via new_aml_dicts or counterpart_aml_dicts), a new journal entry will be created and will contain those
            items, as well as a journal item for the bank statement line.
            Finally, mark the statement line as reconciled by putting the matched moves ids in the column journal_entry_ids.

            :param self: browse collection of records that are supposed to have no accounting entries already linked.
            :param (list of dicts) counterpart_aml_dicts: move lines to create to reconcile with existing payables/receivables.
                The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'move_line'
                    # The move line to reconcile (partially if specified debit/credit is lower than move line's credit/debit)

            :param (list of recordsets) payment_aml_rec: recordset move lines representing existing payments (which are already fully reconciled)

            :param (list of dicts) new_aml_dicts: move lines to create. The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'account_id'
                - (optional) 'tax_ids'
                - (optional) Other account.move.line fields like analytic_account_id or analytics_id

            :returns: The journal entries with which the transaction was matched. If there was at least an entry in counterpart_aml_dicts or new_aml_dicts, this list contains
                the move created by the reconciliation, containing entries for the statement.line (1), the counterpart move lines (0..*) and the new move lines (0..*).
        """
        counterpart_aml_dicts = counterpart_aml_dicts or []
        payment_aml_rec = payment_aml_rec or self.env['account.move.line']
        new_aml_dicts = new_aml_dicts or []

        aml_obj = self.env['account.move.line']

        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        st_line_currency = self.currency_id or statement_currency

        counterpart_moves = self.env['account.move']

        # Check and prepare received data
        if any(rec.statement_id for rec in payment_aml_rec):
            raise UserError(_('A selected move line was already reconciled.'))
        for aml_dict in counterpart_aml_dicts:
            if aml_dict['move_line'].reconciled:
                raise UserError(_('A selected move line was already reconciled.'))
            if isinstance(aml_dict['move_line'], pycompat.integer_types):
                aml_dict['move_line'] = aml_obj.browse(aml_dict['move_line'])
        for aml_dict in (counterpart_aml_dicts + new_aml_dicts):
            if aml_dict.get('tax_ids') and isinstance(aml_dict['tax_ids'][0], pycompat.integer_types):
                # Transform the value in the format required for One2many and Many2many fields
                aml_dict['tax_ids'] = [(4, id, None) for id in aml_dict['tax_ids']]
        if any(line.journal_entry_ids for line in self):
            raise UserError(_('A selected statement line was already reconciled with an account move.'))

        # Fully reconciled moves are just linked to the bank statement
        total = self.amount
        for aml_rec in payment_aml_rec:
            total -= aml_rec.debit - aml_rec.credit
            aml_rec.write({'statement_line_id': self.id,'branch_id': self.branch_id.id})
            counterpart_moves = (counterpart_moves | aml_rec.move_id)

        # Create move line(s). Either matching an existing journal entry (eg. invoice), in which
        # case we reconcile the existing and the new move lines together, or being a write-off.
        if counterpart_aml_dicts or new_aml_dicts:
            st_line_currency = self.currency_id or statement_currency
            st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False

            # Create the move
            self.sequence = self.statement_id.line_ids.ids.index(self.id) + 1
            move_vals = self._prepare_reconciliation_move(self.statement_id.name)
            move_vals.update({'branch_id': self.branch_id.id})
            move = self.env['account.move'].create(move_vals)
            counterpart_moves = (counterpart_moves | move)

            # Create The payment
            payment = self.env['account.payment']
            if abs(total)>0.00001:
                partner_id = self.partner_id and self.partner_id.id or False
                partner_type = False
                if partner_id:
                    if total < 0:
                        partner_type = 'supplier'
                    else:
                        partner_type = 'customer'

                payment_methods = (total>0) and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
                currency = self.journal_id.currency_id or self.company_id.currency_id
                payment = self.env['account.payment'].create({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': total >0 and 'inbound' or 'outbound',
                    'partner_id': self.partner_id and self.partner_id.id or False,
                    'partner_type': partner_type,
                    'journal_id': self.statement_id.journal_id.id,
                    'payment_date': self.date,
                    'state': 'reconciled',
                    'branch_id': self.branch_id.id,
                    'currency_id': currency.id,
                    'amount': abs(total),
                    'communication': self._get_communication(payment_methods[0] if payment_methods else False),
                    'name': self.statement_id.name,
                })

            # Complete dicts to create both counterpart move lines and write-offs
            to_create = (counterpart_aml_dicts + new_aml_dicts)
            ctx = dict(self._context, date=self.date)
            for aml_dict in to_create:
                aml_dict['move_id'] = move.id
                aml_dict['branch_id'] = self.branch_id.id
                aml_dict['partner_id'] = self.partner_id.id
                aml_dict['statement_line_id'] = self.id
                if st_line_currency.id != company_currency.id:
                    aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
                    aml_dict['currency_id'] = st_line_currency.id
                    if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                        # Statement is in company currency but the transaction is in foreign currency
                        aml_dict['debit'] = company_currency.round(aml_dict['debit'] / st_line_currency_rate)
                        aml_dict['credit'] = company_currency.round(aml_dict['credit'] / st_line_currency_rate)
                    elif self.currency_id and st_line_currency_rate:
                        # Statement is in foreign currency and the transaction is in another one
                        aml_dict['debit'] = statement_currency.with_context(ctx).compute(aml_dict['debit'] / st_line_currency_rate, company_currency)
                        aml_dict['credit'] = statement_currency.with_context(ctx).compute(aml_dict['credit'] / st_line_currency_rate, company_currency)
                    else:
                        # Statement is in foreign currency and no extra currency is given for the transaction
                        aml_dict['debit'] = st_line_currency.with_context(ctx).compute(aml_dict['debit'], company_currency)
                        aml_dict['credit'] = st_line_currency.with_context(ctx).compute(aml_dict['credit'], company_currency)
                elif statement_currency.id != company_currency.id:
                    # Statement is in foreign currency but the transaction is in company currency
                    prorata_factor = (aml_dict['debit'] - aml_dict['credit']) / self.amount_currency
                    aml_dict['amount_currency'] = prorata_factor * self.amount
                    aml_dict['currency_id'] = statement_currency.id

            # Create write-offs
            # When we register a payment on an invoice, the write-off line contains the amount
            # currency if all related invoices have the same currency. We apply the same logic in
            # the manual reconciliation.
            counterpart_aml = self.env['account.move.line']
            for aml_dict in counterpart_aml_dicts:
                counterpart_aml |= aml_dict.get('move_line', self.env['account.move.line'])
            new_aml_currency = False
            if counterpart_aml\
                    and len(counterpart_aml.mapped('currency_id')) == 1\
                    and counterpart_aml[0].currency_id\
                    and counterpart_aml[0].currency_id != company_currency:
                new_aml_currency = counterpart_aml[0].currency_id
            for aml_dict in new_aml_dicts:
                aml_dict['payment_id'] = payment and payment.id or False
                if new_aml_currency and not aml_dict.get('currency_id'):
                    aml_dict['currency_id'] = new_aml_currency.id
                    aml_dict['amount_currency'] = company_currency.with_context(ctx).compute(aml_dict['debit'] - aml_dict['credit'], new_aml_currency)
                aml_obj.with_context(check_move_validity=False, apply_taxes=True).create(aml_dict)

            # Create counterpart move lines and reconcile them
            for aml_dict in counterpart_aml_dicts:
                if aml_dict['move_line'].partner_id.id:
                    aml_dict['partner_id'] = aml_dict['move_line'].partner_id.id
                aml_dict['account_id'] = aml_dict['move_line'].account_id.id
                aml_dict['payment_id'] = payment and payment.id or False

                counterpart_move_line = aml_dict.pop('move_line')
                if counterpart_move_line.currency_id and counterpart_move_line.currency_id != company_currency and not aml_dict.get('currency_id'):
                    aml_dict['currency_id'] = counterpart_move_line.currency_id.id
                    aml_dict['amount_currency'] = company_currency.with_context(ctx).compute(aml_dict['debit'] - aml_dict['credit'], counterpart_move_line.currency_id)
                new_aml = aml_obj.with_context(check_move_validity=False).create(aml_dict)

                (new_aml | counterpart_move_line).reconcile()

            # Balance the move
            st_line_amount = -sum([x.balance for x in move.line_ids])
            aml_dict = self._prepare_reconciliation_move_line(move, st_line_amount)
            aml_dict['payment_id'] = payment and payment.id or False
            aml_obj.with_context(check_move_validity=False).create(aml_dict)

            move.post()
            #record the move name on the statement line to be able to retrieve it in case of unreconciliation
            self.write({'move_name': move.name})
            payment and payment.write({'payment_reference': move.name})
        elif self.move_name:
            raise UserError(_('Operation not allowed. Since your statement line already received a number, you cannot reconcile it entirely with existing journal entries otherwise it would make a gap in the numbering. You should book an entry and make a regular revert of it in case you want to cancel it.'))
        counterpart_moves.assert_balanced()
        return counterpart_moves


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
