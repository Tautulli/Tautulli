sync_table_options = {
    "processing": false,
    "serverSide": false,
    "pagingType": "bootstrap",
    "order": [ [ 0, 'desc'], [ 1, 'asc'], [2, 'asc'] ],
    "pageLength": 25,
    "stateSave": false,
    "language": {
        "search":"Search: ",
        "lengthMenu":"Show _MENU_ lines per page",
        "emptyTable": "No synced items",
        "info":"Showing _START_ to _END_ of _TOTAL_ lines",
        "infoEmpty":"Showing 0 to 0 of 0 lines",
        "infoFiltered":"(filtered from _MAX_ total lines)",
        "loadingRecords":'<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "columnDefs": [
        {
            "targets": [0],
            "data": "state",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === 'pending') {
                    $(td).addClass('currentlyWatching');
                    $(td).html('Pending...');
                } else {
                    $(td).html(cellData.toProperCase());
                }
            },
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [1],
            "data": "friendly_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['user_id']) {
                        $(td).html('<a href="user?user_id=' + rowData['user_id'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('<a href="user?user=' + rowData['user'] + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap"
        },
        {
            "targets": [2],
            "data": "title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['metadata_type'] !== '') {
                        $(td).html('<a href="info?rating_key=' + rowData['rating_key'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html(cellData);
                    }
                }
            }
        },
        {
            "targets": [3],
            "data": "metadata_type",
            "render": function ( data, type, full ) {
                return data.toProperCase();
            },
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [4],
            "data": "platform",
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [5],
            "data": "device_name",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [6],
            "data": "total_size",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData > 0 ) {
                    megabytes = Math.round((cellData/1024)/1024, 0)
                    $(td).html(megabytes + 'MB');
                } else {
                    $(td).html('0MB');
                }
            },
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [7],
            "data": "item_count",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [8],
            "data": "item_complete_count",
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [9],
            "data": "item_downloaded_count",
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [10],
            "data": "item_downloaded_percent_complete",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData['item_count'] > 0 ) {
                    $(td).html('<span class="badge">' + cellData + '%</span>');
                } else {
                    $(td).html('<span class="badge">0%</span>');
                }
            },
            "className": "no-wrap hidden-sm hidden-xs"
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        $('html,body').scrollTop(0);
    }
}
