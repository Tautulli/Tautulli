function initConfigCheckbox(elem) {
	var config = $(elem).parent().next();	
	if ( $(elem).is(":checked") ) {
		config.show();
	} else {
		config.hide();
	}
	$(elem).click(function(){
		var config = $(this).parent().next();	
		if ( $(this).is(":checked") ) {
			config.slideDown();
		} else {
			config.slideUp();
		}
	});
}     

function refreshTab() {
	var url =  $(location).attr('href');
	var tabId = $('.ui-tabs-panel:visible').attr("id");
	$('.ui-tabs-panel:visible').load(url + " #"+ tabId, function() {
		initThisPage();
	});
}

function showMsg(msg,loader,timeout,ms) {
	var feedback = $("#ajaxMsg");
	update = $("#updatebar");
	if ( update.is(":visible") ) {
		var height = update.height() + 35;
		feedback.css("bottom",height + "px");
	} else {
		feedback.removeAttr("style");
	}
	feedback.fadeIn();
	var message = $("<div class='msg'>" + msg + "</div>");
	if (loader) {
		var message = $("<i class='fa fa-refresh fa-spin'></i> " + msg + "</div>");
		feedback.css("padding","14px 10px")
	}
	$(feedback).prepend(message);
	if (timeout) {
		setTimeout(function(){
			message.fadeOut(function(){
				$(this).remove();
				feedback.fadeOut();					
			});
		},ms);
	} 
}

function doAjaxCall(url,elem,reload,form) {
	// Set Message
	feedback = $("#ajaxMsg");
	update = $("#updatebar");
	if ( update.is(":visible") ) {
		var height = update.height() + 35;
		feedback.css("bottom",height + "px");
	} else {
		feedback.removeAttr("style");
	}
	
	feedback.fadeIn();
	// Get Form data
	var formID = "#"+url;
	if ( form == true ) {
		var dataString = $(formID).serialize();
	}
	// Loader Image
	var loader = $("<i class='fa fa-refresh fa-spin'></i>");
	// Data Success Message
	var dataSucces = $(elem).data('success');
	if (typeof dataSucces === "undefined") {
		// Standard Message when variable is not set
		var dataSucces = "Success!";
	} 
	// Data Errror Message
	var dataError = $(elem).data('error');
	if (typeof dataError === "undefined") {
		// Standard Message when variable is not set
		var dataError = "There was an error";
	} 	
	// Get Success & Error message from inline data, else use standard message
	var succesMsg = $("<div class='msg'><i class='fa fa-check'></i> " + dataSucces + "</div>");
	var errorMsg = $("<div class='msg'><i class='fa fa-exclamation-triangle'></i> " + dataError + "</div>");
	
	// Check if checkbox is selected
	if ( form ) {
		if ( $('td#select input[type=checkbox]').length > 0 && !$('td#select input[type=checkbox]').is(':checked') || $('#importLastFM #username:visible').length > 0 && $("#importLastFM #username" ).val().length === 0 ) {
			feedback.addClass('error')
			$(feedback).prepend(errorMsg);
			setTimeout(function(){
				errorMsg.fadeOut(function(){
					$(this).remove();
					feedback.fadeOut(function(){
						feedback.removeClass('error');
					});					
				})
				$(formID + " select").children('option[disabled=disabled]').attr('selected','selected');
			},2000);
			return false;
		} 
	} 
	
	// Ajax Call
	$.ajax({
	  url: url,
	  data: dataString,
	  type: 'post',
	  beforeSend: function(jqXHR, settings) {
	  	// Start loader etc.
	  	feedback.prepend(loader);
	  },
	  error: function(jqXHR, textStatus, errorThrown)  {
	  	feedback.addClass('error')
	  	feedback.prepend(errorMsg);
	  	setTimeout(function(){
	  		errorMsg.fadeOut(function(){
	  			$(this).remove();
	  			feedback.fadeOut(function(){
	  				feedback.removeClass('error')
	  			});	  			
	  		})
	  	},2000);
	  },
	  success: function(data,jqXHR) {
	  	feedback.prepend(succesMsg);
	  	feedback.addClass('success')
	  	setTimeout(function(e){
	  		succesMsg.fadeOut(function(){
	  			$(this).remove();
	  			feedback.fadeOut(function(){
	  				feedback.removeClass('success');
	  			});
	  			if ( reload == true ) 	refreshSubmenu();
	  			if ( reload == "table") {
	  				console.log('refresh'); refreshTable();
	  			}
	  			if ( reload == "tabs") 	refreshTab();
	  			if ( reload == "page") 	location.reload();
	  			if ( reload == "submenu&table") {
	  				refreshSubmenu();
	  				refreshTable();
	  			}
	  			if ( form ) {
	  				// Change the option to 'choose...'
	  				$(formID + " select").children('option[disabled=disabled]').attr('selected','selected');
	  			}
	  		})
	  	},2000);
	  },
	  complete: function(jqXHR, textStatus) {
	  	// Remove loaders and stuff, ajax request is complete!
	  	loader.remove();
	  }
	});
}

function doSimpleAjaxCall(url) {
	$.ajax(url);
}

function resetFilters(text){
	if ( $(".dataTables_filter").length > 0 ) {
		$(".dataTables_filter input").attr("placeholder","filter " + text + "");
	}
}

function getPlatformImagePath(platformName) {

    if (platformName.indexOf("Roku") > -1) {
        return 'interfaces/default/images/platforms/roku.png';
    } else if (platformName.indexOf("Apple TV") > -1) {
        return 'interfaces/default/images/platforms/appletv.png';
    } else if (platformName.indexOf("Firefox") > -1) {
        return 'interfaces/default/images/platforms/firefox.png';
    } else if (platformName.indexOf("Chromecast") > -1) {
        return 'interfaces/default/images/platforms/chromecast.png';
    } else if (platformName.indexOf("Chrome") > -1) {
        return 'interfaces/default/images/platforms/chrome.png';
    } else if (platformName.indexOf("Android") > -1) {
        return 'interfaces/default/images/platforms/android.png';
    } else if (platformName.indexOf("Nexus") > -1) {
        return 'interfaces/default/images/platforms/android.png';
    } else if (platformName.indexOf("iPad") > -1) {
        return 'interfaces/default/images/platforms/ios.png';
    } else if (platformName.indexOf("iPhone") > -1) {
        return 'interfaces/default/images/platforms/ios.png';
    } else if (platformName.indexOf("iOS") > -1) {
        return 'interfaces/default/images/platforms/ios.png';
    } else if (platformName.indexOf("Plex Home Theater") > -1) {
        return 'interfaces/default/images/platforms/pht.png';
    } else if (platformName.indexOf("Linux/RPi-XMBC") > -1) {
        return 'interfaces/default/images/platforms/xbmc.png';
    } else if (platformName.indexOf("Safari") > -1) {
        return 'interfaces/default/images/platforms/safari.png';
    } else if (platformName.indexOf("Internet Explorer") > -1) {
        return 'interfaces/default/images/platforms/ie.png';
    } else if (platformName.indexOf("Unknown Browser") > -1) {
        return 'interfaces/default/images/platforms/dafault.png';
    } else if (platformName.indexOf("Windows-XBMC") > -1) {
        return 'interfaces/default/images/platforms/xbmc.png';
    } else if (platformName.indexOf("Xbox") > -1) {
        return 'interfaces/default/images/platforms/xbox.png';
    } else if (platformName.indexOf("Samsung") > -1) {
        return 'interfaces/default/images/platforms/samsung.png';
    } else if (platformName.indexOf("Opera") > -1) {
        return 'interfaces/default/images/platforms/opera.png';
    } else if (platformName.indexOf("KODI") > -1) {
        return 'interfaces/default/images/platforms/kodi.png';
    } else if (platformName.indexOf("Mystery 3") > -1) {
        return 'interfaces/default/images/platforms/playstation.png';
    } else if (platformName.indexOf("Mystery 4") > -1) {
        return 'interfaces/default/images/platforms/playstation.png';
    } else {
        return 'interfaces/default/images/platforms/default.png';
    }
}

function isPrivateIP(ip_address) {
    if (ip_address.indexOf(".") > -1) {
        var parts = ip_address.split('.');
        if (parts[0] === '10' ||
            (parts[0] === '172' && (parseInt(parts[1], 10) >= 16 && parseInt(parts[1], 10) <= 31)) ||
            (parts[0] === '192' && parts[1] === '168')) {
            return true;
        }
        return false;
    } else {
        return true;
    }
}

function humanTime(seconds) {
    if (seconds >= 86400) {
        text = '<h1> / </h1><h3>' + Math.floor(moment.duration(seconds, 'seconds').asDays()) +
                '</h3><p> days </p><h3>' +  Math.floor(moment.duration((seconds % 86400), 'seconds').asHours()) +
                '</h3><p> hrs</p><h3>'  +  Math.floor(moment.duration(((seconds % 86400) % 3600), 'seconds').asMinutes()) + '</h3><p> mins</p>';
        return text;
    } else if (seconds >= 3600) {
        text = '<h1> / </h1><h3>' + Math.floor(moment.duration((seconds % 86400), 'seconds').asHours()) +
                '</h3><p>hrs</p><h3>' +  Math.floor(moment.duration(((seconds % 86400) % 3600), 'seconds').asMinutes()) + '</h3><p> mins</p>';
        return text;
    } else if (seconds >= 60) {
        text = '<h1> / </h1><h3>' + Math.floor(moment.duration(((seconds % 86400) % 3600), 'seconds').asMinutes()) + '</h3><p> mins</p>';
        return text;
    }
}

String.prototype.toProperCase = function () {
    return this.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
};