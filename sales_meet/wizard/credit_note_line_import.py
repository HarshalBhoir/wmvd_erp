# # -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import base64
import csv
import cStringIO


class WizardImport(models.TransientModel):
    _name = 'wizard.import'
    _description = 'Import CN Lines'

    @api.model
    def _default_cn_id(self):
        if '_default_cn_id' in self._context:
            return self._context['default_cn_id']
        if self._context.get('active_model') == 'credit.note':
            return self._context.get('active_id')
        return False

    data = fields.Binary('File',attachment=True , required=True)
    name = fields.Char('Filename')
    delimeter = fields.Char('Delimeter', default=',',
                            help='Default delimeter is ","')
    cn_id = fields.Many2one('credit.note', default=_default_cn_id)
    
    @api.multi
    def add_lines(self):
        """Load credit_note Line data from the CSV file."""
        ctx = self.env.context
        credit_note_obj = self.env['credit.note']
        credit_note_line_obj = self.env['credit.note.line']
        charge_obj = self.env['credit.note.charge']
        org_obj = self.env['org.master']
        partner_ids = self.env['res.partner']
        
        credit_note = credit_note_obj
        if 'active_id' in ctx:
            credit_note = credit_note_obj.browse(ctx['active_id'])

        todaydate = "{:%Y-%m-%d}".format(datetime.now())

        cn_name = 'Normal Credit Note (' + todaydate + ')'

        # Decode the file data
        if credit_note.state == 'draft':
            data = base64.b64decode(self.data)
            file_input = cStringIO.StringIO(data)
            file_input.seek(0)
            reader_info = []
            if self.delimeter:
                delimeter = str(self.delimeter)
            else:
                delimeter = ','
            reader = csv.reader(file_input, delimiter=delimeter,lineterminator='\r\n')
            try:
                reader_info.extend(reader)
            except Exception:
                reader_info.extend(reader)
                raise exceptions.Warning(_("Not a valid file!"))
            keys = reader_info[0]
            # check if keys exist
            if not isinstance(keys, list) or ('Organisation' not in keys or
                                              'Code' not in keys or
                                              'Charge' not in keys or
                                              'Description' not in keys or
                                              'Amount' not in keys ):
                raise exceptions.Warning(
                    _("'Organisation' or 'Code' or 'Charge' or 'Description'  keys not found"))
            del reader_info[0]
            values = {}
            # credit_note.write({'imported': True,})
            
            for i in range(len(reader_info)):
                val = {}
                field = reader_info[i]
                values = dict(zip(keys, field))
    
                charge_list = charge_obj.search([('name', '=',values['Charge'])], limit= 1)
                if charge_list:
                    val['charge_id'] = charge_list[0].id
                    val['charge_name'] = charge_list[0].name
                

                org_list = org_obj.search([('name', '=',values['Organisation'])], limit= 1)
                if org_list:
                    val['ad_org_id'] = org_list[0].id
                    val['ad_org'] = org_list[0].name

                partner_list = partner_ids.search([('bp_code', '=',values['Code'])], limit= 1)
                if partner_list:
                    val['partner_id'] = partner_list[0].id
                    val['beneficiary_name'] = partner_list[0].name

                
                val['beneficiary_code'] = values['Code']
                val['description'] = values['Description']
                val['totalamt'] = values['Amount']
                val['value_date'] = date.today()
                val['company_id'] = self.cn_id.company_id.id
                # val['check_lines'] = True
     
                val['credit_note_id'] = credit_note.id

                credit_note.write({'check_lines': True,'name':cn_name})
                
                credit_lines = credit_note_line_obj.create(val)

                # tax_obj.tax_id = prod_tax
                
        else:
            raise exceptions.Warning(_("Credit Note can be imported only in 'Draft' Stage"))
