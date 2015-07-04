var plex_log_table_options = {
    "destroy": true,
    "responsive": {
        details: false
    },
    "processing": false,
    "serverSide": false,
    "sPaginationType": "bootstrap",
    "order": [ 0, 'desc'],
    "pageLength": 10,
    "stateSave": false,
    "language": {
                "search":"Search: ",
                "lengthMenu":"Show _MENU_ lines per page",
                "emptyTable": "No log information available. Have you set your logs folder in the <a href='config'>settings</a>?",
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
    ]
}
