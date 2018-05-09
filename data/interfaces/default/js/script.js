function initConfigCheckbox(elem, reverse) {
    var config = $(elem).closest('div').next();
    config.css('overflow', 'hidden');
    if (reverse) {
        if ($(elem).is(":checked")) {
            config.hide();
        } else {
            config.show();
        }
    } else {
        if ($(elem).is(":checked")) {
            config.show();
        } else {
            config.hide();
        }
    }
    $(elem).click(function () {
        var config = $(this).closest('div').next();
        if (reverse) {
            if ($(this).is(":checked")) {
                config.slideUp();
            } else {
                config.slideDown();
            }

        } else {
            if ($(this).is(":checked")) {
                config.slideDown();
            } else {
                config.slideUp();
            }
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
        message = $("<i class='fa fa-refresh fa-spin'></i> " + msg + "</div>");
        feedback.css("padding", "14px 10px")
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
            showMsg(loader_msg, true, false)
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
                    showMsg('<i class="fa fa-check"></i> ' + msg, false, true, 5000)
                } else {
                    showMsg('<i class="fa fa-times"></i> ' + msg, false, true, 5000, true)
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
    feedback = (showMsg) ? $("#ajaxMsg") : $();
    update = $("#updatebar");
    if (update.is(":visible")) {
        var height = update.height() + 35;
        feedback.css("bottom", height + "px");
    } else {
        feedback.removeAttr("style");
    }
    feedback.fadeIn();
    // Get Form data
    var formID = "#" + url;
    if (form == true) {
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
    if (form) {
        if ($('td#select input[type=checkbox]').length > 0 && !$('td#select input[type=checkbox]').is(':checked') ||
            $('#importLastFM #username:visible').length > 0 && $("#importLastFM #username").val().length === 0) {
            feedback.addClass('error')
            $(feedback).prepend(errorMsg);
            setTimeout(function () {
                errorMsg.fadeOut(function () {
                    $(this).remove();
                    feedback.fadeOut(function () {
                        feedback.removeClass('error');
                    });
                })
                $(formID + " select").children('option[disabled=disabled]').attr('selected', 'selected');
            }, 2000);
            return false;
        }
    }
    // Ajax Call
    $.ajax({
        url: url,
        data: dataString,
        type: 'post',
        beforeSend: function (jqXHR, settings) {
            // Start loader etc.
            feedback.prepend(loader);
        },
        error: function (jqXHR, textStatus, errorThrown) {
            feedback.addClass('error')
            feedback.prepend(errorMsg);
            setTimeout(function () {
                errorMsg.fadeOut(function () {
                    $(this).remove();
                    feedback.fadeOut(function () {
                        feedback.removeClass('error')
                    });
                })
            }, 2000);
        },
        success: function (data, jqXHR) {
            feedback.prepend(succesMsg);
            feedback.addClass('success')
            setTimeout(function (e) {
                succesMsg.fadeOut(function () {
                    $(this).remove();
                    feedback.fadeOut(function () {
                        feedback.removeClass('success');
                    });
                    if (reload == true) refreshSubmenu();
                    if (reload == "table") {
                        refreshTable();
                    }
                    if (reload == "tabs") refreshTab();
                    if (reload == "page") location.reload();
                    if (reload == "submenu&table") {
                        refreshSubmenu();
                        refreshTable();
                    }
                    if (form) {
                        // Change the option to 'choose...'
                        $(formID + " select").children('option[disabled=disabled]').attr(
                            'selected', 'selected');
                    }
                })
            }, 2000);
        },
        complete: function (jqXHR, textStatus) {
            // Remove loaders and stuff, ajax request is complete!
            loader.remove();
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
            var addr = ipaddr.process(ip_address)

            if (addr.kind() === 'ipv4') {
                var rangeList = [
                    ipaddr.parseCIDR('127.0.0.0/8'),
                    ipaddr.parseCIDR('10.0.0.0/8'),
                    ipaddr.parseCIDR('172.16.0.0/12'),
                    ipaddr.parseCIDR('192.168.0.0/16')
                ]
            } else {
                var rangeList = [
                    ipaddr.parseCIDR('fd00::/8')
                ]
            }

            if (ipaddr.subnetMatch(addr, rangeList, -1) >= 0) {
                defer.resolve();
            } else {
                defer.reject();
            }
        } else {
            defer.resolve('n/a');
        }
    })

    return defer.promise();
}

function humanTime(seconds) {
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
        if (c.indexOf(name) == 0) return c.substring(name.length, c.length);
    }
    return "";
}
var Accordion = function (el, multiple) {
    this.el = el || {};
    this.multiple = multiple || false;
    // Variables privadas
    var links = this.el.find('.link');
    // Evento
    links.on('click', {
        el: this.el,
        multiple: this.multiple
    }, this.dropdown)
}
Accordion.prototype.dropdown = function (e) {
    var $el = e.data.el;
    $this = $(this),
        $next = $this.next();
    $next.slideToggle();
    $this.parent().toggleClass('open');
    if (!e.data.multiple) {
        $el.find('.submenu').not($next).slideUp().parent().removeClass('open');
    };
}

function clearSearchButton(tableName, table) {
    $('#' + tableName + '_filter').find('input[type=search]').wrap(
        '<div class="input-group" role="group" aria-label="Search"></div>').after(
        '<span class="input-group-btn"><button class="btn btn-form" data-toggle="button" aria-pressed="false" autocomplete="off" id="clear-search-' +
        tableName + '"><i class="fa fa-remove"></i></button></span>')
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
            console.log(pms_proxy_url)
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
    var units = si
        ? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
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
    else if (min != undefined && val < min) {
        elem.val(min);
    }
    else if (max != undefined && val > max) {
        elem.val(max);
    }
    else {
        elem.val(val);
    }
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}