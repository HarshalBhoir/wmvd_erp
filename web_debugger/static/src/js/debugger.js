odoo.define('web_debugger.debugger_topbar', function(require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var debugger_menu = Widget.extend({
        template: 'web_debugger.debugger_menu',
        events: {
            "click .oe_debugger_menu_mode": "oe_debugger_menu_mode",
            "click .oe_dark_mode_toggle": "oe_dark_mode_toggle",
            
        },
        oe_debugger_menu_mode: function(event) {
            event.preventDefault();
            if (window.location.href.indexOf("?debug=assets") > -1) {
                window.location = window.location.href.replace('?debug=assets', '?debug=');
            } else {
                window.location = $.param.querystring(window.location.href, 'debug=assets');
            }
        },

        oe_dark_mode_toggle: function(event) {
            event.preventDefault();
            var dark_mode = document.getElementById("dark_mode");

            if (typeof(dark_mode) != 'undefined' && dark_mode != null) {
                dark_mode.remove();
                $('.fa-toggle-on').addClass('fa-toggle-off').removeClass('fa-toggle-on');
            } else {                
                $('.fa-toggle-off').addClass('fa-toggle-on').removeClass('fa-toggle-off');
                // var css = '@supports (backdrop-filter:invert(100%)){#mybpwaycfxccmnp-dblt-backdrop-filter{display:block!important;position:fixed!important;top:0!important;bottom:0!important;left:0!important;right:0!important;margin:0!important;pointer-events:none!important;z-index:2147483647!important;backdrop-filter:invert(100%) hue-rotate(180deg)!important}img:not(.mwe-math-fallback-image-inline):not([alt=inline_formula]),video{filter:invert(100%) hue-rotate(180deg)!important}}@supports not (backdrop-filter:invert(100%)){div#viewer.pdfViewer div.page,embed[type="application/x-shockwave-flash"],html,img:not(.mwe-math-fallback-image-inline):not([alt=inline_formula]),object[type="application/x-shockwave-flash"],video{filter:invert(100%) hue-rotate(180deg)!important}:fullscreen video,video:fullscreen{filter:none!important}html{background-color:#000!important}}@supports not (backdrop-filter:invert(100%)){div.dash-box@supports (backdrop-filter:invert(100%)){position:fixed!important;top:0!important;bottom:0!important;left:0!important;right:0!important;margin:0!important;pointer-events:none!important;z-index:2147483647!important;backdrop-filter:invert(100%) hue-rotate(180deg)!important}img:not(.mwe-math-fallback-image-inline):not([alt=inline_formula]),video{filter:invert(100%) hue-rotate(180deg)!important}}@supports not (backdrop-filter:invert(100%)){div#viewer.pdfViewer div.page,embed[type="application/x-shockwave-flash"],html,img:not(.mwe-math-fallback-image-inline):not([alt=inline_formula]),object[type="application/x-shockwave-flash"],video{filter:invert(100%) hue-rotate(180deg)!important}:fullscreen video,video:fullscreen{filter:none!important}html{background-color:#000!important}}@supports not (backdrop-filter:invert(100%)){div.dash-box{filter:invert(100%) hue-rotate(180deg)!important}}button,input,optgroup,select,textarea{background-color:#fff;color:#000}input,optgroup,select,textarea{background-color:#fff;color:#000}',
                var css = '@supports (backdrop-filter:invert(100%)){#mybpwaycfxccmnp-dblt-backdrop-filter{display:block!important;position:fixed!important;top:0!important;bottom:0!important;left:0!important;right:0!important;margin:0!important;pointer-events:none!important;z-index:2147483647!important;backdrop-filter:invert(100%) hue-rotate(180deg)!important}img:not(.mwe-math-fallback-image-inline):not([alt=inline_formula]),video{filter:invert(100%) hue-rotate(180deg)!important}}@supports not (backdrop-filter:invert(100%)){div#viewer.pdfViewer div.page,embed[type="application/x-shockwave-flash"],html,img:not(.mwe-math-fallback-image-inline):not([alt=inline_formula]),object[type="application/x-shockwave-flash"],video{filter:invert(100%) hue-rotate(180deg)!important}:fullscreen video,video:fullscreen{filter:none!important}html{background-color:#000!important}}@supports not (backdrop-filter:invert(100%)){div.dash-box{filter:invert(100%) hue-rotate(180deg)!important}}button,input,optgroup,select,textarea{background-color:#fff;color:#000}@supports (-webkit-backdrop-filter:invert(100%)){#mybpwaycfxccmnp-dblt-backdrop-filter{display:block!important;position:fixed!important;top:0!important;bottom:0!important;left:0!important;right:0!important;margin:0!important;pointer-events:none!important;z-index:2147483647!important;-webkit-backdrop-filter:invert(100%) hue-rotate(180deg)!important}img:not(.mwe-math-fallback-image-inline):not([alt=inline_formula]),video{-webkit-filter:invert(100%) hue-rotate(180deg)!important}}@supports not (-webkit-backdrop-filter:invert(100%)){div#viewer.pdfViewer div.page,embed[type="application/x-shockwave-flash"],html,img:not(.mwe-math-fallback-image-inline):not([alt=inline_formula]),object[type="application/x-shockwave-flash"],video{-webkit-filter:invert(100%) hue-rotate(180deg)!important}:fullscreen video,video:fullscreen{-webkit-filter:none!important}html{-webkit-background-color:#000!important}}@supports not (-webkit-backdrop-filter:invert(100%)){div.dash-box{-webkit-filter:invert(100%) hue-rotate(180deg)!important}}',

                    body = document.body || document.getElementsByTagName('body')[0],
                    style = document.createElement('style');

                body.appendChild(style);

                style.id = 'dark_mode'
                style.type = 'text/css';            
                if (style.styleSheet){
                  // This is required for IE8 and below.
                  style.styleSheet.cssText = css;
                } else {
                  style.appendChild(document.createTextNode(css));
                }
            }

            
        },
    });
    
    SystrayMenu.Items.push(debugger_menu);
});
