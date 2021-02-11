from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import datetime
from datetime import datetime, timedelta , date
import time
from cStringIO import StringIO
import xlwt
import base64

class approved_payment_report(models.TransientModel):
    _name = 'approved.invoice.report'
    _description = "Approved Invoice Report"


    name = fields.Char(string="Approved_Payment_Report")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    owner_id = fields.Many2one('erp.representative.approver', string='Owner' )
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    company_id = fields.Many2one('res.company', string='Company')

  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True
    

    @api.multi
    def print_report(self):
        
        self.ensure_one()
        status = ''
        # self.sudo().unlink()
        if self.date_from and self.date_to:

            rep_name = "Approved Invoice Report"
            if  not self.name:
                date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                if self.date_from == self.date_to:
                    rep_name = "Approved Invoice Report(%s)" % (date_from,)
                else:
                    rep_name = "Approved Invoice Report(%s-%s)" % (date_from, date_to)
            self.name = rep_name

            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet(rep_name)
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; \
                    borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center, vertical center; \
                borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color gray_ega;' )
            base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
            base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
            base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; \
                pattern: pattern fine_dots, fore_color white, back_color yellow;')
            
            worksheet.write_merge(0, 1, 0, 14, self.name ,main_style)
            row_index = 2
            
            worksheet.col(0).width = 2000
            worksheet.col(1).width = 3000
            worksheet.col(2).width = 6000
            worksheet.col(3).width = 10000
            worksheet.col(4).width = 10000
            worksheet.col(5).width = 6000
            worksheet.col(6).width = 2000
            worksheet.col(7).width = 5000
            worksheet.col(8).width = 5000
            worksheet.col(9).width = 3000
            worksheet.col(10).width = 12000
            worksheet.col(11).width = 5000
            worksheet.col(12).width = 5000
            worksheet.col(13).width = 5000
            worksheet.col(14).width = 3000

            
            # Headers
            header_fields = [
                'Sr No.',
                'Date',
                'Doc',
                'Owner',
                'User',
                'Client',
                'Inv No.',
                'Date Account',
                'DocumentNo',
                'Code',
                'Beneficiary',
                'Total',
                'Allocated Amt',
                'Unallocated Amt',
                'Due Days',
                ]
            row_index += 1
            
        #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
            
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

            if self.owner_id:
                bank_payment_id = self.env['bank.payment'].sudo().search([('date','>=',self.date_from),
                                                                      ('date','<=',self.date_to),
                                                                      ('state','=', 'approved'),
                                                                      ('company_id','=', self.company_id.id),
                                                                      ('owner_id','=', self.owner_id.id)])
            else:
                bank_payment_id = self.env['bank.payment'].sudo().search([('date','>=',self.date_from),
                                                                      ('date','<=',self.date_to),
                                                                      ('state','=', 'approved'),
                                                                      ('company_id','=', self.company_id.id)])
            
            if (not bank_payment_id):
                raise Warning(_('Records Not Found'))

            if bank_payment_id:

                count = 0        
                for rec in bank_payment_id:
                    po_date = ''
                    new_index = row_index

                    if rec:
                        issuance_lines = rec.invoice_filter_one2many

                        if issuance_lines:

                            count +=1
                            worksheet.write(row_index, 0,count, base_style_gray )
                            worksheet.write(row_index, 1,rec.date  or '',  base_style_gray )
                            worksheet.write(row_index, 2,rec.name  or '',  base_style_gray )
                            worksheet.write(row_index, 3,rec.owner_id.owner_id.name or '',  base_style_gray )
                            worksheet.write(row_index, 4,rec.user_id.name or '',  base_style_gray )
                            worksheet.write(row_index, 5,rec.company_id.name or '',  base_style_gray )

                            count2 = 0
                            for record in issuance_lines:
                                count2 +=1

                                worksheet.write(row_index, 6,count2, base_style_yellow )
                                worksheet.write(row_index, 7, record.value_date , base_style_yellow )
                                worksheet.write(row_index, 8, record.documentno, base_style_yellow )
                                worksheet.write(row_index, 9, record.customercode, base_style_yellow )
                                worksheet.write(row_index, 10, record.beneficiary_name, base_style_yellow )
                                worksheet.write(row_index, 11, str(abs(record.totalamt)), base_style_yellow )
                                worksheet.write(row_index, 12, str(abs(record.allocatedamt)), base_style_yellow )
                                worksheet.write(row_index, 13, str(abs(record.unallocated)), base_style_yellow )
                                worksheet.write(row_index, 14, record.duedays, base_style_yellow )
                        
                                row_index += 1

                            row_index += 1


            row_index +=1
            workbook.save(fp)


        out = base64.encodestring(fp.getvalue())
        self.write({'state': 'get','report': out,'name':rep_name+'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approved.invoice.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new',
        }