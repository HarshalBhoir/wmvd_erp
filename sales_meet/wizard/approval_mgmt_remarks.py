# # -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import base64
import csv
import cStringIO


class ApprovalMgmtWizard(models.TransientModel):

    _name = "approval.management.approval.wizard"
    _description = "Request Approval Remarks wizard"

    remarks = fields.Char(string='Remarks', required=True)

    @api.multi
    def approve_approval_request(self):
        self.ensure_one()

        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        approval_management = self.env['approval.management'].browse(active_ids)
        approval_management.approve_approval_request(self.remarks)
        return {'type': 'ir.actions.act_window_close'}
