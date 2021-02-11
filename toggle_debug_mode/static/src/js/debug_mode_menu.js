odoo.define('web.DebugModeMenu', function(require) {
"use strict";
var Model = require('web.Model');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');
var core = require('web.core');
var _t = core._t;

var DebugModeMenu = Widget.extend({
    template: 'DebugModeMenu',
    start: function() {
        var self = this;
        var current_url = window.location.href;

        this.$el.on('click', '#debug_button', function(ev) {
            ev.preventDefault();

            //replace debug mode in current url
            var qs = $.deparam.querystring();
            qs.debug = true;

            window.location.search = '?' + $.param(qs);
        });

        if(current_url.indexOf('?debug')!=-1){
            self.$('#debug_button').parent().hide();
        }


        return self._super();
    },
});

SystrayMenu.Items.push(DebugModeMenu);

});
