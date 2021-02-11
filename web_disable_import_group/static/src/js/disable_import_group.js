odoo.define("web_disable_import_group", function(require) {
"use strict";

    var core = require("web.core");
    var Sidebar = require("web.Sidebar");
    var _t = core._t;
    var Model = require("web.Model");
    var session = require("web.session");
    var ListView = require('web.ListView');

   ListView.include({
        render_buttons: function() {
            var self = this;
            this._super.apply(this, arguments);
            var add_button = false;
            if (session.is_superuser) {
                add_button = true;
            } else {
                var model_res_users = new Model("res.users");
                model_res_users.call("has_group", ["web_disable_import_group.group_import_data"]).done(function(can_import) {
                    if (!can_import) {
                        self.$buttons.find('.o_button_import').hide();
                    }
                });
            }
        }
    });



});
