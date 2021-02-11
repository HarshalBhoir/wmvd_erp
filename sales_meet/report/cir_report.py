from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta , date
from cStringIO import StringIO
import xlwt
import re
import base64


class cir_report(models.TransientModel):
    _name = 'cir.report'
    _description = "CIR Details Report"


    name = fields.Char(string="CirDetailsReport", compute="_get_name")
    date_from = fields.Date(string="Date From", default=lambda self: fields.datetime.now())
    date_to = fields.Date(string="Date To", default=lambda self: fields.datetime.now())
    attachment_id = fields.Many2one( 'ir.attachment', string="Attachment", ondelete='cascade')
    datas = fields.Binary(string="XLS Report", related="attachment_id.datas")
    user_id = fields.Many2one( 'res.users', string="User")
    user_ids = fields.Many2many('res.users', 'cir_details_report_res_user_rel', string='Users')
    cir_id = fields.Many2one('cir.extension', 'CIR')
    report = fields.Binary('Prepared file', filters='.xls', readonly=True)
    state = fields.Selection([('choose', 'choose'), ('get', 'get')],
                             default='choose')
    export_file = fields.Char(string="Export")
    status = fields.Selection([
            ('draft', 'Draft'),
            ('done', 'Submitted'),
            ('tse_approved', 'TSE Approved'),
            ('lab_approved', 'LAB Approved'),
            ('zsm_approved', 'ZSM Approved'),
            ('product_head_approved', 'Product Head Approved'),
            ('closed', 'Closed'),
        ], string='Status')


  
    @api.constrains('date_from','date_to')
    @api.depends('date_from','date_to')
    def date_range_check(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date should be before or be the same as End Date."))
        return True
    
    @api.depends('date_from','date_to')
    @api.multi
    def _get_name(self):
        rep_name = "CIR_Details_Report"
        if self.date_from and self.date_to and  not self.name:
            date_from = datetime.strptime(self.date_from, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            date_to = datetime.strptime(self.date_to, tools.DEFAULT_SERVER_DATE_FORMAT).strftime('%d-%b-%Y')
            if self.date_from == self.date_to:
                rep_name = "CIR Details Report(%s)" % (date_from,)
            else:
                rep_name = "CIR Details Report(%s|%s)" % (date_from, date_to)
        self.name = rep_name


    @api.multi
    def print_report(self):
        
        self.ensure_one()
        if self.date_from and self.date_to:
            if not self.attachment_id:
                pending_order_ids = []
                order_list = []
                workbook = xlwt.Workbook(encoding='utf-8')
                worksheet = workbook.add_sheet('CIR Details')
                fp = StringIO()
                
                main_style = xlwt.easyxf('font: bold on, height 400; align: wrap 1, vert centre, horiz left; borders: bottom thick, top thick, left thick, right thick')
                sp_style = xlwt.easyxf('font: bold on, height 350;')
                header_style = xlwt.easyxf('font: bold on, height 220; align: wrap 1,  horiz center; borders: bottom thin, top thin, left thin, right thin')
                base_style = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin')
                base_style_gray = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color gray_ega;')
                base_style_yellow = xlwt.easyxf('align: wrap 1; borders: bottom thin, top thin, left thin, right thin; pattern: pattern fine_dots, fore_color white, back_color red;')
                
                worksheet.write_merge(0, 1, 0, 34, self.name ,main_style)
                row_index = 2
                
                worksheet.col(0).width = 2000
                worksheet.col(1).width = 4000
                worksheet.col(2).width = 4000
                worksheet.col(3).width = 16000
                worksheet.col(4).width = 16000
                worksheet.col(5).width = 14000
                worksheet.col(6).width = 6000
                worksheet.col(7).width = 4000
                worksheet.col(8).width = 6000
                worksheet.col(9).width = 6000
                worksheet.col(10).width = 5000
                worksheet.col(11).width = 6000
                worksheet.col(12).width = 16000
                worksheet.col(13).width = 5000
                worksheet.col(14).width = 5005
                worksheet.col(15).width = 5000
                worksheet.col(16).width = 4000
                worksheet.col(17).width = 4000
                worksheet.col(18).width = 4000
                worksheet.col(19).width = 6000
                worksheet.col(20).width = 6000
                worksheet.col(21).width = 6000
                worksheet.col(22).width = 6000
                worksheet.col(23).width = 6000
                worksheet.col(24).width = 3000
                worksheet.col(25).width = 8000
                worksheet.col(26).width = 8000
                worksheet.col(27).width = 8000
                worksheet.col(28).width = 12000
                worksheet.col(29).width = 4000
                worksheet.col(30).width = 12000
                worksheet.col(31).width = 4000
                worksheet.col(32).width = 12000
                worksheet.col(33).width = 4000
                worksheet.col(34).width = 8000
                worksheet.col(35).width = 12000
                worksheet.col(36).width = 4000
                worksheet.col(37).width = 12000
                worksheet.col(38).width = 4000
                worksheet.col(39).width = 8000


                
                # Headers
                header_fields = ['Sr.No',
                                'Complaint No',
                                'Code',
                                'Customer Name',
                                'Address',
                                'Retailer/ Project / Site',
                                'State',
                                'Zone',
                                'Customer Group',
                                'Batch No',
                                'Complaint Received Date',
                                'Complaint Type',
                                'Product',
                                'Extent of Complaint (Bags)',
                                'Source of Supply',
                                'Invoice No',
                                'Invoice Date',
                                'Invoice Value',
                                'Quantity Supplied',
                                'Status of Material (Sent to LAB)',
                                'Courier name',
                                'POD details',
                                'Application Date',
                                'Sales Remark',
                                'Code',
                                'Sales Executive',
                                'Manager Name',
                                'TSE Name',
                                'TSE Remark',
                                'TSE Updated Date',
                                'LAB Remark',
                                'LAB Updated Date',
                                'Product Head Remark',
                                'Product Head Updated Date',
                                'ASM/RSM/ZSM Name',
                                'HO Remark',
                                'HO Updated Date',
                                'Conclusion']

                row_index += 1
                
            #     # https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py
                
                for index, value in enumerate(header_fields):
                    worksheet.write(row_index, index, value, header_style)
                row_index += 1

                user_id = [user.id for user in self.user_ids]
                
                cir_rec = self.env['cir.extension']

                if not self.user_ids:
                    cir_ids = cir_rec.sudo().search([('complaint_received_date','>=',self.date_from),
                                                     ('complaint_received_date','<=',self.date_to)])
                else:
                    cir_ids = cir_rec.sudo().search([('salesuser_id','in',user_id),
                                                     ('complaint_received_date','>=',self.date_from),
                                                     ('complaint_received_date','<=',self.date_to)])


                if self.status:
                    cir_ids = cir_ids.sudo().search([('state','=',self.status)])

               
                if (not cir_ids):
                    raise Warning(_('Record Not Found'))

                if cir_ids:
                    conclusion = ''
                    count = 0
                    for cir_id in cir_ids:
                        new_index = row_index

                        if cir_id:

                            product_name = [(product.name + ', ' )for product in cir_id.product_id]

                            if cir_id.conclusion:
                                if cir_id.credit_note_amount:
                                    conclusion =  cir_id.conclusion + ' - ' + str(cir_id.credit_note_amount)
                                if cir_id.replacement_bags:
                                    conclusion =  cir_id.conclusion + ' - ' + str(cir_id.replacement_bags)
                                if cir_id.other_conclusion:
                                    conclusion =  cir_id.conclusion + ' - ' + cir_id.other_conclusion
                            else:
                                conclusion = ''

                            employee_ids = self.env['hr.employee'].sudo().search([
                                ('user_id','=',cir_id.salesuser_id.id),
                                '|',('active','=',False),('active','=',True)], limit=1)
                            
                            count +=1
                            worksheet.write(row_index,0,count, base_style )
                            worksheet.write(row_index,1,cir_id.name  or '',  base_style )
                            worksheet.write(row_index,2,cir_id.partner_id.bp_code  or '',  base_style )
                            worksheet.write(row_index,3,cir_id.partner_id.name  or '',  base_style )
                            worksheet.write(row_index,4,cir_id.partner_address or '',  base_style )
                            worksheet.write(row_index,5,cir_id.lead_id.name or '',  base_style )
                            worksheet.write(row_index,6,cir_id.state_id.name or '',  base_style )
                            worksheet.write(row_index,7,cir_id.zone or '',  base_style )
                            worksheet.write(row_index,8,cir_id.partner_group_id.name or '',  base_style )
                            worksheet.write(row_index,9,cir_id.batch_no or '',  base_style )
                            worksheet.write(row_index,10,cir_id.complaint_received_date or '',  base_style )
                            worksheet.write(row_index,11,cir_id.complaint_id.name or '',  base_style )
                            worksheet.write(row_index,12,product_name or '',  base_style )
                            worksheet.write(row_index,13,cir_id.complaint_extent or '',  base_style )
                            worksheet.write(row_index,14,cir_id.source_id.name or '',  base_style )
                            worksheet.write(row_index,15,cir_id.invoice_no or '',  base_style )
                            worksheet.write(row_index,16,cir_id.invoice_date or '',  base_style )
                            worksheet.write(row_index,17,cir_id.invoice_value or '',  base_style )
                            worksheet.write(row_index,18,cir_id.quantity_supplied or '',  base_style )
                            worksheet.write(row_index,19,cir_id.material_status or '',  base_style )
                            worksheet.write(row_index,20,cir_id.courier_details or '',  base_style )
                            worksheet.write(row_index,21,cir_id.pod_details or '',  base_style )
                            worksheet.write(row_index,22,cir_id.applicator_date or '',  base_style )
                            worksheet.write(row_index,23,cir_id.salesperson_remark or '',  base_style )
                            worksheet.write(row_index,24,employee_ids.emp_id or '',  base_style )
                            worksheet.write(row_index,25,cir_id.salesuser_id.name or '',  base_style )
                            worksheet.write(row_index,26,cir_id.manager_id.name or '',  base_style )
                            worksheet.write(row_index,27,cir_id.investigator_id.name or '',  base_style )
                            worksheet.write(row_index,28,cir_id.tse_remark or '',  base_style )
                            worksheet.write(row_index,29,cir_id.investigation_date or '',  base_style )
                            worksheet.write(row_index,30,cir_id.lab_remark or '',  base_style )
                            worksheet.write(row_index,31,cir_id.lab_date or '',  base_style )
                            worksheet.write(row_index,32,cir_id.product_head_remark or '',  base_style )
                            worksheet.write(row_index,33,cir_id.product_head_date or '',  base_style )
                            worksheet.write(row_index,34,cir_id.zsm_id.name or '',  base_style )
                            worksheet.write(row_index,35,cir_id.ho_remark or '',  base_style )
                            worksheet.write(row_index,36,cir_id.ho_date or '',  base_style )
                            worksheet.write(row_index,37,conclusion or '',  base_style )


                            row_index += 1

                row_index +=1
                workbook.save(fp)


            out = base64.encodestring(fp.getvalue())
            self.write({'state': 'get','report': out,'export_file':self.name+'.xls'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'cir.report',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }
