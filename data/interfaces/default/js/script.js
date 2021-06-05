var p = {
    name: 'Unknown',
    version: 'Unknown',
    os: 'Unknown'
};
if (typeof platform !== 'undefined') {
    p.name = platform.name;
    p.version = platform.version;
    p.os = platform.os.toString();
}

if (['IE', 'Microsoft Edge', 'IE Mobile'].indexOf(p.name) > -1) {
    if (!getCookie('browserDismiss')) {
        var $browser_warning = $('<div id="browser-warning">' +
            '<i class="fa fa-exclamation-circle"></i>&nbsp;' +
            'Tautulli does not support Internet Explorer or Microsoft Edge! ' +
            'Please use a different browser such as Chrome or Firefox.' +
            '<button type="button" class="close"><i class="fa fa-remove"></i></button>' +
            '</div>');
        $('body').prepend($browser_warning);
        var offset = $browser_warning.height();
        warningOffset(offset);

        $browser_warning.one('click', 'button.close', function () {
            $browser_warning.remove();
            warningOffset(-offset);
            setCookie('browserDismiss', 'true', 7);
        });

        function warningOffset(offset) {
            var navbar = $('.navbar-fixed-top');
            if (navbar.length) {
                navbar.offset({top: navbar.offset().top + offset});
            }
            var container = $('.body-container');
            if (container.length) {
                container.offset({top: container.offset().top + offset});
            }
        }
    }
}

function initConfigCheckbox(elem, toggleElem, reverse) {
    toggleElem = (toggleElem === undefined) ? null : toggleElem;
    reverse = (reverse === undefined) ? false : reverse;
    var config = toggleElem ? $(toggleElem) : $(elem).closest('div').next();
    config.addClass('hidden-settings');
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
    var token_error = $("#token_error_bar");
    if (update.is(":visible") || token_error.is(":visible")) {
        var height = (update.is(":visible") ? update.height() : 0) + (token_error.is(":visible") ? token_error.height() : 0) + 35;
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
    var token_error = $("#token_error_bar");
    if (update.is(":visible") || token_error.is(":visible")) {
        var height = (update.is(":visible") ? update.height() : 0) + (token_error.is(":visible") ? token_error.height() : 0) + 35;
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

getBrowsePath = function (key, path, filter_ext) {
    var deferred = $.Deferred();

    $.ajax({
        url: 'browse_path',
        type: 'GET',
        data: {
            key: key,
            path: path,
            filter_ext: filter_ext
        },
        success: function(data) {
            deferred.resolve(data);
        },
        error: function() {
            deferred.reject();
        }
    });
    return deferred;
};

function doSimpleAjaxCall(url) {
    $.ajax(url);
}

function resetFilters(text) {
    if ($(".dataTables_filter").length > 0) {
        $(".dataTables_filter input").attr("placeholder", "filter " + text + "");
    }
}

function isPrivateIP(ip_address) {
    var defer = $.Deferred();

    if (ipaddr.isValid(ip_address)) {
        var addr = ipaddr.process(ip_address);
        if (addr.range() === 'loopback' || addr.range() === 'private' || addr.range() === 'linkLocal') {
            defer.resolve();
        } else {
            defer.reject();
        }
    } else {
        defer.resolve('n/a');
    }

    return defer.promise();
}

function humanTime(seconds) {
    var d = Math.floor(moment.duration(seconds, 'seconds').asDays());
    var h = Math.floor(moment.duration((seconds % 86400), 'seconds').asHours());
    var m = Math.round(moment.duration(((seconds % 86400) % 3600), 'seconds').asMinutes());

    var text = '';
    if (d > 0) {
        text = '<h3>' + d + '</h3><p> day' + ((d > 1) ? 's' : '') + '</p>'
             + '<h3>' + h + '</h3><p> hr' + ((h > 1) ? 's' : '') + '</p>'
             + '<h3>' + m + '</h3><p> min' + ((m > 1) ? 's' : '') + '</p>';
    } else if (h > 0) {
        text = '<h3>' + h + '</h3><p> hr' + ((h > 1) ? 's' : '') + '</p>'
             + '<h3>' + m + '</h3><p> min' + ((m > 1) ? 's' : '') + '</p>';
    } else {
        text = '<h3>' + m + '</h3><p> min' + ((m > 1) ? 's' : '') + '</p>';
    }

    return text
}

String.prototype.toProperCase = function () {
    return this.replace(/\w\S*/g, function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
};

function getPercent(value1, value2) {
    value1 = parseFloat(value1) | 0
    value2 = parseFloat(value2) | 0

    var percent = 0;
    if (value1 !== 0 && value2 !== 0) {
        percent = (value1 / value2) * 100
    }

    return Math.round(percent)
}

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

function humanDuration(ms, sig='dhm', units='ms', return_seconds=300000) {
    var factors = {
        d: 86400000,
        h: 3600000,
        m: 60000,
        s: 1000,
        ms: 1
    }

    ms = parseInt(ms);
    var d, h, m, s;

    if (ms > 0) {
        if (return_seconds && ms < return_seconds) {
            sig = 'dhms'
        }

        ms = ms * factors[units];

        h =  ms % factors['d'];
        d = Math.trunc(ms / factors['d']);

        m = h % factors['h'];
        h = Math.trunc(h / factors['h']);

        s = m % factors['m'];
        m = Math.trunc(m / factors['m']);

        ms = s % factors['s'];
        s = Math.trunc(s / factors['s']);

        var hd_list = [];
        if (sig >= 'd' && d > 0) {
            d = (sig === 'd' && h >= 12) ? d + 1 : d;
            hd_list.push(d.toString() + ' day' + ((d > 1) ? 's' : ''));
        }
        if (sig >= 'dh' && h > 0) {
            h = (sig === 'dh' && m >= 30) ? h + 1 : h;
            hd_list.push(h.toString() + ' hr' + ((h > 1) ? 's' : ''));
        }
        if (sig >= 'dhm' && m > 0) {
            m = (sig === 'dhm' && s >= 30) ? m + 1 : m;
            hd_list.push(m.toString() + ' min' + ((m > 1) ? 's' : ''));
        }
        if (sig >= 'dhms' && s > 0) {
            hd_list.push(s.toString() + ' sec' + ((s > 1) ? 's' : ''));
        }

        return hd_list.join(' ')
    } else {
        return '0'
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

    if (pms_proxy_url.indexOf('pms_image_proxy') === -1) {
        console.log('PMS image proxy url not found.');
    } else {
        background_div.css('background-image', 'none')
        $.ajax({
            url: pms_proxy_url,
            headers: {
                'Cache-Control': 'no-cache'
            },
            success: function () {
                background_div.css('background-image', 'url(' + pms_proxy_url + ')');
            }
        });
    }
});

// Taken from http://stackoverflow.com/questions/10420352/converting-file-size-in-bytes-to-human-readable#answer-14919494
function humanFileSize(bytes, si = true) {
    //var thresh = si ? 1000 : 1024;
    var thresh = 1024;  // Always divide by 2^10 but display SI units
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


function setLocalStorage(key, value, path) {
    var key_path = key;
    if (path !== false) {
        key_path = key_path + '_' + window.location.pathname;
    }
    localStorage.setItem(key_path, value);
}
function getLocalStorage(key, default_value, path) {
    var key_path = key;
    if (path !== false) {
        key_path = key_path + '_' + window.location.pathname;
    }
    var value = localStorage.getItem(key_path);
    if (value !== null) {
        return value
    } else if (default_value !== undefined) {
        setLocalStorage(key, default_value, path);
        return default_value
    }
}

function uuidv4() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, function(c) {
        var cryptoObj = window.crypto || window.msCrypto; // for IE 11
        return (c ^ cryptoObj.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    });
}

function getPlexHeaders() {
    return {
        'Accept': 'application/json',
        'X-Plex-Product': 'Tautulli',
        'X-Plex-Version': 'Plex OAuth',
        'X-Plex-Client-Identifier': getLocalStorage('Tautulli_ClientID', uuidv4(), false),
        'X-Plex-Platform': p.name,
        'X-Plex-Platform-Version': p.version,
        'X-Plex-Model': 'Plex OAuth',
        'X-Plex-Device': p.os,
        'X-Plex-Device-Name': p.name,
        'X-Plex-Device-Screen-Resolution': window.screen.width + 'x' + window.screen.height,
        'X-Plex-Language': 'en'
    };
}

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
    var x_plex_headers = getPlexHeaders();
    var deferred = $.Deferred();

    $.ajax({
        url: 'https://plex.tv/api/v2/pins?strong=true',
        type: 'POST',
        headers: x_plex_headers,
        success: function(data) {
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
    closePlexOAuthWindow();
    plex_oauth_window = PopupCenter('', 'Plex-OAuth', 600, 700);
    $(plex_oauth_window.document.body).html(plex_oauth_loader);

    getPlexOAuthPin().then(function (data) {
        var x_plex_headers = getPlexHeaders();
        const pin = data.pin;
        const code = data.code;

        var oauth_params = {
            'clientID': x_plex_headers['X-Plex-Client-Identifier'],
            'context[device][product]': x_plex_headers['X-Plex-Product'],
            'context[device][version]': x_plex_headers['X-Plex-Version'],
            'context[device][platform]': x_plex_headers['X-Plex-Platform'],
            'context[device][platformVersion]': x_plex_headers['X-Plex-Platform-Version'],
            'context[device][device]': x_plex_headers['X-Plex-Device'],
            'context[device][deviceName]': x_plex_headers['X-Plex-Device-Name'],
            'context[device][model]': x_plex_headers['X-Plex-Model'],
            'context[device][screenResolution]': x_plex_headers['X-Plex-Device-Screen-Resolution'],
            'context[device][layout]': 'desktop',
            'code': code
        }

        plex_oauth_window.location = 'https://app.plex.tv/auth/#!?' + encodeData(oauth_params);
        polling = pin;

        (function poll() {
            $.ajax({
                url: 'https://plex.tv/api/v2/pins/' + pin,
                type: 'GET',
                headers: x_plex_headers,
                success: function (data) {
                    if (data.authToken){
                        closePlexOAuthWindow();
                        if (typeof success === "function") {
                            success(data.authToken)
                        }
                    }
                },
                error: function (jqXHR, textStatus, errorThrown) {
                    if (textStatus !== "timeout") {
                        closePlexOAuthWindow();
                        if (typeof error === "function") {
                            error()
                        }
                    }
                },
                complete: function () {
                    if (!plex_oauth_window.closed && polling === pin){
                        setTimeout(function() {poll()}, 1000);
                    }
                },
                timeout: 10000
            });
        })();
    }, function () {
        closePlexOAuthWindow();
        if (typeof error === "function") {
            error()
        }
    });
}

function encodeData(data) {
    return Object.keys(data).map(function(key) {
        return [key, data[key]].map(encodeURIComponent).join("=");
    }).join("&");
}

function page(endpoint, ...args) {
    let endpoints = {
        'pms_image_proxy': pms_image_proxy,
        'info': info_page,
        'library': library_page,
        'user': user_page
    };

    var params = {};

    if (endpoint in endpoints) {
        params = endpoints[endpoint](...args);
    }

    return endpoint + '?' + $.param(params).replace(/'/g, '%27');
}

function pms_image_proxy(img, rating_key, width, height, opacity, background, blur, fallback, refresh, clip, img_format) {
    var params = {};

    if (img != null) { params.img = img; }
    if (rating_key != null) { params.rating_key = rating_key; }
    if (width != null) { params.width = width; }
    if (height != null) { params.height = height; }
    if (opacity != null) { params.opacity = opacity; }
    if (background != null) { params.background = background; }
    if (blur != null) { params.blur = blur; }
    if (fallback != null) { params.fallback = fallback; }
    if (refresh != null) { params.refresh = true; }
    if (clip != null) { params.clip = true; }
    if (img_format != null) { params.img_format = img_format; }

    return params;
}

function info_page(rating_key, guid, history, live) {
    var params = {};

    if (live && history) {
        params.guid = guid;
    } else {
        params.rating_key = rating_key;
    }

    if (history) { params.source = 'history'; }

    return params;
}

function library_page(section_id) {
    var params = {};

    if (section_id != null) { params.section_id = section_id; }

    return params;
}

function user_page(user_id, user) {
    var params = {};

    if (user_id != null) { params.user_id = user_id; }
    if (user != null) { params.user = user; }

    return params;
}

MEDIA_TYPE_HEADERS = {
    'movie': 'Movies',
    'show': 'TV Shows',
    'season': 'Seasons',
    'episode': 'Episodes',
    'artist': 'Artists',
    'album': 'Albums',
    'track': 'Tracks',
    'video': 'Videos',
    'audio': 'Tracks',
    'photo': 'Photos'
}

function short_season(title) {
    if (title.startsWith('Season ') && /^\d+$/.test(title.substring(7))) {
        return 'S' + title.substring(7)
    }
    return title
}

function loadAllBlurHash() {
    $('[data-blurhash]').each(function() {
        const elem = $(this);
        const src = elem.data('blurhash');
        loadBlurHash(elem, src);
    });
}

function loadBlurHash(elem, src) {
    const img = new Image();
    img.src = src;
    img.onload = () => {
        const imgData = blurhash.getImageData(img);

        blurhash
            .encodePromise(imgData, img.width, img.height, 4, 4)
            .then(hash => {
                return blurhash.decodePromise(
                    hash,
                    img.width,
                    img.height
                );
            })
            .then(blurhashImgData => {
                const imgObject = blurhash.getImageDataAsImage(
                    blurhashImgData,
                    img.width,
                    img.height,
                    (event, imgObject) => {
                        elem.css('background-image', 'url(' + imgObject.src + ')')
                    }
                );
            });
    }
}

function _toggleRevealToken(elem, click) {
    var input = elem.parent().siblings('input');
    if ((input.prop('type') === 'password' && click) || !input.val()) {
        input.prop('type', 'text');
        elem.children('.fa').removeClass('fa-eye-slash').addClass('fa-eye');
    } else {
        input.prop('type', 'password');
        elem.children('.fa').removeClass('fa-eye').addClass('fa-eye-slash');
    }
}
function toggleRevealTokens() {
    $('.reveal-token').each(function () {
        _toggleRevealToken($(this));
    });
}

$('body').on('click', '.reveal-token', function() {
    _toggleRevealToken($(this), true);
});

// https://stackoverflow.com/a/57414592
// prevent modal close when click starts in modal and ends on backdrop
$(document).on('mousedown', '.modal', function(e){
    window.clickStartedInModal = $(e.target).is('.modal-dialog *');
});
$(document).on('mouseup', '.modal', function(e){
    if(!$(e.target).is('.modal-dialog *') && window.clickStartedInModal) {
        window.preventModalClose = true;
    }
});
$('.modal').on('hide.bs.modal', function (e) {
    if(window.preventModalClose){
        window.preventModalClose = false;
        return false;
    }
});
