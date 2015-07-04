var log_table_options = {
    "destroy": true,
    "responsive": {
        details: false
    },
    "serverSide": true,
    "processing": false,
    "sPaginationType": "bootstrap",
    "order": [ 0, 'desc'],
    "pageLength": 10,
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
            "className": "no-wrap"
        },
        {
            "targets": [1],
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [2],
            "width": "75%"
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        $('html,body').scrollTop(0);
        $('#ajaxMsg').addClass('success').fadeOut();
    },
    "preDrawCallback": function(settings) {
        $('#ajaxMsg').html("<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...</div>");
        $('#ajaxMsg').addClass('success').fadeIn();
    }
}
