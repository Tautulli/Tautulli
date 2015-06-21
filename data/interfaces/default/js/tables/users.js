users_list_table_options = {
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
    "order": [ 0, 'asc'],
    "ajax": {
        "url": "get_user_list"
    },
    "bLengthChange": true,
    "bInfo": true,
    "bAutoWidth": true,
    "aaSorting": [[ 0, "asc" ]],
    "bStateSave": true,
    "bSortClasses": true,
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
            "data": "user",
             "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="user?user=' + cellData + '">' + cellData + '</a>');
                } else {
                    $(td).html(cellData);
                }
            },
        },
        {
            "targets": [2],
            "data": "time",
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
        $('#ajaxMsg').html("<div class='msg'><span class='ui-icon ui-icon-check'></span>Fetching rows...</div>");
        $('#ajaxMsg').addClass('success').fadeIn();
    }
}
