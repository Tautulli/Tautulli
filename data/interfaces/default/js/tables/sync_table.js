var syncs_to_delete = [];

sync_table_options = {
    "processing": false,
    "serverSide": false,
    "pagingType": "full_numbers",
    "order": [ [ 0, 'desc'], [ 1, 'asc'], [2, 'asc'] ],
    "pageLength": 25,
    "stateSave": true,
    "stateDuration": 0,
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ lines per page",
        "emptyTable": "No synced items",
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
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                $(td).html('<div class="edit-sync-toggles">' +
                    '<button class="btn btn-xs btn-warning delete-sync" data-id="' + rowData['sync_id'] + '" data-toggle="button"><i class="fa fa-trash-o fa-fw"></i> Delete</button>&nbsp' +
                    '</div>');
            },
            "width": "7%",
            "className": "delete-control no-wrap hidden",
            "searchable": false,
            "orderable": false
        },
        {
            "targets": [1],
            "data": "state",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === 'pending') {
                    $(td).html('Pending...');
                } else {
                    $(td).html(cellData.toProperCase());
                }
            },
            "className": "no-wrap"
        },
        {
            "targets": [2],
            "data": "user",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['user_id']) {
                        $(td).html('<a href="' + page('user', rowData['user_id']) + '" title="' + rowData['username'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('<a href="' + page('user', null, rowData['user']) + '" title="' + rowData['username'] + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "sync_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['rating_key'] && !rowData['rating_key'].includes(',')) {
                        $(td).html('<a href="' + page('info', rowData['rating_key']) + '">' + cellData + '</a>');
                    } else {
                        $(td).html(cellData);
                    }
                }
            },
            "className": "datatable-wrap"
        },
        {
            "targets": [4],
            "data": "metadata_type",
            "render": function ( data, type, full ) {
                return data.toProperCase();
            },
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data": "platform",
            "className": "no-wrap"
        },
        {
            "targets": [6],
            "data": "device_name",
            "className": "no-wrap"
        },
        {
            "targets": [7],
            "data": "total_size",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData > 0 ) {
                    megabytes = Math.round((cellData/1024)/1024, 0);
                    $(td).html(megabytes + 'MB');
                } else {
                    $(td).html('0MB');
                }
            },
            "className": "no-wrap"
        },
        {
            "targets": [8],
            "data": "item_count",
            "className": "no-wrap"
        },
        {
            "targets": [9],
            "data": "item_complete_count",
            "className": "no-wrap"
        },
        {
            "targets": [10],
            "data": "item_downloaded_count",
            "className": "no-wrap"
        },
        {
            "targets": [11],
            "data": "item_downloaded_percent_complete",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData['item_count'] > 0 ) {
                    $(td).html('<span class="badge">' + cellData + '%</span>');
                } else {
                    $(td).html('<span class="badge">0%</span>');
                }
            },
            "className": "no-wrap"
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);

        $('#ajaxMsg').fadeOut();

        if ($('#sync-row-edit-mode').hasClass('active')) {
            $('.sync_table .delete-control').each(function () {
                $(this).removeClass('hidden');
            });
        }

    },
    "preDrawCallback": function (settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0)
    },
    "rowCallback": function (row, rowData, rowIndex) {
        if (rowData['state'] === 'pending') {
            $(row).addClass('current-activity-row');
        }
    }
};

$('.sync_table').on('click', 'td.delete-control > .edit-sync-toggles > button.delete-sync', function () {
    var tr = $(this).parents('tr');
    var row = sync_table.row(tr);
    var rowData = row.data();

    var index_delete = syncs_to_delete.findIndex(function (x) {
        return x.client_id === rowData['client_id'] && x.sync_id === rowData['sync_id'];
    });

    if (index_delete === -1) {
        syncs_to_delete.push({ client_id: rowData['client_id'], sync_id: rowData['sync_id'] });
    } else {
        syncs_to_delete.splice(index_delete, 1);
    }

    $(this).toggleClass('btn-warning').toggleClass('btn-danger');
});
