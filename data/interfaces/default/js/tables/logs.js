var log_table_options = {
    "destroy": true,
    "serverSide": true,
    "processing": false,
    "pagingType": "bootstrap",
    "order": [ 0, 'desc'],
    "pageLength": 50,
    "stateSave": false,
    "language": {
                "search":"Search: ",
                "lengthMenu":"Show _MENU_ lines per page",
                "emptyTable": "No log information available",
                "info":"Showing _START_ to _END_ of _TOTAL_ lines",
                "infoEmpty":"Showing 0 to 0 of 0 lines",
                "infoFiltered":"(filtered from _MAX_ total lines)"},
    "columnDefs": [
        {
            "targets": [0],
            "width": "15%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [1],
            "width": "10%",
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [2],
            "width": "75%"
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        //$('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...";
        showMsg(msg, false, false, 0)
    }
}
