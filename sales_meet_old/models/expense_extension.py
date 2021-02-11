from odoo.tools.translate import _
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo import tools, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT , DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _
import logging
from odoo.osv import  osv
from odoo import SUPERUSER_ID
from time import gmtime, strftime
from openerp.exceptions import UserError , ValidationError
import dateutil.parser
from werkzeug import url_encode
# import requests
# import urllib
# import simplejson


class expense_extension(models.Model):
    _inherit = "hr.expense"

    def _default_grade(self):
        employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
        grade = self.env['hr.employee'].sudo().search([('id', '=', employee_id.id)]).grade_id.id
        return grade

    def _default_work_location(self):
        return self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1).work_location

    @api.multi
    def _compute_can_edit_name(self):
        self.can_edit_name = self.env.user.sudo().has_group('sales_meet.group_expense_manager_user')
        print "1111111111111111111111111111111111111111 _compute_can_edit_name"



    meeting_id = fields.Many2one("calendar.event", string="Meeting" ) #,  domain=[('user_id', 'in',[self.env.uid])]
    name = fields.Char(string='Expense Description', required=False) # related="product_id.name" ,
    grade_id = fields.Many2one("grade.master", string="Grade" , default=_default_grade, store=True, track_visibility='onchange' ) #related="employee_id.grade_id" 
    grade_amount = fields.Float(string='Amount allocated' , compute='_compute_grade_amount' , store=True, track_visibility='onchange')
    fixed_asset = fields.Boolean("Fixed Asset", store=True, track_visibility='onchange', compute='_compute_grade_amount')
    unit_amount = fields.Float(string='Unit Price', store=True, track_visibility='onchange', readonly=False )
    week_no = fields.Char(string='Week' , compute='_onchange_date' , store=True, track_visibility='onchange' , readonly=False )
    backdate_alert = fields.Boolean("Back Dated Record", store=True, track_visibility='onchange')
    work_location = fields.Char(string='Work Location', default=_default_work_location, store=True, track_visibility='onchange' , readonly=False )
    idempere_no = fields.Char(string='Idempiere No' , store=True, track_visibility='onchange' , readonly=False )
    meeting_address = fields.Char(string='Meeting Address', related="meeting_id.reverse_location" , store=True, track_visibility='onchange' , readonly=False )
    claimed_amount = fields.Float(string='Claimed Amount', store=True, track_visibility='onchange', readonly=False )
    expense_attachments = fields.Many2many('ir.attachment', 'expense_attachments_rel' , copy=False, attachment=True)
    manager_id = fields.Many2one('hr.employee', string="Manager" , related="employee_id.parent_id")
    meeting_boolean = fields.Boolean("Meeting Bool" , default=False )
    once_only = fields.Boolean("Only Once")
    product_id = fields.Many2one('product.product', string='Product', 
         domain=[('can_be_expensed', '=', True)], required=True)
    # readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]},



    can_edit_name = fields.Boolean(compute='_compute_can_edit_name')
    posted_bool = fields.Boolean('Posted', default=False)


    @api.multi
    def unlink(self):
        for order in self:
            if order.state != 'draft'  and self.env.uid != 1:
                raise UserError(_('You can only Delete Draft Entries'))
        return super(expense_extension, self).unlink()


    @api.multi
    def submit_expenses(self):
        if any(expense.state != 'draft' for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report!"))

        employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)])


        print "-------------------------- employee_id --------------------------" , employee_id

        if self.total_amount == 0.0:
            raise UserError(_("You cannot Submit expense with 0.0 Rs !"))

        expense_ids = self.env['hr.expense'].search([
                                                    ('employee_id', '=', self.employee_id.id),
                                                    ('product_id', '=', self.product_id.id),
                                                    ('date', '=', self.date),
                                                    ('once_only','=',True)])
        # ,('meeting_id', '=', self.meeting_id.id) ('state', 'not in', ('draft','refused')),
        print "gggggggggggggggggggggggggggggggggggg" ,  self.employee_id , expense_ids
        if len(expense_ids) > 1:
            raise UserError(_("Expense Already Created for '%s' - Dated %s" %(self.product_id.name, self.date)))

        expense_ids2 = self.env['hr.expense'].search([
                                                    ('employee_id', '=', self.employee_id.id),
                                                    ('product_id', '=', self.product_id.id),
                                                    ('date', '=', self.date),
                                                    ('meeting_id', '=', self.meeting_id.id)])


        print "========================== expense_ids2 ========================== " , expense_ids2


        print "lllllllllllllllllllllllllllllllllllllll" , expense_ids2

        if len(expense_ids2) > 1:
            raise UserError(_("Expense Already Created for '%s' for this meeting dated - %s" %(self.product_id.name, self.date)))


        return {
             'type': 'ir.actions.act_window',
             'view_mode': 'form',
             'res_model': 'hr.expense.sheet',
             'target': 'new',
             'context': {
                 'default_expense_line_ids': [line.id for line in self],
                 'default_employee_id': self[0].employee_id.id,
                 'default_name': self[0].name if len(self.ids) == 1 else '',
                 'default_expense_meeting_id': self[0].meeting_id.id,
             }
        }
        # 'target': 'current',


    @api.onchange('claimed_amount')
    def _onchange_claimed_amount(self):
        if self.claimed_amount:
            self.unit_amount = self.claimed_amount
            # self.claimed_amount = 0.0


    @api.onchange('product_id')
    def _onchange_product_id(self):
        amount = 0.0
        fixed_asset = False
        if self.product_id:
            if not self.name:
                self.name = self.product_id.display_name or ''

            grade_ids = self.env['grade.master'].sudo().search([('id', '=', self.grade_id.id)])
            for line_ids in grade_ids.grade_line_ids:
                for lines in line_ids:
                    if lines.name.id == self.product_id.id:

                        amount = lines.value
                        fixed_asset = lines.fixed_asset
                        if lines.fixed_asset:
                            self.unit_amount = amount
                            self.claimed_amount = amount

            # self.unit_amount = amount
            # self.claimed_amount = amount
            daymonth = datetime.strptime(self.date, "%Y-%m-%d")
            month2 = daymonth.strftime("%b")
            day = daymonth.strftime("%d")
            week_day = daymonth.strftime("%a")
            year = daymonth.strftime("%y")
            self.name = self.product_id.name + ' ' + str(day) + ' ' + str(month2) + ' ' + str(week_day) + ' ' + str(year) 
            # self.fixed_asset = fixed_asset
            # self.grade_amount = amount
            self.product_uom_id = self.product_id.uom_id
            self.tax_ids = self.product_id.supplier_taxes_id
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            if account:
                self.account_id = account


    # @api.one
    @api.depends('product_id')
    def _compute_grade_amount(self):
        print "DDDDDDDDDDDDDDDDDDDDDDDD _compute_grade_amount  DDDDDDDDDDDDDDDDDDDD"
        grade_amount = 0.0
        fixed_asset = False
        once_only = False
        for res in self:
            grade_ids = self.env['grade.master'].sudo().search([('id', '=', res.grade_id.id)])
            for line_ids in grade_ids.grade_line_ids:
                for lines in line_ids:
                    if lines.name.id == res.product_id.id:
                        grade_amount = lines.value
                        fixed_asset = lines.fixed_asset
                        once_only = lines.once_only

        self.grade_amount = grade_amount
        self.fixed_asset = fixed_asset
        self.once_only =  once_only


    # @api.onchange('unit_amount')
    # @api.depends('grade_amount')
    # def onchange_unit_amount(self):
    #     print "Unit Amount !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" , self.grade_amount , self.unit_amount
    #     if self.unit_amount:

    @api.model
    def create(self, vals):
        
        result = super(expense_extension, self).create(vals)

        create_date = dateutil.parser.parse(result.create_date).date()
        back_date = create_date - timedelta(days=15 ) 
        expense_date = datetime.strptime(result.date, '%Y-%m-%d').date()
        if expense_date < back_date:
            result.backdate_alert = True

        return result



    @api.onchange('date')
    def _onchange_date(self):
        for res in self:
            if res.date and res.meeting_boolean == False:
                datey = res.date
                today = datetime.now()
                daymonth = datetime.strptime(datey, "%Y-%m-%d")
                month2 = daymonth.strftime("%b")
                week_number2 = (daymonth.day - 1) // 7 + 1
                # day_of_month = datetime.now().day
                # month = datetime.now().strftime("%b")
                # today = datetime.now()
                # week_number = (day_of_month - 1) // 7 + 1
                # create_date = datetime.strptime(self.create_date + 15, "%Y-%m-%d")

                res.week_no =  month2 + ' ' + str(week_number2) + ' Week'
                res.meeting_id = ''

            return {'domain': {
                'meeting_id': [('user_id', 'in', [res.env.uid]),('expense_date', 'in', [res.date]),
                ('name','!=',False),'|',('active','=',False),('active','!=',False)]}}


class HrExpenseSheetExtension(models.Model):

    _inherit = "hr.expense.sheet"

    @api.multi
    def _compute_can_edit_name(self):
        print "1111111111111111111111111111111111111111 _compute_can_edit_name"
        self.can_edit_name = self.env.user.has_group('sales_meet.group_expense_manager_user')

    parent_boolean = fields.Boolean("Manager approval", store=True, track_visibility='onchange')

    state = fields.Selection([('submit', 'Submitted'),
                              ('manager_approve', 'Manager Approved'),
                              ('approve', 'Approved'),
                              ('post', 'Posted'),
                              ('done', 'Paid'),
                              ('cancel', 'Refused')
                              ], string='Status', index=True, readonly=True, track_visibility='onchange', copy=False, default='submit', required=True,
        help='Expense Report State')

    parent_id = fields.Many2one('hr.employee', string="Manager" )
    expense_note = fields.Text(string="Expense Note" ,readonly=True)
    meeting_id = fields.Integer('Expense Meeting')
    reason = fields.Text(string="Reason", readonly=True ) #
    expense_meeting_id = fields.Many2one("calendar.event", string="Meeting" ) #,  domain=[('user_id', 'in',[self.env.uid])]
    expense_date  = fields.Date(string="Expense Date")
    meeting_date  = fields.Date(string="Meeting Date")
    expense_submit = fields.Boolean("Submitted", store=True)
    manager_approve = fields.Char(string="", default="Manager Approval Needed")
    approve_date  = fields.Date(string="Approve Date")
    can_edit_name = fields.Boolean(compute='_compute_can_edit_name')
    meeting_address = fields.Char(string='Meeting Address', store=True )



    @api.multi
    def unlink(self):
        for order in self:
            if order.state  and self.env.uid != 1:
                raise UserError(_("You can't Delete Submitted Entries"))
        return super(HrExpenseSheetExtension, self).unlink()

    @api.model 
    def action_save(self,context):
        # self.ensure_one()
        
        write_data = self.search([('id', '=', context[0])]).sudo().write(
            {'expense_date': date.today(), 'expense_submit': True})

        return {'type': 'ir.actions.act_window_close'}


    @api.multi
    def action_get_meeting(self):
        print "iiiiiiiiiiiiiiiiiiiiiiiiiiiiiii" , self.expense_meeting_id.id
        meeting_ids = self.env['calendar.event'].search([("id","=",self.expense_meeting_id.id)])
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('sales_meet.action_calendar_event_crm')
        list_view_id = imd.xmlid_to_res_id('sales_meet.view_calendar_event_tree_extension')
        form_view_id = imd.xmlid_to_res_id('sales_meet.view_calendar_event_form_extension')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'],
                [False, 'graph'], [False, 'kanban'], [False, 'pivot']],
            'target': action.target,
            
            'context': action.context,
            'res_model': action.res_model,
        }
        # 'target': action.target,
        if len(meeting_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % meeting_ids.ids
        elif len(meeting_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = meeting_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


    @api.multi
    def approve_expense_sheets(self):
        if not self.user_has_groups('hr_expense.group_hr_expense_user'):
            raise UserError(_("Only HR Officers can approve expenses"))
        self.sudo().write({'state': 'approve', 'responsible_id': self.env.user.id, 'approve_date':date.today()})




    @api.multi
    def approve_expense_sheets_manager(self):
        expense_manager = self.env.user.has_group('sales_meet.group_expense_manager_user')
        if str(self.parent_id.work_email) == str(self.env.user.login) or self.env.user.has_group('sales_meet.group_expense_manager_user') or self.env.uid == 1:
            self.sudo().write({'state': 'manager_approve', 'responsible_id': self.env.user.id, 'approve_date':date.today()})
        else:
            raise UserError("Only %s 's manager (%s) or Expense Manager can approve his expenses" %(self.employee_id.name,self.employee_id.parent_id.name))
        
    
    @api.multi
    def refuse_expenses(self, reason):
        if not  (str(self.parent_id.work_email) == str(self.env.user.login) \
            or  self.env.user.has_group('sales_meet.group_expense_manager_user')) \
            and self.env.uid != 1:
            # print "jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj"
            raise UserError(_("Only Expense Managers can refuse expenses"))
        self.sudo().write({'state': 'cancel','reason':reason})
        for sheet in self:
            body = (_("Your Expense %s has been refused.<br/><ul class=o_timeline_tracking_value_list><li>Reason<span> : \
             </span><span class=o_timeline_tracking_value>%s</span></li></ul>") % (sheet.name, reason))
            sheet.sudo().message_post(body=body)
        


    @api.model
    def create(self, vals):
        result = super(HrExpenseSheetExtension, self).create(vals)
        manager_users = []
        for res in result:
            for rec in result.expense_line_ids:
                res.meeting_date = result.expense_line_ids.meeting_id.expense_date
                res.meeting_address = result.expense_line_ids.meeting_address
            	res.expense_note = 'Meeting :  ' + result.expense_line_ids.meeting_id.name \
                          + '\n' + 'Amount Allocated :  ' + str(rec.grade_amount) \
            			  + '\n' + 'Amount Claimed   :  ' + str(rec.claimed_amount) \
            		   + '\n' + ( ('Reference        :  ' + rec.reference) if rec.reference else '')
                if float(rec.grade_amount) != 0.0:
                    if rec.claimed_amount > rec.grade_amount:

                        parent_id = self.env['hr.employee'].sudo().search([('id', '=', res.employee_id.id)]).parent_id.id
                        parent_user_id = self.env['hr.employee'].sudo().search([('id', '=', res.employee_id.id)]).parent_id.user_id

                        # res.parent_id = res.employee_id.parent_id.id
                        # manager_users.append(result.employee_id.parent_id.user_id)

                        res.parent_id = parent_id
                        manager_users.append(parent_user_id)
                        recepients = manager_users


                        main_id = result.id
                        expensename = result.name
                        employeename = result.employee_id.name
                        meetingvisit = result.expense_line_ids.meeting_id.name
                        grade_amount = result.expense_line_ids.grade_amount
                        claimed_amount = result.expense_line_ids.claimed_amount
                        reference = result.expense_line_ids.reference

                        self.sudo().mail_send(recepients , main_id, expensename , employeename , meetingvisit , grade_amount, claimed_amount , reference)

                        # recepients = mgmt_users
                        # mgmt_partners = [x.partner_id.id for x in mgmt_users]
                        # mgmt_names = ", ".join([x.partner_id.name for x in mgmt_users])
                        # if mgmt_partners:
                        #     self.sudo().message_subscribe(partner_ids=mgmt_partners)
                        # notification_text = "<b>Email sent to MD &amp; CEO - %s for approval.</b>" % (mgmt_names,)
                        # self.sudo().message_post(body=notification_text)
                        

                        # template_id = self.env['ir.model.data'].get_object_reference('sales_meet','expense_assign_action')[1]
                        # print "llllllllllrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr" , 
                        # email_template_obj = self.env['mail.template'].browse(template_id)
                        # if template_id:
                        #     values = email_template_obj.generate_email(result.id, fields=None)
                        #     values['email_from'] = result.employee_id.work_email
                        #     values['email_to'] = result.employee_id.parent_id.work_email
                        #     values['email_cc'] = 'varad.dalvi@walplast.com'
                        #     values['res_id'] = False
                        #     mail_mail_obj = self.env['mail.mail']
                        #     msg_id = mail_mail_obj.sudo().create(values)
                        #     self.mail_date = datetime.now()
                        #     if msg_id:
                        #         msg_id.sudo().send()


        return result



    @api.multi
    def mail_send(self, recepients=[],main_id=False, expensename=False , employeename=False , meetingvisit=False , grade_amount=False, claimed_amount=False , reference=False):
        tkt_type_val = 'Expense'
        lines = ''
        amnt = 0.0
        body = """ """
        subject = ""

        body = """
            <style type="text/css">
            * {font-family: "Helvetica Neue", Helvetica, sans-serif, Arial !important;}
            </style>
            <h3>Following are the details as Below Listed. </h3>

            <ul>
              <li>Description &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: %s</li>
              <li>Employee &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  : %s</li>
              <li>Meeting  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;  : %s</li>
              <li>Amount Allocated : %s</li>
              <li>Amount Claimed &nbsp;&nbsp;: <b style="color: red;"> %s </b></li>
              <li>Bill Reference &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: %s</li>
            </ul> 


            <br/>

        """ % (expensename or '', employeename  or '', meetingvisit  or '' , grade_amount  or '', claimed_amount  or '' , reference  or '' )

        subject = "[Approval] - %s 's Reimbursment for ( %s ) " % (employeename or '' ,expensename or '')
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        
        for rec in recepients:

            approve_url = base_url + '/expense?%s' % (url_encode({
                    'model': 'hr.expense.sheet',
                    'meeting_id': main_id,
                    'res_id': rec.id,
                    'action': 'approve_expense_sheets_manager',
                }))
            reject_url = base_url + '/expense?%s' % (url_encode({
                    'model': 'hr.expense.sheet',
                    'meeting_id': main_id,
                    'res_id': rec.id,
                    'action': 'refuse_expenses',
                }))

            report_check = base_url + '/web#%s' % (url_encode({
                'model': 'hr.expense.sheet',
                'view_type': 'form',
                'id': main_id,
            }))

            full_body = body + """<br/>
            <table class="table" style="border-collapse: collapse; border-spacing: 0px;">
                <tbody>
                    <tr class="text-center">
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF;
                             border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                              vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; 
                              border: 1px solid #337ab7; margin-right: 10px;">Approve</a>
                        </td>
                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF;
                             border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                              vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                               margin-right: 10px;">Reject</a>
                        </td>

                        <td>
                            <a href="%s" target="_blank" style="-webkit-user-select: none; padding: 5px 10px; font-size: 12px; line-height: 18px; color: #FFFFFF; 
                            border-color:#337ab7; text-decoration: none; display: inline-block; margin-bottom: 0px; font-weight: 400; text-align: center;
                             vertical-align: middle; cursor: pointer; white-space: nowrap; background-image: none; background-color: #337ab7; border: 1px solid #337ab7;
                              margin-right: 10px;">Check Request</a>
                        </td>

                    </tr>
                </tbody>
            </table>
            """ % (approve_url, reject_url, report_check)

            # expense_manager = self.env.user.has_group('sales_meet.group_expense_manager_user')

            # print "aaaaaaaaaaaaaaaaaaaaaaaa" , recepients , main_id , rec.email , type(rec.email), subject ,self._name
            
            
            composed_mail = self.env['mail.mail'].sudo().create({
                    'model': self._name,
                    'res_id': main_id,
                    'email_to': rec.email,
                    'email_cc' : 'varad.dalvi@walplast.com',
                    'subject': subject,
                    'body_html': full_body,
                    'auto_delete': False,
                    'priority_mail': True,
                })
            composed_mail.sudo().send()
              


    @api.multi
    def action_sheet_move_create(self):
        res = super(HrExpenseSheetExtension,self).action_sheet_move_create()

        expense_line_ids2 = self.mapped('expense_line_ids')

        post_bool = expense_line_ids2.sudo().write({'posted_bool': True})

        print "kkkkkkkkkkkkkkkkkkkkkkkkkkkkkk" , expense_line_ids2 , post_bool

        return res