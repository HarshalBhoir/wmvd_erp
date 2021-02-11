from openerp import models, fields, api, _, tools
from openerp.exceptions import UserError, Warning, ValidationError
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

import logging
import xmlrpclib
import sys
from openerp.exceptions import UserError , ValidationError

_logger = logging.getLogger(__name__)

import shutil
import os
import time
import psycopg2
import urllib
import tarfile

import json
import odoo.http as http
from odoo.http import request
from odoo.addons.web.controllers.main import ExcelExport


class sale_register_report(models.Model):
    _name = 'sale.register.report'
    _description = "Sale Register Report"


    name = fields.Char(string="Name")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    partner_id = fields.Many2one( 'res.partner', string="Partner")
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('generated', 'Generated'), ('printed', 'Printed')],
                             default='draft')
    lines_one2many = fields.One2many('sale.register.line','register_id',string="Line Details" , ondelete='cascade')
    config_id = fields.Many2one('external.db.configuration', string='Database', track_visibility='onchange',  
    default=lambda self: self.env['external.db.configuration'].search([('id', '!=', 0)], limit=1))
    report_name = fields.Char(string="Report Name")

  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True
    
    @api.multi
    def get_data(self):
        conn_pg = None
        print "[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[["
        if self.partner_id and self.config_id:
            print "oooooooooooo"
            if not self.partner_id.c_bpartner_id:
                raise UserError("Kindly update idempiere ID for partner")
            partner_id=self.partner_id.c_bpartner_id
            date_from =self.date_from
            date_to = self.date_to


            print "#-------------Select --TRY----------------------#"
            try:
                conn_pg = psycopg2.connect(dbname= self.config_id.database_name, user=self.config_id.username, password=self.config_id.password, host= self.config_id.ip_address)
                pg_cursor = conn_pg.cursor()

                pg_cursor.execute("select (select c_order.documentno from c_order where c_order.c_order_id = inv.c_order_id ),\
                inv.documentno,inv.POReference ,inv.DateAcct,inv.totallines,\
                (select sum(ct.taxamt) from C_InvoiceTax ct where ct.C_Invoice_ID = inv.C_Invoice_ID  ) as taxamount,\
                (select sum(line.TotalPriceList) from c_invoiceline line  where line.C_Invoice_ID = inv.C_Invoice_ID and COALESCE(line.c_charge_id::text, '') <> '' ) as otherexpense,\
                inv.RoundFactor, inv.grandtotal\
                from c_invoice inv where inv.c_bpartner_id = %s and inv.dateacct between %s and %s ",(partner_id,date_from,date_to))
                records = pg_cursor.fetchall()


                if len(records) == 0:
                    raise UserError("No records Found")

                for record in records:
                    vals_line = {
                      'register_id':self.id,
                      'sale_order_no':record[0],
                      'document_no':record[1],
                      'invoice_no':record[2],
                      'doc_date':record[3],
                      'total_lines':record[4],
                      'tax_amount':record[5],
                      'other_expenses':record[6],
                      'round_off':record[7],
                      'grandtotal':record[8],
                      
                    }
                    self.env['sale.register.line'].create(vals_line)
                    self.state = 'generated'
                    daymonthfrom = datetime.strptime(date_from, "%Y-%m-%d")
                    daymonthto = datetime.strptime(date_to, "%Y-%m-%d")
                    dayfrom = daymonthfrom.strftime("%d")
                    dayto = daymonthto.strftime("%d")
                    monthfrom = daymonthfrom.strftime("%b")
                    monthto = daymonthto.strftime("%b")
                    yearfrom = int(daymonthfrom.strftime("%y"))
                    yearto = daymonthto.strftime("%y")
                    self.name = self.partner_id.name + ' (' + str(dayfrom) + str(monthfrom) + str(yearfrom) \
                    + ' - '+ str(dayto) + str(monthto) + str(yearto) + ' )'

            except psycopg2.DatabaseError, e:
                if conn_pg:
                    print "#-------------------Except----------------------#"
                    conn_pg.rollback()

                print 'Error %s' % e    

            finally:
                if conn_pg:
                    print "#--------------Select ----Finally----------------------#"
                    conn_pg.close()

        else:
            raise UserError("DB Configuration not found.")

    @api.multi
    def print_report(self):
        
        self.ensure_one()
        status = ''
        # self.sudo().unlink()
        if self.date_from and self.date_to:
            if not self.attachment_id:
                pending_order_ids = []
                order_list = []
                # file_name = self.name + '.xls'
                workbook = xlwt.Workbook(encoding='utf-8')
                worksheet = workbook.add_sheet('Sale Register Report')
                fp = StringIO()
                
                main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz center; borders: bottom thick, top thick, left thick, right thick')
                sp_style = xlwt.easyxf('font: bold on, height 350;')
                header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
                base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
                base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')
                
                worksheet.write_merge(0, 1, 0, 9, self.name ,main_style)
                row_index = 2
                
                worksheet.col(0).width = 3000
                worksheet.col(1).width = 8000
                worksheet.col(2).width = 8000
                worksheet.col(3).width = 8000
                worksheet.col(4).width = 8000
                worksheet.col(5).width = 6000
                worksheet.col(6).width = 6000
                worksheet.col(7).width = 6000
                worksheet.col(8).width = 6000
                worksheet.col(9).width = 6000

                
                # Headers
                header_fields = ['Sr.No','Sale Order No','Document No','Inv. No.','Doc. Date','Total Lines','Tax','Other Expenses','Round Off','GrandTotal']
                row_index += 1
                                
                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1

                line_ids = self.env['sale.register.line'].sudo().search([('register_id','=',self.id)])

                if (not line_ids):
                    raise Warning(_('Record Not Found'))

                if line_ids:
                    count = 0        
                    for line_id in line_ids:
                        new_index = row_index

                        if line_id:
                            count +=1
                            worksheet.write(row_index, 0,count, base_style)
                            worksheet.write(row_index, 1,line_id.sale_order_no,  base_style)
                            worksheet.write(row_index, 2,line_id.document_no,  base_style)
                            worksheet.write(row_index, 3,line_id.invoice_no or '',  base_style)
                            worksheet.write(row_index, 4,line_id.doc_date or '',  base_style)
                            worksheet.write(row_index, 5,line_id.total_lines or '',  base_style)
                            worksheet.write(row_index, 6,line_id.tax_amount or '',  base_style)
                            worksheet.write(row_index, 7,line_id.other_expenses or '',  base_style)
                            worksheet.write(row_index, 8,line_id.round_off or '',  base_style)
                            worksheet.write(row_index, 9,line_id.grandtotal or '',  base_style)

                          
                            row_index += 1

                row_index +=1
                workbook.save(fp)


            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'printed','report': out,'report_name':'sale_register_report.xls'})


class sale_register_line(models.Model):
    _name = 'sale.register.line'
    _description = "Sale Register line"

    name = fields.Char('Name')
    register_id = fields.Many2one('sale.register.report', string='connect')
    sale_order_no = fields.Char('Sale Order No')
    document_no = fields.Char('Document No')
    invoice_no = fields.Char('Inv. No.')
    doc_date = fields.Char('Doc. Date')
    cust_state = fields.Char('Cust. State')
    cust_code = fields.Char('Cust. Code')
    cust_name = fields.Char('Cust. Name')
    state_code = fields.Char('State Code')
    total_lines = fields.Float('Total Lines')
    total_accessible_value = fields.Float('Total Accessible Value')
    cgst = fields.Float('CGST_CGST')
    igst = fields.Float('IGST_IGST')
    sgst = fields.Float('SGST_SGST')
    tax = fields.Float('Tax')
    tax_amount = fields.Float('Total Tax')
    other_expenses = fields.Float('Other Expenses')
    round_off = fields.Float('Round Off')
    grandtotal = fields.Float('GrandTotal')
