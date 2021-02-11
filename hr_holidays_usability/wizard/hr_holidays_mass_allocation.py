# -*- coding: utf-8 -*-
# © 2015-2017 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import dateutil.parser
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, date




class HrHolidaysMassAllocation(models.TransientModel):
    _name = 'hr.holidays.mass.allocation'
    _description = 'Wizard for mass allocation of holidays'

    @api.model
    def _default_employees(self):
        return self.env['hr.employee'].search([
            ('holiday_exclude_mass_allocation', '=', False),
            ('company_id', '=', self.env.user.company_id.id),
            ])

    @api.model
    def _get_default_holiday_status(self):
        res = self.env.user.company_id.\
            mass_allocation_default_holiday_status_id or False
        return res

    number_of_days = fields.Float(
        string='Number of Days', required=True, default=2.08)
    holiday_status_id = fields.Many2one(
        'hr.holidays.status', string='Leave Type', required=True,
        default=_get_default_holiday_status)
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees', default=_default_employees)
    auto_approve = fields.Boolean(
        string='Automatic Approval', default=True)
    # size=64 because the name field of hr.holidays is size=64
    name = fields.Char('Description', size=64)

    _sql_constraints = [(
        'number_of_days_positive',
        'CHECK (number_of_days > 0)',
        'The number of days must be positive',
        )]

    @api.multi
    def run(self):
        self.ensure_one()
        if not self.number_of_days:
            raise UserError(_(
                'You must set a value for the number of days.'))
        if not self.employee_ids:
            raise UserError(_(
                'You must select at least one employee.'))
        alloc_hol_ids = []
        hho = self.env['hr.holidays']
        auto_approve = self.auto_approve
        for employee in self.employee_ids:
            hol = hho.create({
                'name': self.name,
                'number_of_days_temp': self.number_of_days,
                'employee_id': employee.id,
                'type': 'add',
                'holiday_type': 'employee',
                'holiday_status_id': self.holiday_status_id.id,
                'state': 'confirm',
                'mass_leave':True,
                })
            if auto_approve:
                hol.with_context(no_email_notification=True).action_validate()
            alloc_hol_ids.append(hol.id)
        action = self.env['ir.actions.act_window'].for_xml_id(
            'hr_holidays', 'open_allocation_holidays')
        action.update({
            'target': 'current',
            'domain': [('id', 'in', alloc_hol_ids)],
            'nodestroy': True,
            'context': "{'default_type':'add'}",
            })
        return action


    @api.model
    @api.multi
    def process_casual_leave_monthly_queue(self):
        alloc_hol_ids = []
        hho = self.env['hr.holidays']
        holidays_id = self.env['hr.holidays.status'].search([("name","=",'Casual Leaves')])
        employee_id = self.env['hr.employee'].search([("state","=",'joined')])
        
        today = datetime.now() - timedelta(days=1 )
        schedular_month = today.strftime("%b")
        month_name = datetime.now().strftime("%b")
       
        for employee in employee_id:
            number_of_days = 1
            date_of_joining = datetime.strptime(employee.date_of_joining, '%Y-%m-%d')
            
            date_of_joining_month = date_of_joining.strftime("%b")
            date_of_joining_day = date_of_joining.strftime("%d")
            
            if str(schedular_month) == str(date_of_joining_month):
                number_of_days = 0
                if int(date_of_joining_day) >= 15:
                    number_of_days = 1
                else:
                    number_of_days = 0.5

            hol = hho.create({
                'name': 'Casual Leaves for ' + str(month_name),
                'number_of_days_temp': number_of_days,
                'employee_id': employee.id,
                'type': 'add',
                'holiday_type': 'employee',
                'holiday_status_id': holidays_id.id,
                'state': 'confirm',
                'mass_leave':True,
                })
            hol.with_context(no_email_notification=True).action_validate()
            alloc_hol_ids.append(hol.id)
        action = self.env['ir.actions.act_window'].for_xml_id(
            'hr_holidays', 'open_allocation_holidays')
        action.update({
            'target': 'current',
            'domain': [('id', 'in', alloc_hol_ids)],
            'nodestroy': True,
            'context': "{'default_type':'add'}",
            })

        return action

    @api.model
    @api.multi
    def process_privilege_leave_monthly_queue(self):
        alloc_hol_ids = []
        hho = self.env['hr.holidays']
        holidays_id = self.env['hr.holidays.status'].search([("name","=",'Privilege Leaves')])
        employee_id = self.env['hr.employee'].search([("state","=",'joined')])
        
        today = datetime.now() - timedelta(days=1 )
        schedular_month = today.strftime("%b")
        month_name = datetime.now().strftime("%b")
       
        for employee in employee_id:
            number_of_days = 2
            date_of_joining = datetime.strptime(employee.date_of_joining, '%Y-%m-%d')
            
            date_of_joining_month = date_of_joining.strftime("%b")
            date_of_joining_day = date_of_joining.strftime("%d")
            
            if str(schedular_month) == str(date_of_joining_month):
                number_of_days = 0
                if int(date_of_joining_day) >= 15:
                    number_of_days = 2
                else:
                    number_of_days = 1

            hol = hho.create({
                'name': 'Privilege Leaves for ' + str(month_name),
                'number_of_days_temp': number_of_days,
                'employee_id': employee.id,
                'type': 'add',
                'holiday_type': 'employee',
                'holiday_status_id': holidays_id.id,
                'state': 'confirm',
                'mass_leave':True,
                })
            hol.with_context(no_email_notification=True).action_validate()
            alloc_hol_ids.append(hol.id)
        action = self.env['ir.actions.act_window'].for_xml_id(
            'hr_holidays', 'open_allocation_holidays')
        action.update({
            'target': 'current',
            'domain': [('id', 'in', alloc_hol_ids)],
            'nodestroy': True,
            'context': "{'default_type':'add'}",
            })

        return action


    @api.model
    @api.multi
    def process_casual_leave_yearly_queue(self):
        alloc_hol_ids = []
        hho = self.env['hr.holidays']
        holidays_id = self.env['hr.holidays.status'].search([("name","=",'Casual Leaves')])
        employee_id = self.env['hr.employee'].search([("state","=",'employment')])
        year_name = datetime.now().strftime("%Y")
    
        for employee in employee_id:
            
            hol = hho.create({
                'name': 'Casual Leaves for Year ' + str(year_name),
                'number_of_days_temp': 6,
                'employee_id': employee.id,
                'type': 'add',
                'holiday_type': 'employee',
                'holiday_status_id': holidays_id.id,
                'state': 'confirm',
                'mass_leave':True,
                })
            hol.with_context(no_email_notification=True).action_validate()
            alloc_hol_ids.append(hol.id)
        action = self.env['ir.actions.act_window'].for_xml_id(
            'hr_holidays', 'open_allocation_holidays')
        action.update({
            'target': 'current',
            'domain': [('id', 'in', alloc_hol_ids)],
            'nodestroy': True,
            'context': "{'default_type':'add'}",
            })

        return action

    @api.model
    @api.multi
    def process_privilege_leave_monthly_confirmed_queue(self):
        alloc_hol_ids = []
        hho = self.env['hr.holidays']
        holidays_id = self.env['hr.holidays.status'].search([("name","=",'Privilege Leaves')])
        employee_id = self.env['hr.employee'].search([("state","=",'employment')])

        month_name = datetime.now().strftime("%b")
       
        for employee in employee_id:
            
            hol = hho.create({
                'name': 'Privilege Leaves for '  + str(month_name),
                'number_of_days_temp': 2,
                'employee_id': employee.id,
                'type': 'add',
                'holiday_type': 'employee',
                'holiday_status_id': holidays_id.id,
                'state': 'confirm',
                'mass_leave':True,
                })
            hol.with_context(no_email_notification=True).action_validate()
            alloc_hol_ids.append(hol.id)
        action = self.env['ir.actions.act_window'].for_xml_id(
            'hr_holidays', 'open_allocation_holidays')
        action.update({
            'target': 'current',
            'domain': [('id', 'in', alloc_hol_ids)],
            'nodestroy': True,
            'context': "{'default_type':'add'}",
            })

        return action