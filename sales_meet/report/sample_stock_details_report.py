from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import datetime
from datetime import datetime, timedelta , date
import time
from cStringIO import StringIO
import xlwt
import base64

class sampling_details_report(models.TransientModel):
    _name = 'sampling.details.report'
    _description = "sampling Details Report"


    name = fields.Char(string="samplingDetailsReport")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    user_ids = fields.Many2many('res.users', 'sampling_details_report_res_user_rel', string='Users')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    partner_id = fields.Many2one('res.partner',string="Distributor / Retailer" )

  
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

            rep_name = "sampling_Details_Report"
            if  not self.name:
                date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
                if self.date_from == self.date_to:
                    rep_name = "Sampling Details Report(%s)" % (date_from,)
                else:
                    rep_name = "Sampling Details Report(%s|%s)" % (date_from, date_to)
            self.name = rep_name

            workbook = xlwt.Workbook(encoding='utf-8')
            worksheet = workbook.add_sheet('Sampling Details')
            fp = StringIO()
            
            main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1; borders: bottom thick, top thick, left thick, right thick')
            sp_style = xlwt.easyxf('font: bold on, height 350;')
            header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
            base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
            base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
            base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color yellow;')
            
            worksheet.write_merge(0, 1, 0, 14, self.name ,main_style)
            row_index = 2
            
            worksheet.col(0).width = 3000
            worksheet.col(1).width = 4000
            worksheet.col(2).width = 4000
            worksheet.col(3).width = 12000
            worksheet.col(4).width = 5000
            worksheet.col(5).width = 5000
            worksheet.col(6).width = 5000
            worksheet.col(7).width = 4000
            worksheet.col(8).width = 14000
            worksheet.col(9).width = 5000
            worksheet.col(10).width = 5000
            worksheet.col(11).width = 5000
            worksheet.col(12).width = 18000
            worksheet.col(13).width = 4000
            worksheet.col(14).width = 10000
            
            # Headers
            header_fields = [
                            'Sr.No',
                            'Sample No',
                            'Partner Code',
                            'Distributer / Retailer',
                            'State',
                            'Dateordered',
                            'Documentno',
                            'Product Code',
                            'Product',
                            'UOM',
                            'Quantity(Kg)',
                            'Grandtotal',
                            'Deliveryadd',
                            'Emp Code',
                            'User',
                            
                            ]
            row_index += 1
            
        #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
            
            for index, value in enumerate(header_fields):
                worksheet.write(row_index, index, value, header_style)
            row_index += 1

            if self.partner_id:
                sample_issuance_id = self.env['sample.issuance'].sudo().search([('partner_id','=',self.partner_id.id)])
            else:
                sample_issuance_id = self.env['sample.issuance'].sudo().search([])
            
            if (not sample_issuance_id):
                raise Warning(_('Records Not Found'))

            if sample_issuance_id:

                count = 0        
                for rec in sample_issuance_id:
                    po_date = ''
                    new_index = row_index

                    if rec:
                        issuance_lines = rec.sample_issuance_line_one2many.search([
                                ('sample_issuance_id','=',rec.id),
                                ('dateordered','>=',self.date_from),
                                ('dateordered','<=',self.date_to)])

                        if issuance_lines:

                            count +=1
                            worksheet.write(row_index, 0,count, base_style_gray )
                            worksheet.write(row_index, 1,rec.name  or '',  base_style_gray )
                            worksheet.write(row_index, 2,rec.partner_id.bp_code  or '',  base_style_gray )
                            worksheet.write(row_index, 3,rec.partner_id.name or '',  base_style_gray )
                            worksheet.write(row_index, 4,rec.partner_id.state_id.name or '',  base_style_gray )

    
                            for record in issuance_lines:

                                employee_ids = self.env['hr.employee'].sudo().search([
                                        ('user_id','=',record.user_id.id),
                                        '|',('active','=',False),('active','=',True)])

                                print "KKKKKKKKKKKKKKKKKKKK" , record.dateordered , self.date_from , self.date_to , type(record.dateordered), type(self.date_from), type(self.date_to)

                                worksheet.write(row_index, 5,record.dateordered or '',  base_style_yellow )
                                worksheet.write(row_index, 6,record.documentno or '',  base_style_yellow )
                                worksheet.write(row_index, 7,record.product_id.value or '',  base_style_yellow )
                                worksheet.write(row_index, 8,record.product_id.name or '',  base_style_yellow )
                                worksheet.write(row_index, 9,record.product_id.uom_id.name or '',  base_style_yellow )
                                worksheet.write(row_index, 10,record.quantity or '',  base_style_yellow )
                                worksheet.write(row_index, 11,record.grandtotal or '',  base_style_yellow )
                                worksheet.write(row_index, 12,record.deliveryadd or '',  base_style_yellow )
                                worksheet.write(row_index, 13,employee_ids.emp_id or '',  base_style_yellow )
                                worksheet.write(row_index, 14,record.user_id.name or '',  base_style_yellow )
                        
                                row_index += 1

                            # row_index += 1


            row_index +=1
            workbook.save(fp)


        out = base64.encodestring(fp.getvalue())
        self.write({'state': 'get','report': out,'name':rep_name+'.xls'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sampling.details.report',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'target': 'new',
        }