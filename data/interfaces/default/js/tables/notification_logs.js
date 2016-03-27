notification_log_table_options = {
    "destroy": true,
    "serverSide": true,
    "processing": false,
    "pagingType": "full_numbers",
    "order": [ 0, 'desc'],
    "pageLength": 50,
    "stateSave": true,
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
            "data": "timestamp",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(moment(cellData, "X").format('YYYY-MM-DD HH:mm:ss'));
                }
            },
            "width": "10%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [1],
            "data": "agent_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "7%",
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [2],
            "data": "notify_action",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "5%"
        },
        {
            "targets": [3],
            "data": "subject_text",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "20%"
        },
        {
            "targets": [4],
            "data": "body_text",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "38%"
        },
        {
            "targets": [5],
            "data": "script_args",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "20%"
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
