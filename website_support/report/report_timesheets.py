# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportTimesheet(models.AbstractModel):
    _name = 'report.website_support.report_timesheets'

    def get_timesheets(self, docs):
        """input : name of employee and the starting date and ending date
        output: timesheets by that particular employee within that period and the total duration"""

        if docs.from_date and docs.to_date:
            rec = self.env['account.analytic.line'].search([('user_id', '=', docs.employee[0].id),
                                                        ('date', '>=', docs.from_date),('date', '<=', docs.to_date)])
        elif docs.from_date:
            rec = self.env['account.analytic.line'].search([('user_id', '=', docs.employee[0].id),
                                                        ('date', '>=', docs.from_date)])
        elif docs.to_date:
            rec = self.env['account.analytic.line'].search([('user_id', '=', docs.employee[0].id),
                                                            ('date', '<=', docs.to_date)])
        else:
            rec = self.env['account.analytic.line'].search([('user_id', '=', docs.employee[0].id)])
        records = []
        total = 0
        for r in rec:
            vals = {'project': r.project_id.name,
                    'user': r.user_id.partner_id.name,
                    'duration': r.unit_amount,
                    'date': r.date,
                    }
            total += r.unit_amount
            records.append(vals)
        return [records, total]

    @api.model
    def render_html(self, docids, data=None):
        """we are overwriting this function because we need to show values from other models in the report
        we pass the objects in the docargs dictionary"""

        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        identification = []
        for i in self.env['hr.employee'].search([('user_id', '=', docs.employee[0].id)]):
            if i:
                identification.append({'id': i.identification_id, 'name': i.name_related})

        timesheets = self.get_timesheets(docs)
        # print "wwwwwwwwwwwwwwwww" , timesheets
        period = None
        if docs.from_date and docs.to_date:
            period = "From " + str(docs.from_date) + " To " + str(docs.to_date)
        elif docs.from_date:
            period = "From " + str(docs.from_date)
        elif docs.from_date:
            period = " To " + str(docs.to_date)
        docargs = {
           'doc_ids': self.ids,
           'doc_model': self.model,
           'docs': docs,
           'timesheets': timesheets[0],
           'total': timesheets[1],
           'company': docs.employee[0].company_id.name,
           'identification': identification,
           'period': period,
        }
        return self.env['report'].render('website_support.report_timesheets', docargs)
