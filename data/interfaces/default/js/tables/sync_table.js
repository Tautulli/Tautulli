sync_table_options = {
    "responsive": {
        details: false
    },
    "processing": false,
    "serverSide": false,
    "sPaginationType": "bootstrap",
    "order": [ 0, 'desc'],
    "pageLength": 25,
    "stateSave": true,
    "language": {
                "search":"Search: ",
                "lengthMenu":"Show _MENU_ lines per page",
                "emptyTable": "No synced items",
                "info":"Showing _START_ to _END_ of _TOTAL_ lines",
                "infoEmpty":"Showing 0 to 0 of 0 lines",
                "infoFiltered":"(filtered from _MAX_ total lines)"},
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
            }
        },
        {
            "targets": [1],
            "data": "friendly_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="user?user=' + rowData['username'] + '">' + cellData + '</a>');
                }
            }
        },
        {
            "targets": [2],
            "data": "title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['metadata_type'] !== 'track') {
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
            }
        },
        {
            "targets": [4],
            "data": "device_name"
        },
        {
            "targets": [5],
            "data": "platform"
        },
        {
            "targets": [6],
            "data": "total_size",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData > 0 ) {
                    megabytes = Math.round((cellData/1024)/1024, 0)
                    $(td).html(megabytes + 'MB');
                } else {
                    $(td).html(megabytes + '0MB');
                }
            }
        },
        {
            "targets": [7],
            "data": "item_count"
        },
        {
            "targets": [8],
            "data": "item_complete_count"
        },
        {
            "targets": [9],
            "data": "item_downloaded_count"
        },
        {
            "targets": [10],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData['item_count'] > 0 ) {
                    percent_complete = Math.round((rowData['item_downloaded_count']/rowData['item_count']*100),0);
                    $(td).html('<span class="badge">' + percent_complete + '%</span>');
                } else {
                    $(td).html('<span class="badge">0%</span>');
                }
            }
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        $('html,body').scrollTop(0);
    }
}
