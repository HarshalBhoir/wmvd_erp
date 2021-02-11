odoo.define('sales_meet.MastersDashboard', function (require) {
"use strict";

var ajax = require('web.ajax');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Model = require('web.Model');
var session = require('web.session');
var utils = require('web.utils');
var web_client = require('web.web_client');
var Widget = require('web.Widget');
var _t = core._t;
var QWeb = core.qweb;


var formats = require('web.formats');
var KanbanView = require('web_kanban.KanbanView');
var KanbanRecord = require('web_kanban.Record');
var ActionManager = require('web.ActionManager');

var _lt = core._lt;

var MastersDashboard = Widget.extend(ControlPanelMixin, {
    template: "sales_meet.MastersDashboardMain",
    events: {
        'click .go_to_wp_customer':'go_to_wp_customer',
        'click .go_to_supplier':'go_to_supplier',
        'click .go_to_product':'go_to_product',
        'click .partner_count':'partner_count',

    },

    init: function(parent, context) {
        this._super(parent, context);
        var self = this;
        this.login_user = true;
        this._super(parent,context);

    },

    start: function() {
        var self = this;

        var model  = new Model('calendar.event').call('get_user_meeting_details').then(function(result){
            this.login_user =  result[0];

            $('.o_masters_dashboard').html(QWeb.render('MastersManagerDashboard', {widget: this}));

        });

    },


    // go_to_customer: function(e) {
    //     var self = this;
    //     e.stopPropagation();
    //     e.preventDefault();
    //     var date = new Date();
        
    //     this.do_action({
    //         type: 'ir.actions.act_window',
    //         res_model: "res.partner",
    //         // res_id: id,
    //         views: [[false, 'form']],
    //         domain: [['customer','=', true],['active','=', false]],
    //         context: {'default_active': false,
    //                     'default_customer': true,

    //                 },
    //         view_id: self.login_user.partner_view_id,
    //     });
    // },

    go_to_wp_customer: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "wp.res.partner",
            // res_id: id,
            views: [[false, 'form']],
            domain: [['customer','=', true]],
            context: {'default_active': true,
                        'default_customer': true,

                    },
            view_id: self.login_user.wp_partner_view_id,
        });
    },

    partner_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Distributors"),
            type: 'ir.actions.act_window',
            res_model: 'wp.res.partner',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            target: 'current'
        })
    },


    go_to_supplier: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "res.partner",
            // res_id: id,
            views: [[false, 'form']],
            domain: [['supplier','=', true],['active','=', false]],
            context: {'default_active': false,
                        'default_supplier': true,
                        'default_customer': false,

                    },
            view_id: self.login_user.supplier_view_id,

        });
    },


    go_to_product: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        
        this.do_action({
            type: 'ir.actions.act_window',
            res_model: "product.product",
            // res_id: id,
            views: [[false, 'form']],
            domain: [['active','=', false]],
            context: {'default_active': false,
                        },
        });
    },

});

core.action_registry.add('masters_dashboard', MastersDashboard);

return MastersDashboard;

});
