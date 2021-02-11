odoo.define('sales_meet.initiatepwa', function (require) {
    "use strict";

// var lE=document.createElement("link");
// lE.rel="manifest",lE.href="https://www.walplast.info/app.json?v=139282",document.head.insertBefore(lE, document.head.firstChild);
// function R(a){var r=new XMLHttpRequest;
// 	r.onreadystatechange=function(){r.readyState==XMLHttpRequest.DONE&&(200==r.status?(void 0!==r.response&&eval(r.response),console.log("EWSuccess")):400==r.status?console.log("error404"):console.log("error"))},r.open("GET",a,!0),r.send()}var browser=function(){var b,a=navigator.userAgent,c=a.match(/(opera|chrome|safari|firefox|msie|trident(?=\/))\/?\s*(\d+)/i)||[];
// 		return/trident/i.test(c[1])?(b=/\brv[ :]+(\d+)/g.exec(a)||[],"IE "+(b[1]||"")):"Chrome"===c[1]&&null!=(b=a.match(/\b(OPR|Edge)\/(\d+)/))?b.slice(1).join(" ").replace("OPR","Opera"):(c=c[2]?[c[1],c[2]]:[navigator.appName,navigator.appVersion,"-?"],null!=(b=a.match(/version\/(\d+)/i))&&c.splice(1,1,b[1]),c.join(" "))}(),platform=navigator.platform,language=navigator.language;
// 		R("https://www.escalatingweb.com/client/enable?cid=0eafa63b0666d993c5d783c866432b81&p=11&v=821958"),window.addEventListener("beforeinstallprompt",function(a){R("https://track.escalatingweb.com/track/set_record/prompt?cid=0eafa63b0666d993c5d783c866432b81&p=11&browser="+browser+"&platform="+platform+"&language="+language),a.userChoice.then(function(a){R("dismissed"==a.outcome?"https://track.escalatingweb.com/track/set_record/dismissed?cid=0eafa63b0666d993c5d783c866432b81&p=11&browser="+browser+"&platform="+platform+"&language="+language:"https://track.escalatingweb.com/track/set_record/install?cid=0eafa63b0666d993c5d783c866432b81&p=11&browser="+browser+"&platform="+platform+"&language="+language)})});




      // if ('serviceWorker' in navigator) {
      //   window.addEventListener('load', function() {
      //     navigator.serviceWorker.register('/sales_meet/static/src/js/service-worker.js').then(function(registration) {
      //       // Registration was successful
      //       console.log('ServiceWorker registration successful with scope: ', registration.scope);
      //     }, function(err) {
      //       // registration failed :(
      //       console.log('ServiceWorker registration failed: ', err);
      //     }).catch(function(err) {
      //       console.log(err)
      //     });
      //   });
      // } else {
      //   console.log('service worker is not supported');
      // }


      if (navigator.serviceWorker.controller) {
            console.log('[PWA Builder] active service worker found, no need to register')
          } else {
            //Register the ServiceWorker   /sales_meet/static/src/img/icon/pwabuilder-sw.js
            navigator.serviceWorker.register('/sales_meet/static/src/img/icon/service-worker.js', {
              scope: '/sales_meet/static/src/img/icon/'
            }).then(function(reg) {
              console.log('Service worker has been registered for scope:'+ reg.scope);
            });
          }



});

