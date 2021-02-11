odoo.define('sales_meet.currentlatlong', function (require) {
    "use strict";

var core = require('web.core');
var Model = require('web.Model');
var QWeb = core.qweb;
var _t = core._t;
var form_common = require('web.form_common');
var fields;
var web_client = require('web.web_client');
var WebClient = require('web.WebClient');
var Class = require('web.Class');
var form_widget = require('web.form_widgets');

var options = {
  enableHighAccuracy: true,
  // timeout: 5000,
  // maximumAge: 0,
  // enableHighAccuracy: true,
        maximumAge: 3600000
};

console.log("LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL");


var calendar_event =  new Model('calendar.event');

console.log("MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM" + calendar_event);
        
    // function success(pos) {
    //     var self = this;
    //       var crd = pos.coords;

    //       console.log('Your current position is:');
    //       console.log(`Latitude : ${crd.latitude}`);
    //       console.log(`Longitude: ${crd.longitude}`);
    //       console.log(`More or less ${crd.accuracy} meters.`);
    //       console.log(self);
          
    //       var checkin_lattitude = crd.latitude;
    //       var checkin_longitude = crd.longitude;

    //       console.log('AAAAAAAAAAAAAA' + checkin_lattitude + checkin_longitude);

    //       calendar_event.checkin_lattitude = checkin_lattitude;

    //       console.log("NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNPPPPPPPPPPPPPP");
    //       self.checkin_lattitude.push(checkin_lattitude)

    //       // document.getElementByName('checkin_lattitude').value='checkin_lattitude' ; 
    //        // document.getElementById("checkin_lattitude").setAttribute('value',checkin_lattitude);

    //        // document.getElementsByName("checkin_lattitude")[0].setAttribute("value", "my value is high");


    //        // return  {
    //        //      checkin_lattitude: checkin_lattitude,
    //        //  };

    //       // my_object.checkin_lattitude = checkin_lattitude

    //        // self.view.fields.checkin_lattitude.set_value(checkin_lattitude);
    //         // this.field_manager.get_field_value('checkin_lattitude');
    //         // self.pos.fields[checkin_lattitude].set_value(checkin_lattitude);

    //     };

    //     function error(err) {
    //       console.warn(`ERROR(${err.code}): ${err.message}`);
    //     };

    //     navigator.geolocation.getCurrentPosition(success, error, options);



    WebClient.include({

    init: function (values) {
        Object.assign(this, values);
        this.tickets = [];
    },


    show_application: function() {
        this._super();
        console.log("--EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE--");
        this.checkin();
    },
    
    checkin: function(){
        var self = this;
        
        new Model("calendar.event").call("checkin", [[]]).then(function(data) {
            console.log('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&');

            function success(pos) {
                  var crd = pos.coords;

                  console.log('Your current position is:');
                  console.log(`Latitude : ${crd.latitude}`);
                  console.log(`Longitude: ${crd.longitude}`);
                  console.log(`More or less ${crd.accuracy} meters.`);
                  console.log(self);
                  
                  var checkin_lattitude = crd.latitude;
                  var checkin_longitude = crd.longitude;

                  console.log('AAAAAAAAAAAAAA' + checkin_lattitude + checkin_longitude);

                  calendar_event.checkin_lattitude = checkin_lattitude;
                   
                  
                  // return self.ticket_values.update();
                  self.des = checkin_lattitude;
                  

                  console.log("NNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNNPPPPPPPPPPPPPP" + self.checkin_lattitude);
                  return checkin_longitude;
                  // self.view.checkin_lattitude.set_value(checkin_lattitude);

                   };

                    function error(err) {
                      console.warn(`ERROR(${err.code}): ${err.message}`);
                    };

                    navigator.geolocation.getCurrentPosition(success, error, options);



        });


        
    },
});





        
});
        
