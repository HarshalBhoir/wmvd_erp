# -*- coding: utf-8 -*-
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# Copyright 2017 Tecnativa - Carlos Dauden
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, exceptions, _


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.onchange('user_id')
    def _onchange_user(self):  # pragma: no cover
        """Don't change date_start when changing the user_id. This screws up
        the default value passed by context when creating a record. It's also
        a nonsense to chain both values.
        """
        old_date_start = self.date_start
        super(ProjectTask, self)._onchange_user()
        if old_date_start > self.date_start:
            self.date_start = old_date_start


# class ProjectProject(models.Model):
#     _inherit = "project.project"

#     kra_id = fields.Many2many("kr.kra", string="KRA" )