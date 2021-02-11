odoo.define('sales_meet.MdmDashboard', function (require) {
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

var MdmDashboard = Widget.extend(ControlPanelMixin, {
    template: "sales_meet.MdmDashboardMain",
    events: {
        'click .customer_count':'customer_count',
        'click .vendor_count':'vendor_count',
        'click .approved_customer_count':'approved_customer_count',
        'click .approved_vendor_count':'approved_vendor_count',
        'click .created_customer_count':'created_customer_count',
        'click .created_vendor_count':'created_vendor_count',
        'click .product_count':'product_count',
    },

    init: function(parent, context) {
        this._super(parent, context);
        var self = this;
        this.login_user = true;
        this._super(parent,context);

    },

    start: function() {
        var self = this;

        var model  = new Model('res.partner').call('get_mdm_details').then(function(result){
            this.login_user =  result[0];
            // self.login_user =  result[0]

            $('.o_mdm_dashboard').html(QWeb.render('MdmManagerDashboard', {widget: this}));

        });

    },


    customer_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Customer"),
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['customer','=', true],['active','=', false],['state', 'in', ['draft','Submitted']]],

            target: 'current'
        })
    },

    approved_customer_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Approved Customer"),
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['customer','=', true],['active','=', false],['state', '=', 'Approved']],

            target: 'current'
        })
    },

    created_customer_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Customer"),
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['customer','=', true],['active','=', true],['state', 'in', ['created','updated']]],

            target: 'current'
        })
    },

    vendor_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Vendor"),
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['supplier','=', true],['active','=', false],['state', 'in', ['draft','Submitted']]],
            target: 'current'
        })
    },

    approved_vendor_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Vendor"),
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['supplier','=', true],['active','=', false],['state', '=', 'Approved']],
            target: 'current'
        })
    },

    created_vendor_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        this.do_action({
            name: _t("Vendor"),
            type: 'ir.actions.act_window',
            res_model: 'res.partner',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['supplier','=', true],['active','=', true],['state', 'in', ['created','updated']]],
            target: 'current'
        })
    },

    product_count: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var date = new Date();
        this.do_action({
            name: _t("Product"),
            type: 'ir.actions.act_window',
            res_model: 'product.product',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['active','=', false]],
            target: 'current'
        })
    },
   

});

core.action_registry.add('mdm_dashboard', MdmDashboard);

return MdmDashboard;

});
