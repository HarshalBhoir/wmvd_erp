odoo.define("web_disable_delete_group", function(require) {
"use strict";

    var core = require("web.core");
    var Sidebar = require("web.Sidebar");
    var _t = core._t;
    var Model = require("web.Model");
    var session = require("web.session");

    Sidebar.include({
        add_items: function(section_delete_code, items) {
            var self = this;
            var _super = this._super;
            if (session.is_superuser) {
                _super.apply(this, arguments);
            } else {
                var model_res_users = new Model("res.users");
                model_res_users.call("has_group", ["web_disable_delete_group.group_delete_data"]).done(function(can_delete) {
                    if (!can_delete) {
                        var delete_label = _t("Delete");
                        var new_items = items;
                        if (section_delete_code === "other") {
                            new_items = [];
                            for (var i = 0; i < items.length; i++) {
                                console.log("items[i]: ", items[i]);
                                if (items[i]["label"] !== delete_label) {
                                    new_items.push(items[i]);
                                }
                            }
                        }
                        if (new_items.length > 0) {
                            _super.call(self, section_delete_code, new_items);
                        }
                    } else {
                        _super.call(self, section_delete_code, items);
                    }
                });
            }
        }
    });
});
