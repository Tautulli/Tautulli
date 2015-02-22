window.log = function(){
    log.history = log.history || [];
    log.history.push(arguments);
    arguments.callee = arguments.callee.caller;

    if (this.console) {
        console.log(Array.prototype.slice.call(arguments));
    }
};

function toggle(source) {
    checkboxes = document.getElementsByClassName('checkbox');

    for (var i in checkboxes) {
        checkboxes[i].checked = source.checked;
    }
}