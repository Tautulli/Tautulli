function initConfigCheckbox(elem, toggleElem, reverse) {
    toggleElem = (toggleElem === undefined) ? null : toggleElem;
    reverse = (reverse === undefined) ? false : reverse;
    var config = toggleElem ? $(toggleElem) : $(elem).closest('div').next();
    config.css('overflow', 'hidden');
    if ($(elem).is(":checked")) {
        config.toggle(!reverse);
    } else {
        config.toggle(reverse);
    }
    $(elem).click(function () {
        var config = toggleElem ? $(toggleElem) : $(this).closest('div').next();
        if ($(this).is(":checked")) {
            config.slideToggleBool(!reverse);
        } else {
            config.slideToggleBool(reverse);
        }
    });
}

function refreshTab() {
    var url = $(location).attr('href');
    var tabId = $('.ui-tabs-panel:visible').attr("id");
    $('.ui-tabs-panel:visible').load(url + " #" + tabId, function () {
        initThisPage();
    });
}

function showMsg(msg, loader, timeout, ms, error) {
    var feedback = $("#ajaxMsg");
    var update = $("#updatebar");
    if (update.is(":visible")) {
        var height = update.height() + 35;
        feedback.css("bottom", height + "px");
    } else {
        feedback.removeAttr("style");
    }
    var message = $("<div class='msg'>" + msg + "</div>");
    if (loader) {
        message = $("<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbsp; " + msg + "</div>");
        feedback.css("padding", "14px 10px");
    }
    if (error) {
        feedback.css("background-color", "rgba(255,0,0,0.5)");
    }
    $(feedback).html(message);
    feedback.fadeIn();
    if (timeout) {
        setTimeout(function () {
            message.fadeOut(function () {
                $(this).remove();
                feedback.fadeOut();
                feedback.css("background-color", "");
            });
        }, ms);
    }
}

function confirmAjaxCall(url, msg, data, loader_msg, callback) {
    $("#confirm-message").html(msg);
    $('#confirm-modal').modal();
    $('#confirm-modal').one('click', '#confirm-button', function () {
        if (loader_msg) {
            showMsg(loader_msg, true, false);
        }
        $.ajax({
            url: url,
            type: 'POST',
            cache: false,
            async: true,
            data: data,
            complete: function (xhr, status) {
                var result = $.parseJSON(xhr.responseText);
                var msg = result.message;
                if (result.result == 'success') {
                    showMsg('<i class="fa fa-check"></i>&nbsp; ' + msg, false, true, 5000);
                } else {
                    showMsg('<i class="fa fa-times"></i>&nbsp; ' + msg, false, true, 5000, true);
                }
                if (typeof callback === "function") {
                    callback(result);
                }
            }
        });
    });
}

function doAjaxCall(url, elem, reload, form, showMsg, callback) {
    // Set Message
    var feedback = (showMsg) ? $("#ajaxMsg") : $();
    var update = $("#updatebar");
    if (update.is(":visible")) {
        var height = update.height() + 35;
        feedback.css("bottom", height + "px");
    } else {
        feedback.removeAttr("style");
    }
    feedback.fadeIn();
    // Get Form data
    var formID = "#" + url;
    var dataString;
    if (form === true) {
        dataString = $(formID).serialize();
    }
    // Loader Image
    var loader = $("<div class='msg ajaxLoader-" + url +"'><i class='fa fa-refresh fa-spin'></i>&nbsp; Saving...</div>");
    // Data Success Message
    var dataSucces = $(elem).data('success');
    if (typeof dataSucces === "undefined") {
        // Standard Message when variable is not set
        dataSucces = "Success!";
    }
    // Data Error Message
    var dataError = $(elem).data('error');
    if (typeof dataError === "undefined") {
        // Standard Message when variable is not set
        dataError = "There was an error";
    }
    // Get Success & Error message from inline data, else use standard message
    var succesMsg = $("<div class='msg'><i class='fa fa-check'></i>&nbsp; " + dataSucces + "</div>");
    var errorMsg = $("<div class='msg'><i class='fa fa-exclamation-triangle'></i>&nbsp; " + dataError + "</div>");
    // Check if checkbox is selected
    if (form) {
        if ($('td#select input[type=checkbox]').length > 0 && !$('td#select input[type=checkbox]').is(':checked') ||
            $('#importLastFM #username:visible').length > 0 && $("#importLastFM #username").val().length === 0) {
            feedback.addClass('error');
            $(feedback).prepend(errorMsg);
            setTimeout(function () {
                errorMsg.fadeOut(function () {
                    $(this).remove();
                    feedback.fadeOut(function () {
                        feedback.removeClass('error');
                    });
                });
                $(formID + " select").children('option[disabled=disabled]').attr('selected', 'selected');
            }, 2000);
            return false;
        }
    }
    // Ajax Call
    $.ajax({
        url: url,
        data: dataString,
        type: 'POST',
        beforeSend: function (jqXHR, settings) {
            // Start loader etc.
            feedback.prepend(loader);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            feedback.addClass('error');
            feedback.prepend(errorMsg);
            setTimeout(function () {
                errorMsg.fadeOut(function () {
                    $(this).remove();
                    feedback.fadeOut(function () {
                        feedback.removeClass('error');
                    });
                });
            }, 2000);
        },
        success: function (data, jqXHR) {
            feedback.prepend(succesMsg);
            feedback.addClass('success');
            setTimeout(function (e) {
                succesMsg.fadeOut(function () {
                    $(this).remove();
                    feedback.fadeOut(function () {
                        feedback.removeClass('success');
                    });
                    if (reload === true) refreshSubmenu();
                    if (reload === "table") {
                        refreshTable();
                    }
                    if (reload === "tabs") refreshTab();
                    if (reload === "page") location.reload();
                    if (reload === "submenu&table") {
                        refreshSubmenu();
                        refreshTable();
                    }
                    if (form) {
                        // Change the option to 'choose...'
                        $(formID + " select").children('option[disabled=disabled]').attr(
                            'selected', 'selected');
                    }
                });
            }, 2000);
        },
        complete: function (jqXHR, textStatus) {
            // Remove loaders and stuff, ajax request is complete!
            $('.ajaxLoader-' + url).remove();
            if (typeof callback === "function") {
                callback(jqXHR);
            }
        }
    });
}

function doSimpleAjaxCall(url) {
    $.ajax(url);
}

function resetFilters(text) {
    if ($(".dataTables_filter").length > 0) {
        $(".dataTables_filter input").attr("placeholder", "filter " + text + "");
    }
}

$.cachedScript = function (url) {
    return $.ajax({
        dataType: "script",
        cache: true,
        url: url
    });
};

function isPrivateIP(ip_address) {
    var defer = $.Deferred();

    $.cachedScript('js/ipaddr.min.js').done(function () {
        if (ipaddr.isValid(ip_address)) {
            var addr = ipaddr.process(ip_address);

            var rangeList = [];
            if (addr.kind() === 'ipv4') {
                rangeList = [
                    ipaddr.parseCIDR('127.0.0.0/8'),
                    ipaddr.parseCIDR('10.0.0.0/8'),
                    ipaddr.parseCIDR('172.16.0.0/12'),
                    ipaddr.parseCIDR('192.168.0.0/16')
                ];
            } else {
                rangeList = [
                    ipaddr.parseCIDR('fd00::/8')
                ];
            }

            if (ipaddr.subnetMatch(addr, rangeList, -1) >= 0) {
                defer.resolve();
            } else {
                defer.reject();
            }
        } else {
            defer.resolve('n/a');
        }
    });

    return defer.promise();
}

function humanTime(seconds) {
    var text;
    if (seconds >= 86400) {
        text = '<h3>' + Math.floor(moment.duration(seconds, 'seconds').asDays()) + '</h3><p> days</p>' + '<h3>' +
            Math.floor(moment.duration((seconds % 86400), 'seconds').asHours()) + '</h3><p> hrs</p>' + '<h3>' +
            Math.floor(moment.duration(((seconds % 86400) % 3600), 'seconds').asMinutes()) + '</h3><p> mins</p>';
        return text;
    } else if (seconds >= 3600) {
        text = '<h3>' + Math.floor(moment.duration((seconds % 86400), 'seconds').asHours()) + '</h3><p> hrs</p>' +
            '<h3>' + Math.floor(moment.duration(((seconds % 86400) % 3600), 'seconds').asMinutes()) +
            '</h3><p> mins</p>';
        return text;
    } else if (seconds >= 60) {
        text = '<h3>' + Math.floor(moment.duration(((seconds % 86400) % 3600), 'seconds').asMinutes()) +
            '</h3><p> mins</p>';
        return text;
    } else {
        text = '<h3>0</h3><p> mins</p>';
        return text;
    }
}

function humanTimeClean(seconds) {
    var text;
    if (seconds >= 86400) {
        text = Math.floor(moment.duration(seconds, 'seconds').asDays()) + ' days ' + Math.floor(moment.duration((
            seconds % 86400), 'seconds').asHours()) + ' hrs ' + Math.floor(moment.duration(
            ((seconds % 86400) % 3600), 'seconds').asMinutes()) + ' mins';
        return text;
    } else if (seconds >= 3600) {
        text = Math.floor(moment.duration((seconds % 86400), 'seconds').asHours()) + ' hrs ' + Math.floor(moment.duration(
            ((seconds % 86400) % 3600), 'seconds').asMinutes()) + ' mins';
        return text;
    } else if (seconds >= 60) {
        text = Math.floor(moment.duration(((seconds % 86400) % 3600), 'seconds').asMinutes()) + ' mins';
        return text;
    } else {
        text = '0';
        return text;
    }
}
String.prototype.toProperCase = function () {
    return this.replace(/\w\S*/g, function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
};

function millisecondsToMinutes(ms, roundToMinute) {
    if (ms > 0) {
      var minutes = Math.floor(ms / 60000);
      var seconds = ((ms % 60000) / 1000).toFixed(0);
      if (roundToMinute) {
          return (seconds >= 30 ? (minutes + 1) : minutes);
      } else {
          return (seconds == 60 ? (minutes + 1) + ":00" : minutes + ":" + (seconds < 10 ? "0" : "") + seconds);
      }
    } else {
        if (roundToMinute) {
            return '0';
        } else {
            return '0:00';
        }
    }
}
// Our countdown plugin takes a callback, a duration, and an optional message
$.fn.countdown = function (callback, duration, message) {
    // If no message is provided, we use an empty string
    message = message || "";
    // Get reference to container, and set initial content
    var container = $(this[0]).html(duration + message);
    // Get reference to the interval doing the countdown
    var countdown = setInterval(function () {
        // If seconds remain
        if (--duration) {
            // Update our container's message
            container.html(duration + message);
            // Otherwise
        } else {
            // Clear the countdown interval
            clearInterval(countdown);
            // And fire the callback passing our container as `this`
            callback.call(container);
        }
        // Run interval every 1000ms (1 second)
    }, 1000);
};

function setCookie(cname, cvalue, exdays) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays * 24 * 60 * 60 * 1000));
    var expires = "expires=" + d.toUTCString();
    document.cookie = cname + "=" + cvalue + "; " + expires;
}

function getCookie(cname) {
    var name = cname + "=";
    var ca = document.cookie.split(';');
    for (var i = 0; i < ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') c = c.substring(1);
        if (c.indexOf(name) === 0) return c.substring(name.length, c.length);
    }
    return "";
}
var Accordion = function (el, multiple, close) {
    this.el = el || {};
    this.multiple = multiple || false;
    this.close = (close === undefined) ? true : close;
    // Variables privadas
    var links = this.el.find('.link');
    // Evento
    links.on('click', {
        el: this.el,
        multiple: this.multiple,
        close: this.close
    }, this.dropdown);
};
Accordion.prototype.dropdown = function (e) {
    var $el = e.data.el;
    $this = $(this);
    $next = $this.next();
    if (!e.data.close && $this.parent().hasClass('open')) {
        return
    }
    $next.slideToggle();
    $this.parent().toggleClass('open');
    if (!e.data.multiple) {
        $el.find('.submenu').not($next).slideUp().parent().removeClass('open');
    }
};

function clearSearchButton(tableName, table) {
    $('#' + tableName + '_filter').find('input[type=search]').wrap(
        '<div class="input-group" role="group" aria-label="Search"></div>').after(
        '<span class="input-group-btn"><button class="btn btn-form" data-toggle="button" aria-pressed="false" autocomplete="off" id="clear-search-' +
        tableName + '"><i class="fa fa-remove"></i></button></span>');
    $('#clear-search-' + tableName).click(function () {
        table.search('').draw();
    });
}
// Taken from https://github.com/Hellowlol/HTPC-Manager
window.onerror = function (message, file, line) {
    var e = {
        'page': window.location.href,
        'message': message,
        'file': file,
        'line': line
    };
    $.post("log_js_errors", e, function (data) { });
};

$('*').on('click', '.refresh_pms_image', function (e) {
    e.preventDefault();
    e.stopPropagation();

    var background_div = $(this).parent().siblings(['style*=pms_image_proxy']).first();
    var pms_proxy_url = background_div.css('background-image');
    pms_proxy_url = /^url\((['"]?)(.*)\1\)$/.exec(pms_proxy_url);
    pms_proxy_url = pms_proxy_url ? pms_proxy_url[2] : ""; // If matched, retrieve url, otherwise ""

    if (pms_proxy_url.indexOf('pms_image_proxy') == -1) {
        console.log('PMS image proxy url not found.');
    } else {
        if (pms_proxy_url.indexOf('refresh=true') > -1) {
            pms_proxy_url = pms_proxy_url.replace("&refresh=true", "");
            background_div.css('background-image', 'url(' + pms_proxy_url + ')');
            background_div.css('background-image', 'url(' + pms_proxy_url + '&refresh=true)');
        } else {
            background_div.css('background-image', 'url(' + pms_proxy_url + '&refresh=true)');
        }
    }
});

// Taken from http://stackoverflow.com/questions/10420352/converting-file-size-in-bytes-to-human-readable#answer-14919494
function humanFileSize(bytes, si) {
    var thresh = si ? 1000 : 1024;
    if (Math.abs(bytes) < thresh) {
        return bytes + ' B';
    }
    var units = si ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        : ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
    var u = -1;
    do {
        bytes /= thresh;
        ++u;
    } while (Math.abs(bytes) >= thresh && u < units.length - 1);
    return bytes.toFixed(1) + '&nbsp;' + units[u];
}

// Force max/min in number inputs
function forceMinMax(elem) {
    var min = parseInt(elem.attr('min'));
    var max = parseInt(elem.attr('max'));
    var val = parseInt(elem.val());
    var default_val = parseInt(elem.data('default'));
    if (isNaN(val)) {
        elem.val(default_val);
    }
    else if (min !== undefined && val < min) {
        elem.val(min);
    }
    else if (max !== undefined && val > max) {
        elem.val(max);
    }
    else {
        elem.val(val);
    }
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

$.fn.slideToggleBool = function(bool, options) {
  return bool ? $(this).slideDown(options) : $(this).slideUp(options);
};

function openPlexXML(endpoint, plextv, params) {
    var data = $.extend({endpoint: endpoint, plextv: plextv}, params);
    $.getJSON('return_plex_xml_url', data, function(xml_url) {
       window.open(xml_url, '_blank');
    });
}

function PopupCenter(url, title, w, h) {
    // Fixes dual-screen position                         Most browsers      Firefox
    var dualScreenLeft = window.screenLeft != undefined ? window.screenLeft : window.screenX;
    var dualScreenTop = window.screenTop != undefined ? window.screenTop : window.screenY;

    var width = window.innerWidth ? window.innerWidth : document.documentElement.clientWidth ? document.documentElement.clientWidth : screen.width;
    var height = window.innerHeight ? window.innerHeight : document.documentElement.clientHeight ? document.documentElement.clientHeight : screen.height;

    var left = ((width / 2) - (w / 2)) + dualScreenLeft;
    var top = ((height / 2) - (h / 2)) + dualScreenTop;
    var newWindow = window.open(url, title, 'scrollbars=yes, width=' + w + ', height=' + h + ', top=' + top + ', left=' + left);

    // Puts focus on the newWindow
    if (window.focus) {
        newWindow.focus();
    }

    return newWindow;
}

if (!localStorage.getItem('Tautulli_ClientId')) {
    localStorage.setItem('Tautulli_ClientId', uuidv4());
}

function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    )
}

var x_plex_headers = {
    'Accept': 'application/json',
    'X-Plex-Product': 'Tautulli',
    'X-Plex-Version': 'Plex OAuth',
    'X-Plex-Client-Identifier': localStorage.getItem('Tautulli_ClientId'),
    'X-Plex-Platform': platform.name,
    'X-Plex-Platform-Version': platform.version,
    'X-Plex-Device': platform.os.toString(),
    'X-Plex-Device-Name': platform.name
};

var plex_oauth_window = null;
const plex_oauth_loader = '<style>' +
        '.login-loader-container {' +
            'font-family: "Open Sans", Arial, sans-serif;' +
            'position: absolute;' +
            'top: 0;' +
            'right: 0;' +
            'bottom: 0;' +
            'left: 0;' +
        '}' +
        '.login-loader-message {' +
            'color: #282A2D;' +
            'text-align: center;' +
            'position: absolute;' +
            'left: 50%;' +
            'top: 25%;' +
            'transform: translate(-50%, -50%);' +
        '}' +
        '.login-loader {' +
            'border: 5px solid #ccc;' +
            '-webkit-animation: spin 1s linear infinite;' +
            'animation: spin 1s linear infinite;' +
            'border-top: 5px solid #282A2D;' +
            'border-radius: 50%;' +
            'width: 50px;' +
            'height: 50px;' +
            'position: relative;' +
            'left: calc(50% - 25px);' +
        '}' +
        '@keyframes spin {' +
            '0% { transform: rotate(0deg); }' +
            '100% { transform: rotate(360deg); }' +
        '}' +
    '</style>' +
    '<div class="login-loader-container">' +
        '<div class="login-loader-message">' +
            '<div class="login-loader"></div>' +
            '<br>' +
            'Redirecting to the Plex login page...' +
        '</div>' +
    '</div>';

function closePlexOAuthWindow() {
    if (plex_oauth_window) {
        plex_oauth_window.close();
    }
}

getPlexOAuthPin = function () {
    var deferred = $.Deferred();

    $.ajax({
        url: 'https://plex.tv/api/v2/pins?strong=true',
        type: 'POST',
        headers: x_plex_headers,
        success: function(data) {
            plex_oauth_window.location = 'https://app.plex.tv/auth/#!?clientID=' + x_plex_headers['X-Plex-Client-Identifier'] + '&code=' + data.code;
            deferred.resolve({pin: data.id, code: data.code});
        },
        error: function() {
            closePlexOAuthWindow();
            deferred.reject();
        }
    });
    return deferred;
};

var polling = null;

function PlexOAuth(success, error, pre) {
    if (typeof pre === "function") {
        pre()
    }
    clearTimeout(polling);
    closePlexOAuthWindow();
    plex_oauth_window = PopupCenter('', 'Plex-OAuth', 600, 700);
    $(plex_oauth_window.document.body).html(plex_oauth_loader);

    getPlexOAuthPin().then(function (data) {
        const pin = data.pin;
        const code = data.code;
        var keep_polling = true;

        (function poll() {
            polling = setTimeout(function () {
                $.ajax({
                    url: 'https://plex.tv/api/v2/pins/' + pin,
                    type: 'GET',
                    headers: x_plex_headers,
                    success: function (data) {
                        if (data.authToken){
                            keep_polling = false;
                            closePlexOAuthWindow();
                            if (typeof success === "function") {
                                success(data.authToken)
                            }
                        }
                    },
                    error: function () {
                        keep_polling = false;
                        closePlexOAuthWindow();
                        if (typeof error === "function") {
                            error()
                        }
                    },
                    complete: function () {
                        if (keep_polling){
                            poll();
                        } else {
                            clearTimeout(polling);
                        }
                    },
                    timeout: 1000
                });
            }, 1000);
        })();
    }, function () {
        closePlexOAuthWindow();
        if (typeof error === "function") {
            error()
        }
    });
}