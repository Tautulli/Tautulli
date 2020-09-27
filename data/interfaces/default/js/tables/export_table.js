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
            "width": "8%",
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
                if (cellData !== null) {
                    $(td).html('<a href="' + page('info', rowData['rating_key']) + '">' + cellData + '</a>');
                }
            },
            "width": "6%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "filename",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['complete'] === 1 && rowData['exists']) {
                        $(td).html('<a href="view_export?export_id=' + rowData['export_id'] + '" target="_blank">' + cellData + '</a>');
                    } else {
                        $(td).html(cellData);
                    }
                }
            },
            "width": "40%",
            "className": "no-wrap"
        },
        {
            "targets": [4],
            "data": "file_format",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var images = '';
                    if (rowData['include_images']) {
                        images = ' + images';
                    }
                    $(td).html(cellData + images);
                }
            },
            "width": "7%",
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data": "metadata_level",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null) {
                    $(td).html(cellData);
                }
            },
            "width": "6%",
            "className": "no-wrap"
        },
        {
            "targets": [6],
            "data": "media_info_level",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null) {
                    $(td).html(cellData);
                }
            },
            "width": "6%",
            "className": "no-wrap"
        },
        {
            "targets": [7],
            "data": "file_size",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '' && cellData !== null) {
                    $(td).html(humanFileSize(cellData));
                }
            },
            "width": "6%",
            "className": "no-wrap"
        },
        {
            "targets": [8],
            "data": "complete",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === 1 && rowData['exists']) {
                    $(td).html('<button class="btn btn-xs btn-success pull-left" data-id="' + rowData['export_id'] + '"><i class="fa fa-file-download fa-fw"></i> Download</button>');
                } else if (cellData === 0) {
                    $(td).html('<span class="btn btn-xs btn-dark pull-left export-processing" data-id="' + rowData['export_id'] + '" disabled><i class="fa fa-spinner fa-spin fa-fw"></i> Processing</span>');
                } else if (cellData === -1) {
                    $(td).html('<span class="btn btn-xs btn-dark pull-left" data-id="' + rowData['export_id'] + '" disabled><i class="fa fa-exclamation-circle fa-fw"></i> Failed</span>');
                } else {
                    $(td).html('<span class="btn btn-xs btn-dark pull-left" data-id="' + rowData['export_id'] + '" disabled><i class="fa fa-question-circle fa-fw"></i> Not Found</span>');
                }
            },
            "width": "7%",
            "className": "export_download"
        },
        {
            "targets": [9],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData['complete'] !== 0) {
                    $(td).html('<button class="btn btn-xs btn-danger pull-left" data-id="' + rowData['export_id'] + '"><i class="fa fa-trash-o fa-fw"></i> Delete</button>');
                } else {
                    $(td).html('<span class="btn btn-xs btn-danger pull-left" data-id="' + rowData['export_id'] + '" disabled><i class="fa fa-trash-o fa-fw"></i> Delete</span>');
                }
            },
            "width": "7%",
            "className": "export_delete"
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        //$('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();

        if (timer) {
            clearTimeout(timer);
        }
        if ($('.export-processing').length) {
            timer = setTimeout(redrawExportTable.bind(null, false), 2000);
        }
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0)
    },
    "rowCallback": function (row, rowData, rowIndex) {
        if (rowData['complete'] === 0) {
            $(row).addClass('current-activity-row');
        }
    }
};

$('.export_table').on('click', '> tbody > tr > td.export_download > button', function (e) {
    var tr = $(this).closest('tr');
    var row = export_table.row(tr);
    var rowData = row.data();

    e.preventDefault();
    window.location.href = 'download_export?export_id=' + rowData['export_id'];
});

$('.export_table').on('click', '> tbody > tr > td.export_delete > button', function (e) {
    var tr = $(this).closest('tr');
    var row = export_table.row(tr);
    var rowData = row.data();

    var msg = 'Are you sure you want to delete the following export?<br /><br /><strong>' + rowData['filename'] + '</strong>';
    var url = 'delete_export?export_id=' + rowData['export_id'];
    confirmAjaxCall(url, msg, null, null, redrawExportTable);
});

function redrawExportTable(paging) {
    export_table.draw(paging);
}

var timer;