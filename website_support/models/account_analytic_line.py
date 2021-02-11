# -*- coding: utf-8 -*-
# Copyright 2015 Camptocamp SA - Guewen Baconnier
# Copyright 2017 Tecnativa, S.L. - Luis M. Ontalba
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from __future__ import division

import math
from datetime import timedelta

from odoo import models, fields, api, exceptions, _
from odoo.tools.float_utils import float_compare


def float_time_convert(float_val):
    hours = math.floor(abs(float_val))
    mins = abs(float_val) - hours
    mins = round(mins * 60)
    if mins >= 60.0:
        hours = hours + 1
        mins = 0.0
    return '%02d:%02d' % (hours, mins)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    ticket_id = fields.Many2one('website.support.ticket', string='Ticket', track_visibility='onchange', domain="[('status', '!=','completed'),('subject', '!=','False')]")

    support_ticket_id = fields.Many2one('website.support.ticket', string='Ticket', track_visibility='onchange', domain="[('status', '!=','completed'),('subject', '!=','False')]")
    person_name = fields.Char(related="support_ticket_id.person_name", string="Customer Name")
    ticket_number_display = fields.Char(related="support_ticket_id.ticket_number_display", string="Ticket Number")
    state = fields.Many2one('website.support.ticket.states', readonly=True, related="support_ticket_id.state", string="State")
    open_time = fields.Datetime(related="support_ticket_id.create_date", string="Open Time")    
    close_time = fields.Datetime(related="support_ticket_id.close_time", string="Close Time")
    planned_hours = fields.Float(string='Initially Planned Hours', related="task_id.planned_hours", help='Estimated time to do the task, usually set by the project manager when the task is in draft state.')    
    remaining_hours = fields.Float(string='Remaining Hours', related="task_id.remaining_hours", digits=(16,2), help="Total remaining time, can be re-estimated periodically by the assignee of the task.")    
    total_hours = fields.Float(string='Total', related="task_id.total_hours", help="Computed as: Time Spent + Remaining Time.")
    effective_hours = fields.Float(string='Hours Spent', related="task_id.effective_hours", help="Computed using the sum of the task work done.")


    time_start = fields.Float(string='Begin Hour')
    time_stop = fields.Float(string='End Hour')
    status = fields.Selection([('inprogress', 'In Progress'),
                        ('10%', '10 %'),
                        ('30%', '30 %'),
                        ('50%', '50 %'),
                        ('80%', '80 %'),
                       ('completed', 'Completed')], string='Status')

    kra_category_id = fields.Many2one('kr.kra.category', string="KRA")


    # @api.onchange('date')
    # def _onchange_date(self):
    #     for res in self:
    #         if res.date:
    #             employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
    #             category_id = [x.category_id.id for x in employee_id.kra_id.line_ids]
    #             print "ooooooooooooooooooooooooooooooooooooooooooo" , category_id


    #             return {'domain': {
    #                 'kra_category_id': [('id','in',category_id)],
    #                 # ('user_id', 'in', [res.env.uid]),('expense_date', 'in', [res.date]),('name','!=',False)
    #             }}

    @api.one
    @api.constrains('time_start', 'time_stop', 'unit_amount')
    def _check_time_start_stop(self):
        start = timedelta(hours=self.time_start)
        stop = timedelta(hours=self.time_stop)
        if stop < start:
            raise exceptions.ValidationError(
                _('The beginning hour (%s) must '
                  'precede the ending hour (%s).') %
                (float_time_convert(self.time_start),
                 float_time_convert(self.time_stop))
            )
        hours = (stop - start).seconds / 3600
        if (hours and
                float_compare(hours, self.unit_amount, precision_digits=4)):
            raise exceptions.ValidationError(
                _('The duration (%s) must be equal to the difference '
                  'between the hours (%s).') %
                (float_time_convert(self.unit_amount),
                 float_time_convert(hours))
            )
        # check if lines overlap
        others = self.search([
            ('id', '!=', self.id),
            ('user_id', '=', self.user_id.id),
            ('date', '=', self.date),
            ('time_start', '<', self.time_stop),
            ('time_stop', '>', self.time_start),
        ])
        if others:
            message = _("Lines can't overlap:\n")
            message += '\n'.join(['%s - %s' %
                                  (float_time_convert(line.time_start),
                                   float_time_convert(line.time_stop))
                                  for line
                                  in (self + others).sorted(
                                      lambda l: l.time_start
                                  )])
            raise exceptions.ValidationError(message)

    @api.onchange('time_start', 'time_stop')
    def onchange_hours_start_stop(self):
        start = timedelta(hours=self.time_start)
        stop = timedelta(hours=self.time_stop)
        if stop < start:
            return
        self.unit_amount = (stop - start).seconds / 3600


class hr_timesheet_sheet_sheet(models.Model):
    _inherit = 'hr_timesheet_sheet.sheet'

    
    @api.multi
    def update_ticket(self):

        for res in self.timesheet_ids:

            if res.ticket_id:
                write_data = self.env['website.support.ticket'].search([('id', '=', res.ticket_id.id)]).sudo().write({
                                                            'status': res.status,
                                                            })

                create_data = self.env['ticket.activity.log.list'].sudo().create({
                                                            'ticket_id': res.ticket_id.id,
                                                            'name': res.name,
                                                            'list_ticket_id': res.ticket_id.id,
                                                            'user_id': res.user_id.id,
                                                            })


