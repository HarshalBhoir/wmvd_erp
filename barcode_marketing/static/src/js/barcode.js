odoo.define('barcode_marketing.barcode_scanning', function (require) {
    "use strict";

var instance = openerp;
var core = require('web.core');
// var Model = require('web.Model');
var QWeb = core.qweb;
var _t = core._t;

var form_widgets = require('web.form_widgets');
var ajax = require('web.ajax');

var framework = require('web.framework');
var Model = require('web.DataModel');
var odoo_session = require('web.session');
var web_client = require('web.web_client');
var Widget = require('web.Widget');
var ajax = require('web.ajax');
var bus = require('bus.bus').bus;
var Notification = require('web.notification').Notification;
var WebClient = require('web.WebClient');
var SystrayMenu = require('web.SystrayMenu');
var form_common = require('web.form_common');
var form_widgets = require('web.form_widgets');

// --------------------------------------

var codes = "";
var codes_el = document.getElementById('codes');
var output_el = document.getElementById('output');



// instance.web.FormView.include({
//     init: function(parent, dataset, view_id, options) {
//         var self = this;
//         this._super(parent, dataset, view_id, options);
//     },
    
//     start: function() {
//         var self = this;
//         this._super.apply(this, arguments);


//           var letter = event.key;
  
// 		  if (letter === 'Enter'){
// 		    event.preventDefault();
// 		    letter = "\n";
// 		    event.target.value = "";
// 		  }
		  
// 		  // match numbers and letters for barcode
// 		  // if (letter.match(/^[a-z0-9]$/gi)){
// 		  //   codes += letter;
// 		  // }
		  
// 		  console.log("IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIi")
// 		  // codes_el.value = codes;
// 		  // output_el.innerHTML = codes;

// 		   $('input.codes').val(codes);
//            $('input.output').val(codes);

//            console.log("YYYYYYYYYYYYYYYYYYYYYYY" + codes  +  output_el)
		        
// 	},



// });


var MarketingBarcodeHandler = form_widgets.FieldChar.extend({
    init: function(parent, context) {
        this.form_view_initial_mode = parent.ViewManager.action.context.form_view_initial_mode;
        return this._super.apply(this, arguments);
    },

    start: function(event) {
        this._super();

        console.log("44444444444444444444444" + codes_el + output_el)




        
    //       var letter = event.key;
  
		  // if (letter === 'Enter'){
		  //   event.preventDefault();
		  //   letter = "\n";
		  //   event.target.value = "";
		  // }
		  
		  // // match numbers and letters for barcode
		  // if (letter.match(/^[a-z0-9]$/gi)){
		  //   codes += letter;
		  // }
		  
		  // console.log("IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIi")
		  // // codes_el.value = codes;
		  // // output_el.innerHTML = codes;

		  // $('input.codes').val(codes);
    //       $('input.output').val(codes);

          console.log("EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE")



    },



});

core.form_widget_registry.add('marketing_barcode_handler', MarketingBarcodeHandler);


return MarketingBarcodeHandler;
// function process_key(event){
  
//   var letter = event.key;
  
//   if (letter === 'Enter'){
//     event.preventDefault();
//     letter = "\n";
//     event.target.value = "";
//   }
  
//   // match numbers and letters for barcode
//   if (letter.match(/^[a-z0-9]$/gi)){
//     codes += letter;
//   }
  
//   console.log("IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIi")
//   codes_el.value = codes;
//   output_el.innerHTML = codes;
// }

// getProcessKey(process_key);
// ------------------------------------------

});

