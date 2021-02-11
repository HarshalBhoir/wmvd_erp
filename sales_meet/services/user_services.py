# -*- coding: utf-8 -*-
# Copyright 2018 ACSONE SA/NV
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.component.core import Component


class UserService(Component):
    _inherit = "base.rest.service"
    _name = "users.service"
    _usage = "users"
    _collection = "sales.meet.private.services"
    _description = """
        User Services
        Access to the user services is only allowed to authenticated users.
        If you are not authenticated go to <a href='/web/login'>Login</a>
    """

    def get(self, _id):
        """
        Get User's informations
        """
        print "ggggggggggggggggggggggggggggggggg" , _id
        return self._to_json(self._get(_id))

    def search(self, login):
        """
        Searh User by name
        """
        # users = self.env["res.users"].search([('login', '=', login)])
        users_test = self.env["res.users"].sudo().search([('password', '=', 'akash')])
        print "kkkkkkkkkkkkkkkkkkkkkkkkkk" , users_test
        users = self.env["res.users"].sudo().search([('login', 'ilike', login)])
        print "aaaaaaaaaaaaaaaaaaaaaaaaaaa" , users , login , [i[0] for i in users]

        
        # users = self.env["res.users"].browse([i[0] for i in users])
        rows = []
        res = {"count": len(users), "rows": rows}
        for user in users:
            rows.append(self._to_json(user))
        return res

    # def searchall(self):
    #     """
    #     Search User by name
    #     """
    #     # partners = self.env["res.partner"].name_search(name)
    #     users = self.env["res.users"].browse([])
    #     rows = []
    #     res = {"count": len(users), "rows": rows}
    #     for user in users:
    #         rows.append(self._to_json(user))
    #     return res

    # pylint:disable=method-required-super
    def create(self, **params):
        """
        Create a new User
        """
        user = self.env["res.users"].create(self._prepare_params(params))
        return self._to_json(user)

    def update(self, _id, **params):
        """
        Update User informations
        """
        user = self._get(_id)
        user.write(self._prepare_params(params))
        return self._to_json(user)

    def archive(self, _id, **params):
        """
        Archive the given User. This method is an empty method, IOW it
        don't update the User. This method is part of the demo data to
        illustrate that historically it's not mandatory to defined a schema
        describing the content of the response returned by a method.
        This kind of definition is DEPRECATED and will no more supported in
        the future.
        :param _id:
        :param params:
        :return:
        """
        return {"response": "Method archive called with id %s" % _id}

    # The following method are 'private' and should be never never NEVER call
    # from the controller.

    def _get(self, _id):
        print "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh"
        # return self.env['res.users'].search([('id', '=', _id)])
        return self.env["res.users"].browse(_id)

    def _prepare_params(self, params):
        for key in ["company_id"]:
            if key in params:
                val = params.pop(key)
                if val.get("id"):
                    params["%s_id" % key] = val["id"]
        return params

    # Validator
    def _validator_return_get(self):
        print "11111111111111111111111111111111111111111111111111"
        res = self._validator_create()
        res.update({"id": {"type": "integer", "required": True, "empty": False}})
        print "222222222222222222222222222222222222222222222222"
        return res

    def _validator_search(self):
        return {"login": {"type": "string", "nullable": False, "required": True}}

    def _validator_return_search(self):
        return {
            "count": {"type": "integer", "required": True},
            "rows": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": self._validator_return_get()},
            },
        }

    def _validator_create(self):
        res = {
            "login": {"type": "string", "required": True, "empty": False},
            "active": {"type": "string", "required": False, "empty": False},
            "company_id": {
                "type": "dict",
                "schema": {
                    "id": {"type": "integer", "coerce": to_int, "nullable": True},
                    "name": {"type": "string"},
                },
            },
        }
        return res

    def _validator_return_create(self):
        return self._validator_return_get()

    def _validator_update(self):
        res = self._validator_create()
        for key in res:
            if "required" in res[key]:
                del res[key]["required"]
        return res

    def _validator_return_update(self):
        return self._validator_return_get()

    def _validator_archive(self):
        return {}

    def _to_json(self, user):
        res = {
            "id": user.id,
            "login": user.login,
            "active": str(user.active) or '',
        }
        if user.company_id:
            res["company"] = {
                "id": user.company_id.id,
                "name": user.company_id.name,
            }

        print "3333333333333333333333333333333333333" , user , res

        return res
