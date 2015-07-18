users_list_table_options = {
    "responsive": {
        details: false
    },
    "language": {
        "search": "Search: ",
        "lengthMenu":"Show _MENU_ entries per page",
        "info":"Showing _START_ to _END_ of _TOTAL_ active users",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"",
        "emptyTable": "No data in table",
    },
    "destroy": true,
    "processing": false,
    "serverSide": true,
    "pageLength": 10,
    "order": [ 1, 'asc'],
    "autoWidth": true,
    "stateSave": true,
    "sPaginationType": "bootstrap",
    "columnDefs": [
        {
            "targets": [0],
            "data": "thumb",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === '') {
                    $(td).html('<img src="interfaces/default/images/gravatar-default-80x80.png" alt="User Logo"/>');
                } else {
                    $(td).html('<img src="' + cellData + '" alt="User Logo"/>');
                }
            },
            "orderable": false,
            "className": "users-poster-face",
            "width": "40px"
        },
        {
            "targets": [1],
            "data": "friendly_name",
             "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['user_id'] > 0) {
                        $(td).html('<a href="user?user_id=' + rowData['user_id'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('<a href="user?user=' + rowData['user'] + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html(cellData);
                }
            },
        },
        {
            "targets": [2],
            "data": "started",
            "render": function ( data, type, full ) {
                return moment(data, "X").fromNow();
            }
        },
        {
            "targets": [3],
            "data": "ip_address",
            "searchable": false
        },
        {
            "targets": [4],
            "data": "plays"
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
