accounts_table_options = {
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "",
        "infoEmpty": "",
        "infoFiltered": "",
        "emptyTable": "No Accounts Defined",
        "loadingRecords": '<div><i class="fa fa-refresh fa-spin"></i> Refreshing Accounts...</div>'
    },
    "rowId": 'id',
    "destroy": true,
    "processing": false,
    "serverSide": false,
    "ordering": true,
    "stateSave": false,
    "stateDuration": 0,
    "paging": false,
    "pagingType": "full_numbers",
    "autoWidth": false,
    "searching": false,
    "columnDefs": [
        {
            "targets": "username",
            "data": "username",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "width": "40px",
            "searchable": true,
            "orderable": true
        },
        {
            "targets": "usertoken",
            "data": "usertoken",
            "createdCell": function (td, cellData, rowData, row, col) {
                var isValid = (rowData['isValid']) ? '' : 'style="color:red" class="toggle-left trigger-tooltip" data-toggle="tooltip" data-placement="top" title="Token is not valid"';
                if (cellData !== null && cellData !== '') {
                    $(td).html('<span ' + isValid + '>' + cellData + '</span>');
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "40px",
            "className": "no-wrap"
        },
        {
            "targets": "isAdmin",
            "data": "isAdmin",
            "createdCell": function (td, cellData, rowData, row, col) {
                var checked = (rowData['isAdmin']) ? 'CHECKED' : '';
                $(td).html(
                  '<input type="checkbox" class="isAdmin" data-token="' + rowData['usertoken'] + '" value="1"' + checked + '>'
                );
            },
            "className": "center",
            "width": "25px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "delete-account",
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html('<span style="color: red;" class="toggle-left trigger-tooltip" data-toggle="tooltip" data-placement="top" title="Delete"><i class="fas fa-2x fa-times"></i></span>');
                }
            },
            "className": "toggle-right pointer delete-account",
            "width": "25px",
            "searchable": false,
            "orderable": true
        },
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        //$('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('body').tooltip({
            selector: '[data-toggle="tooltip"]',
            container: 'body'
        });
    },
    "preDrawCallback": function(settings) {
    },
    "rowCallback": function (row, rowData) {
    }
}
