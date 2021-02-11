from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

import datetime
from datetime import datetime, timedelta , date
import time
from dateutil import relativedelta
from cStringIO import StringIO
import xlwt
import re
import base64
import pytz

import json
import odoo.http as http
from odoo.http import request
from odoo.addons.web.controllers.main import ExcelExport


class exec_sampling_details_report(models.TransientModel):
    _name = 'exec.sampling.details.report'
    _description = "Sampling Details Report"


    name = fields.Char(string="ExecSamplingDetailsReport")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    user_ids = fields.Many2many('res.users', 'exec_sampling_details_report_res_user_rel', string='Users')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    partner_id = fields.Many2one('res.partner',string="Distributor / Retailer" )
    status = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Generated'),
        ('refused', 'Refused'),
        ('approved', 'Approved'),
        ('posted', 'Posted'),
        ], string='Status',
        copy=False, index=True, track_visibility='always', default='draft')

  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True


    @api.multi
    def print_report(self):
        file = StringIO()
        today_date = str(date.today())

        self.ensure_one()
        status = ''

        rep_name = "exec_sampling_details_Report"
        if self.date_from and self.date_to and  not self.name:
            date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            if self.date_from == self.date_to:
                rep_name = "Exec Sampling Details Report(%s)" % (date_from,)
            else:
                rep_name = "Exec Sampling Details Report(%s|%s)" % (date_from, date_to)
        self.name = rep_name

        order_list = []
        second_heading = approval_status = ''
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Sample Report')
        fp = StringIO()
        row_index = 0

        main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
        sp_style = xlwt.easyxf('font: bold on, height 350;')
        header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
        base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
        base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
        base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')
        base_style_red = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')

        worksheet.col(0).width = 2000
        worksheet.col(1).width = 4000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 4000
        worksheet.col(4).width = 6000
        worksheet.col(5).width = 12000
        worksheet.col(6).width = 6000
        worksheet.col(7).width = 8000
        worksheet.col(8).width = 6000
        worksheet.col(9).width = 6000
        worksheet.col(10).width = 6000
        worksheet.col(11).width = 6000
        worksheet.col(12).width = 6000
        worksheet.col(13).width = 6001

        worksheet.col(14).width = 6002
        worksheet.col(15).width = 6003
        worksheet.col(16).width = 6004
        worksheet.col(17).width = 6005
        worksheet.col(18).width = 6006
        worksheet.col(19).width = 6007
        worksheet.col(20).width = 6008
        worksheet.col(21).width = 12000
        worksheet.col(22).width = 12000
        worksheet.col(23).width = 4002
        worksheet.col(24).width = 5003



        # Headers
        header_fields = [
                        'SrNo.',
                        'Date',
                        'Applicator',
                        'Sales Person Code',
                        'Sales Person',
                        'Product',
                        'Qty in KG',
                        'Project Name',
                        'Status',
                        'Contact No.',
                        'Applicator No.',
                        'Total Cost',
                        'Sample No.',
                        'Document No.',

                        'Contact Person',
                        'City',
                        'Project Size',
                        'Order Qty',
                        'Order Amt',
                        'Ratings',
                        'Follow Up Date',
                        'Cust Feedback',
                        'Distributor',
                        'Partner Code',
                        'State',
                        ]
        # row_index += 1
     
        for index, value in enumerate(header_fields):
            worksheet.write(row_index, index, value, base_style_yellow)



        if self.user_id:
            if self.status:
                exec_sample_issuance_id = self.env['sample.requisition'].sudo().search([
                    ('user_id','=',self.user_id.id),
                    ('date_sample','>=',self.date_from),
                    ('date_sample','<=',self.date_to),
                    ('state','=',self.status),
                    ])
            else:


                exec_sample_issuance_id = self.env['sample.requisition'].sudo().search([
                        ('user_id','=',self.user_id.id),
                        ('date_sample','>=',self.date_from),
                        ('date_sample','<=',self.date_to)
                        ])

        else:
            if self.status:
                exec_sample_issuance_id = self.env['sample.requisition'].sudo().search([
                    ('date_sample','>=',self.date_from),
                    ('date_sample','<=',self.date_to),
                    ('state','=',self.status),
                    ])

            else:
                exec_sample_issuance_id = self.env['sample.requisition'].sudo().search([
                        ('date_sample','>=',self.date_from),
                        ('date_sample','<=',self.date_to)
                        ])



        row_index += 1

        count = 1

        for res in exec_sample_issuance_id:

                employee_ids = self.env['hr.employee'].sudo().search([
                                ('user_id','=',res.user_id.id),'|',('active','=',False),('active','=',True)], limit=1)

                worksheet.write(row_index, 0,count, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 1,res.date_sample, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 2,res.applicator, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 3,employee_ids.emp_id  or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 4,res.user_id.name, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 5,res.product_id.name, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 6,res.total_quantity, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 7,res.lead_id.name or res.project_partner_id.name, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 8,res.state, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 9,res.contact_no, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 10,res.applicator_no, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 11,res.applicator_cost, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 12,res.name, base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 13,res.name  or '', base_style_red if res.state=='draft' else base_style )

                worksheet.write(row_index, 14,res.contact_person  or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 15,res.city  or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 16,res.project_size  or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 17,res.order_quantity  or '' , base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 18,res.order_amt  or '' , base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 19,res.set_priority  or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 20,res.followup_date  or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 21,res.customer_feedback or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 22,res.partner_id.name or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 23,res.partner_id.bp_code or '', base_style_red if res.state=='draft' else base_style )
                worksheet.write(row_index, 24,res.partner_id.state_id.name or '', base_style_red if res.state=='draft' else base_style )

            
                row_index += 1
                count += 1


        row_index +=1
        workbook.save(fp)



        out = base64.encodestring(fp.getvalue())
        self.write({'state': 'get','report': out,'name':self.name+'.xls'})
        # print error
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'exec.sampling.details.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new',
        }
    

