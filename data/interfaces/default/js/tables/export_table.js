var date_format = 'YYYY-MM-DD';
var time_format = 'hh:mm a';

$.ajax({
    url: 'get_date_formats',
    type: 'GET',
    success: function (data) {
        date_format = data.date_format;
        time_format = data.time_format;
    }
});

export_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ library items",
        "infoEmpty": "Showing 0 to 0 of 0 entries",
        "infoFiltered": "<span class='hidden-md hidden-sm hidden-xs'>(filtered from _MAX_ total entries)</span>",
        "emptyTable": "No data in table",
        "loadingRecords": '<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "pagingType": "full_numbers",
    "stateSave": true,
    "stateDuration": 0,
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [0, 'desc'],
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data": "timestamp",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(moment(cellData, "X").format(date_format + ' ' + time_format));
                }
            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [1],
            "data": "media_type_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "7%",
            "className": "no-wrap"
        },
        {
            "targets": [2],
            "data": "rating_key",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "7%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "file_format",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "7%",
            "className": "no-wrap"
        },
        {
            "targets": [4],
            "data": "filename",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "55%",
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data": "complete",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === 1) {
                    $(td).html('<button class="btn btn-xs btn-dark btn-download" data-id="' + rowData['row_id'] + '"><i class="fa fa-file-download fa-fw"></i> Download</button>');
                } else {
                    $(td).html('<button class="btn btn-xs btn-dark" data-id="' + rowData['row_id'] + '" disabled><i class="fa fa-spinner fa-spin fa-fw"></i> Processing</button>');
                }
            },
            "width": "7%"
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
    },
    "rowCallback": function (row, rowData, rowIndex) {
        if (rowData['complete'] !== 1) {
            $(row).addClass('current-activity-row');
        }
    }
};
