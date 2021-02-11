# -*- coding: utf-8 -*-
# Copyright 2015-2017 Odoo S.A.
# Copyright 2017 Vicent Cubells <vicent.cubells@tecnativa.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models, tools
from odoo.tools import html2plaintext
from odoo.addons.base.res.res_request import referenceable_models
from datetime import datetime, timedelta, date


class letter_class(models.Model):
    """ Class to define the classification of letter like : classified,
    confidential, personal, etc. """
    _name = 'letter.class'
    _description = "Letter Classification"
    

    name =  fields.Char('Type', required=True)



class letter_channel(models.Model):
    """ Class to define various channels using which letters can be sent or
    received like : post, fax, email. """
    _name = 'letter.channel'
    _description = "Send/Receive channel"


    name =  fields.Char('Type', required=True)


class letter_reassignment(models.Model):
    """A line to forward a letter with a comment"""
    _name = 'letter.reassignment'
    _description = 'Reassignment line'

    name =  fields.Many2one(
        'res.users', string='Name', help='User to forward letter to.')
    comment = fields.Text(
        'Comment', help='Comment for user explaining forward.')
    letter_id =  fields.Many2one(
        'res.letter', string='Letter', help='Letter in question.')
    department_id = fields.Many2one('hr.department', string='Department', help='Department of user to whom letter is reassigned.')



class letter_folder(models.Model):
    """Folder which contains collections of letters"""
    _name = 'letter.folder'
    _description = 'Letter Folder'

    name =fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    letter_ids = fields.One2many('res.letter', 'folder_id', string='Letters',
    help='Letters contained in this folder.')

    _sql_constraints = [('code_uniq', 'unique(code)', 'Code must be unique !')]


class letter_type(models.Model):
    """Class to define various types for letters like : envelope,parcel,
    etc."""
    _name = 'letter.type'
    _description = "Letter Type"

    name = fields.Char('Type', required=True)
    code = fields.Char('Code', required=True)

    _sql_constraints = [('code_uniq', 'unique(code)', 'Code must be unique !')]



class res_letter(models.Model):
    """A register class to log all movements regarding letters"""
    _name = 'res.letter'
    _description = "Log of Letter Movements"
    _inherit = 'mail.thread'

    # def _get_number(self):

    #     sequence_pool = self.env['ir.sequence']
    #     move_type = self.env.context.get('move', 'in')
    #     return sequence_pool.get(
    #         cr, uid, '%s.letter' % move_type, context=context)

    @api.model
    def create(self, vals):
        if vals['move'] == 'in':
            vals['number'] = self.env['ir.sequence'].next_by_code('in.letter')
        else:
            vals['number'] = self.env['ir.sequence'].next_by_code('out.letter')

        vals['state'] = 'created'
        result = super(res_letter, self).create(vals)
        result.action_name()
        return result



    name = fields.Text('Subject', help="Subject of letter.")
    folder_id = fields.Many2one('letter.folder', string='Folder',
        help='Folder which contains letter.')
    number = fields.Char('Number', help="Auto Generated Number of letter." , track_visibility='onchange' ,store=True )
    move =fields.Selection([('in', 'IN'), ('out', 'OUT')], 'Move', help="Incoming or Outgoing Letter.")
    type_id =fields.Many2one('letter.type', 'Type',
        help="Type of Letter, Depending upon size.")
    class_id =fields.Many2one('letter.class', 'Class', help="Classification of Document.")
    date =fields.Datetime('Letter Date', help='The letter\'s date')
    snd_rec_date =fields.Datetime('Sent / Received Date', help='Created Date of Letter Logging.',default=datetime.now())
    recipient_partner_id =fields.Many2one('hr.employee', string='Recipient', track_visibility='onchange')
    sender_partner_id =fields.Many2one('hr.employee', string='Sender', track_visibility='onchange')
    note =fields.Text('Note')
    state =fields.Selection([('draft', 'Draft'),
                               ('created', 'Created'),
                               ('rec', 'Received'),
                               ('sent', 'Sent'),
                               ('rec_bad', 'Received Damage'),
                               ('rec_ret', 'Received But Returned'),
                               ('cancel', 'Cancelled')],
                              'State', readonly=True, default='draft',
                              track_visibility='onchange')
    parent_id =fields.Many2one('res.letter', 'Parent')
    child_line =fields.One2many('res.letter', 'parent_id', 'Letter Lines')
    channel_id =fields.Many2one('letter.channel', 'Sent / Receive Source')
    orig_ref =fields.Char('Original Reference', help="Reference Number at Origin.")
    expeditor_ref =fields.Char('Expeditor Reference', help="Reference Number used by Expeditor.")
    track_ref =fields.Char('Tracking Reference', help="Reference Number used for Tracking.")
    weight =fields.Float('Weight (in KG)')
    size =fields.Char('Size')
    reassignment_ids =fields.One2many('letter.reassignment', 'letter_id', string='Reassignment lines',
        help='Reassignment users and comments')
    extern_partner_ids =fields.Many2many('res.partner', string='Recipients')
    external_person = fields.Char('External Person')

    move = fields.Selection([('in', 'IN') ,('out', 'OUT'), ('intern', 'INTERN')], 'Move', readonly=True,
                             help="Incoming, Outgoing or Internal Letter.")
    recipient_intern_ids = fields.Many2many('hr.employee', string="Send to",
                                             help="Persons who will receive Letter.")
    department_id = fields.Many2one('hr.department', string='Department',
                                     help='Department who will receive letter.')
    cc_employee_ids = fields.Many2many('hr.employee', string='Employee',
                                        help='Send copies to these employees.')
    cc_department_ids = fields.Many2many('hr.department', string='Department',
                                          help='Send copies to these departments.')
    reassignment_employee_ids = fields.Many2many('hr.employee', string='Reassignment',
                                                  help='Reassign letter to these employees.')
    reassignment_department_ids = fields.Many2many('hr.department', string='Department',
                                                    help='Reassign copies to these departments.')


    _defaults = {
        'move': lambda self, cr, uid, context: context.get('move', 'in'),
    }

    def action_received(self):
        self.write({'state': 'rec'})
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_name(self):
        if self.type_id and self.recipient_partner_id and self.sender_partner_id:
            self.name = self.type_id.name + ' for ' + self.recipient_partner_id.name + ' from ' + self.sender_partner_id.name
        # self.write({'state': 'created'})
        # return True

    def action_send(self):
        self.write({'state': 'sent','snd_rec_date': self.snd_rec_date})
            
        return True

    def action_rec_ret(self):
        self.write({'state': 'rec_ret'})
        return True

    def action_rec_bad(self):
        self.write({'state': 'rec_bad'})
        return True

    def action_set_draft(self):
        self.write({'state': 'draft'})
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: