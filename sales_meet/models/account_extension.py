# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError , ValidationError

class account_payment_term_extension(models.Model):
    _inherit = "account.payment.term"

    netdays = fields.Char('Net Days')
    c_paymentterm_id = fields.Char('Idempiere ID')
    value = fields.Char('Search Key')

class AccountMoveExtension(models.Model):
    _inherit = "account.move"

    @api.multi
    def _post_validate(self):
        for move in self:
            if move.line_ids:
                if not any([x.company_id.id == move.company_id.id for x in move.line_ids]):
                    raise UserError(_("Cannot create moves for different companies."))
        self.assert_balanced()
        return self._check_lock_date()