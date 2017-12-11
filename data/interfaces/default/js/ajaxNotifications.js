// Taken from https://github.com/SickRage/SickRage

PNotify.prototype.options.addclass = "stack-bottomright";
PNotify.prototype.options.buttons.closer_hover = false;
PNotify.prototype.options.desktop = { desktop: true, icon: 'images/logo.png' }
PNotify.prototype.options.history = false;
PNotify.prototype.options.shadow = false;
PNotify.prototype.options.stack = { dir1: 'up', dir2: 'left', firstpos1: 25, firstpos2: 25 };
PNotify.prototype.options.styling = 'fontawesome';
PNotify.prototype.options.type = 'notice';
PNotify.prototype.options.width = '340px';

function displayPNotify(title, message) {
    var notification = new PNotify({
        title: title,
        text: message
    });
}

function check_notifications() {
    $.getJSON('get_browser_notifications', function (data) {
        if (data) {
            $.each(data, function (i, notification) {
                if (notification.delay == 0) {
                    PNotify.prototype.options.hide = false;
                } else {
                    PNotify.prototype.options.hide = true;
                    PNotify.prototype.options.delay = notification.delay * 1000;
                }
                displayPNotify(notification.subject_text, notification.body_text);
            });
        }
    });
    setTimeout(function () {
        "use strict";
        check_notifications();
    }, 3000);
}

$(document).ready(function () {
    check_notifications();
});