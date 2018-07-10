var plex_log_table_options = {
    "destroy": true,
    "serverSide": false,
    "processing": false,
    "pagingType": "full_numbers",
    "order": [ 0, 'desc'],
    "pageLength": 50,
    "stateSave": true,
    "language": {
                "search": "Search: ",
                "lengthMenu": "Show _MENU_ lines per page",
                "emptyTable": "No log information available. Have you set your logs folder in the <a href='settings'>settings</a>?",
                "info": "Showing _START_ to _END_ of _TOTAL_ lines",
                "infoEmpty": "Showing 0 to 0 of 0 lines",
                "infoFiltered": "(filtered from _MAX_ total lines)",
                "loadingRecords": '<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "autoWidth": false,
    "scrollX": true,
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
        //$('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0)
    }
}
